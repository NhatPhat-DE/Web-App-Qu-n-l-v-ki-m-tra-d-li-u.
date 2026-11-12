"""NV-02 lifecycle. Callers serialize writes with dataset -> batch locks.

No engine execution, row-number matching across versions, or snapshot rewriting.
"""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, insert, update, func
from app.models import (Dataset, DataBatch, DatasetColumn, DatasetVersion, DatasetRow, QualityRule,
    QualityRun, QualityViolation, DatasetIdentity, WorkflowReconciliation, DataIssue, IssueEvent,
    IssueObservation, ReconciliationItem, BatchEvent, User)
from app.services.quality_rules import rule_connection
from app.services.quality_engine import ENGINE_VERSION, is_missing

STATES = ('OPEN','IN_PROGRESS','PENDING_RECHECK','RESOLVED','IGNORED')


def reject(status, code, message):
    raise HTTPException(status, detail={'code':code,'message':message})


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def steward(actor):
    if not actor or actor['role'] not in ('admin','data_steward'):
        reject(403,'STEWARD_REQUIRED','Chỉ Steward hoặc quản trị viên được thực hiện thao tác này.')


def actor_values(actor):
    return {'actor_id':actor['user_id'] if actor else None,'actor_label':actor['username'] if actor else 'SYSTEM'}


def lock_batch(c, dataset_id, batch_id, require_open=True):
    if c.execute(select(Dataset.id).where(Dataset.id==dataset_id).with_for_update()).first() is None:
        reject(404,'NOT_FOUND','Không tìm thấy bộ dữ liệu.')
    batch=c.execute(select(DataBatch).where(DataBatch.id==batch_id,DataBatch.dataset_id==dataset_id).with_for_update()).mappings().first()
    if not batch:reject(404,'NOT_FOUND','Không tìm thấy đợt dữ liệu.')
    if require_open and batch['business_state']=='COMPLETED':
        reject(409,'BATCH_COMPLETED','Đợt đã hoàn tất. Cần mở lại với lý do trước khi thay đổi.')
    return dict(batch)


def assert_batch_open(c, batch_id):
    batch=c.execute(select(DataBatch).where(DataBatch.id==batch_id).with_for_update()).mappings().one()
    if batch['business_state']=='COMPLETED':reject(409,'BATCH_COMPLETED','Đợt đã hoàn tất. Hãy mở lại trước khi thay đổi.')
    return batch


def identity(c, dataset_id):
    row=c.execute(select(DatasetIdentity).where(DatasetIdentity.dataset_id==dataset_id,DatasetIdentity.is_current)).mappings().first()
    return dict(row) if row else None


def configure_identity(dataset_id, columns, actor):
    steward(actor)
    with rule_connection() as c:
        if not c.execute(select(Dataset.id).where(Dataset.id==dataset_id).with_for_update()).first():reject(404,'NOT_FOUND','Không tìm thấy bộ dữ liệu.')
        batches=c.execute(select(DataBatch).where(DataBatch.dataset_id==dataset_id).order_by(DataBatch.id).with_for_update()).mappings().all()
        if any(b['business_state']=='COMPLETED' for b in batches):reject(409,'COMPLETED_BATCH_IDENTITY_LOCK','Cần mở lại các đợt đã hoàn tất trước khi đổi khóa nhận diện.')
        header=c.execute(select(DatasetColumn.name).where(DatasetColumn.dataset_id==dataset_id)).scalars().all()
        if not columns or len(set(columns))!=len(columns) or any(col not in header for col in columns):
            reject(422,'INVALID_IDENTITY','Chọn một hoặc nhiều cột có thật, không trùng nhau, làm khóa nhận diện.')
        old=identity(c,dataset_id)
        if old and old['columns']==columns:return old
        c.execute(update(DatasetIdentity).where(DatasetIdentity.dataset_id==dataset_id,DatasetIdentity.is_current).values(is_current=False))
        revision=(c.execute(select(func.max(DatasetIdentity.revision)).where(DatasetIdentity.dataset_id==dataset_id)).scalar_one() or 0)+1
        return dict(c.execute(insert(DatasetIdentity).values(dataset_id=dataset_id,revision=revision,columns=columns,actor_id=actor['user_id']).returning(*DatasetIdentity.__table__.columns)).mappings().one())


