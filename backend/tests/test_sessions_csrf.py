from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import insert, select, update, func
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, Session
from app.services.auth_sessions import create_session, find_session, revoke_session, SessionError
from app.services import csrf
from app.auth_config import get_auth_settings, AuthConfigurationError
from test_dataset_import import isolated_database

NOW = datetime(2026,10,15,tzinfo=timezone.utc)


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setenv('AUTH_CSRF_SECRET', 'ab'*32)
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS','http://127.0.0.1:5173')
    monkeypatch.setenv('AUTH_COOKIE_SECURE','false')


def test_sessions_lifecycle(isolated_database):
    with isolated_database.begin() as c:
        user = c.execute(insert(User).values(username='steward',password_hash='fixture',role='data_steward').returning(User.id)).scalar_one()
        session = create_session(c,user,NOW)
    assert session['expires_at'] == NOW + timedelta(hours=8)
    with isolated_database.connect() as c:
        row = c.execute(select(Session)).mappings().one()
        assert len(row['token_hash']) == 64 and row['token_hash'] != session['token']
        assert session['token'] not in str(dict(row))
        assert find_session(c,session['token'],NOW)['role'] == 'data_steward'
        assert find_session(c,session['token'],NOW+timedelta(hours=8,microseconds=-1))['expires_at'] == session['expires_at']
        for when in [NOW+timedelta(hours=8), NOW+timedelta(hours=9)]:
            with pytest.raises(SessionError): find_session(c,session['token'],when)
        for token in ['',None,'x'*43,'x'*10000]:
            with pytest.raises(SessionError): find_session(c,token,NOW)
    with isolated_database.begin() as c: c.execute(update(User).where(User.id==user).values(role='admin'))
    with isolated_database.connect() as c: assert find_session(c,session['token'],NOW)['role']=='admin'
    with isolated_database.begin() as c: c.execute(update(User).where(User.id==user).values(is_active=False))
    with isolated_database.begin() as c:
        with pytest.raises(SessionError): find_session(c,session['token'],NOW)
        with pytest.raises(SessionError): create_session(c,user,NOW)
        assert revoke_session(c,session['token'],NOW+timedelta(minutes=1)) == 1
        assert revoke_session(c,session['token'],NOW+timedelta(minutes=2)) == 0
        c.execute(update(User).values(is_active=True))
    with isolated_database.connect() as c:
        with pytest.raises(SessionError): find_session(c,session['token'],NOW+timedelta(minutes=3))
        assert c.execute(select(Session.revoked_at)).scalar_one() == NOW+timedelta(minutes=1)


def test_rollback(isolated_database):
    with isolated_database.begin() as c:
        user=c.execute(insert(User).values(username='rollback',password_hash='fixture',role='admin').returning(User.id)).scalar_one()
    with pytest.raises(RuntimeError), isolated_database.begin() as c:
        create_session(c,user,NOW)
        raise RuntimeError('test')
    with isolated_database.begin() as c:
        assert c.execute(select(func.count()).select_from(Session)).scalar_one()==0
        session=create_session(c,user,NOW)
    with pytest.raises(RuntimeError), isolated_database.begin() as c:
        revoke_session(c,session['token'],NOW)
        raise RuntimeError('test')
    with isolated_database.connect() as c: assert find_session(c,session['token'],NOW)['id']==session['id']


def test_challenge_and_labels(settings, monkeypatch):
    challenge=csrf.create_challenge(NOW)
    token=csrf.preauth_csrf_token(challenge,NOW)
    csrf.validate_preauth_csrf(challenge,token,NOW+timedelta(minutes=15,microseconds=-1))
    for when in [NOW-timedelta(seconds=1), NOW+timedelta(minutes=15), NOW+timedelta(minutes=16)]:
        with pytest.raises(csrf.CSRFError): csrf.preauth_csrf_token(challenge,when)
    for invalid in [None,'','a'*10000,'..','é','x'*43+'.1.901.'+'a'*64,challenge[:-1]+('0' if challenge[-1]!='0' else '1')]:
        with pytest.raises(csrf.CSRFError): csrf.preauth_csrf_token(invalid,NOW)
    session='A'*43
    session_token=csrf.session_csrf_token(session)
    csrf.validate_session_csrf(session,session_token)
    for wrong in [token,csrf.session_csrf_token('B'*43),'é',None,'a'*10000]:
        with pytest.raises(csrf.CSRFError): csrf.validate_session_csrf(session,wrong)
    with pytest.raises(csrf.CSRFError): csrf.validate_preauth_csrf(challenge,session_token,NOW)
    monkeypatch.setenv('AUTH_CSRF_SECRET','cd'*32)
    with pytest.raises(csrf.CSRFError): csrf.preauth_csrf_token(challenge,NOW)
    with pytest.raises(csrf.CSRFError): csrf.validate_session_csrf(session,session_token)


@pytest.mark.parametrize('origin',[None,'null','https://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8000','http://127.0.0.1:5173/','http://127.0.0.1:5173,http://evil','http://evil',' http://127.0.0.1:5173'])
def test_bad_origin(settings,origin):
    with pytest.raises(csrf.CSRFError): csrf.validate_origin(origin)


def test_good_origin(settings):
    csrf.validate_origin('http://127.0.0.1:5173')
    assert 'abab' not in repr(get_auth_settings())


@pytest.mark.parametrize('key,value',[('AUTH_CSRF_SECRET',''),('AUTH_CSRF_SECRET','change_me'),('AUTH_ALLOWED_ORIGINS',''),('AUTH_ALLOWED_ORIGINS','*'),('AUTH_ALLOWED_ORIGINS','http://user:pass@localhost'),('AUTH_COOKIE_SECURE','maybe'),('AUTH_ALLOWED_ORIGINS','https://localhost')])
def test_bad_configuration(settings,monkeypatch,key,value):
    monkeypatch.setenv(key,value)
    with pytest.raises(AuthConfigurationError): get_auth_settings()
    with TestClient(app) as client: assert client.get('/api/health').status_code==200


def test_business_api_without_auth_config(isolated_database,monkeypatch):
    for name in ['AUTH_CSRF_SECRET','AUTH_ALLOWED_ORIGINS','AUTH_COOKIE_SECURE']:
        monkeypatch.delenv(name,raising=False)
    with pytest.raises(AuthConfigurationError): get_auth_settings()
    with TestClient(app) as client:
        assert client.get('/api/datasets').status_code==401
        assert client.post('/api/datasets/import',data={'name':'unprotected'},files={'file':('a.csv',b'a\n1')}).status_code==401
