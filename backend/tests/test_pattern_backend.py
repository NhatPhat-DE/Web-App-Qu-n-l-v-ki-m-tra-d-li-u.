from nv01_fixtures import saved_run_fields
from nv01_fixtures import batch_rule_path
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import threading

import pytest
from sqlalchemy import select, update, func
from app.models import DatasetRow, DatasetVersion, QualityRule, QualityRun, QualityViolation, User
from app.services import pattern_worker as worker
from app.services.quality_trend import fingerprint
from test_data_type_backend import context, counts
from test_dataset_import import isolated_database
from test_sessions_csrf import settings
from xlsx_reader import read_xlsx

SAMPLES=Path(__file__).resolve().parents[1]/'samples'
EXPECTED=json.loads((SAMPLES/'pattern_qt04a_expected.json').read_text(encoding='utf-8'))


@pytest.fixture
def patterned(context):
    engine,client,_,user=context
    response=client.post(batch_rule_path(client, '/api/datasets/import'),data={'name':'Pattern isolated'},files={'file':('pattern_qt04a.csv',(SAMPLES/'pattern_qt04a.csv').read_bytes())})
    assert response.status_code==201
    data=response.json(); base=f"/api/datasets/{data['dataset_id']}"
    response=client.post(batch_rule_path(client, base+'/rules'),json={'name':'Product code','rule_type':'pattern','columns':['product_code'],'config':EXPECTED['config']})
    assert response.status_code==201
    return engine,client,data,user,response.json()


def test_lifecycle_snapshot_reports_and_raw(patterned):
    engine,client,data,_,rule=patterned
    base=f"/api/datasets/{data['dataset_id']}"; path=base+f"/versions/{data['version_id']}/runs"
    with engine.connect() as c: inferred=c.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id==data['version_id'])).scalar_one()
    response=client.post(batch_rule_path(client, path)); assert response.status_code==201,response.text
    result=response.json(); run=result['run_id']
    assert all(result[k]==v for k,v in EXPECTED['statistics'].items())
    detail=client.get(batch_rule_path(client, base+f'/runs/{run}')).json()
    assert detail['engine_version']=='quality-v6' and detail['rule_snapshot'][0]['config']==EXPECTED['config']
    report=client.get(batch_rule_path(client, base+f'/runs/{run}/report')).json()
    violations=report['violations']
    assert [e['row_number'] for e in violations]==EXPECTED['error_rows']
    assert all(e['error_code']=='PATTERN_MISMATCH' and 'SP[0-9]{4}' in e['message'] for e in violations)
    for e in violations: assert e['values']==EXPECTED['rows'][e['row_number']-1]
    all_pages=[]
    for page in range(1,5): all_pages+=client.get(batch_rule_path(client, base+f'/runs/{run}/violations'),params={'page':page,'page_size':2}).json()['items']
    assert all_pages==violations
    excel=client.get(batch_rule_path(client, base+f'/runs/{run}/report.xlsx'));assert excel.status_code==200
    sheets=read_xlsx(excel.content)
    assert len(sheets)==3 and len(sheets['Chi tiết lỗi']['rows'])==8
    assert json.loads(sheets['Quy tắc đã áp dụng']['rows'][1][5])==EXPECTED['config']
    assert 're2-v1' in sheets['Chi tiết lỗi']['rows'][1][5]
    point=client.get(batch_rule_path(client, base+'/quality-trend')).json()['points'][0]
    assert point['rule_set_fingerprint']==fingerprint(detail['rule_snapshot'])
    assert client.get(batch_rule_path(client, base+'/runs')).json()['items'][0]['run_id']==run
    assert client.patch(batch_rule_path(client, base+f"/rules/{rule['id']}"),json={'config':{'pattern':'.*','dialect':'re2-v1'}}).status_code==200
    assert saved_run_fields(client.get(batch_rule_path(client, base+f'/runs/{run}')).json()) == saved_run_fields(detail)
    assert client.get(batch_rule_path(client, base+f'/runs/{run}/report')).json()['violations']==violations
    again=client.post(batch_rule_path(client, path)).json(); assert again['violation_count']==0
    assert len(read_xlsx(client.get(batch_rule_path(client, base+f"/runs/{again['run_id']}/report.xlsx")).content))==3
    with engine.connect() as c:
        assert c.execute(select(DatasetRow.values).where(DatasetRow.version_id==data['version_id']).order_by(DatasetRow.row_number)).scalars().all()==EXPECTED['rows']
        assert c.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id==data['version_id'])).scalar_one()==inferred


