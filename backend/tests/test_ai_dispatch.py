import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from contextlib import contextmanager
from unittest.mock import Mock
import pytest
from sqlalchemy import update,select,func
from app.models import User,QualityRule,QualityRun
from app.services import ai_dispatch,ai_preview,ai_payload,ai_suggestions
from app.services.auth_sessions import revoke_session
from test_ai_preview import setup,client_for
from test_ai_services import stored,suggestion,wire,OUT_OF_SCOPE_RULE_TYPES
from test_dataset_import import isolated_database
from test_sessions_csrf import settings
from fastapi.testclient import TestClient

class FakeAdapter:
    def __init__(self,raw='{"suggestions":[]}',action=None):
        self.calls=0;self.raw=raw;self.action=action
    async def suggest(self,payload,limits):
        self.calls+=1
        assert limits.total_timeout==20 and limits.connect_timeout==5 and limits.max_output_bytes==16384
        if self.action: await self.action(payload,limits)
        return self.raw

@pytest.fixture
def configured(setup,monkeypatch):
    engine,dataset,version,user,token=setup
    preview=ai_preview.issue_preview(dataset,version,['code'],True,True,user,token)['preview_token']
    adapter=FakeAdapter(wire([suggestion()]))
    monkeypatch.setattr(ai_dispatch,'get_adapter',lambda:adapter)
    monkeypatch.setattr(ai_dispatch,'quota',ai_dispatch.Quota())
    return setup,preview,adapter

def post(client,dataset,version,preview,**changes):
    body=dict(version_id=version,preview_token=preview,confirmed=True);body.update(changes)
    return client.post(f'/api/datasets/{dataset}/ai-rule-suggestions',json=body)

def check(response,status):
    assert response.status_code==status
    assert response.headers['cache-control']=='no-store'
    assert response.json()['request_id']==response.headers['x-request-id']

@pytest.mark.parametrize('role',['admin','data_steward'])
@pytest.mark.parametrize('kind',['required','unique','numeric_range'])
def test_valid_no_transaction_no_writes(configured,monkeypatch,role,kind):
    (engine,dataset,version,user,token),preview,adapter=configured
    adapter.raw=wire([suggestion(kind,config={'min':'0','max':'1'} if kind=='numeric_range' else {})])
    with engine.begin() as c:c.execute(update(User).where(User.id==user).values(role=role))
    active=[0]
    def wrap(original):
        @contextmanager
        def tracked():
            with original() as c:
                active[0]+=1
                try:yield c
                finally:active[0]-=1
        return tracked
    monkeypatch.setattr(ai_preview,'rule_connection',wrap(ai_preview.rule_connection))
    monkeypatch.setattr(ai_payload,'catalog_connection',wrap(ai_payload.catalog_connection))
    async def outside(payload,limits):
        assert active[0]==0
        assert set(payload)=={'schema_version','columns','row_count'}
    adapter.action=outside
    with client_for(token) as client: response=post(client,dataset,version,preview)
    check(response,200)
    assert len(response.json()['suggestions'])==1 and adapter.calls==1
    assert response.json()['suggestions'][0]['rule_type']==kind
    with engine.connect() as c:
        for model in [QualityRule,QualityRun]:assert c.execute(select(func.count()).select_from(model)).scalar_one()==0


def test_denied_and_unconfirmed_no_adapter(configured):
    (engine,dataset,version,user,token),preview,adapter=configured
    with TestClient(app_for_test()) as client:check(post(client,dataset,version,preview),401)
    with client_for(token) as client:
        client.headers.clear();check(post(client,dataset,version,preview),403)
    with client_for(token) as client:
        check(post(client,dataset,version,preview,confirmed=False),422)
        check(post(client,dataset,version,preview,confirmed='true'),422)
        check(post(client,dataset,version,preview,extra=1),422)
        check(post(client,dataset,version,'invalid'),409)
        expired=ai_preview.issue_preview(dataset,version,['code'],True,True,user,token,now=1)['preview_token']
        check(post(client,dataset,version,expired),409)
        from app.models import DatasetColumn
        with engine.begin() as c:c.execute(update(DatasetColumn).where(DatasetColumn.dataset_id==dataset).values(description='changed'))
        check(post(client,dataset,version,preview),409)
    assert adapter.calls==0


