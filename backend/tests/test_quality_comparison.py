from nv01_fixtures import current_version_values
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, update, select, func, event, text
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.models import Dataset, DatasetVersion, DatasetRow, DatasetColumn, QualityRule, QualityRun, QualityViolation, User
from app.services import quality_comparison as comparison
from app.services.quality_trend import fingerprint
from app.services.quality_execution import RunError
from app.services.auth_sessions import create_session, revoke_session
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

SNAP = [{'id': 2, 'name': 'Code required', 'rule_type': 'required', 'columns': ['code'], 'config': {}},
        {'id': 3, 'name': 'Amount 0 to 100', 'rule_type': 'numeric_range', 'columns': ['amount'], 'config': {'min': '0', 'max': '100'}}]
WHEN = datetime(2026, 1, 1, tzinfo=timezone.utc)


def add_run(c, version, snapshot=SNAP, engine='quality-v1', status='completed', rows=4, errors=2, violations=3, rate='50.0000'):
    fields = dict(dataset_version_id=version, started_at=WHEN, status=status, engine_version=engine, rule_snapshot=snapshot)
    if status == 'completed':
        fields.update(finished_at=WHEN+timedelta(seconds=1), total_rows=rows, error_row_count=errors,
                      violation_count=violations, error_row_rate=Decimal(rate))
    elif status == 'failed':
        fields.update(finished_at=WHEN+timedelta(seconds=1), failure_code='RUN_FAILED', failure_message='Safe failure')
    return c.execute(insert(QualityRun).values(**fields).returning(QualityRun.id)).scalar_one()


@pytest.fixture
def pair(isolated_database, settings):
    engine = isolated_database
    with engine.begin() as c:
        datasets = [c.execute(insert(Dataset).values(name=name).returning(Dataset.id)).scalar_one() for name in ['comparison', 'other']]
        versions = [c.execute(insert(DatasetVersion).values(**current_version_values(c, dataset_id=dataset, version_number=number,
            original_filename=filename, file_size_bytes=100, row_count=rows, inferred_types=[]))
            .returning(DatasetVersion.id)).scalar_one() for dataset,number,filename,rows in
            [(datasets[0],1,'before.csv',4),(datasets[0],2,'after.csv',8),(datasets[1],1,'secret.csv',4)]]
        a=add_run(c,versions[0]); b=add_run(c,versions[1],rows=8,rate='25.0000')
        other=add_run(c,versions[2])
        user=c.execute(insert(User).values(username='compare_user',password_hash='fixture-only',role='admin').returning(User.id)).scalar_one()
        token=create_session(c,user)['token']
    return engine,datasets,versions,a,b,other,user,token


def client_for(token):
    client=TestClient(app)
    client.cookies.set('datalens_session',token,path='/api')
    return client


def path(dataset):
    return f'/api/datasets/{dataset}/run-comparison'


def test_api_pair_reverse_same_run_and_unchanged_snapshots(pair):
    engine,datasets,versions,a,b,other,user,token=pair
    with engine.connect() as connection:
        batch_id = connection.execute(select(DatasetVersion.batch_id).where(DatasetVersion.id==versions[0])).scalar_one()
    with client_for(token) as client:
        for role in ('admin','data_steward'):
            with engine.begin() as c: c.execute(update(User).where(User.id==user).values(role=role))
            result=client.get(path(datasets[0]),params={'a_run_id':a,'b_run_id':b})
            assert result.status_code==200,result.text
            body=result.json()
            assert body['comparable'] and not body['same_run'] and body['non_comparable_reasons']==[]
            assert body['delta']==dict(total_rows=4,error_row_count=0,violation_count=0,error_row_rate='-25.0000',pass_rate='25.0000')
            assert body['a']['version']==dict(id=versions[0],version_number=1,original_filename='before.csv',batch_id=batch_id)
            assert body['b']['version']==dict(id=versions[1],version_number=2,original_filename='after.csv',batch_id=batch_id)
            assert body['a']['rule_snapshot']==body['b']['rule_snapshot']==SNAP
            assert body['a']['rule_set_fingerprint']=='rules-v1:6e1d08c0ad0fd73a9ab69975b78f1dc010013bca4be5bb944d7eb139649cce87'
            assert body['a']['started_at'].endswith('Z') or body['a']['started_at'].endswith('+00:00')
        swapped=client.get(path(datasets[0]),params={'a_run_id':b,'b_run_id':a}).json()
        assert swapped['delta']==dict(total_rows=-4,error_row_count=0,violation_count=0,error_row_rate='25.0000',pass_rate='-25.0000')
        same=client.get(path(datasets[0]),params={'a_run_id':a,'b_run_id':a}).json()
        assert same['same_run'] and same['comparable'] and same['delta']==dict(total_rows=0,error_row_count=0,violation_count=0,error_row_rate='0.0000',pass_rate='0.0000')
        with engine.begin() as c:
            c.execute(insert(QualityRule).values(dataset_id=datasets[0],name='current different rule',rule_type='required',columns=['new_column'],config={}))
        assert client.get(path(datasets[0]),params={'a_run_id':a,'b_run_id':b}).json()==body


