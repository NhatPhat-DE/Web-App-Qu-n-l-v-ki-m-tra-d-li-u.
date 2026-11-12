import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import insert,select,update,func
from fastapi.testclient import TestClient
from app.main import app
from app.models import User,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun
from app.services import ai_preview
from app.services.ai_payload import build_payload
from app.services.auth_sessions import create_session
from app.services.csrf import session_csrf_token
from test_ai_services import stored
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

ORIGIN='http://127.0.0.1:5173'

@pytest.fixture
def setup(stored,settings,monkeypatch):
    monkeypatch.delenv('GEMINI_MODEL',raising=False)
    engine,dataset,version=stored
    monkeypatch.setenv('AI_PREVIEW_SECRET','cd'*32)
    monkeypatch.setattr(ai_preview,'preview_limiter',ai_preview.PreviewLimiter())
    with engine.begin() as c:
        user=c.execute(insert(User).values(username='preview_user',password_hash='test-only',role='admin').returning(User.id)).scalar_one()
        token=create_session(c,user)['token']
    return engine,dataset,version,user,token


def client_for(token):
    c=TestClient(app)
    c.cookies.set('datalens_session',token,path='/api')
    c.headers.update({'Origin':ORIGIN,'X-CSRF-Token':session_csrf_token(token)})
    return c


def body(version,**overrides):
    return dict(version_id=version,columns=['code','empty'],include_descriptions=True,include_statistics=True,**overrides)


def url(dataset): return f'/api/datasets/{dataset}/ai-rule-suggestions/preview'

@pytest.mark.parametrize('role',['admin','data_steward'])
@pytest.mark.parametrize('descriptions,statistics',[(True,True),(False,False)])
def test_preview_and_confirmation(setup,role,descriptions,statistics):
    engine,dataset,version,user,token=setup
    with engine.begin() as c: c.execute(update(User).where(User.id==user).values(role=role))
    with client_for(token) as client:
        response=client.post(url(dataset),json={'version_id':version,'columns':['empty','code'],'include_descriptions':descriptions,'include_statistics':statistics})
    assert response.status_code==200
    assert response.headers['cache-control']=='no-store'
    result=response.json()
    assert result['payload']==build_payload(dataset,version,['empty','code'],descriptions,statistics)
    assert result['provider'] is None and result['model'] is None and result['provider_status']=='not_configured'
    claims=json.loads(base64.urlsafe_b64decode(result['preview_token'].split('.')[0]+'=='))
    assert claims['expires']-claims['issued']==300
    assert 'code' not in json.dumps(claims) and '<b>' not in json.dumps(claims) and token not in json.dumps(claims)
    assert ai_preview.confirm_preview(result['preview_token'],user,token,dataset,version)==result['payload']
    with engine.connect() as c:
        for model in [QualityRule,QualityRun]: assert c.execute(select(func.count()).select_from(model)).scalar_one()==0


def test_denied_before_payload(setup,monkeypatch):
    engine,dataset,version,user,token=setup
    def forbidden(*a,**k): raise AssertionError('Unauthorized must never build payload')
    monkeypatch.setattr(ai_preview,'build_payload',forbidden)
    with TestClient(app) as client: assert client.post(url(dataset),json=body(version)).status_code==401
    with client_for(token) as client:
        for headers in [{},{'Origin':ORIGIN},{'Origin':'null','X-CSRF-Token':session_csrf_token(token)},{'Origin':ORIGIN,'X-CSRF-Token':'wrong'}]:
            client.headers.clear();client.headers.update(headers)
            response=client.post(url(dataset),json=body(version))
            assert response.status_code==403 and response.headers['cache-control']=='no-store'
    with engine.begin() as c: c.execute(update(User).where(User.id==user).values(is_active=False))
    with client_for(token) as client: assert client.post(url(dataset),json=body(version)).status_code==401


def test_token_context_signature_expiry(setup):
    engine,dataset,version,user,token=setup
    now=int(time.time())
    result=ai_preview.issue_preview(dataset,version,['code'],True,True,user,token,now)
    preview=result['preview_token']
    with engine.begin() as c:
        other=create_session(c,user)['token']
        other_user=c.execute(insert(User).values(username='other_preview',password_hash='test-only',role='data_steward').returning(User.id)).scalar_one()
        other_token=create_session(c,other_user)['token']
    assert ai_preview.confirm_preview(preview,user,token,dataset,version,now+299)==result['payload']
    for args in [(preview,user,token,dataset,version,now+300),(preview,user,token,dataset,version,now-1),
                 (preview,user,other,dataset,version,now),(preview,other_user,other_token,dataset,version,now),
                 (preview,user,token,dataset,version+1,now),(preview,user,token,dataset+1,version,now)]:
        with pytest.raises(ai_preview.PreviewError) as exc: ai_preview.confirm_preview(*args)
        assert exc.value.status==409
    for invalid in [None,'','x'*5000,preview[:-1]+('0' if preview[-1]!='0' else '1'),'@@@@.bad']:
        with pytest.raises(ai_preview.PreviewError): ai_preview.confirm_preview(invalid,user,token,dataset,version,now)


@pytest.mark.parametrize('change',['description','type','statistics'])
def test_changed_payload(setup,change):
    engine,dataset,version,user,token=setup
    result=ai_preview.issue_preview(dataset,version,['code'],True,True,user,token)
    with engine.begin() as c:
        if change=='description': c.execute(update(DatasetColumn).where(DatasetColumn.dataset_id==dataset,DatasetColumn.name=='code').values(description='changed'))
        elif change=='type': c.execute(update(DatasetVersion).where(DatasetVersion.id==version).values(inferred_types=[]))
        else: c.execute(update(DatasetRow).where(DatasetRow.version_id==version,DatasetRow.row_number==1).values(values=['nonempty',' ']))
    with pytest.raises(ai_preview.PreviewError) as exc: ai_preview.confirm_preview(result['preview_token'],user,token,dataset,version)
    assert exc.value.status==409 and exc.value.code=='AI_PREVIEW_CHANGED'