def record_keys(c, version_id, config, schema):
    if not config:return {},{},'IDENTITY_NOT_CONFIGURED'
    if not schema:return {},{},'SCHEMA_SNAPSHOT_UNAVAILABLE'
    header=[col['name'] for col in schema]
    if any(col not in header for col in config['columns']):return {},{},'IDENTITY_COLUMNS_UNAVAILABLE'
    positions=[header.index(col) for col in config['columns']]
    by_row,by_key={},{}
    for row in c.execute(select(DatasetRow.row_number,DatasetRow.values).where(DatasetRow.version_id==version_id).order_by(DatasetRow.row_number)):
        values=[row.values[p] for p in positions]
        if any(is_missing(value) for value in values):return {},{},'IDENTITY_MISSING'
        key=digest(values)
        if key in by_key:return {},{},'IDENTITY_DUPLICATE'
        by_row[row.row_number]=(key,values);by_key[key]=values
    if not by_row:return {},{},'NO_RECORDS'
    return by_row,by_key,None


def context_key(run):
    return digest({'rules':run['rule_snapshot'],'revision':run['batch_rules_revision'],
        'engine':run['engine_version'],'schema':run['schema_snapshot']})


def issue_event(c, issue_id, action, old, new, note, actor=None, run_id=None):
    c.execute(insert(IssueEvent).values(issue_id=issue_id,action=action,from_status=old,to_status=new,note=note,run_id=run_id,**actor_values(actor)))


def batch_event(c,batch,action,state,note,actor,evidence=None):
    c.execute(insert(BatchEvent).values(batch_id=batch['id'],action=action,from_state=batch['business_state'],to_state=state,note=note,evidence=evidence or {},**actor_values(actor)))


