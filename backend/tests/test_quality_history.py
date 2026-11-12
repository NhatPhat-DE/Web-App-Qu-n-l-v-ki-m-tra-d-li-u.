from nv01_fixtures import current_version_values
from datetime import datetime, timezone
from authenticated_client import TestClient
from sqlalchemy import insert, select, update
from app.main import app
from app.models import QualityRun, QualityRule, DatasetVersion
from app.services.quality_engine import ENGINE_VERSION
from test_quality_results import stored
from test_dataset_import import isolated_database
from test_quality_execution import path


def info(stored):
    engine,_,version,_,_=stored
    with engine.connect() as connection:
        dataset=connection.execute(select(DatasetVersion.dataset_id).where(DatasetVersion.id==version)).scalar_one()
    return engine,dataset,version


def test_history_versions_states(stored):
    engine,dataset,version=info(stored)
    running=stored[1]
    with TestClient(app) as client:
        completed=client.post(path(stored)).json()['run_id']
        with engine.begin() as connection:
            version2=connection.execute(insert(DatasetVersion).values(**current_version_values(connection, dataset_id=dataset,version_number=2,original_filename='v2.csv',file_size_bytes=10,row_count=1,inferred_types=[])).returning(DatasetVersion.id)).scalar_one()
            failed=connection.execute(insert(QualityRun).values(dataset_version_id=version2,status='failed',started_at=datetime(2026,1,1,tzinfo=timezone.utc),finished_at=datetime.now(timezone.utc),rule_snapshot=stored[3],engine_version='quality-v1',failure_code='RAW',failure_message='private SQL/password').returning(QualityRun.id)).scalar_one()
            connection.execute(update(QualityRun).values(started_at=datetime(2026,1,1,tzinfo=timezone.utc)))
        base=f'/api/datasets/{dataset}/runs'
        result=client.get(base,params={'page_size':2}).json()
        assert result['total']==3
        assert [item['run_id'] for item in result['items']]==[failed,completed]
        assert 'rule_snapshot' not in result['items'][0]
        assert client.get(base,params={'page':2,'page_size':2}).json()['items'][0]['run_id']==running
        assert client.get(base,params={'version_id':version2}).json()['items'][0]['version_number']==2
        for run_id,status in [(running,'running'),(failed,'failed'),(completed,'completed')]:
            response=client.get(base+f'/{run_id}')
            assert response.status_code==200
            detail=response.json()
            assert detail['status']==status and detail['rule_snapshot']==stored[3]
            assert detail['engine_version']==('quality-v1' if run_id==failed else ENGINE_VERSION)
            if status!='completed':
                assert all(detail[key] is None for key in ['total_rows','error_row_count','violation_count','error_row_rate'])
                response=client.get(base+f'/{run_id}/violations')
                assert response.status_code==409 and response.json()['error']['code']=='RUN_NOT_COMPLETED'
            else: assert detail['error_row_rate']=='50.0000'
        assert 'private' not in client.get(base+f'/{failed}').text
        assert client.get(base,params={'page':99}).json()['total']==3
        assert client.get(base,params={'page':99}).json()['items']==[]


def test_violation_filters_and_snapshot(stored):
    engine,dataset,_=info(stored)
    with TestClient(app) as client:
        run_id=client.post(path(stored)).json()['run_id']
        with engine.begin() as connection:
            connection.execute(update(QualityRule).values(name='new name',config={}))
        base=f'/api/datasets/{dataset}/runs/{run_id}'
        errors=[]
        for page in [1,2,3,4]:
            result=client.get(base+'/violations',params={'page':page,'page_size':1}).json()
            assert result['total']==3
            errors+=result['items']
        expected=stored[4]['errors']
        assert [(e['row_number'],e['rule_order']) for e in errors]==[(1,1),(1,2),(2,2)]
        assert [e['values'] for e in errors]==[e['values'] for e in expected]
        assert [e['rule_name'] for e in errors]==['required a','range amount','range amount']
        assert client.get(base).json()['rule_snapshot']==stored[3]
        filtered=client.get(base+'/violations',params={'row_number':1,'rule_id_snapshot':stored[3][1]['id']}).json()
        assert filtered['total']==1 and filtered['items'][0]['error_code']=='NUMERIC_OUT_OF_RANGE'
        assert client.get(base+'/violations',params={'rule_id_snapshot':999999}).json()['total']==0
        assert client.get(base+'/violations',params={'row_number':99}).json()['items']==[]


def test_empty_and_validation(stored):
    engine,dataset,version=info(stored)
    with TestClient(app) as client:
        connection=engine.connect()
        with connection.begin():
            connection.execute(update(QualityRule).values(is_active=False))
            connection.execute(update(QualityRule).where(QualityRule.id==stored[3][0]['id']).values(is_active=True,columns=['amount']))
        connection.close()
        run_id=client.post(path(stored)).json()['run_id']
        base=f'/api/datasets/{dataset}/runs'
        result=client.get(base+f'/{run_id}/violations').json()
        assert result=={'items':[],'total':0,'page':1,'page_size':20}
        other=client.post('/api/datasets/import',data={'name':'other'},files={'file':('a.csv',b'a\n1')}).json()['dataset_id']
        for url in [f'/api/datasets/{other}/runs/{run_id}',f'/api/datasets/{other}/runs/{run_id}/violations',base+'/999999','/api/datasets/999999/runs']:
            assert client.get(url).status_code==404
        assert client.get(f'/api/datasets/{other}/runs',params={'version_id':version}).status_code==404
        assert client.get(base,params={'version_id':999999}).status_code==404
        for url,params in [(base,{'page':0}),(base,{'page_size':101}),(base,{'version_id':'x'}),(base+f'/{run_id}/violations',{'row_number':0}),(base+f'/{run_id}/violations',{'rule_id_snapshot':0})]:
            assert client.get(url,params=params).status_code==422


def test_database_unavailable(stored,monkeypatch):
    _,dataset,_=info(stored)
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://test:example@127.0.0.1:65432/test')
    with TestClient(app) as client:
        for url in [f'/api/datasets/{dataset}/runs',f'/api/datasets/{dataset}/runs/1',f'/api/datasets/{dataset}/runs/1/violations']:
            response=client.get(url)
            assert response.status_code==503 and 'example' not in response.text
