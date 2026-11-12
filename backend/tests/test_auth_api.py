from nv01_fixtures import batch_rule_path
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,update,func
from app.main import app
from app.models import User,Session
from app.services import accounts,auth_sessions
from app.services.login_limit import LoginLimiter,LoginLimited
from app.routers import auth
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

ORIGIN='http://127.0.0.1:5173'
PASSWORD='demo password'


@pytest.fixture
def account(isolated_database,settings,monkeypatch):
    monkeypatch.setattr(auth,'login_limiter',LoginLimiter())
    identifier=accounts.bootstrap_admin('admin',PASSWORD)
    return isolated_database,identifier


def bootstrap(client):
    response=client.get('/api/auth/me')
    assert response.status_code==401 and response.headers['cache-control']=='no-store'
    return response.json()['csrf_token']


def login(client,csrf,password=PASSWORD,username='admin'):
    return client.post('/api/auth/login',json={'username':username,'password':password},headers={'Origin':ORIGIN,'X-CSRF-Token':csrf})


def test_flow_rotation_cookie(account):
    engine,_=account
    with TestClient(app) as client:
        token=bootstrap(client); challenge=client.cookies.get(auth.PREAUTH)
        assert bootstrap(client)==token and client.cookies.get(auth.PREAUTH)==challenge
        response=login(client,token);assert response.status_code==200
        cookie=response.headers['set-cookie'];assert 'HttpOnly' in cookie and 'SameSite=lax' in cookie and 'Path=/api' in cookie and 'Domain=' not in cookie
        first=client.cookies.get(auth.SESSION);assert first not in response.text
        expiry=response.json()['expires_at']
        response=client.get('/api/auth/me');assert response.status_code==200 and response.json()['expires_at']==expiry
        response=login(client,response.json()['csrf_token']);assert response.status_code==200
        second=client.cookies.get(auth.SESSION);assert first!=second
        with engine.connect() as c:
            with pytest.raises(auth_sessions.SessionError): auth_sessions.find_session(c,first)
        response=client.post('/api/auth/logout',headers={'Origin':ORIGIN,'X-CSRF-Token':response.json()['csrf_token']})
        assert response.status_code==204 and response.headers['cache-control']=='no-store'
        with engine.connect() as c:
            with pytest.raises(auth_sessions.SessionError): auth_sessions.find_session(c,second)
        token=bootstrap(client)
        assert client.post('/api/auth/logout',headers={'Origin':ORIGIN,'X-CSRF-Token':token}).status_code==204


def test_invalid_credentials_limit_and_csrf(account,monkeypatch):
    engine,user=account
    with TestClient(app) as client:
        token=bootstrap(client)
        answers=[login(client,token,'incorrect password').json(),login(client,token,username='missing').json()]
        with engine.begin() as c: c.execute(update(User).where(User.id==user).values(is_active=False))
        answers.append(login(client,token).json());assert answers[0]==answers[1]==answers[2]
        for headers in [{},{'Origin':'null','X-CSRF-Token':token},{'Origin':ORIGIN},{'Origin':ORIGIN,'X-CSRF-Token':'bad'}]:
            r=client.post('/api/auth/login',json={'username':'admin','password':PASSWORD},headers=headers)
            assert r.status_code==403 and r.headers['cache-control']=='no-store'
        def forbidden(*args): raise AssertionError('must not hash/verify after rate limit')
        for _ in range(3): assert login(client,token).status_code==401
        monkeypatch.setattr(accounts,'verify_password',forbidden)
        r=login(client,token);assert r.status_code==429 and int(r.headers['retry-after'])>0
        r=client.post('/api/auth/login',json={'password':'short'})
        assert r.status_code==422 and 'short' not in r.text and r.headers['cache-control']=='no-store'


def test_expiry_inactive_and_csrf_binding(account,monkeypatch):
    engine,user=account;now=datetime(2026,10,15,tzinfo=timezone.utc)
    real_now=auth_sessions.utc_now
    monkeypatch.setattr(auth_sessions,'utc_now',lambda value=None: real_now(value or now))
    with TestClient(app) as client:
        challenge=bootstrap(client)
        now+=timedelta(minutes=15)
        assert login(client,challenge).status_code==403
        token=bootstrap(client);r=login(client,token);assert r.status_code==200
        sessioncsrf=r.json()['csrf_token'];expires=datetime.fromisoformat(r.json()['expires_at'])
        assert client.post('/api/auth/logout',headers={'Origin':ORIGIN,'X-CSRF-Token':token}).status_code==403
        with engine.begin() as c: c.execute(update(User).where(User.id==user).values(is_active=False))
        assert client.get('/api/auth/me').status_code==401
        with engine.begin() as c: c.execute(update(User).where(User.id==user).values(is_active=True))
        r=login(client,bootstrap(client));assert r.status_code==200
        expires=datetime.fromisoformat(r.json()['expires_at'])
        now=expires-timedelta(microseconds=1);assert client.get('/api/auth/me').status_code==200
        now=expires;assert client.get('/api/auth/me').status_code==401


def test_failure_rollback_config_db(account,monkeypatch):
    engine,_=account
    with TestClient(app) as client:
        token=bootstrap(client)
        original=auth_sessions.create_session
        def fail(*args): original(*args);raise RuntimeError('private SQL')
        with monkeypatch.context() as patch:
            patch.setattr(auth_sessions,'create_session',fail)
            r=login(client,token);assert r.status_code==500 and 'private' not in r.text
        with engine.connect() as c: assert c.execute(select(func.count()).select_from(Session)).scalar_one()==0
        with monkeypatch.context() as patch:
            patch.setenv('DATABASE_URL','postgresql+psycopg://test:private@127.0.0.1:65432/test')
            for path in ['/api/auth/me','/api/auth/logout']:
                r=client.get(path) if path.endswith('/me') else client.post(path,headers={'Origin':ORIGIN,'X-CSRF-Token':token})
                assert r.status_code==503 and 'private' not in r.text
        monkeypatch.delenv('AUTH_CSRF_SECRET')
        assert client.get('/api/auth/me').status_code==503
        assert client.get('/api/datasets').status_code==401