def sync_run(c, run_id, actor=None):
    """Runs inside result transaction or explicit registration under the same locks."""
    run=dict(c.execute(select(QualityRun).where(QualityRun.id==run_id)).mappings().one())
    version=dict(c.execute(select(DatasetVersion).where(DatasetVersion.id==run['dataset_version_id'])).mappings().one())
    batch=lock_batch(c,version['dataset_id'],version['batch_id'])
    if not batch['workflow_enabled']:return None
    if run['status']!='completed':reject(409,'RUN_NOT_COMPLETED','Chỉ đối soát kết quả kiểm tra đã hoàn tất thành công.')
    config=identity(c,version['dataset_id']);revision=config['revision'] if config else 0
    existing=c.execute(select(WorkflowReconciliation.id).where(WorkflowReconciliation.run_id==run_id,WorkflowReconciliation.identity_revision==revision)).scalar_one_or_none()
    if existing:return existing
    highest=c.execute(select(func.max(DatasetVersion.version_number)).select_from(WorkflowReconciliation).join(QualityRun,QualityRun.id==WorkflowReconciliation.run_id).join(DatasetVersion,DatasetVersion.id==QualityRun.dataset_version_id).where(WorkflowReconciliation.batch_id==batch['id'])).scalar_one()
    historical=highest is not None and highest>version['version_number']
    same_version=highest==version['version_number']
    row_keys,key_values,key_error=record_keys(c,version['id'],config,run['schema_snapshot'])
    reasons=[key_error] if key_error else []
    if historical:reasons.append('HISTORICAL_READ_ONLY')
    elif same_version:reasons.append('NO_NEW_VERSION')
    recon_id=c.execute(insert(WorkflowReconciliation).values(batch_id=batch['id'],run_id=run_id,
        identity_config_id=config['id'] if config else None,identity_revision=revision,identity_columns=config['columns'] if config else [],
        eligible=not key_error and not historical,result='HISTORICAL' if historical else 'SAME_VERSION' if same_version else 'BASELINE' if highest is None else 'RECONCILED',reasons=reasons,actor_id=actor['user_id'] if actor else None).returning(WorkflowReconciliation.id)).scalar_one()
    issues={row['issue_key']:dict(row) for row in c.execute(select(DataIssue).where(DataIssue.batch_id==batch['id']).with_for_update()).mappings()}
    by_id={item['id']:item for item in issues.values()}
    observed_here={}
    for observed in c.execute(select(IssueObservation.issue_id,QualityViolation.row_number).join(QualityViolation,QualityViolation.id==IssueObservation.violation_id).join(QualityRun,QualityRun.id==QualityViolation.run_id).where(QualityRun.dataset_version_id==version['id'])):
        item=by_id.get(observed.issue_id)
        if item:
            local_record=item['record_key'] or ('row',observed.row_number)
            observed_here[(item['identity_config_id'],local_record,item['rule_id_snapshot'],tuple(item['rule_snapshot']['columns']))]=item
    rules={rule['id']:rule for rule in run['rule_snapshot']};ctx=context_key(run);seen=set();outcomes={}
    for violation in c.execute(select(QualityViolation).where(QualityViolation.run_id==run_id).order_by(QualityViolation.id)).mappings():
        record=row_keys.get(violation['row_number'])
        # A row number is only ever used WITH a version ID for unbound same-file dedup.
        key=digest([revision,ctx,record[0] if record else ['unbound',version['id'],violation['row_number']],violation['rule_id_snapshot']])
        issue=issues.get(key);created=False
        # A config edit on the SAME immutable file must not duplicate its issues.
        # Retain original context, and flag unknown instead of claiming a repair.
        if not issue and same_version:
            issue=observed_here.get((config['id'] if config else None,record[0] if record else ('row',violation['row_number']),violation['rule_id_snapshot'],tuple(violation['columns'])))
        if not issue:
            if historical:continue
            issue=dict(c.execute(insert(DataIssue).values(dataset_id=version['dataset_id'],batch_id=batch['id'],issue_key=key,
                identity_config_id=config['id'] if config else None,record_key=record[0] if record else None,key_values=record[1] if record else None,
                context_key=ctx,rule_id_snapshot=violation['rule_id_snapshot'],rule_snapshot=rules[violation['rule_id_snapshot']],
                origin_run_id=run_id,origin_version_id=version['id'],last_run_id=run_id,uncertain_reason=key_error).returning(*DataIssue.__table__.columns)).mappings().one())
            issues[key]=issue;created=True
            issue_event(c,issue['id'],'DETECTED',None,'OPEN',key_error or 'Phát hiện từ kết quả kiểm tra.',actor,run_id)
        if not c.execute(select(IssueObservation.id).where(IssueObservation.issue_id==issue['id'],IssueObservation.violation_id==violation['id'])).first():
            c.execute(insert(IssueObservation).values(issue_id=issue['id'],violation_id=violation['id'],reconciliation_id=recon_id))
        seen.add(issue['id'])
        if historical:continue
        old=issue['status'];new=old
        if not created and old!='IGNORED' and (not same_version or old=='RESOLVED'):new='OPEN'
        uncertain=key_error or ('RULE_ENGINE_OR_SCHEMA_CHANGED' if issue['context_key']!=ctx else 'NO_NEW_VERSION' if same_version and old=='PENDING_RECHECK' else None)
        c.execute(update(DataIssue).where(DataIssue.id==issue['id']).values(status=new,last_run_id=run_id,uncertain_reason=uncertain,
            status_revision=DataIssue.status_revision+1,updated_at=func.now()))
        if not created:issue_event(c,issue['id'],'OBSERVED',old,new,uncertain or 'Vi phạm vẫn có trong kết quả kiểm tra.',actor,run_id)
        outcomes[issue['id']]=('UNKNOWN' if uncertain else 'NEW' if created else 'PERSISTING',uncertain,issue['origin_version_id'])
    if not historical:
        for issue in issues.values():
            if issue['id'] in seen or issue['status']=='RESOLVED':continue
            reason=key_error
            if not reason and (not issue['record_key'] or issue['identity_config_id']!=(config['id'] if config else None)):reason='IDENTITY_CHANGED_OR_UNBOUND'
            if not reason and issue['context_key']!=ctx:reason='RULE_ENGINE_OR_SCHEMA_CHANGED'
            origin=c.execute(select(DatasetVersion).where(DatasetVersion.id==issue['origin_version_id'])).mappings().one()
            if not reason and origin['version_number']>=version['version_number']:reason='NO_NEW_VERSION'
            if not reason:
                source_run=c.execute(select(QualityRun).where(QualityRun.id==issue['origin_run_id'])).mappings().one()
                _,_,reason=record_keys(c,origin['id'],config,source_run['schema_snapshot'])
            if not reason and issue['record_key'] not in key_values:reason='RECORD_MISSING_OR_KEY_CHANGED'
            new=issue['status'] if reason else 'RESOLVED'
            c.execute(update(DataIssue).where(DataIssue.id==issue['id']).values(status=new,uncertain_reason=reason,status_revision=DataIssue.status_revision+1,updated_at=func.now()))
            issue_event(c,issue['id'],'UNCERTAIN' if reason else 'RECHECK_RESOLVED',issue['status'],new,reason or 'Phiên bản mới nhận diện cùng bản ghi và không còn vi phạm theo cùng cấu hình.',actor,run_id)
            outcomes[issue['id']]=('UNKNOWN' if reason else 'RESOLVED',reason,issue['origin_version_id'])
        if batch['business_state']=='RECEIVING':c.execute(update(DataBatch).where(DataBatch.id==batch['id']).values(business_state='PROCESSING'))
    for issue_id,(outcome,reason,source) in outcomes.items():
        c.execute(insert(ReconciliationItem).values(reconciliation_id=recon_id,issue_id=issue_id,outcome=outcome,reason=reason,source_version_id=source))
    if any(outcome[0]=='UNKNOWN' for outcome in outcomes.values()) and not historical:
        c.execute(update(WorkflowReconciliation).where(WorkflowReconciliation.id==recon_id).values(result='PARTIAL'))
    return recon_id