def app_for_test():
    from app.main import app
    return app

@pytest.mark.parametrize('raw,status',[
    ('{"suggestions":[]}',200),('{}',502),('x'*16385,502),
    ('{"suggestions":[],"extra":0}',502),('not JSON',502)])
def test_output(configured,raw,status):
    (engine,dataset,version,user,token),preview,adapter=configured
    adapter.raw=raw
    with client_for(token) as client:response=post(client,dataset,version,preview)
    check(response,status);assert adapter.calls==1
    if status==200:assert response.json()['suggestions']==[]
    assert user not in ai_dispatch.quota.active
    with engine.connect() as c:
        for model in [QualityRule,QualityRun]:assert c.execute(select(func.count()).select_from(model)).scalar_one()==0


@pytest.mark.parametrize('kind',OUT_OF_SCOPE_RULE_TYPES)
@pytest.mark.parametrize('placement',['alone','first','last'])
def test_out_of_scope_response_rejected_without_drafts_or_writes(configured,monkeypatch,kind,placement):
    (engine,dataset,version,user,token),preview,adapter=configured
    bad=suggestion(kind)
    items=[bad] if placement=='alone' else ([bad,suggestion()] if placement=='first' else [suggestion(),bad])
    adapter.raw=wire(items)
    validator=Mock(return_value=None)
    allocate_id=Mock(wraps=ai_suggestions.uuid4)
    monkeypatch.setattr(ai_suggestions,'validate',validator)
    monkeypatch.setattr(ai_suggestions,'uuid4',allocate_id)

    with client_for(token) as client:response=post(client,dataset,version,preview)

    check(response,502)
    assert response.json()['error']['code']=='AI_INVALID_RESPONSE'
    assert 'suggestions' not in response.json() and adapter.calls==1
    validator.assert_not_called()
    allocate_id.assert_not_called()
    assert user not in ai_dispatch.quota.active and len(ai_dispatch.quota.users[user])==1
    with engine.connect() as c:
        for model in [QualityRule,QualityRun]:assert c.execute(select(func.count()).select_from(model)).scalar_one()==0

@pytest.mark.parametrize('failure',['timeout','provider'])
def test_failures_counted_no_retry(configured,monkeypatch,failure):
    (engine,dataset,version,user,token),preview,adapter=configured
    if failure=='provider':
        async def fail(payload,limits):raise RuntimeError('private provider response')
        adapter.action=fail
    else:
        ticks=iter([0.0,21.0])
        monkeypatch.setattr(ai_dispatch,'clock',lambda:next(ticks))
    with client_for(token) as client:response=post(client,dataset,version,preview)
    check(response,504 if failure=='timeout' else 503)
    assert adapter.calls==1 and len(ai_dispatch.quota.users[user])==1
    assert 'private' not in response.text
    assert user not in ai_dispatch.quota.active


def test_runtime_not_configured(setup):
    engine,dataset,version,user,token=setup
    preview=ai_preview.issue_preview(dataset,version,['code'],True,True,user,token)['preview_token']
    with client_for(token) as client:response=post(client,dataset,version,preview)
    check(response,503);assert response.json()['error']['code']=='AI_NOT_CONFIGURED'


def test_revoked_during_adapter(configured):
    (engine,dataset,version,user,token),preview,adapter=configured
    async def revoke(payload,limits):
        with engine.begin() as c:revoke_session(c,token)
    adapter.action=revoke
    with client_for(token) as client:response=post(client,dataset,version,preview)
    check(response,401);assert 'suggestions' not in response.json() and adapter.calls==1


