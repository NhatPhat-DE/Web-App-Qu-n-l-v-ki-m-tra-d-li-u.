"""SRC-01 real PostgreSQL acceptance; every test uses a disposable database."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlalchemy import text
from authenticated_client import TestClient
from test_dataset_import import isolated_database
from app.main import app


def post(c,url,data=None,**kwargs):
    r=c.post(url,**({'json':data} if data is not None else kwargs))
    assert r.status_code==201,(url,r.status_code,r.text)
    return r.json()


def sources(c):
    brands=[post(c,'/api/suppliers/brands',dict(code=k,name=k)) for k in ['QA_A','QA_B']]
    return [post(c,'/api/suppliers/stores',dict(code='SHOP_'+str(i),name='Cửa hàng '+str(i),brand_id=b['id'])) for i,b in enumerate(brands)]


def upload(c,ds,batch,clean=False):
    return post(c,f'/api/datasets/{ds}/batches/{batch}/versions/import',files={'file':('source.csv',b'id,name\nA,Alice\nB,'+(b'Bob' if clean else b''))})


def test_two_sources_same_dataset_period_independent_current_versions_and_history(isolated_database):
    with TestClient(app) as c:
        stores=sources(c)
        ds=post(c,'/api/datasets',dict(name='SRC isolated',source='Legacy text; not a store'))['id']
        batches=[post(c,f'/api/datasets/{ds}/batches',dict(name='Nov '+str(i),period_label='11/2026',store_id=s['id']))['id'] for i,s in enumerate(stores)]
        runs=[]
        for i,b in enumerate(batches):
            v=upload(c,ds,b,clean=bool(i))
            post(c,f'/api/datasets/{ds}/batches/{b}/rules',dict(name='Name required',rule_type='required',columns=['name'],config={},is_active=True))
            runs.append(post(c,f'/api/datasets/{ds}/versions/{v["version_id"]}/runs')['run_id'])
        for i,s in enumerate(stores):
            dash=c.get(f'/api/batch-dashboard?store_id={s["id"]}').json()
            assert dash['selected_batch_ids']==[batches[i]]
            assert (dash['total_rows'],dash['violated_rows_count'],dash['total_violations_count'])==(2,1-i,1-i)
            assert c.get(f'/api/batch-dashboard?brand_id={s["brand_id"]}').json()['selected_batch_ids']==[batches[i]]
        assert c.get(f'/api/batch-dashboard?brand_id={stores[0]["brand_id"]}&store_id={stores[1]["id"]}').json()['items']==[]
        old=c.get(f'/api/datasets/{ds}/runs/{runs[0]}/error-export-context').json()
        assert old['supplier']['store_name']=='Cửa hàng 0'
        assert c.patch(f'/api/suppliers/stores/{stores[0]["id"]}',json={'name':'Tên mới'}).status_code==200
        assert c.patch(f'/api/suppliers/brands/{stores[0]["brand_id"]}',json={'name':'Thương hiệu mới'}).status_code==200
        assert c.get(f'/api/datasets/{ds}/runs/{runs[0]}/error-export-context').json()==old
        report=c.get(f'/api/datasets/{ds}/runs/{runs[0]}/report').json()
        assert report['supplier']['store_name']=='Cửa hàng 0' and report['supplier']['brand_name']=='QA_A'
        assert c.get(f'/api/datasets/{ds}/runs/{runs[0]}/report.xlsx').status_code==200
        assert c.get(f'/api/datasets/{ds}/batches/{batches[0]}').json()['supplier']['store_name']=='Tên mới'
        assert c.patch(f'/api/datasets/{ds}/batches/{batches[0]}',json={'store_id':stores[1]['id']}).status_code==409
        before_b=c.get(f'/api/datasets/{ds}/batches/{batches[1]}').json()
        fix=upload(c,ds,batches[0],True)
        post(c,f'/api/datasets/{ds}/versions/{fix["version_id"]}/runs')
        assert c.get(f'/api/datasets/{ds}/batches/{batches[1]}').json()==before_b
        assert c.get(f'/api/batch-dashboard?store_id={stores[0]["id"]}').json()['violated_rows_count']==0


def test_duplicate_inactive_identity_protection_and_legacy_unknown(isolated_database):
    with TestClient(app) as c:
        a,b=sources(c)
        assert c.post('/api/suppliers/brands',json=dict(code='qa_a',name='Duplicate')).status_code==409
        assert c.post('/api/suppliers/stores',json=dict(code=a['code'].lower(),name='Duplicate',brand_id=b['brand_id'])).status_code==409
        assert c.patch(f'/api/suppliers/stores/{a["id"]}',json={'brand_id':b['brand_id']}).status_code==422
        assert c.patch(f'/api/suppliers/stores/{a["id"]}',json={'code':'NEW'}).status_code==422
        assert c.patch(f'/api/suppliers/stores/{a["id"]}',json={'name':None}).status_code==422
        ds=post(c,'/api/datasets',dict(name='Legacy',source='SHOP_0'))['id']
        assert c.post(f'/api/datasets/{ds}/batches',json=dict(name='Missing store')).status_code==422
        # Legacy rows come from migration, never from the new creation endpoint.
        with isolated_database.begin() as db:
            legacy={'id':db.execute(text("INSERT INTO data_batches(dataset_id,name) VALUES(:ds,'Legacy unknown') RETURNING id"),{'ds':ds}).scalar_one()}
        legacy=c.get(f'/api/datasets/{ds}/batches/{legacy["id"]}').json()
        assert legacy['supplier'] is None
        assert c.get('/api/batch-dashboard?store_id=0').json()['selected_batch_ids']==[legacy['id']]
        assert c.patch(f'/api/datasets/{ds}/batches/{legacy["id"]}',json={'store_id':a['id']}).status_code==200
        assert c.get('/api/suppliers/history').json()[0]['before']=={'store_id':None}
        assert c.patch(f'/api/suppliers/stores/{a["id"]}',json={'is_active':False}).status_code==200
        assert c.post(f'/api/datasets/{ds}/batches',json={'name':'Blocked','store_id':a['id']}).status_code==422
        assert c.patch(f'/api/suppliers/brands/{b["brand_id"]}',json={'is_active':False}).status_code==200
        assert c.post(f'/api/datasets/{ds}/batches',json={'name':'Blocked brand','store_id':b['id']}).status_code==422
        assert c.get(f'/api/datasets/{ds}/batches/{legacy["id"]}').status_code==200


def test_legacy_run_never_infers_supplier_from_current_batch(isolated_database):
    with TestClient(app) as c:
        s=sources(c)[0];ds=post(c,'/api/datasets',dict(name='Legacy'))['id']
        batch=post(c,f'/api/datasets/{ds}/batches',dict(name='New',store_id=s['id']))['id']
        v=upload(c,ds,batch)
        post(c,f'/api/datasets/{ds}/batches/{batch}/rules',dict(name='Required',rule_type='required',columns=['name'],config={},is_active=True))
        run=post(c,f'/api/datasets/{ds}/versions/{v["version_id"]}/runs')['run_id']
        with isolated_database.begin() as db:
            db.execute(text("UPDATE quality_runs SET export_context_snapshot=export_context_snapshot-'supplier' WHERE id=:id"),{'id':run})
        assert c.get(f'/api/datasets/{ds}/runs/{run}').json()['supplier'] is None
        assert c.get(f'/api/datasets/{ds}/runs/{run}/error-export-context').json()['supplier'] is None


def test_source_assignment_races_upload_without_changing_source_after_version(isolated_database):
    from app.services import data_batches,dataset_import
    from app.services.csv_reader import parse_csv
    from app.services.quality_execution import RunError
    with TestClient(app) as c:
        a,b=sources(c);ds=post(c,'/api/datasets',dict(name='Race'))['id']
        batch=post(c,f'/api/datasets/{ds}/batches',dict(name='Concurrent',store_id=a['id']))['id']
    def assign():
        try:return data_batches.patch_batch(ds,batch,{'store_id':b['id']})['store_id']
        except RunError as e:assert e.code=='BATCH_SOURCE_LOCKED';return None
    with ThreadPoolExecutor(2) as pool:
        write=pool.submit(dataset_import.import_version,ds,parse_csv(b'id,name\nA,Alice'),'race.csv',batch)
        change=pool.submit(assign)
        write.result();change.result()
    frozen=data_batches.get_batch(ds,batch)['store_id']
    try:data_batches.patch_batch(ds,batch,{'store_id':a['id'] if frozen==b['id'] else b['id']})
    except RunError as e:assert e.code=='BATCH_SOURCE_LOCKED'
    else:raise AssertionError('Source changed after upload')


def test_owner_can_read_but_cannot_change_supplier_catalog(isolated_database):
    with TestClient(app) as c:
        store=sources(c)[0]
        with isolated_database.begin() as db:db.execute(text("UPDATE users SET role='data_owner' WHERE username='test_admin'"))
        assert c.get('/api/suppliers').status_code==200
        assert c.post('/api/suppliers/brands',json={'code':'FORBIDDEN','name':'Forbidden'}).status_code==403
        assert c.patch(f'/api/suppliers/stores/{store["id"]}',json={'name':'Forbidden'}).status_code==403