def activate(dataset_id,batch_id,actor):
    steward(actor)
    with rule_connection() as c:
        batch=lock_batch(c,dataset_id,batch_id)
        if batch['workflow_enabled']:return {'enabled':True}
        if not identity(c,dataset_id):reject(422,'IDENTITY_REQUIRED','Cấu hình khóa nhận diện trước khi bật xử lý lỗi.')
        c.execute(update(DataBatch).where(DataBatch.id==batch_id).values(workflow_enabled=True))
        batch_event(c,batch,'INITIALIZED','PROCESSING','Đăng ký rõ ràng các kết quả cũ theo thứ tự phiên bản.',actor)
        runs=c.execute(select(QualityRun.id).join(DatasetVersion,DatasetVersion.id==QualityRun.dataset_version_id).where(DatasetVersion.batch_id==batch_id,QualityRun.status=='completed').order_by(DatasetVersion.version_number,QualityRun.id)).scalars().all()
        for run_id in runs:sync_run(c,run_id,actor)
        c.execute(update(DataBatch).where(DataBatch.id==batch_id).values(business_state='PROCESSING'))
        return {'enabled':True,'registered_runs':len(runs)}


def reconcile(dataset_id,batch_id,run_id,actor):
    with rule_connection() as c:
        batch=lock_batch(c,dataset_id,batch_id)
        if not batch['workflow_enabled']:reject(409,'WORKFLOW_NOT_ENABLED','Bật quản lý xử lý lỗi trước khi đối soát.')
        run=c.execute(select(QualityRun.id).join(DatasetVersion,DatasetVersion.id==QualityRun.dataset_version_id).where(QualityRun.id==run_id,DatasetVersion.batch_id==batch_id)).first()
        if not run:reject(404,'NOT_FOUND','Lần kiểm tra không thuộc đợt này.')
        return {'reconciliation_id':sync_run(c,run_id,actor)}