def test_two_requests_one_inflight(configured):
    (engine,dataset,version,user,token),preview,adapter=configured
    entered=Event();release=Event()
    async def waiting(payload,limits):
        entered.set()
        assert await asyncio.to_thread(release.wait,5)
    adapter.action=waiting
    def first():
        with client_for(token) as client:return post(client,dataset,version,preview)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(first)
        try:
            assert entered.wait(5)
            with client_for(token) as client:response=post(client,dataset,version,preview)
            check(response,429);assert response.headers['retry-after']=='1'
            assert adapter.calls==1
        finally:release.set()
        check(future.result(10),200)


def test_user_quota_counts_errors(configured):
    (engine,dataset,version,user,token),preview,adapter=configured
    adapter.raw='invalid'
    with client_for(token) as client:
        for _ in range(5):check(post(client,dataset,version,preview),502)
        response=post(client,dataset,version,preview);check(response,429)
    assert adapter.calls==5 and int(response.headers['retry-after'])>0


def test_quota_fake_clocks_cleanup_cap_day_and_atomic():
    now=[0.0];wall=[0.0];quota=ai_dispatch.Quota(lambda:now[0],lambda:wall[0],capacity=2)
    for _ in range(5):quota.reserve(1);quota.release(1)
    with pytest.raises(ai_dispatch.AIError):quota.reserve(1)
    now[0]=600;quota.reserve(1);quota.release(1)
    quota.reserve(2);quota.release(2)
    with pytest.raises(ai_dispatch.AIError):quota.reserve(3)
    now[0]=1200
    for user in range(4,17):quota.reserve(user);quota.release(user);now[0]+=600
    assert quota.daily==20
    with pytest.raises(ai_dispatch.AIError) as exc:quota.reserve(99)
    assert exc.value.retry_after==86400
    wall[0]=86400;quota.reserve(99);quota.release(99)
    assert quota.daily==1 and len(quota.users)<=2
    quota=ai_dispatch.Quota(lambda:0,lambda:0)
    def attempt(_):
        try:quota.reserve(1);return 200
        except ai_dispatch.AIError:return 429
    with ThreadPoolExecutor(max_workers=10) as pool:results=list(pool.map(attempt,range(20)))
    assert results.count(200)==1 and results.count(429)==19


def test_timeout_retains_slot_until_adapter_actually_stops(configured,monkeypatch):
    (engine,dataset,version,user,token),preview,adapter=configured
    async def scenario():
        entered=asyncio.Event();release=asyncio.Event();cancelled=asyncio.Event()
        async def resistant(payload,limits):
            entered.set()
            try:await release.wait()
            except asyncio.CancelledError:
                cancelled.set()
                await release.wait()
        adapter.action=resistant
        async def timeout(task,seconds):
            await entered.wait()
            raise TimeoutError()
        monkeypatch.setattr(ai_dispatch,'await_adapter',timeout)
        with pytest.raises(ai_dispatch.AIError) as exc:
            await ai_dispatch.generate(dataset,version,preview,user,token)
        assert exc.value.status==504
        await cancelled.wait()
        assert user in ai_dispatch.quota.active
        try:
            with pytest.raises(ai_dispatch.AIError) as exc:
                await ai_dispatch.generate(dataset,version,preview,user,token)
            assert exc.value.status==429 and adapter.calls==1
        finally:
            release.set()
            for _ in range(3):await asyncio.sleep(0)
        assert user not in ai_dispatch.quota.active
    asyncio.run(scenario())


def test_provider_error_mapping_survives_orchestration(configured):
    (engine,dataset,version,user,token),preview,adapter=configured
    async def fail(payload,limits):raise ai_dispatch.AIError(429,'AI_PROVIDER_QUOTA',60)
    adapter.action=fail
    with client_for(token) as client:response=post(client,dataset,version,preview)
    check(response,429)
    assert response.json()['error']['code']=='AI_PROVIDER_QUOTA'
    assert response.headers['retry-after']=='60' and adapter.calls==1
