"""Dashboard workflow presentation; real PostgreSQL, no application writes."""
from authenticated_client import TestClient
from app.main import app
from app.services import workflow_dashboard,quality_execution
from test_dataset_import import isolated_database
from test_nv02 import seed,post,run,upload,issues,change,RAW,V2,CLEAN


def dashboard(c,batches):
    response=c.get('/api/batch-dashboard?'+'&'.join(f'batch_id={b}' for b in batches))
    assert response.status_code==200,response.text
    return response.json()


def test_quality_totals_separate_from_issues_and_completion(isolated_database):
    with TestClient(app) as c:
        ds,a,base,v1,rules=seed(c);run(c,ds,v1)
        run(c,ds,upload(c,base,V2));run(c,ds,upload(c,base,CLEAN))
        post(c,base+'/workflow/complete',json={'confirm':True})
        def another(name,content=RAW):
            bid=post(c,f'/api/datasets/{ds}/batches',json={'name':name,'copy_template_rules':False})['id']
            url=f'/api/datasets/{ds}/batches/{bid}'
            version=upload(c,url,content)
            r=[]
            for body in [dict(name='Điểm 0–10',rule_type='numeric_range',columns=['amount'],config={'min':'0','max':'10'}),dict(name='Tên bắt buộc',rule_type='required',columns=['name'],config={})]:
                r.append(post(c,url+'/rules',json={**body,'is_active':True}))
            post(c,url+'/workflow/activate',json={'confirm':True});run(c,ds,version)
            return bid,url,version,r
        b,_,_,_=another('B sạch',CLEAN)
        missing=b'id,part,amount,name\nB,X,3,Bee\nC,X,8,Cee\nA,,2,Able\n'
        missing_id,missing_url,_,_=another('C thiếu khóa');run(c,ds,upload(c,missing_url,missing))
        ignored_id,ignored_url,_,_=another('D ngoại lệ')
        for item in issues(c,ignored_url):assert change(c,ignored_url,item,'IGNORED','QA: ngoại lệ').status_code==200
        post(c,ignored_url+'/workflow/complete',json={'confirm':True,'accept_ignored':True,'note':'Chấp nhận 3 ngoại lệ'})
        changed_id,changed_url,version,rules=another('E đổi quy tắc')
        response=c.patch(changed_url+f'/rules/{rules[0]["id"]}',json={'config':{'min':'-10','max':'30'}})
        assert response.status_code==200,response.text
        run(c,ds,version)
        data=dashboard(c,[a,b,missing_id,ignored_id,changed_id]);items={i['batch_id']:i for i in data['items']}
        assert (data['total_rows'],data['violated_rows_count'],data['total_violations_count'],data['violation_rate'])==(15,3,4,'20.0000')
        assert items[a]['workflow']['unprocessed_count']==0 and items[a]['workflow']['completion_blockers']==[]
        missing_item=items[missing_id]
        assert missing_item['status']=='PASSED' and missing_item['run']['violation_count']==0
        assert missing_item['workflow']['unprocessed_count']==3 and missing_item['workflow']['uncertain_count']==3
        assert 'IDENTITY_MISSING' in missing_item['workflow']['completion_blockers']
        changed=items[changed_id]
        assert changed['run']['violation_count']==1
        assert changed['workflow']['unprocessed_count']==3 and changed['workflow']['uncertain_count']==3
        assert 'RULE_ENGINE_OR_SCHEMA_CHANGED' in changed['workflow']['completion_blockers']
        assert items[ignored_id]['workflow']['ignored_count']==3
        assert items[ignored_id]['workflow']['completion_blockers']==[]
        # Read-only aggregate: snapshots and issue states remain unchanged.
        assert dashboard(c,[a,b,missing_id,ignored_id,changed_id])==data


def test_summary_uses_fixed_batch_queries_and_unenabled_is_explicit(isolated_database,monkeypatch):
    original=workflow_dashboard.summaries;query_counts=[]
    class CountedConnection:
        def __init__(self,c):self.c=c;self.count=0
        def execute(self,*args,**kwargs):self.count+=1;return self.c.execute(*args,**kwargs)
    def counted(c,*args):
        proxy=CountedConnection(c);result=original(proxy,*args);query_counts.append(proxy.count);return result
    monkeypatch.setattr(workflow_dashboard,'summaries',counted)
    with TestClient(app) as c:
        ds,bid,base,version,_=seed(c);run(c,ds,version)
        empty=post(c,f'/api/datasets/{ds}/batches',json={'name':'Chưa bật','copy_template_rules':False})['id']
        dashboard(c,[bid]);data=dashboard(c,[bid,empty])
        assert query_counts==[7,7]
        item=next(i for i in data['items'] if i['batch_id']==empty)
        assert not item['workflow']['enabled']
        assert 'WORKFLOW_NOT_ENABLED' in item['workflow']['completion_blockers']
        assert 'NO_CURRENT_VERSION' in item['workflow']['completion_blockers']


def test_failed_latest_run_blocks_completion_without_changing_quality_totals(isolated_database,monkeypatch):
    with TestClient(app) as c:
        ds,bid,base,version,_=seed(c);run(c,ds,version)
        before=dashboard(c,[bid])
        def fail(*args,**kwargs):raise RuntimeError('UX04 injected failure')
        monkeypatch.setattr(quality_execution,'check_quality',fail)
        response=c.post(f'/api/datasets/{ds}/versions/{version}/runs');assert response.status_code>=400
        after=dashboard(c,[bid])
        for key in ('total_rows','violated_rows_count','total_violations_count','violation_rate'):assert after[key]==before[key]
        assert after['items'][0]['status']=='FAILED'
        assert 'LATEST_RUN_NOT_COMPLETED' in after['items'][0]['workflow']['completion_blockers']
        assert after['items'][0]['workflow']['unprocessed_count']==3
