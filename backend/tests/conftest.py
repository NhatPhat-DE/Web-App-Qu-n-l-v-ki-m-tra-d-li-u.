import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import accounts
from app.routers import auth
from app.services.login_limit import LoginLimiter
import authenticated_client
from test_dataset_import import isolated_database

BUSINESS_TESTS={'test_exp01','test_ux04','test_nv02','test_nv01','test_dataset_catalog','test_demo_flow','test_quality_report','test_dataset_import','test_import_inference','test_quality_execution','test_quality_history','test_dataset_metadata','test_quality_rules','test_version_import','test_dataguard_hm01','test_dataguard_hm01d_batches'}
BUSINESS_TESTS.add('test_src01')


@pytest.fixture(autouse=True)
def authenticated_business_tests(request,monkeypatch):
    if request.module.__name__.split('.')[-1] not in BUSINESS_TESTS:
        yield
        return
    request.getfixturevalue('isolated_database')
    monkeypatch.setenv('AUTH_CSRF_SECRET','ab'*32)
    monkeypatch.setenv('AUTH_ALLOWED_ORIGINS','http://127.0.0.1:5173')
    monkeypatch.setenv('AUTH_COOKIE_SECURE','false')
    monkeypatch.setattr(auth,'login_limiter',LoginLimiter())
    accounts.bootstrap_admin('test_admin','integration password')
    with TestClient(app) as client:
        challenge=client.get('/api/auth/me').json()['csrf_token']
        response=client.post('/api/auth/login',json={'username':'test_admin','password':'integration password'},headers={'Origin':'http://127.0.0.1:5173','X-CSRF-Token':challenge})
        assert response.status_code==200
        authenticated_client.session_cookie=client.cookies.get('datalens_session')
        authenticated_client.csrf_token=response.json()['csrf_token']
    yield
    authenticated_client.session_cookie=None
    authenticated_client.csrf_token=None