def change_issue(dataset_id,batch_id,issue_id,status,note,expected_revision,actor):
    if status=='RESOLVED':reject(403,'SYSTEM_RESOLUTION_REQUIRED','RESOLVED chỉ được xác nhận bằng đối soát hợp lệ; không được đóng lỗi trực tiếp.')
    if status not in STATES:reject(422,'INVALID_STATUS','Trạng thái xử lý không hợp lệ.')
    if status=='IGNORED':
        steward(actor)
        if not note.strip():reject(422,'IGNORE_NOTE_REQUIRED','Bỏ qua cần ghi chú lý do và sẽ được ghi nhận người/thời điểm.')
    with rule_connection() as c:
        lock_batch(c,dataset_id,batch_id)
        item=c.execute(select(DataIssue).where(DataIssue.id==issue_id,DataIssue.batch_id==batch_id).with_for_update()).mappings().first()
        if not item:reject(404,'NOT_FOUND','Không tìm thấy issue trong đợt.')
        if expected_revision!=item['status_revision']:reject(409,'ISSUE_CHANGED','Issue đã thay đổi. Tải lại trước khi cập nhật.')
        allowed={'OPEN':{'IN_PROGRESS','IGNORED'},'IN_PROGRESS':{'OPEN','PENDING_RECHECK','IGNORED'},'PENDING_RECHECK':{'IN_PROGRESS','IGNORED'},'IGNORED':{'OPEN'},'RESOLVED':set()}
        if status not in allowed[item['status']]:reject(409,'INVALID_TRANSITION','Chuyển trạng thái này không hợp lệ.')
        if item['status']=='IGNORED':
            steward(actor)
            if not note.strip():reject(422,'NOTE_REQUIRED','Cần lý do khi mở lại issue đã bỏ qua.')
        c.execute(update(DataIssue).where(DataIssue.id==issue_id).values(status=status,ignored_note=note.strip() if status=='IGNORED' else item['ignored_note'],status_revision=DataIssue.status_revision+1,updated_at=func.now()))
        issue_event(c,issue_id,'STATUS_CHANGED',item['status'],status,note.strip(),actor)
        return {'id':issue_id,'status':status}