def test_canonicalization_and_basis_gate(pair):
    engine,datasets,versions,a,b,other,user,token=pair
    unique={'id':4,'name':'pair','rule_type':'unique','columns':['a','b'],'config':{}}
    allowed={'id':5,'name':'set','rule_type':'allowed_values','columns':['code'],'config':{'values':['NEW','DONE','é']}}
    baseline=deepcopy(SNAP)+[unique,allowed]
    same=deepcopy(baseline[::-1])
    for i,rule in enumerate(same):rule.update(id=100+i,name='renamed')
    same[0]['config']['values'].reverse();same[1]['columns'].reverse()
    same[2]['config']={'min':'-0.00','max':'1e2'}
    changed=deepcopy(baseline);changed[0]['columns']=['other']
    duplicate=deepcopy(baseline)+[{**SNAP[0],'id':6}]
    variants=[(same,'quality-v1',[]),(baseline,'quality-v2',['ENGINE_VERSION_DIFFERENT']),
              (changed,'quality-v1',['RULE_SET_FINGERPRINT_DIFFERENT']),
              (duplicate,'quality-v2',['ENGINE_VERSION_DIFFERENT','RULE_SET_FINGERPRINT_DIFFERENT'])]
    for value in ('new',' NEW','e\u0301'):
        variant=deepcopy(baseline);variant[-1]['config']['values'][2]=value
        variants.append((variant,'quality-v1',['RULE_SET_FINGERPRINT_DIFFERENT']))
    for kind,config,changed_config in [
            ('data_type',{'type':'integer'},{'type':'decimal'}),
            ('date_format',{'format':'DD/MM/YYYY'},{'format':'MM/DD/YYYY'}),
            ('pattern',{'pattern':'SP[0-9]{4}','dialect':'re2-v1'},{'pattern':'[A-Z]{2}[0-9]{4}','dialect':'re2-v1'})]:
        variants.append((baseline+[{'id':6,'name':kind,'rule_type':kind,'columns':['code'],'config':config}],
                         'quality-v1',['RULE_SET_FINGERPRINT_DIFFERENT']))
        assert fingerprint([{'id':6,'name':kind,'rule_type':kind,'columns':['code'],'config':config}]) != fingerprint(
            [{'id':6,'name':kind,'rule_type':kind,'columns':['code'],'config':changed_config}])
    with engine.begin() as c:
        c.execute(update(QualityRun).where(QualityRun.id==a).values(rule_snapshot=baseline))
    with client_for(token) as client:
        for snapshot,engine_version,reasons in variants:
            with engine.begin() as c:
                c.execute(update(QualityRun).where(QualityRun.id==b).values(rule_snapshot=snapshot,engine_version=engine_version))
            body=client.get(path(datasets[0]),params={'a_run_id':a,'b_run_id':b}).json()
            assert body['non_comparable_reasons']==reasons
            assert body['comparable']==(not reasons)
            assert (body['delta'] is None)==bool(reasons)
            assert body['b']['rule_snapshot']==snapshot
        # Empty historical snapshots are valid, not fabricated hash defaults.
        with engine.begin() as c:
            c.execute(update(QualityRun).where(QualityRun.id.in_([a,b])).values(rule_snapshot=[],engine_version='quality-v1'))
        body=client.get(path(datasets[0]),params={'a_run_id':a,'b_run_id':b}).json()
        assert body['comparable'] and body['a']['rule_set_fingerprint']==fingerprint([])