def test_config_columns_auth_csrf_and_patch_rollback(patterned):
    engine,client,data,user,rule=patterned
    base=f"/api/datasets/{data['dataset_id']}/rules"; original=client.get(batch_rule_path(client, base)).json()
    invalid=[{},None,{'pattern':'x','dialect':'re2-v2'},{'pattern':'x','dialect':'re2-v1','extra':0},
             {'pattern':'(?i)x','dialect':'re2-v1'},{'pattern':'x'*513,'dialect':'re2-v1'},
             {'pattern':'(a{1000}){1000}','dialect':'re2-v1'}]
    for config in invalid:
        assert client.post(batch_rule_path(client, base),json={'name':'bad','rule_type':'pattern','columns':['product_code'],'config':config}).status_code==422
        assert client.patch(batch_rule_path(client, base+f"/{rule['id']}"),json={'config':config}).status_code==422
        assert client.get(batch_rule_path(client, base)).json()==original
    for columns in [[],['missing'],['product_code','product_code']]:
        assert client.patch(batch_rule_path(client, base+f"/{rule['id']}"),json={'columns':columns}).status_code==422
    headers=dict(client.headers); csrf=client.headers.pop('X-CSRF-Token')
    assert client.patch(batch_rule_path(client, base+f"/{rule['id']}"),json={'name':'bad'}).status_code==403
    client.headers['X-CSRF-Token']=csrf
    client.headers['Origin']='https://evil.invalid'
    assert client.post(batch_rule_path(client, base),json={'name':'bad'}).status_code==403
    client.headers['Origin']=headers['origin']
    with engine.begin() as c: c.execute(update(User).where(User.id==user).values(is_active=False))
    assert client.patch(batch_rule_path(client, base+f"/{rule['id']}"),json={'name':'bad'}).status_code==401
    client.cookies.clear()
    assert client.get(batch_rule_path(client, base)).status_code==401
    assert counts(engine)==[1,0,0]


def test_preflight_no_run(patterned,monkeypatch):
    engine,client,data,_,rule=patterned
    base=f"/api/datasets/{data['dataset_id']}"; path=base+f"/versions/{data['version_id']}/runs"
    monkeypatch.setattr(worker,'MAX_RULES',0)
    response=client.post(batch_rule_path(client, path));assert response.status_code==422 and response.json()['error']['code']=='PATTERN_RULE_LIMIT'
    assert counts(engine)==[1,0,0]
    monkeypatch.setattr(worker,'MAX_RULES',10)
    with engine.begin() as c: c.execute(update(DatasetRow).where(DatasetRow.version_id==data['version_id'],DatasetRow.row_number==1).values(values=['x'*4097]))
    response=client.post(batch_rule_path(client, path));assert response.status_code==422 and response.json()['error']['code']=='PATTERN_VALUE_LIMIT'
    assert counts(engine)==[1,0,0]
    with engine.begin() as c: c.execute(update(DatasetRow).where(DatasetRow.version_id==data['version_id'],DatasetRow.row_number==1).values(values=['SP0001']))
    monkeypatch.setattr(worker,'MAX_MATCH_BYTES',1)
    response=client.post(batch_rule_path(client, path));assert response.status_code==422 and response.json()['error']['code']=='PATTERN_BYTE_BUDGET'
    assert counts(engine)==[1,0,0]


@pytest.mark.parametrize('code',['PATTERN_TIMEOUT','PATTERN_WORKER_FAILED','PATTERN_RESOURCE_LIMIT','PATTERN_COMPILE_FAILED'])
def test_mixed_worker_failure_atomic_and_retry(patterned,monkeypatch,code):
    engine,client,data,_,rule=patterned
    base=f"/api/datasets/{data['dataset_id']}";path=base+f"/versions/{data['version_id']}/runs"
    assert client.post(batch_rule_path(client, base+'/rules'),json={'name':'Required','rule_type':'required','columns':['product_code'],'config':{}}).status_code==201
    original=worker.evaluate
    def fail(*a,**k): raise worker.PatternError(code,'Safe worker failure')
    monkeypatch.setattr(worker,'evaluate',fail)
    response=client.post(batch_rule_path(client, path)); assert response.status_code==503
    payload=response.json()['error'];assert payload['code']==code and payload['failure_recorded'] is True
    detail=client.get(batch_rule_path(client, base+f"/runs/{payload['run_id']}")).json()
    assert detail['status']=='failed' and detail['failure_code']==code
    assert all(detail[k] is None for k in ['total_rows','error_row_count','violation_count','error_row_rate'])
    assert counts(engine)==[2,1,0]
    assert client.get(batch_rule_path(client, base+f"/runs/{payload['run_id']}/report")).status_code==409
    monkeypatch.setattr(worker,'evaluate',original)
    assert client.post(batch_rule_path(client, path)).json()['violation_count']==8


def test_concurrent_admission_no_rejected_run(patterned,monkeypatch):
    engine,client,data,_,_=patterned
    path=f"/api/datasets/{data['dataset_id']}/versions/{data['version_id']}/runs"
    ready=threading.Event();release=threading.Event();original=worker.evaluate;calls=[]
    def held(*a,**k):
        calls.append(1);ready.set();assert release.wait(5)
        return original(*a,**k)
    monkeypatch.setattr(worker,'evaluate',held)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(client.post,path)
        try:
            assert ready.wait(5)
            second=client.post(batch_rule_path(client, path))
            assert second.status_code==409 and second.json()['error']['code']=='PATTERN_WORKER_BUSY'
            assert counts(engine)==[1,1,0] and calls==[1]
        finally: release.set()
        assert first.result(timeout=10).status_code==201
    assert counts(engine)==[1,1,7]


def test_disconnect_cancels_without_partial_persistence(patterned):
    import asyncio
    from app.routers.runs import run
    engine,_,data,_,_=patterned
    class Disconnected:
        async def is_disconnected(self): return True
    response=asyncio.run(run(data['dataset_id'],data['version_id'],Disconnected()))
    assert response.status_code==503
    assert json.loads(response.body)['error']['code']=='PATTERN_CANCELLED'
    assert counts(engine)==[1,1,0]
    with engine.connect() as c:
        row=c.execute(select(QualityRun)).mappings().one()
        assert row['status']=='failed' and row['failure_code']=='PATTERN_CANCELLED' and row['total_rows'] is None
