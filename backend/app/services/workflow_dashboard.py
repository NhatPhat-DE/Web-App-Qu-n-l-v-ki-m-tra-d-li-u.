"""Read-only workflow summaries, loaded in a fixed number of batch queries.

This is presentation, not admission to completion: finish() still revalidates
under locks. Immutable runs/reconciliation provide identity evidence here.
"""
from collections import defaultdict
from sqlalchemy import select,func
from app.models import (DataIssue,DatasetIdentity,DatasetColumn,QualityRule,QualityRun,
    DatasetVersion,WorkflowReconciliation,IssueObservation,QualityViolation)
from app.services.quality_engine import ENGINE_VERSION


def summaries(c,batches,items,latest_runs):
    if not batches:return {}
    ids=[b['id'] for b in batches];dataset_ids={b['dataset_id'] for b in batches}
    counts={bid:dict(unprocessed_count=0,uncertain_count=0,ignored_count=0) for bid in ids}
    uncertain=defaultdict(list)
    for bid,status,reason,count in c.execute(select(DataIssue.batch_id,DataIssue.status,DataIssue.uncertain_reason,func.count())
            .where(DataIssue.batch_id.in_(ids)).group_by(DataIssue.batch_id,DataIssue.status,DataIssue.uncertain_reason)):
        if status in ('OPEN','IN_PROGRESS','PENDING_RECHECK'):
            counts[bid]['unprocessed_count']+=count
            if reason:
                counts[bid]['uncertain_count']+=count
                uncertain[bid].append(reason)
        elif status=='IGNORED':counts[bid]['ignored_count']+=count
    configs={r['dataset_id']:r for r in c.execute(select(DatasetIdentity).where(DatasetIdentity.dataset_id.in_(dataset_ids),DatasetIdentity.is_current)).mappings()}
    schemas=defaultdict(list)
    for row in c.execute(select(DatasetColumn.dataset_id,DatasetColumn.name,DatasetColumn.position,DatasetColumn.description)
            .where(DatasetColumn.dataset_id.in_(dataset_ids)).order_by(DatasetColumn.position)).mappings():
        schemas[row['dataset_id']].append({k:row[k] for k in ('name','position','description')})
    rules=defaultdict(list)
    for row in c.execute(select(QualityRule.batch_id,QualityRule.id,QualityRule.name,QualityRule.rule_type,QualityRule.columns,QualityRule.config)
            .where(QualityRule.batch_id.in_(ids),QualityRule.is_active).order_by(QualityRule.id)).mappings():
        rules[row['batch_id']].append({k:row[k] for k in ('id','name','rule_type','columns','config')})
    run_ids=[r['id'] for r in latest_runs.values() if r]
    recons={(r['run_id'],r['identity_revision']):r for r in c.execute(select(WorkflowReconciliation).where(WorkflowReconciliation.run_id.in_(run_ids))).mappings()}
    running=dict(c.execute(select(DatasetVersion.batch_id,func.count()).join(QualityRun,QualityRun.dataset_version_id==DatasetVersion.id)
        .where(DatasetVersion.batch_id.in_(ids),QualityRun.status=='running').group_by(DatasetVersion.batch_id)).all())
    covered=dict(c.execute(select(QualityViolation.run_id,func.count(func.distinct(IssueObservation.violation_id)))
        .select_from(IssueObservation).join(DataIssue,DataIssue.id==IssueObservation.issue_id)
        .join(QualityViolation,QualityViolation.id==IssueObservation.violation_id)
        .join(DatasetIdentity,DatasetIdentity.id==DataIssue.identity_config_id)
        .where(QualityViolation.run_id.in_(run_ids),DataIssue.status=='IGNORED',DatasetIdentity.is_current)
        .group_by(QualityViolation.run_id)).all())
    output={};by_id={i['batch_id']:i for i in items}
    for batch in batches:
        bid=batch['id'];item=by_id[bid];config=configs.get(batch['dataset_id']);run=latest_runs.get(bid);problems=[]
        if batch['business_state']!='COMPLETED':
            if not batch['workflow_enabled']:problems.append('WORKFLOW_NOT_ENABLED')
            if not config:problems.append('IDENTITY_NOT_CONFIGURED')
            if not item['current_version']:problems.append('NO_CURRENT_VERSION')
            if running.get(bid):problems.append('RUN_IN_PROGRESS')
            if not run or run['status']!='completed':problems.append('LATEST_RUN_NOT_COMPLETED')
            else:
                if (run['batch_rules_revision']!=batch['rules_revision'] or run['rule_snapshot']!=rules[bid]
                        or run['engine_version']!=ENGINE_VERSION or run['schema_snapshot']!=schemas[batch['dataset_id']]):
                    problems.append('CURRENT_CONFIGURATION_NOT_CHECKED')
                recon=recons.get((run['id'],config['revision'] if config else 0))
                if not recon or not recon['eligible']:
                    problems.append('CURRENT_RECONCILIATION_REQUIRED')
                    if recon:problems.extend(r for r in recon['reasons'] if r!='NO_NEW_VERSION')
                if run['violation_count'] and covered.get(run['id'],0)!=run['violation_count']:problems.append('CURRENT_VIOLATIONS_UNHANDLED')
            if counts[bid]['unprocessed_count']:problems.append('ISSUES_UNPROCESSED_OR_UNCERTAIN')
            problems.extend(uncertain[bid])
        output[bid]={'enabled':batch['workflow_enabled'],**counts[bid],'completion_blockers':list(dict.fromkeys(problems))}
    return output
