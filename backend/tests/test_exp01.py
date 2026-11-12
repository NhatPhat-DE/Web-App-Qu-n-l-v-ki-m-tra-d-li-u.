"""EXP-01 export evidence: only disposable PostgreSQL fixtures."""
import csv,io
from sqlalchemy import select,update
from authenticated_client import TestClient
from app.main import app
from app.models import QualityRun
from test_dataset_import import isolated_database
from test_nv02 import seed,post,run,upload

def context(c,ds,r):
    response=c.get(f'/api/datasets/{ds}/runs/{r}/error-export-context')
    assert response.status_code==200,response.text
    return response.json()

def test_composite_snapshot_survives_identity_and_metadata_changes(isolated_database):
    with TestClient(app) as c:
        ds,bid,base,version,_=seed(c);r=run(c,ds,version)['run_id']
        before=context(c,ds,r)
        assert before['identity']['columns']==['id','part'] and before['scope_source']=='run_snapshot'
        assert before['rows']==[{'row_number':1,'values':['A','X']},{'row_number':3,'values':['C','X']}]
        assert c.put(f'/api/datasets/{ds}/identity',json={'columns':['name']}).status_code==200
        assert c.patch(base,json={'name':'Tên đợt mới','period_label':'Kỳ sau'}).status_code==200
        assert c.patch(f'/api/datasets/{ds}',json={'name':'Tên dataset mới'}).status_code==200
        post(c,base+'/workflow/reconcile',json={'run_id':r})
        assert context(c,ds,r)==before
        # Simulate pre-0012 row: keep NULL, do not backfill or use latest recheck.
        with isolated_database.begin() as db:db.execute(update(QualityRun).where(QualityRun.id==r).values(export_context_snapshot=None))
        legacy=context(c,ds,r)
        assert legacy['scope_source']=='legacy_ids_only' and legacy['dataset']['name'] is None and legacy['batch']['name'] is None
        assert legacy['identity_source']=='first_reconciliation_snapshot' and legacy['identity']['columns']==['id','part']
        assert legacy['rows']==before['rows']

def test_reordered_rows_and_formula_like_keys_are_exact_source_cells(isolated_database):
    rows=[['=HYPERLINK("x")','line,\n"quoted"','-1',''],['0','\t=2','-1','NULL'],['001','   @SUM(A1)','-1','NaN']]
    def content(records):
        out=io.StringIO(newline='');w=csv.writer(out);w.writerow(['id','part','amount','name']);w.writerows(records);return out.getvalue().encode()
    with TestClient(app) as c:
        ds,_,base,v1,_=seed(c,content(rows));r1=run(c,ds,v1)['run_id']
        r2=run(c,ds,upload(c,base,content(list(reversed(rows)))))['run_id']
        assert [r['values'] for r in context(c,ds,r1)['rows']]==[r[:2] for r in rows]
        assert [r['values'] for r in context(c,ds,r2)['rows']]==[r[:2] for r in reversed(rows)]
        assert context(c,ds,r1)['rows'][0]['values'][0]=='=HYPERLINK("x")'

def test_no_identity_does_not_borrow_configuration_created_later(isolated_database):
    with TestClient(app) as c:
        ds=post(c,'/api/datasets',json={'name':'EXP không khóa'})['id']
        bid=post(c,f'/api/datasets/{ds}/batches',json={'name':'Không khóa','copy_template_rules':False})['id'];base=f'/api/datasets/{ds}/batches/{bid}'
        v=upload(c,base,b'id,value\nA,\n')
        post(c,base+'/rules',json={'name':'Bắt buộc','rule_type':'required','columns':['value'],'config':{},'is_active':True})
        r=run(c,ds,v)['run_id'];before=context(c,ds,r)
        assert before['identity_status']=='not_configured' and before['identity'] is None and before['rows']==[]
        assert c.put(f'/api/datasets/{ds}/identity',json={'columns':['id']}).status_code==200
        post(c,base+'/workflow/activate',json={'confirm':True})
        assert context(c,ds,r)==before
        with isolated_database.begin() as db:db.execute(update(QualityRun).where(QualityRun.id==r).values(export_context_snapshot=None))
        old=context(c,ds,r);assert old['identity_status']=='unavailable' and old['identity'] is None
        assert c.get(f'/api/datasets/{ds+1}/runs/{r}/error-export-context').status_code==404

def test_unfinished_run_and_additive_snapshot_persistence(isolated_database,monkeypatch):
    with TestClient(app) as c:
        ds,_,_,v,_=seed(c);r=run(c,ds,v)['run_id']
        with isolated_database.connect() as db:
            frozen=db.execute(select(QualityRun.export_context_snapshot).where(QualityRun.id==r)).scalar_one()
        assert frozen['identity']['columns']==['id','part']
        from app.services import quality_execution
        def fail(*args,**kwargs):raise RuntimeError('EXP01 injected failure')
        monkeypatch.setattr(quality_execution,'check_quality',fail)
        failed=c.post(f'/api/datasets/{ds}/versions/{v}/runs')
        assert failed.status_code>=400
        failed_id=failed.json()['error']['run_id']
        assert c.get(f'/api/datasets/{ds}/runs/{failed_id}/error-export-context').status_code==409