def test_configuration_input_limits_and_rate(setup,monkeypatch):
    engine,dataset,version,user,token=setup
    with client_for(token) as client:
        monkeypatch.delenv('AI_PREVIEW_SECRET')
        response=client.post(url(dataset),json=body(version)); assert response.status_code==503
        assert 'AI_PREVIEW_NOT_CONFIGURED' in response.text
        assert client.get('/api/datasets').status_code==200
        monkeypatch.setenv('AI_PREVIEW_SECRET','cd'*32)
        assert client.post(url(dataset),content=b' '*8193).status_code==413
        assert client.post(url(dataset),content='{"version_id":1,"version_id":2}').status_code==422
        for bad in [{},{'version_id':version,'columns':[]},{'version_id':version,'columns':['bad']},{'version_id':version,'columns':['code'],'include_statistics':'false'},{'version_id':version,'columns':['code'],'extra':1}]:
            assert client.post(url(dataset),json=bad).status_code==422
        monkeypatch.setattr(ai_preview,'preview_limiter',ai_preview.PreviewLimiter())
        for _ in range(10): assert client.post(url(dataset),json=body(version)).status_code==200
        response=client.post(url(dataset),json=body(version))
        assert response.status_code==429 and 1<=int(response.headers['retry-after'])<=60
        assert response.headers['cache-control']=='no-store'


def test_limiter_atomic_cleanup_capacity():
    now=[0.0];limiter=ai_preview.PreviewLimiter(clock=lambda:now[0],capacity=1)
    def attempt(_):
        try: limiter.reserve(1);return 200
        except ai_preview.PreviewError as exc: return exc.status
    with ThreadPoolExecutor(max_workers=20) as pool: results=list(pool.map(attempt,range(20)))
    assert results.count(200)==10 and results.count(429)==10
    with pytest.raises(ai_preview.PreviewError): limiter.reserve(2)
    assert len(limiter.counters)==1
    now[0]=60;limiter.reserve(2)
    assert list(limiter.counters)==[2]


def test_payload_limits_revoked_session_and_secret_rotation(setup,monkeypatch):
    from app.services.auth_sessions import revoke_session
    from app.services.ai_payload import serialize_payload
    engine,dataset,version,user,token=setup
    assert serialize_payload({'b':1,'a':2})==serialize_payload({'a':2,'b':1})
    result=ai_preview.issue_preview(dataset,version,['code'],True,False,user,token)
    monkeypatch.setenv('AI_PREVIEW_SECRET','ef'*32)
    with pytest.raises(ai_preview.PreviewError): ai_preview.confirm_preview(result['preview_token'],user,token,dataset,version)
    monkeypatch.setenv('AI_PREVIEW_SECRET','cd'*32)
    names=[f'col_{i}' for i in range(30)]
    with engine.begin() as c:
        for position,name in enumerate(names,3):
            c.execute(insert(DatasetColumn).values(dataset_id=dataset,name=name,position=position,description='界'*500))
    with client_for(token) as client:
        response=client.post(url(dataset),json={'version_id':version,'columns':names,'include_statistics':False})
        assert response.status_code==422 and response.json()['error']['code']=='AI_PAYLOAD_TOO_LARGE'
    with engine.begin() as c: revoke_session(c,token)
    with pytest.raises(ai_preview.PreviewError) as exc: ai_preview.confirm_preview(result['preview_token'],user,token,dataset,version)
    assert exc.value.status==401


def test_503_and_preauth_rejection(setup,monkeypatch):
    from contextlib import contextmanager
    engine,dataset,version,user,token=setup
    with client_for(token) as client,TestClient(app) as anonymous:
        pre=anonymous.get('/api/auth/me').json()['csrf_token']
        client.headers['X-CSRF-Token']=pre
        assert client.post(url(dataset),json=body(version)).status_code==403
        client.headers['X-CSRF-Token']=session_csrf_token(token)
        @contextmanager
        def unavailable():
            raise ConnectionError('private detail')
            yield
        monkeypatch.setattr(ai_preview,'rule_connection',unavailable)
        response=client.post(url(dataset),json=body(version))
        assert response.status_code==503 and 'private' not in response.text


def test_configuration_change_requires_new_preview(setup,monkeypatch):
    from app.services.ai_preview import issue_preview,confirm_preview,PreviewError
    engine,dataset,version,user,token=setup
    first=issue_preview(dataset,version,['code'],True,False,user,token)
    monkeypatch.setenv('GEMINI_API_KEY','test-key-not-real')
    monkeypatch.setenv('GEMINI_MODEL','gemini-3.5-flash-lite')
    with pytest.raises(PreviewError):confirm_preview(first['preview_token'],user,token,dataset,version)
    second=issue_preview(dataset,version,['code'],True,False,user,token)
    assert second['provider']=='gemini' and second['model']=='gemini-3.5-flash-lite'
    assert confirm_preview(second['preview_token'],user,token,dataset,version)==second['payload']
    monkeypatch.setenv('GEMINI_MODEL','gemini-3.8-flash')
    with pytest.raises(PreviewError):confirm_preview(second['preview_token'],user,token,dataset,version)
