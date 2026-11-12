from nv01_fixtures import batch_rule_path
from datetime import datetime
from authenticated_client import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from psycopg.errors import CheckViolation
from app.main import app
from app.services import quality_rules
from test_version_import import original
from test_dataset_import import isolated_database


def test_metadata_fields_and_history_unchanged(original):
    dataset,version,run=original
    with TestClient(app) as client:
        base=f'/api/datasets/{dataset}'
        before=client.get(batch_rule_path(client, base)).json()
        rows=client.get(batch_rule_path(client, base+f'/versions/{version}/rows')).json()
        history=client.get(batch_rule_path(client, base+f'/runs/{run["run_id"]}')).json()
        errors=client.get(batch_rule_path(client, base+f'/runs/{run["run_id"]}/violations')).json()
        for key,value in [('name','New name'),('description','Mô tả'),('source','CSV'),('owner','Người phụ trách')]:
            old=client.get(batch_rule_path(client, base)).json()
            response=client.patch(batch_rule_path(client, base),json={key:value})
            assert response.status_code==200
            saved=response.json();assert saved[key]==value
            assert datetime.fromisoformat(saved['updated_at'])>datetime.fromisoformat(old['updated_at'])
            for other in ['name','description','source','owner']:
                if other!=key: assert saved[other]==old[other]
        assert client.patch(batch_rule_path(client, base),json={'description':'','source':None,'owner':''}).json()['description']==''
        detail=client.get(batch_rule_path(client, base)).json();assert detail['source'] is None and detail['owner']==''
        column=before['columns'][0]
        old_time=detail['updated_at']
        response=client.patch(batch_rule_path(client, base+f'/columns/{column["id"]}'),json={'description':'Mô tả cột'})
        assert response.status_code==200 and response.json()['description']=='Mô tả cột'
        assert client.get(batch_rule_path(client, base)).json()['updated_at']>old_time
        assert client.patch(batch_rule_path(client, base+f'/columns/{column["id"]}'),json={'description':''}).json()['description']==''
        assert client.patch(batch_rule_path(client, base+f'/columns/{column["id"]}'),json={'description':None}).json()['description'] is None
        after=client.get(batch_rule_path(client, base)).json()
        assert after['versions']==before['versions'] and after['columns']==before['columns']
        assert client.get(batch_rule_path(client, base+f'/versions/{version}/rows')).json()==rows
        assert client.get(batch_rule_path(client, base+f'/runs/{run["run_id"]}')).json()==history
        assert client.get(batch_rule_path(client, base+f'/runs/{run["run_id"]}/violations')).json()==errors


def test_invalid_input_and_ownership(original):
    dataset,_,_=original
    with TestClient(app) as client:
        base=f'/api/datasets/{dataset}';before=client.get(batch_rule_path(client, base)).json()
        for body in [{},{'name':None},{'name':''},{'name':' \t'},{'name':3},{'description':False},{'name':'\x00'},{'id':1},{'updated_at':'now'}]:
            assert client.patch(batch_rule_path(client, base),json=body).status_code==422
            assert client.get(batch_rule_path(client, base)).json()==before
        column=before['columns'][0]['id'];url=base+f'/columns/{column}'
        for body in [{},{'name':'rename'},{'position':2},{'dataset_id':999},{'inferred_types':[]},{'description':123}]:
            assert client.patch(batch_rule_path(client, url),json=body).status_code==422
        other=client.post(batch_rule_path(client, '/api/datasets/import'),data={'name':'other'},files={'file':('a.csv',b'a\n1')}).json()['dataset_id']
        assert client.patch(batch_rule_path(client, f'/api/datasets/{other}/columns/{column}'),json={'description':'x'}).status_code==404
        assert client.patch(batch_rule_path(client, base+'/columns/999999'),json={'description':'x'}).status_code==404
        assert client.patch(batch_rule_path(client, '/api/datasets/999999'),json={'name':'x'}).status_code==404


def test_rollback_and_connection_failure(original,monkeypatch):
    dataset,_,_=original
    with TestClient(app) as client:
        base=f'/api/datasets/{dataset}';before=client.get(batch_rule_path(client, base)).json();column=before['columns'][0]['id']
        def factory(*args,**kwargs):
            target=create_engine(*args,**kwargs)
            @event.listens_for(target,'before_cursor_execute')
            def fail(connection,cursor,statement,parameters,context,executemany):
                if statement.startswith('UPDATE datasets'): raise IntegrityError('private SQL',{},CheckViolation('private'))
            return target
        with monkeypatch.context() as patch:
            patch.setattr(quality_rules,'create_engine',factory)
            for url,body in [(base,{'name':'failed'}),(base+f'/columns/{column}',{'description':'failed'})]:
                response=client.patch(batch_rule_path(client, url),json=body);assert response.status_code==500 and 'private' not in response.text
        assert client.get(batch_rule_path(client, base)).json()==before
        with monkeypatch.context() as patch:
            patch.setenv('DATABASE_URL','postgresql+psycopg://test:example@127.0.0.1:65432/test')
            for url,body in [(base,{'name':'failed'}),(base+f'/columns/{column}',{'description':'failed'})]:
                assert client.patch(batch_rule_path(client, url),json=body).status_code==503
        assert client.get(batch_rule_path(client, base)).json()==before