def test_membership_status_validation_and_corrupt_snapshot(pair):
    engine,datasets,versions,a,b,other,user,token=pair
    with engine.begin() as c:
        running=add_run(c,versions[0],status='running');failed=add_run(c,versions[0],status='failed')
    with client_for(token) as client:
        for left,right in [(a,other),(other,a),(a,999999),(running,other)]:
            r=client.get(path(datasets[0]),params={'a_run_id':left,'b_run_id':right})
            assert r.status_code==404 and r.json()['error']['code']=='NOT_FOUND'
            assert 'secret.csv' not in r.text
        for right in (running,failed):
            r=client.get(path(datasets[0]),params={'a_run_id':a,'b_run_id':right})
            assert r.status_code==409 and r.json()['error']['code']=='RUN_NOT_COMPLETED'
        assert client.get(path(999999),params={'a_run_id':a,'b_run_id':b}).status_code==404
        for params in [{},{'a_run_id':a},{'a_run_id':0,'b_run_id':b},{'a_run_id':'x','b_run_id':b}]:
            assert client.get(path(datasets[0]),params=params).status_code==422
        assert client.get(path(0),params={'a_run_id':a,'b_run_id':b}).status_code==422
        for snapshot in [[{'id':2,'name':'safe','rule_type':'unknown','columns':['x'],'config':{}}],
                         [{**SNAP[0],'name':None}], [{**SNAP[0],'id':True}],
                         [{**SNAP[0],'config':{'SECRET_SQL':'SELECT private'}}],
                         [{**SNAP[1],'config':{'min':0.5,'max':'100'}}]]:
            with engine.begin() as c:c.execute(update(QualityRun).where(QualityRun.id==b).values(rule_snapshot=snapshot))
            r=client.get(path(datasets[0]),params={'a_run_id':a,'b_run_id':b})
            assert r.status_code==500 and r.json()['error']['code']=='INVALID_RUN_RESULT'
            assert 'SECRET_SQL' not in r.text and 'SELECT' not in r.text and 'delta' not in r.json()


def test_old_runs_read_only_consistent_transaction_and_no_heavy_reads(pair,monkeypatch):
    engine,datasets,versions,a,b,other,user,token=pair
    def no_execution(*args,**kwargs):raise AssertionError('Comparison must not execute quality checks')
    from app.services import quality_execution, quality_engine, quality_history
    monkeypatch.setattr(quality_execution,'execute_run',no_execution)
    monkeypatch.setattr(quality_engine,'check_quality',no_execution)
    monkeypatch.setattr(quality_history,'export_report',no_execution)
    with engine.begin() as c:
        for _ in range(121):add_run(c,versions[1])
    statements=[];writes=[]
    @contextmanager
    def connection():
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
            @event.listens_for(c,'after_cursor_execute')
            def after_read(c,cursor,statement,parameters,context,executemany):
                statements.append(statement)
                assert not any(table in statement.lower() for table in ('quality_violations','dataset_rows','quality_rules'))
                if statement.startswith('SELECT quality_runs.') and not writes:
                    assert c.exec_driver_sql('SHOW transaction_read_only').scalar_one()=='on'
                    with engine.begin() as writer:
                        writer.execute(update(DatasetVersion).where(DatasetVersion.id==versions[1]).values(original_filename='new-name.csv'))
                    writes.append(True)
            yield c
    monkeypatch.setattr(comparison,'catalog_connection',connection)
    before=None
    with engine.connect() as c:before=c.execute(select(func.count()).select_from(QualityRun)).scalar_one()
    result=comparison.compare_runs(datasets[0],a,b)
    assert result['b']['version']['original_filename']=='after.csv'
    assert comparison.compare_runs(datasets[0],a,b)['b']['version']['original_filename']=='new-name.csv'
    assert not any(s.lstrip().upper().startswith(('UPDATE','INSERT','DELETE')) for s in statements)
    with engine.connect() as c:assert c.execute(select(func.count()).select_from(QualityRun)).scalar_one()==before


