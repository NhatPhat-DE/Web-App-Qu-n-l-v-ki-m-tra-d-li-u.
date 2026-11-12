from nv01_fixtures import batch_rule_path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,update
from app.main import app
from app.models import User,Dataset,DatasetVersion,QualityRun,QualityRule
from app.services import accounts
from app.routers import auth
from app.services.login_limit import LoginLimiter
from app.services.auth_sessions import create_session,revoke_session
from datetime import datetime,timedelta,timezone
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

ORIGIN='http://127.0.0.1:5173'


@pytest.mark.parametrize('role',['admin','data_steward'])
def test_all_routes_and_write_guards(isolated_database,settings,monkeypatch,role):
    monkeypatch.setattr(auth,'login_limiter',LoginLimiter())
    user=accounts.bootstrap_admin('access_user','integration password')
    with isolated_database.begin() as c:c.execute(update(User).where(User.id==user).values(role=role))
    with TestClient(app) as anonymous:
        for route in app.routes:
            if not getattr(route,'path','').startswith('/api/datasets'):continue
            path=route.path
            for parameter in ['dataset_id','version_id','column_id','rule_id','run_id']:path=path.replace('{'+parameter+'}','999999')
            for method in route.methods:
                assert anonymous.request(method,path).status_code==401,(method,path)
    with TestClient(app) as client:
        pre=client.get(batch_rule_path(client, '/api/auth/me')).json()['csrf_token']
        response=client.post(batch_rule_path(client, '/api/auth/login'),json={'username':'access_user','password':'integration password'},headers={'Origin':ORIGIN,'X-CSRF-Token':pre})
        assert response.status_code==200
        token=response.json()['csrf_token'];client.headers.update({'Origin':ORIGIN,'X-CSRF-Token':token})
        response=client.post(batch_rule_path(client, '/api/datasets/import'),data={'name':'access'},files={'file':('a.csv',b'a\n1')});assert response.status_code==201
        dataset=response.json()['dataset_id'];version=response.json()['version_id']
        detail=client.get(batch_rule_path(client, f'/api/datasets/{dataset}')).json();column=detail['columns'][0]['id']
        base=f'/api/datasets/{dataset}'
        rule=client.post(batch_rule_path(client, base+'/rules'),json={'name':'required','rule_type':'required','columns':['a'],'config':{}}).json()['id']
        writes=[('POST','/api/datasets/import',dict(data={'name':'blocked'},files={'file':('a.csv',b'a\n1')})),
            ('POST',base+'/versions/import',dict(files={'file':('a.csv',b'a\n2')})),('PATCH',base,dict(json={'name':'new'})),
            ('PATCH',base+f'/columns/{column}',dict(json={'description':'new'})),('POST',base+'/rules',dict(json={'name':'new','rule_type':'required','columns':['a'],'config':{}})),
            ('PATCH',base+f'/rules/{rule}',dict(json={'is_active':False})),('POST',base+f'/versions/{version}/runs',{})]
        def counts():
            with isolated_database.connect() as c:return [c.execute(select(func.count()).select_from(m)).scalar_one() for m in [Dataset,DatasetVersion,QualityRule,QualityRun]]
        before=counts()
        for bad in [{'Origin':ORIGIN},{'Origin':'http://evil','X-CSRF-Token':token},{'Origin':ORIGIN,'X-CSRF-Token':'wrong'},{'X-CSRF-Token':token},{'Origin':ORIGIN,'X-CSRF-Token':pre}]:
            client.headers.clear();client.headers.update(bad)
            for method,path,kwargs in writes:assert client.request(method,batch_rule_path(client, path),**kwargs).status_code==403,(method,path)
            assert counts()==before
        client.headers.update({'Origin':ORIGIN,'X-CSRF-Token':token})
        assert client.patch(batch_rule_path(client, base),json={'name':'updated'}).status_code==200
        assert client.patch(batch_rule_path(client, base+f'/columns/{column}'),json={'description':'updated'}).status_code==200
        assert client.patch(batch_rule_path(client, base+f'/rules/{rule}'),json={'name':'updated rule'}).status_code==200
        assert client.post(batch_rule_path(client, base+'/versions/import'),files={'file':('v.csv',b'a\n2')}).status_code==201
        run=client.post(batch_rule_path(client, base+f'/versions/{version}/runs')).json()['run_id']
        for path in ['/api/datasets',base,base+f'/versions/{version}/rows',base+'/rules',base+'/runs',base+f'/runs/{run}',base+f'/runs/{run}/violations',base+f'/runs/{run}/report']:
            assert client.get(batch_rule_path(client, path)).status_code==200,path
        with isolated_database.begin() as c:c.execute(update(User).where(User.id==user).values(is_active=False))
        assert client.get(batch_rule_path(client, base)).status_code==401


@pytest.mark.parametrize('invalid_state',['expired','revoked','inactive'])
def test_invalid_sessions_all_routes(isolated_database,settings,invalid_state):
    user=accounts.bootstrap_admin('session_user','integration password')
    now=datetime.now(timezone.utc)
    with isolated_database.begin() as c:
        session=create_session(c,user,now-timedelta(hours=9) if invalid_state=='expired' else now)
        if invalid_state=='revoked':revoke_session(c,session['token'],now)
        if invalid_state=='inactive':c.execute(update(User).where(User.id==user).values(is_active=False))
    with TestClient(app) as client:
        client.cookies.set('datalens_session',session['token'],path='/api')
        for route in app.routes:
            if not getattr(route,'path','').startswith('/api/datasets'):continue
            path=route.path
            for parameter in ['dataset_id','version_id','column_id','rule_id','run_id']:path=path.replace('{'+parameter+'}','999999')
            for method in route.methods:assert client.request(method,batch_rule_path(client, path)).status_code==401,(invalid_state,method,path)
