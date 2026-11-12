from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import select, func, event
from sqlalchemy.exc import SQLAlchemyError
from app.main import app
from app.models import User, Session
from app.services import accounts, admin_users
from app.services.auth_sessions import create_session
from app.services.csrf import session_csrf_token
from app.routers import admin_users as router
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

BASE='/api/admin/users'
ORIGIN='http://127.0.0.1:5173'
PASSWORD='test-only password 25B'
PUBLIC={'id','username','role','is_active','created_at','updated_at'}

@pytest.fixture
def setup(isolated_database,settings):
    root=accounts.bootstrap_admin('root_admin',PASSWORD)
    with isolated_database.begin() as c: token=create_session(c,root)['token']
    return isolated_database,root,token

def client_for(token):
    client=TestClient(app)
    client.cookies.set('datalens_session',token,path='/api')
    client.headers.update({'Origin':ORIGIN,'X-CSRF-Token':session_csrf_token(token)})
    return client

def add(client,name='second_user',role='data_steward'):
    response=client.post(BASE,json={'username':name,'password':PASSWORD,'role':role})
    assert response.status_code==201
    assert set(response.json())==PUBLIC
    return response.json()['id']

def snapshot(engine):
    with engine.connect() as c:
        return c.execute(select(User).order_by(User.id)).all(),c.execute(select(Session).order_by(Session.id)).all()

def test_create_list_patch_sessions(setup):
    engine,root,token=setup
    with client_for(token) as client:
        user=add(client,' Mixed_User ')
        with engine.begin() as c:
            row=c.execute(select(User).where(User.id==user)).mappings().one()
            assert row['username']=='mixed_user' and row['is_active']
            assert row['password_hash'].startswith('$argon2id$') and accounts.verify_password(row['password_hash'],PASSWORD)
            sessions=[create_session(c,user)['token'] for _ in range(2)]
        result=client.get(BASE,params={'page_size':1}).json()
        assert result['total']==2 and result['page']==1 and result['page_size']==1
        assert result['items'][0]['id']==root and set(result['items'][0])==PUBLIC
        assert client.get(BASE,params={'page':2,'page_size':1}).json()['items'][0]['id']==user
        assert client.get(BASE,params={'page':3}).json()['items']==[]
        before=snapshot(engine)
        assert client.patch(f'{BASE}/{user}',json={'role':'data_steward','is_active':True}).status_code==200
        assert snapshot(engine)==before
        response=client.patch(f'{BASE}/{user}',json={'role':'admin'})
        assert response.status_code==200 and set(response.json())==PUBLIC
        for old in sessions:
            with client_for(old) as stale: assert stale.get(BASE).status_code==401
        with engine.begin() as c: fresh=create_session(c,user)['token']
        assert client.patch(f'{BASE}/{user}',json={'is_active':False}).status_code==200
        assert client.patch(f'{BASE}/{user}',json={'is_active':True}).status_code==200
        with client_for(fresh) as stale: assert stale.get(BASE).status_code==401
        with engine.connect() as c:
            assert c.execute(select(func.count()).select_from(Session).where(Session.user_id==user,Session.revoked_at.is_(None))).scalar_one()==0
        assert client.patch(f'{BASE}/999999',json={'is_active':False}).status_code==404
        assert client.get(BASE).headers['cache-control']=='no-store'

@pytest.mark.parametrize('body',[{}, {'username':'ab','password':PASSWORD,'role':'admin'}, {'username':'bad space','password':PASSWORD,'role':'admin'}, {'username':'valid_user','password':'short','role':'admin'}, {'username':'valid_user','password':PASSWORD,'role':'owner'}, {'username':'valid_user','password':PASSWORD,'role':'admin','is_active':False}, {'username':None,'password':PASSWORD,'role':'admin'}, {'username':'valid_user','password':123,'role':'admin'}])
def test_invalid_create_safe_response(setup,body):
    engine,_,token=setup
    with client_for(token) as client:
        before=snapshot(engine);response=client.post(BASE,json=body)
        assert response.status_code==422 and snapshot(engine)==before
        assert PASSWORD not in response.text and 'short' not in response.text and 'password_hash' not in response.text

def test_duplicate_patch_validation(setup):
    engine,root,token=setup
    with client_for(token) as client:
        add(client);before=snapshot(engine)
        assert client.post(BASE,json={'username':' SECOND_USER ','password':PASSWORD,'role':'admin'}).status_code==409
        for body in [{},{'role':None},{'is_active':None},{'role':'owner'},{'is_active':'false'},{'username':'changed'},{'password':PASSWORD},{'extra':True}]:
            assert client.patch(f'{BASE}/{root}',json=body).status_code==422
            assert snapshot(engine)==before
        for params in [{'page':0},{'page_size':101},{'page_size':0}]: assert client.get(BASE,params=params).status_code==422