def test_limiter_clock_atomic_capacity():
    now=[0]; limiter=LoginLimiter(clock=lambda:now[0])
    def attempt(_):
        try:limiter.reserve('ip','name');return True
        except LoginLimited:return False
    with ThreadPoolExecutor(max_workers=20) as pool: assert sum(pool.map(attempt,range(30)))==5
    now[0]=600;limiter.reserve('ip','name')
    limiter=LoginLimiter(clock=lambda:now[0])
    for i in range(20):limiter.reserve('ip',str(i))
    with pytest.raises(LoginLimited):limiter.reserve('ip','new')
    limiter=LoginLimiter(clock=lambda:now[0],capacity=2);limiter.reserve('ip','one')
    with pytest.raises(LoginLimited):limiter.reserve('other','two')
    now[0]+=600;limiter.reserve('other','two');assert len(limiter.counters)==2


def test_parallel_login_and_dummy_hash(account,monkeypatch):
    verified=[];original=accounts.verify_password
    def spy(hashed,password):
        verified.append(hashed);return original(hashed,password)
    monkeypatch.setattr(accounts,'verify_password',spy)
    with TestClient(app) as client:
        token=bootstrap(client)
        def attempt(i):
            return client.post('/api/auth/login',json={'username':'missing','password':PASSWORD},headers={'Origin':ORIGIN,'X-CSRF-Token':token,'X-Forwarded-For':str(i)}).status_code
        with ThreadPoolExecutor(max_workers=10) as pool:statuses=list(pool.map(attempt,range(10)))
        assert statuses.count(401)==5 and statuses.count(429)==5
        assert verified==[auth.DUMMY_HASH]*5


def test_secure_cookie_and_duplicate_origin(account,monkeypatch):
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS','https://localhost')
    monkeypatch.setenv('AUTH_COOKIE_SECURE','true')
    with TestClient(app,base_url='https://localhost') as client:
        token=bootstrap(client)
        r=client.post('/api/auth/login',json={'username':'admin','password':PASSWORD},headers={'Origin':'https://localhost','X-CSRF-Token':token})
        assert r.status_code==200 and 'Secure' in r.headers['set-cookie']
        r=client.post('/api/auth/logout',headers=[('Origin','https://localhost'),('Origin','https://evil'),('X-CSRF-Token',r.json()['csrf_token'])])
        assert r.status_code==403


def test_real_http_vite_proxy_cookie_jar(account,tmp_path):
    import os,sys,socket,subprocess,time,shutil
    from pathlib import Path
    import httpx
    def free_port():
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));return sock.getsockname()[1]
    backend_port,proxy_port=free_port(),free_port()
    origin=f'http://127.0.0.1:{proxy_port}'
    environment={**os.environ,'AUTH_ALLOWED_ORIGINS':origin,'RAYON_NUM_THREADS':'1'}
    backend=Path(__file__).resolve().parents[1];frontend=backend.parent/'frontend'
    config=tmp_path/'vite.config.mjs'
    config.write_text('export default '+__import__('json').dumps({'server':{'host':'127.0.0.1','port':proxy_port,'strictPort':True,'proxy':{'/api':f'http://127.0.0.1:{backend_port}'}}}),encoding='utf8')
    processes=[]
    try:
        processes.append(subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(backend_port)],cwd=backend,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        processes.append(subprocess.Popen([shutil.which('node'),str(frontend/'node_modules/vite/bin/vite.js'),'--config',str(config)],cwd=frontend,env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        with httpx.Client(base_url=origin,timeout=5) as client:
            deadline=time.monotonic()+20
            while True:
                try:
                    if client.get('/api/health').status_code==200:break
                except httpx.HTTPError:pass
                if time.monotonic()>deadline:raise AssertionError('Test servers did not start')
                time.sleep(.1)  # Startup only; rate-limit tests use fake clock, never sleep.
            first=client.get('/api/auth/me');assert first.status_code==401
            r=client.post('/api/auth/login',json={'username':'admin','password':PASSWORD},headers={'Origin':origin,'X-CSRF-Token':first.json()['csrf_token']})
            assert r.status_code==200
            r=client.get('/api/auth/me');assert r.status_code==200
            headers={'Origin':origin,'X-CSRF-Token':r.json()['csrf_token']}
            imported=client.post('/api/datasets/import',data={'name':'protected proxy flow'},files={'file':('a.csv',b'a\n\n')},headers=headers)
            assert imported.status_code==422
            imported=client.post('/api/datasets/import',data={'name':'protected proxy flow'},files={'file':('a.csv',b'a\n1')},headers=headers)
            assert imported.status_code==201
            dataset=imported.json()['dataset_id'];version=imported.json()['version_id']
            assert client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'),json={'name':'required','rule_type':'required','columns':['a'],'config':{}},headers=headers).status_code==201
            run=client.post(f'/api/datasets/{dataset}/versions/{version}/runs',headers=headers)
            assert run.status_code==201
            report=client.get(f'/api/datasets/{dataset}/runs/{run.json()["run_id"]}/report')
            assert report.status_code==200 and report.json()['run']['violation_count']==0
            r=client.post('/api/auth/logout',headers={'Origin':origin,'X-CSRF-Token':r.json()['csrf_token']});assert r.status_code==204
            assert client.get('/api/auth/me').status_code==401
    finally:
        for process in processes:
            process.terminate()
        for process in processes:process.wait(timeout=10)
