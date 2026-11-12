from concurrent.futures import ThreadPoolExecutor
from nv01_fixtures import batch_rule_path
import pytest
from authenticated_client import TestClient
from sqlalchemy import create_engine,event
from sqlalchemy.exc import IntegrityError
from psycopg.errors import CheckViolation
from app.main import app
from app.services import quality_rules
from test_dataset_import import isolated_database


@pytest.fixture
def original(isolated_database):
    with TestClient(app) as client:
        result=client.post('/api/datasets/import',data={'name':'versions'},files={'file':('v1.csv',b'a,b\n001,2')}).json()
        dataset=result['dataset_id'];version=result['version_id']
        client.post(batch_rule_path(client,f'/api/datasets/{dataset}/rules'),json={'name':'required','rule_type':'required','columns':['a'],'config':{}})
        run=client.post(f'/api/datasets/{dataset}/versions/{version}/runs').json()
    return dataset,version,run


def test_version2_preserves_old(original):
    dataset,version,run=original
    with TestClient(app) as client:
        old=client.get(f'/api/datasets/{dataset}').json()
        history=client.get(f'/api/datasets/{dataset}/runs').json()
        response=client.post(f'/api/datasets/{dataset}/versions/import',files={'file':('v2.CSV','a,b\n001,  Việt 日本語  \n'.encode())})
        assert response.status_code==201
        new=response.json();assert new['version_number']==2 and new['column_count']==2 and new['row_count']==1
        detail=client.get(f'/api/datasets/{dataset}').json()
        assert detail['columns']==old['columns']
        assert detail['name']==old['name'] and detail['updated_at']>=old['updated_at']
        assert detail['versions'][1]=={**old['versions'][0], 'is_current': False}
        assert detail['versions'][0]['inferred_types']==[
            {'column_name':'a','position':1,'inferred_type':'text','non_missing_count':1,'missing_count':0},
            {'column_name':'b','position':2,'inferred_type':'text','non_missing_count':1,'missing_count':0}]
        assert old['versions'][0]['inferred_types'][1]['inferred_type']=='integer'
        assert client.get(f'/api/datasets/{dataset}/versions/{version}/rows').json()['items'][0]['values']==['001','2']
        assert client.get(f'/api/datasets/{dataset}/versions/{new["version_id"]}/rows').json()['items'][0]['values']==['001','  Việt 日本語  ']
        assert client.get(f'/api/datasets/{dataset}/runs').json()==history


@pytest.mark.parametrize('content,status,code',[
    (b'x,b\n1,2',422,'CSV_SCHEMA_MISMATCH'),(b'b,a\n1,2',422,'CSV_SCHEMA_MISMATCH'),
    (b'a,b,c\n1,2,3',422,'CSV_SCHEMA_MISMATCH'),(b'a,b\n1',422,'COLUMN_COUNT_MISMATCH'),
    (b'x'*(5*1024*1024+1),413,'FILE_TOO_LARGE')],ids=['name','order','count','invalid','oversize'])
def test_rejected_no_partial(original,content,status,code):
    dataset,_,_=original
    with TestClient(app) as client:
        before=client.get(f'/api/datasets/{dataset}').json()
        response=client.post(f'/api/datasets/{dataset}/versions/import',files={'file':('v.csv',content)})
        assert response.status_code==status and response.json()['error']['code']==code
        assert client.get(f'/api/datasets/{dataset}').json()==before
        assert client.post('/api/datasets/999999/versions/import',files={'file':('v.csv',b'a\n1')}).status_code==404


def test_failure_rollback_and_concurrent(original,monkeypatch):
    dataset,_,_=original
    def factory(*args,**kwargs):
        target=create_engine(*args,**kwargs)
        @event.listens_for(target,'before_cursor_execute')
        def fail(connection,cursor,statement,parameters,context,executemany):
            if statement.startswith('INSERT INTO dataset_rows'): raise IntegrityError('private',{},CheckViolation('private'))
        return target
    with TestClient(app) as client:
        with monkeypatch.context() as patch:
            patch.setattr(quality_rules,'create_engine',factory)
            response=client.post(f'/api/datasets/{dataset}/versions/import',files={'file':('v.csv',b'a,b\n1,2')})
            assert response.status_code==500
        assert len(client.get(f'/api/datasets/{dataset}').json()['versions'])==1
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _: client.post(f'/api/datasets/{dataset}/versions/import',files={'file':('v.csv',b'a,b\n1,2')}),range(2)))
        assert all(response.status_code==201 for response in responses)
        assert {response.json()['version_number'] for response in responses}=={2,3}