def test_permissions_csrf(setup):
    engine,root,token=setup
    with client_for(token) as admin:
        steward=add(admin)
        with engine.begin() as c: other=create_session(c,steward)['token']
        before=snapshot(engine)
        operations=[('GET',BASE,None),('POST',BASE,{'username':'blocked_user','password':PASSWORD,'role':'admin'}),('PATCH',f'{BASE}/{steward}',{'is_active':False})]
        with TestClient(app) as anonymous,client_for(other) as forbidden:
            for method,path,body in operations:
                assert anonymous.request(method,path,json=body).status_code==401
                assert forbidden.request(method,path,json=body).status_code==403
        with TestClient(app) as anonymous: pre=anonymous.get('/api/auth/me').json()['csrf_token']
        for headers in [{},{'Origin':ORIGIN},{'Origin':'null','X-CSRF-Token':session_csrf_token(token)},{'Origin':'http://evil','X-CSRF-Token':session_csrf_token(token)},{'Origin':ORIGIN,'X-CSRF-Token':'wrong'},{'Origin':ORIGIN,'X-CSRF-Token':pre}]:
            admin.headers.clear();admin.headers.update(headers)
            for method,path,body in operations[1:]: assert admin.request(method,path,json=body).status_code==403
        assert snapshot(engine)==before

def test_self_and_last_admin(setup):
    engine,root,token=setup
    with client_for(token) as client:
        for change in [{'is_active':False},{'role':'data_steward'}]:
            before=snapshot(engine)
            assert client.patch(f'{BASE}/{root}',json=change).status_code==409 and snapshot(engine)==before
            with pytest.raises(HTTPException) as exc:
                with engine.begin() as c:
                    admin_users.lock_accounts(c);admin_users.patch_user(c,-1,root,change)
            assert exc.value.detail['code']=='LAST_ACTIVE_ADMIN'
        add(client,role='admin')
        assert client.patch(f'{BASE}/{root}',json={'is_active':False}).status_code==409

@pytest.mark.parametrize('change',[{'is_active':False},{'role':'data_steward'}])
def test_concurrent_admin_removal(setup,change):
    engine,root,token=setup
    with client_for(token) as client: other=add(client,role='admin')
    with engine.begin() as c: other_token=create_session(c,other)['token']
    barrier=Barrier(2)
    def attempt(actor,target):
        with client_for(actor) as client:
            barrier.wait(timeout=10)
            return client.patch(f'{BASE}/{target}',json=change).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(attempt,token,other);b=pool.submit(attempt,other_token,root)
        assert sorted([a.result(timeout=30),b.result(timeout=30)])==[200,401]
    with engine.connect() as c:
        assert c.execute(select(func.count()).select_from(User).where(User.role=='admin',User.is_active.is_(True))).scalar_one()==1

def test_rollback_connection(setup,monkeypatch):
    engine,_,token=setup
    with client_for(token) as client:
        user=add(client)
        with engine.begin() as c: create_session(c,user)
        before=snapshot(engine)
        def fail(conn,cursor,statement,parameters,context,executemany):
            if statement.startswith('UPDATE user_sessions'): raise SQLAlchemyError('private detail')
        event.listen(engine.__class__,'before_cursor_execute',fail)
        try:
            response=client.patch(f'{BASE}/{user}',json={'is_active':False})
            assert response.status_code==503 and 'private' not in response.text
        finally: event.remove(engine.__class__,'before_cursor_execute',fail)
        assert snapshot(engine)==before
        @contextmanager
        def unavailable():
            raise ConnectionError('private detail')
            yield
        monkeypatch.setattr(router,'rule_connection',unavailable)
        for method,path,body in [('GET',BASE,None),('POST',BASE,{'username':'new_user','password':PASSWORD,'role':'admin'}),('PATCH',f'{BASE}/{user}',{'is_active':False})]:
            response=client.request(method,path,json=body)
            assert response.status_code==503 and 'private' not in response.text
        assert snapshot(engine)==before

@pytest.mark.parametrize('change',[{'is_active':False},{'role':'data_steward'}])
def test_last_admin_lock_serializes_two_transactions(setup,change):
    engine,root,token=setup
    with client_for(token) as client: other=add(client,role='admin')
    barrier=Barrier(2)
    def attempt(target):
        barrier.wait(timeout=10)
        try:
            with engine.begin() as c:
                admin_users.lock_accounts(c)
                admin_users.patch_user(c,-1,target,change)
            return 200
        except HTTPException as exc:
            assert exc.detail['code']=='LAST_ACTIVE_ADMIN'
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(attempt,root);b=pool.submit(attempt,other)
        assert sorted([a.result(timeout=30),b.result(timeout=30)])==[200,409]
    with engine.connect() as c:
        assert c.execute(select(func.count()).select_from(User).where(User.role=='admin',User.is_active.is_(True))).scalar_one()==1

@pytest.mark.parametrize('state',['expired','revoked','inactive'])
def test_invalid_admin_session_all_endpoints(setup,state):
    from datetime import timedelta
    from sqlalchemy import update
    from app.services.auth_sessions import utc_now
    engine,root,token=setup
    with engine.begin() as c:
        if state=='inactive': c.execute(update(User).where(User.id==root).values(is_active=False))
        elif state=='revoked': c.execute(update(Session).values(revoked_at=utc_now()))
        else:
            now=utc_now()
            c.execute(update(Session).values(created_at=now-timedelta(hours=9),expires_at=now-timedelta(hours=1)))
    before=snapshot(engine)
    with client_for(token) as client:
        for method,path,body in [('GET',BASE,None),('POST',BASE,{'username':'blocked_user','password':PASSWORD,'role':'admin'}),('PATCH',f'{BASE}/{root}',{'is_active':True})]:
            assert client.request(method,path,json=body).status_code==401
    assert snapshot(engine)==before
