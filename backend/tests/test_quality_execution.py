from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, update, func, create_engine, event
from sqlalchemy.exc import IntegrityError
from psycopg.errors import CheckViolation
import pytest
from authenticated_client import TestClient
from app.main import app
from app.models import DatasetVersion, DatasetRow, QualityRun, QualityViolation, QualityRule
from app.services import quality_execution, quality_rules
from app.services.quality_engine import ENGINE_VERSION
from test_quality_results import stored
from test_dataset_import import isolated_database


def path(stored):
    engine,_,version,_,_=stored
    with engine.connect() as connection:
        dataset=connection.execute(select(DatasetVersion.dataset_id).where(DatasetVersion.id==version)).scalar_one()
    return f'/api/datasets/{dataset}/versions/{version}/runs'


def test_run_matches_written_answer(stored):
    engine,_,_,snapshot,expected=stored
    with TestClient(app) as client:
        response=client.post(path(stored))
    assert response.status_code==201
    result=response.json()
    assert (result['total_rows'],result['error_row_count'],result['violation_count'],result['error_row_rate'])==(4,2,3,'50.0000')
    assert result['status']=='completed' and result['duration_seconds']>=0
    with engine.connect() as connection:
        saved=connection.execute(select(QualityRun).where(QualityRun.id==result['run_id'])).mappings().one()
        assert saved['rule_snapshot']==snapshot and saved['engine_version']==ENGINE_VERSION
        errors=connection.execute(select(QualityViolation).where(QualityViolation.run_id==result['run_id']).order_by(QualityViolation.row_number,QualityViolation.rule_order)).mappings().all()
        assert [{'rule_id':e['rule_id_snapshot'],'rule_type':e['rule_type'],'row_number':e['row_number'],'columns':e['columns'],'values':e['values'],'code':e['error_code'],'message':e['message']} for e in errors]==expected['errors']


def test_pass_and_inactive_rules(stored):
    engine,_,version,snapshot,_=stored
    with engine.begin() as connection:
        connection.execute(update(QualityRule).where(QualityRule.id==snapshot[1]['id']).values(is_active=False))
        connection.execute(update(DatasetRow).where(DatasetRow.version_id==version,DatasetRow.row_number==1).values(values=['ok','101']))
    with TestClient(app) as client:
        response=client.post(path(stored))
    assert response.status_code==201
    result=response.json()
    assert result['error_row_count']==result['violation_count']==0 and result['error_row_rate']=='0.0000'
    with engine.connect() as connection:
        assert connection.execute(select(QualityRun.rule_snapshot).where(QualityRun.id==result['run_id'])).scalar_one()==snapshot[:1]


def test_no_rules_and_wrong_version(stored):
    engine,_,version,_,_=stored
    with engine.begin() as connection:
        connection.execute(update(QualityRule).values(is_active=False))
    with TestClient(app) as client:
        assert client.post(path(stored)).json()['error']['code']=='NO_ACTIVE_RULES'
        assert client.post(path(stored)).status_code==422
        assert client.post('/api/datasets/999999/versions/999999/runs').status_code==404
        assert client.post(path(stored).replace(f'/versions/{version}/','/versions/999999/')).status_code==404
        other=client.post('/api/datasets/import',data={'name':'other'},files={'file':('a.csv',b'a\n1')}).json()['dataset_id']
        assert client.post(f'/api/datasets/{other}/versions/{version}/runs').status_code==404
    with engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(QualityRun)).scalar_one()==1  # only fixture run


def test_snapshot_not_reread(stored,monkeypatch):
    engine,_,_,snapshot,_=stored
    original=quality_execution.check_quality
    def change_rule(header,rows,rules):
        with engine.begin() as connection:
            connection.execute(update(QualityRule).where(QualityRule.id==snapshot[1]['id']).values(name='new',config={'min':'-1000','max':'1000'}))
        return original(header,rows,rules)
    monkeypatch.setattr(quality_execution,'check_quality',change_rule)
    with TestClient(app) as client: result=client.post(path(stored)).json()
    assert result['violation_count']==3
    with engine.connect() as connection:
        assert connection.execute(select(QualityRun.rule_snapshot).where(QualityRun.id==result['run_id'])).scalar_one()==snapshot


@pytest.mark.parametrize('failure',['engine','saving','unrecordable'])
def test_failed_run_no_partial_violations(stored,monkeypatch,failure):
    engine,_,_,_,_=stored
    if failure in ['engine','unrecordable']:
        def fail(*args): raise RuntimeError('private SQL credentials')
        monkeypatch.setattr(quality_execution,'check_quality',fail)
    else:
        def factory(*args,**kwargs):
            target=create_engine(*args,**kwargs)
            @event.listens_for(target,'before_cursor_execute')
            def fail_completed(connection,cursor,statement,parameters,context,executemany):
                if statement.startswith('UPDATE quality_runs') and context.compiled_parameters[0].get('status')=='completed':
                    raise IntegrityError('private SQL',{},CheckViolation('private'))
            return target
        monkeypatch.setattr(quality_rules,'create_engine',factory)
    if failure=='unrecordable':
        def cannot_mark(*args): raise ConnectionError('private')
        monkeypatch.setattr(quality_execution,'mark_failed',cannot_mark)
    with TestClient(app) as client: response=client.post(path(stored))
    assert response.status_code==500 and 'private' not in response.text
    error=response.json()['error']
    assert error['failure_recorded'] is (failure!='unrecordable')
    with engine.connect() as connection:
        run=connection.execute(select(QualityRun).where(QualityRun.id==error['run_id'])).mappings().one()
        assert run['status']==('running' if failure=='unrecordable' else 'failed')
        assert run['total_rows'] is None
        if failure!='unrecordable': assert run['finished_at'] is not None and run['failure_code']=='RUN_FAILED'
        assert connection.execute(select(func.count()).select_from(QualityViolation).where(QualityViolation.run_id==error['run_id'])).scalar_one()==0


def test_two_independent_requests(stored):
    with TestClient(app) as client:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:client.post(path(stored)),range(2)))
    assert all(response.status_code==201 for response in responses)
    assert len({response.json()['run_id'] for response in responses})==2


def test_inconsistent_rows_and_db_offline(stored,monkeypatch):
    engine,_,version,_,_=stored
    with engine.begin() as connection:
        connection.execute(update(DatasetRow).where(DatasetRow.version_id==version,DatasetRow.row_number==4).values(row_number=5))
    with TestClient(app) as client:
        response=client.post(path(stored))
        assert response.status_code==500 and response.json()['error']['code']=='DATA_INCONSISTENT'
        url=path(stored)
        monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://test:example@127.0.0.1:65432/test')
        assert client.post(url).status_code==503
    with engine.connect() as connection:
        assert connection.execute(select(func.count()).select_from(QualityRun)).scalar_one()==1