def completion_checks(c,batch):
    problems=[];current=c.execute(select(DatasetVersion).where(DatasetVersion.batch_id==batch['id'],DatasetVersion.is_current)).mappings().first()
    config=identity(c,batch['dataset_id'])
    if not batch['workflow_enabled']:problems.append('WORKFLOW_NOT_ENABLED')
    if not config:problems.append('IDENTITY_NOT_CONFIGURED')
    if not current:problems.append('NO_CURRENT_VERSION')
    running=c.execute(select(func.count()).select_from(QualityRun).join(DatasetVersion,DatasetVersion.id==QualityRun.dataset_version_id).where(DatasetVersion.batch_id==batch['id'],QualityRun.status=='running')).scalar_one()
    if running:problems.append('RUN_IN_PROGRESS')
    run=c.execute(select(QualityRun).where(QualityRun.dataset_version_id==current['id']).order_by(QualityRun.id.desc()).limit(1)).mappings().first() if current else None
    if not run or run['status']!='completed':problems.append('LATEST_RUN_NOT_COMPLETED')
    recon=None
    if run and run['status']=='completed':
        rules=[dict(r) for r in c.execute(select(QualityRule.id,QualityRule.name,QualityRule.rule_type,QualityRule.columns,QualityRule.config).where(QualityRule.batch_id==batch['id'],QualityRule.is_active).order_by(QualityRule.id)).mappings()]
        schema=[dict(r) for r in c.execute(select(DatasetColumn.name,DatasetColumn.position,DatasetColumn.description).where(DatasetColumn.dataset_id==batch['dataset_id']).order_by(DatasetColumn.position)).mappings()]
        if run['batch_rules_revision']!=batch['rules_revision'] or run['rule_snapshot']!=rules or run['engine_version']!=ENGINE_VERSION or run['schema_snapshot']!=schema:problems.append('CURRENT_CONFIGURATION_NOT_CHECKED')
        _,_,key_error=record_keys(c,current['id'],config,run['schema_snapshot'])
        if key_error:problems.append(key_error)
        recon=c.execute(select(WorkflowReconciliation).where(WorkflowReconciliation.run_id==run['id'],WorkflowReconciliation.identity_revision==config['revision'] if config else WorkflowReconciliation.identity_revision==0)).mappings().first()
        if not recon or not recon['eligible']:problems.append('CURRENT_RECONCILIATION_REQUIRED')
    unresolved=c.execute(select(func.count()).select_from(DataIssue).where(DataIssue.batch_id==batch['id'],DataIssue.status.not_in(['RESOLVED','IGNORED']))).scalar_one()
    if unresolved:problems.append('ISSUES_UNPROCESSED_OR_UNCERTAIN')
    ignored=c.execute(select(DataIssue.id,DataIssue.ignored_note).where(DataIssue.batch_id==batch['id'],DataIssue.status=='IGNORED')).mappings().all()
    if run and run['status']=='completed' and run['violation_count']:
        covered=c.execute(select(func.count(func.distinct(IssueObservation.violation_id))).join(DataIssue,DataIssue.id==IssueObservation.issue_id).join(QualityViolation,QualityViolation.id==IssueObservation.violation_id).where(QualityViolation.run_id==run['id'],DataIssue.status=='IGNORED',DataIssue.identity_config_id==config['id'] if config else DataIssue.identity_config_id.is_(None))).scalar_one()
        if covered!=run['violation_count']:problems.append('CURRENT_VIOLATIONS_UNHANDLED')
    return {'can_complete':not problems,'reasons':list(dict.fromkeys(problems)),'ignored':list(map(dict,ignored)),
        'run_id':run['id'] if run else None,'version_id':current['id'] if current else None,'reconciliation_id':recon['id'] if recon else None}


def finish(dataset_id,batch_id,note,accept_ignored,actor):
    steward(actor)
    with rule_connection() as c:
        batch=lock_batch(c,dataset_id,batch_id)
        checks=completion_checks(c,batch)
        if not checks['can_complete']:reject(409,'COMPLETION_BLOCKED','Chưa đủ điều kiện hoàn tất: '+', '.join(checks['reasons']))
        if checks['ignored'] and (not accept_ignored or not note.strip()):reject(422,'IGNORED_CONFIRMATION_REQUIRED','Cần ghi chú và xác nhận rõ các ngoại lệ IGNORED.')
        c.execute(update(DataBatch).where(DataBatch.id==batch_id).values(business_state='COMPLETED',updated_at=func.now()))
        batch_event(c,batch,'COMPLETED','COMPLETED',note.strip(),actor,checks)
        return {'business_state':'COMPLETED','evidence':checks}


def reopen(dataset_id,batch_id,note,actor):
    steward(actor)
    if not note.strip():reject(422,'REOPEN_REASON_REQUIRED','Mở lại đợt cần ghi rõ lý do.')
    with rule_connection() as c:
        batch=lock_batch(c,dataset_id,batch_id,False)
        if batch['business_state']!='COMPLETED':reject(409,'BATCH_NOT_COMPLETED','Chỉ mở lại đợt đã hoàn tất.')
        c.execute(update(DataBatch).where(DataBatch.id==batch_id).values(business_state='PROCESSING',updated_at=func.now()))
        batch_event(c,batch,'REOPENED','PROCESSING',note.strip(),actor)
        return {'business_state':'PROCESSING'}