def test_access_and_safe_database_errors(pair,monkeypatch):
    engine,datasets,versions,a,b,other,user,token=pair
    params={'a_run_id':a,'b_run_id':b}
    with TestClient(app) as anonymous:assert anonymous.get(path(datasets[0]),params=params).status_code==401
    from app import access
    original=access.find_session
    monkeypatch.setattr(access,'find_session',lambda *args:{'role':'unauthorized'})
    with client_for(token) as client:assert client.get(path(datasets[0]),params=params).status_code==403
    monkeypatch.setattr(access,'find_session',original)
    def broken():raise ConnectionError('SECRET password SELECT')
    monkeypatch.setattr(comparison,'catalog_connection',broken)
    with client_for(token) as client:
        r=client.get(path(datasets[0]),params=params)
        assert r.status_code==503 and r.json()['error']['code']=='DATABASE_UNAVAILABLE' and 'SECRET' not in r.text
    def sql_broken():raise SQLAlchemyError('SECRET SELECT')
    monkeypatch.setattr(comparison,'catalog_connection',sql_broken)
    with client_for(token) as client:
        r=client.get(path(datasets[0]),params=params)
        assert r.status_code==500 and r.json()['error']['code']=='DATABASE_ERROR' and 'SELECT' not in r.text
    with engine.begin() as c:revoke_session(c,token)
    with client_for(token) as client:assert client.get(path(datasets[0]),params=params).status_code==401


@pytest.mark.parametrize('change',[
    {'total_rows':None},{'total_rows':True},{'total_rows':0},{'error_row_count':5},{'violation_count':1},
    {'error_row_rate':None},{'error_row_rate':float('nan')},{'error_row_rate':Decimal('NaN')},
    {'error_row_rate':Decimal('Infinity')},{'error_row_rate':Decimal('100.0001')},
    {'error_row_rate':Decimal('33.33333')},{'finished_at':None},{'started_at':datetime(2026,1,1)},
    {'engine_version':''},{'rule_snapshot':None},{'rule_snapshot':[{'id':2,'name':'secret'}]},
])
def test_invalid_stored_result_maps_to_one_safe_code(change):
    row={'id':1,'dataset_version_id':1,'total_rows':4,'error_row_count':2,'violation_count':3,
         'error_row_rate':Decimal('50.0000'),'started_at':WHEN,'finished_at':WHEN+timedelta(seconds=1),
         'engine_version':'quality-v1','rule_snapshot':deepcopy(SNAP),**change}
    with pytest.raises(RunError) as error:comparison._side(row,{'id':1,'version_number':1,'original_filename':'file.csv'})
    assert error.value.status==500 and error.value.code=='INVALID_RUN_RESULT'
    assert 'secret' not in error.value.message


def test_decimal_precision_and_same_version(pair):
    engine,datasets,versions,a,b,other,user,token=pair
    with engine.begin() as c:
        c.execute(update(QualityRun).where(QualityRun.id==a).values(total_rows=3,error_row_count=1,violation_count=1,error_row_rate=Decimal('33.3333')))
        c.execute(update(QualityRun).where(QualityRun.id==b).values(dataset_version_id=versions[0],total_rows=3,error_row_count=2,violation_count=2,error_row_rate=Decimal('66.6667')))
    with localcontext() as ctx:
        ctx.prec=2
        result=comparison.compare_runs(datasets[0],a,b)
    assert result['a']['version']==result['b']['version']
    assert result['a']['pass_rate']=='66.6667' and result['b']['pass_rate']=='33.3333'
    assert result['delta']['error_row_rate']=='33.3334' and result['delta']['pass_rate']=='-33.3334'
