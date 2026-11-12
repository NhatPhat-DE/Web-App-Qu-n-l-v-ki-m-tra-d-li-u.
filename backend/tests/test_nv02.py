"""NV-02 real PostgreSQL acceptance; never writes the application database."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient as RawClient
from sqlalchemy import select, func
from authenticated_client import TestClient
from test_dataset_import import isolated_database
from app.main import app
from app.models import QualityRun, QualityViolation, DataIssue, IssueEvent, WorkflowReconciliation, DatasetIdentity, DataBatch
from app.services import issue_workflow as work, quality_execution, dataset_import, quality_rules
from app.services.csv_reader import parse_csv

RAW=b'id,part,amount,name\nA,X,-1,\nB,X,5,Bee\nC,X,20,Cee\n'
V2=b'id,part,amount,name\nC,X,8,Cee\nA,X,2,\nB,X,-2,Bee\n'
CLEAN=b'id,part,amount,name\nB,X,3,Bee\nC,X,8,Cee\nA,X,2,Able\n'


def post(c,url,**kwargs):
    if url.endswith('/batches'):
        from src01_fixtures import batch_payload
        kwargs['json']=batch_payload(c,kwargs['json'])
    response=c.post(url,**kwargs)
    assert response.status_code in (200,201),response.text
    return response.json()


def seed(c,content=RAW,keys=None):
    ds=post(c,'/api/datasets',json={'name':'NV-02 QA riêng'})['id']
    batch=post(c,f'/api/datasets/{ds}/batches',json={'name':'NV-02 xử lý lỗi','copy_template_rules':False})['id']
    base=f'/api/datasets/{ds}/batches/{batch}'
    version=post(c,base+'/versions/import',files={'file':('v1.csv',content)})['version_id']
    rules=[]
    for body in [dict(name='Điểm 0–10',rule_type='numeric_range',columns=['amount'],config={'min':'0','max':'10'}),dict(name='Tên bắt buộc',rule_type='required',columns=['name'],config={})]:
        rules.append(post(c,base+'/rules',json={**body,'is_active':True}))
    response=c.put(f'/api/datasets/{ds}/identity',json={'columns':keys or ['id','part']});assert response.status_code==200,response.text
    post(c,base+'/workflow/activate',json={'confirm':True})
    return ds,batch,base,version,rules


def run(c,ds,version):return post(c,f'/api/datasets/{ds}/versions/{version}/runs')
def issues(c,base):return c.get(base+'/workflow/issues').json()['items']
def state(c,base):return c.get(base+'/workflow').json()
def upload(c,base,content):return post(c,base+'/versions/import',files={'file':('new.csv',content)})['version_id']
def change(c,base,item,status,note=''):
    return c.patch(base+f'/workflow/issues/{item["id"]}',json={'status':status,'note':note,'expected_revision':item['status_revision']})


def test_lifecycle_reorder_rechecks_failure_and_completion(isolated_database,monkeypatch):
    with TestClient(app) as c:
        ds,batch,base,v1,rules=seed(c)
        r1=run(c,ds,v1);assert (r1['error_row_count'],r1['violation_count'])==(2,3)
        original=c.get(f'/api/datasets/{ds}/runs/{r1["run_id"]}').json()
        first=issues(c,base);assert len(first)==3 and all(i['status']=='OPEN' for i in first)
        for item in first:
            assert change(c,base,item,'IN_PROGRESS').status_code==200
            current=next(i for i in issues(c,base) if i['id']==item['id'])
            assert change(c,base,current,'PENDING_RECHECK','Đã gửi bản sửa').status_code==200
        v2=upload(c,base,V2);r2=run(c,ds,v2)
        counts=state(c,base)['counts'];assert counts['RESOLVED']==2 and counts['OPEN']==2
        report=state(c,base)['reconciliations'][0]
        assert report['counts']=={'NEW':1,'PERSISTING':1,'RESOLVED':2,'UNKNOWN':0}
        assert report['identity_columns']==['id','part']
        # Same-file rerun retains pending status, and never duplicates an issue.
        pending=next(i for i in issues(c,base) if i['status']=='OPEN')
        assert change(c,base,pending,'IN_PROGRESS').status_code==200
        pending=next(i for i in issues(c,base) if i['id']==pending['id'])
        assert change(c,base,pending,'PENDING_RECHECK').status_code==200
        run(c,ds,v2);assert len(issues(c,base))==4
        assert next(i for i in issues(c,base) if i['id']==pending['id'])['status']=='PENDING_RECHECK'
        before=issues(c,base)
        saved=quality_execution.check_quality
        monkeypatch.setattr(quality_execution,'check_quality',lambda *a,**k:(_ for _ in ()).throw(ValueError('injected engine failure')))
        assert c.post(f'/api/datasets/{ds}/versions/{v2}/runs').status_code==500
        assert issues(c,base)==before
        assert c.post(base+'/workflow/complete',json={'confirm':True}).status_code==409

        monkeypatch.setattr(quality_execution,'check_quality',saved)
        v3=upload(c,base,CLEAN);r3=run(c,ds,v3);assert r3['violation_count']==0
        assert state(c,base)['counts']['RESOLVED']==4
        completed=post(c,base+'/workflow/complete',json={'confirm':True})
        assert completed['business_state']=='COMPLETED'
        assert c.post(base+'/versions/import',files={'file':('blocked.csv',CLEAN)}).status_code==409
        assert c.patch(base+f'/rules/{rules[0]["id"]}',json={'name':'not allowed'}).status_code==409
        assert c.patch(base,json={'name':'not allowed'}).status_code==409
        assert c.post(f'/api/datasets/{ds}/versions/{v3}/runs').status_code==409
        assert c.put(f'/api/datasets/{ds}/identity',json={'columns':['id']}).status_code==409
        assert c.post(base+'/workflow/reopen',json={'confirm':True}).status_code==422
        post(c,base+'/workflow/reopen',json={'confirm':True,'note':'Nhận bổ sung kỳ mới'})
        assert upload(c,base,CLEAN)>v3
        after=c.get(f'/api/datasets/{ds}/runs/{r1["run_id"]}').json()
        for field in ['rule_snapshot','schema_snapshot','total_rows','error_row_count','violation_count','error_row_rate']:
            assert after[field]==original[field]
        detail=c.get(base+f'/workflow/issues/{first[0]["id"]}').json()
        assert any(e['action']=='STATUS_CHANGED' and e['actor_id'] for e in detail['events'])
        assert any(e['action']=='RECHECK_RESOLVED' and e['run_id'] for e in detail['events'])
        assert c.get(f'/api/datasets/{ds}/runs/{r1["run_id"]}/issue-links').json()


def test_same_run_idempotency_and_key_zero(isolated_database):
    with TestClient(app) as c:
        ds,batch,base,v1,_=seed(c,RAW.replace(b'A,X',b'0,X'))
        r1=run(c,ds,v1);initial=issues(c,base)
        assert any(i['key_values']==['0','X'] for i in initial)
        before=state(c,base)['reconciliations']
        post(c,base+'/workflow/reconcile',json={'run_id':r1['run_id']})
        assert state(c,base)['reconciliations']==before and issues(c,base)==initial
        run(c,ds,upload(c,base,CLEAN.replace(b'A,X',b'0,X')))
        assert all(i['status']=='RESOLVED' for i in issues(c,base))


def test_same_file_config_edit_does_not_duplicate_or_resolve(isolated_database):
    with TestClient(app) as c:
        ds,batch,base,v1,rules=seed(c);run(c,ds,v1)
        ids={i['id'] for i in issues(c,base)}
        assert c.patch(base+f'/rules/{rules[0]["id"]}',json={'name':'Tên cấu hình mới'}).status_code==200
        run(c,ds,v1);run(c,ds,v1)
        assert {i['id'] for i in issues(c,base)}==ids
        assert all(i['status']!='RESOLVED' and i['uncertain_reason']=='RULE_ENGINE_OR_SCHEMA_CHANGED' for i in issues(c,base))


@pytest.mark.parametrize('bad,reason',[
    (b'id,part,amount,name\n,X,2,Able\nB,X,3,Bee\nC,X,8,Cee\n','IDENTITY_MISSING'),
    (b'id,part,amount,name\nA,X,2,Able\nA,X,3,Bee\nC,X,8,Cee\n','IDENTITY_DUPLICATE'),
    (b'id,part,amount,name\nB,X,3,Bee\nC,X,8,Cee\n','RECORD_MISSING_OR_KEY_CHANGED'),
    (b'id,part,amount,name\nZ,X,2,Able\nB,X,3,Bee\nC,X,8,Cee\n','RECORD_MISSING_OR_KEY_CHANGED'),
])
def test_invalid_or_disappeared_identity_never_resolves(isolated_database,bad,reason):
    with TestClient(app) as c:
        ds,batch,base,v1,_=seed(c);run(c,ds,v1)
        a_ids={i['id'] for i in issues(c,base) if i['key_values']==['A','X']}
        run(c,ds,upload(c,base,bad))
        a=[i for i in issues(c,base) if i['id'] in a_ids]
        assert all(i['status']!='RESOLVED' and i['uncertain_reason']==reason for i in a)
        assert state(c,base)['reconciliations'][0]['counts']['UNKNOWN']>=2
        assert c.post(base+'/workflow/complete',json={'confirm':True}).status_code==409


def test_identity_and_rule_changes_preserve_evidence(isolated_database):
    with TestClient(app) as c:
        ds,batch,base,v1,rules=seed(c);r1=run(c,ds,v1)
        old=issues(c,base);old_report=state(c,base)['reconciliations'][0]
        assert c.patch(base+f'/rules/{rules[0]["id"]}',json={'is_active':False}).status_code==200
        run(c,ds,upload(c,base,CLEAN))
        assert all(next(i for i in issues(c,base) if i['id']==item['id'])['status']!='RESOLVED' for item in old)
        assert c.put(f'/api/datasets/{ds}/identity',json={'columns':['id']}).status_code==200
        post(c,base+'/workflow/reconcile',json={'run_id':r1['run_id']})
        history=state(c,base)['reconciliations']
        assert next(r for r in history if r['id']==old_report['id'])['identity_columns']==['id','part']
        assert c.post(base+'/workflow/complete',json={'confirm':True}).status_code==409


def test_unbound_old_rows_never_auto_acquire_identity(isolated_database):
    with TestClient(app) as c:
        ds,batch,base,v1,_=seed(c,RAW.replace(b'B,X,5',b'A,X,5'));run(c,ds,v1)
        initial=issues(c,base);assert all(i['record_key'] is None for i in initial)
        run(c,ds,upload(c,base,CLEAN))
        assert all(next(i for i in issues(c,base) if i['id']==old['id'])['record_key'] is None for old in initial)
        assert all(next(i for i in issues(c,base) if i['id']==old['id'])['status']!='RESOLVED' for old in initial)


def test_roles_transitions_ignore_and_exception_completion(isolated_database):
    with TestClient(app) as c:
        ds,batch,base,v1,_=seed(c);r1=run(c,ds,v1);first=issues(c,base)[0]
        assert change(c,base,first,'RESOLVED').status_code==403
        assert change(c,base,first,'PENDING_RECHECK').status_code==409
        assert change(c,base,first,'IGNORED').status_code==422
        post(c,'/api/admin/users',json={'username':'nv02_owner','password':'temporary-test-owner-password','role':'data_owner'})
        with RawClient(app) as owner:
            origin={'Origin':'http://127.0.0.1:5173'}
            csrf=owner.get('/api/auth/me').json()['csrf_token']
            logged=owner.post('/api/auth/login',json={'username':'nv02_owner','password':'temporary-test-owner-password'},headers={**origin,'X-CSRF-Token':csrf})
            assert logged.status_code==200,logged.text
            owner.headers.update({**origin,'X-CSRF-Token':logged.json()['csrf_token']})
            assert change(owner,base,first,'RESOLVED').status_code==403
            assert change(owner,base,first,'IGNORED','Lý do').status_code==403
            assert change(owner,base,first,'IN_PROGRESS','Đang sửa').status_code==200
            assert owner.post(base+'/workflow/complete',json={'confirm':True}).status_code==403
        post(c,'/api/admin/users',json={'username':'nv02_steward','password':'temporary-test-steward-password','role':'data_steward'})
        with RawClient(app) as steward_client:
            csrf=steward_client.get('/api/auth/me').json()['csrf_token']
            logged=steward_client.post('/api/auth/login',json={'username':'nv02_steward','password':'temporary-test-steward-password'},headers={'Origin':'http://127.0.0.1:5173','X-CSRF-Token':csrf})
            assert logged.status_code==200
            steward_client.headers.update({'Origin':'http://127.0.0.1:5173','X-CSRF-Token':logged.json()['csrf_token']})
            assert change(steward_client,base,first,'RESOLVED').status_code==403
            assert change(steward_client,base,first,'IGNORED').status_code==422
        for item in issues(c,base):assert change(c,base,item,'IGNORED','Ngoại lệ đã được kiểm tra').status_code==200
        assert c.post(base+'/workflow/complete',json={'confirm':True}).status_code==422
        post(c,base+'/workflow/complete',json={'confirm':True,'accept_ignored':True,'note':'Xác nhận cả ba ngoại lệ'})
        assert c.get(f'/api/datasets/{ds}/runs/{r1["run_id"]}').json()['violation_count']==3
        completed=state(c,base)['events'][0]
        assert completed['action']=='COMPLETED' and len(completed['evidence']['ignored'])==3
        assert completed['actor_label']=='test_admin' and completed['note']=='Xác nhận cả ba ngoại lệ'


@pytest.mark.parametrize('operation',['upload','rule'])
def test_completion_conflicts_serialize(isolated_database,operation):
    with TestClient(app) as c:
        ds,batch,base,v1,rules=seed(c,CLEAN);run(c,ds,v1)
        barrier=Barrier(2)
        actor={'user_id':1,'username':'test_admin','role':'admin'}
        def finish():
            barrier.wait()
            try:return 'ok',work.finish(ds,batch,'',False,actor)
            except HTTPException as e:return 'blocked',e.status_code
        def mutate():
            barrier.wait()
            try:
                if operation=='upload':value=dataset_import.import_version(ds,parse_csv(CLEAN),'race.csv',batch)
                else:value=quality_rules.patch_rule(ds,rules[0]['id'],{'name':'Thay đổi đồng thời'},batch)
                return 'ok',value
            except HTTPException as e:return 'blocked',e.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(finish);b=pool.submit(mutate);results=[a.result(timeout=15),b.result(timeout=15)]
        assert sorted(r[0] for r in results)==['blocked','ok'],results


def test_running_run_blocks_completion(isolated_database,monkeypatch):
    with TestClient(app) as c:
        ds,batch,base,v1,_=seed(c,CLEAN);run(c,ds,v1)
        entered,release=Event(),Event();original=quality_execution.check_quality
        def slow(*args,**kwargs):
            entered.set();assert release.wait(10)
            return original(*args,**kwargs)
        monkeypatch.setattr(quality_execution,'check_quality',slow)
        with ThreadPoolExecutor(max_workers=1) as pool:
            task=pool.submit(quality_execution.execute_run,ds,v1)
            try:
                assert entered.wait(8)
                response=c.post(base+'/workflow/complete',json={'confirm':True})
                assert response.status_code==409 and 'RUN_IN_PROGRESS' in response.text
            finally:release.set()
            assert task.result(timeout=12)['status']=='completed'