def state(dataset_id,batch_id):
    with rule_connection() as c:
        batch=c.execute(select(DataBatch).where(DataBatch.id==batch_id,DataBatch.dataset_id==dataset_id)).mappings().first()
        if not batch:reject(404,'NOT_FOUND','Không tìm thấy đợt.')
        counts={status:0 for status in STATES}
        counts.update(dict(c.execute(select(DataIssue.status,func.count()).where(DataIssue.batch_id==batch_id).group_by(DataIssue.status)).all()))
        recons=[]
        for recon in c.execute(select(WorkflowReconciliation).where(WorkflowReconciliation.batch_id==batch_id).order_by(WorkflowReconciliation.id.desc()).limit(20)).mappings():
            value=dict(recon);items=[dict(r) for r in c.execute(select(ReconciliationItem).where(ReconciliationItem.reconciliation_id==recon['id'])).mappings()]
            value['counts']={outcome:sum(i['outcome']==outcome for i in items) for outcome in ('NEW','PERSISTING','RESOLVED','UNKNOWN')};value['items']=items;recons.append(value)
        return {'batch_id':batch_id,'business_state':batch['business_state'],'enabled':batch['workflow_enabled'],'identity':identity(c,dataset_id),'counts':counts,'reconciliations':recons,
            'completion':completion_checks(c,batch),'events':[dict(e) for e in c.execute(select(BatchEvent).where(BatchEvent.batch_id==batch_id).order_by(BatchEvent.id.desc())).mappings()]}


def issue_list(dataset_id,batch_id,status=None,page=1):
    with rule_connection() as c:
        if not c.execute(select(DataBatch.id).where(DataBatch.id==batch_id,DataBatch.dataset_id==dataset_id)).first():reject(404,'NOT_FOUND','Không tìm thấy đợt.')
        conditions=[DataIssue.batch_id==batch_id]
        if status:
            if status not in STATES:reject(422,'INVALID_STATUS','Trạng thái không hợp lệ.')
            conditions.append(DataIssue.status==status)
        total=c.execute(select(func.count()).select_from(DataIssue).where(*conditions)).scalar_one()
        rows=c.execute(select(DataIssue).where(*conditions).order_by(DataIssue.id).offset((page-1)*20).limit(20)).mappings().all()
        return {'items':list(map(dict,rows)),'total':total,'page':page,'page_size':20}


def issue_detail(dataset_id,batch_id,issue_id):
    with rule_connection() as c:
        item=c.execute(select(DataIssue).where(DataIssue.id==issue_id,DataIssue.dataset_id==dataset_id,DataIssue.batch_id==batch_id)).mappings().first()
        if not item:reject(404,'NOT_FOUND','Không tìm thấy issue.')
        return {'issue':dict(item),'business_state':c.execute(select(DataBatch.business_state).where(DataBatch.id==batch_id)).scalar_one(),'events':[dict(e) for e in c.execute(select(IssueEvent).where(IssueEvent.issue_id==issue_id).order_by(IssueEvent.id)).mappings()],
            'observations':[dict(e) for e in c.execute(select(IssueObservation,QualityViolation.run_id,QualityViolation.row_number).join(QualityViolation,QualityViolation.id==IssueObservation.violation_id).where(IssueObservation.issue_id==issue_id)).mappings()]}


def violation_links(dataset_id,run_id):
    with rule_connection() as c:
        if not c.execute(select(QualityRun.id).join(DatasetVersion,DatasetVersion.id==QualityRun.dataset_version_id).where(QualityRun.id==run_id,DatasetVersion.dataset_id==dataset_id)).first():reject(404,'NOT_FOUND','Không tìm thấy lần chạy.')
        return [dict(r) for r in c.execute(select(IssueObservation.violation_id,QualityViolation.row_number,DataIssue.id.label('issue_id'),DataIssue.batch_id,DataIssue.status,DataIssue.identity_config_id).join(DataIssue,DataIssue.id==IssueObservation.issue_id).join(QualityViolation,QualityViolation.id==IssueObservation.violation_id).where(QualityViolation.run_id==run_id)).mappings()]
