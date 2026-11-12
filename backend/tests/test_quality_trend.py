from nv01_fixtures import current_version_values
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from decimal import Decimal,localcontext
from contextlib import contextmanager
import pytest
from sqlalchemy import insert,update,select,event
from app.models import Dataset,DatasetVersion,QualityRun,QualityRule
from app.services.quality_trend import fingerprint,decimal_key
from app.services import quality_trend,quality_history
from app.services.quality_execution import RunError
from app import access
from test_ai_preview import setup,client_for
from test_ai_services import stored
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

SNAP=[{'id':10,'name':'original','rule_type':'required','columns':['code'],'config':{}},
      {'id':20,'name':'bounds','rule_type':'numeric_range','columns':['amount'],'config':{'min':'0','max':'100'}},
      {'id':30,'name':'pair','rule_type':'unique','columns':['code','amount'],'config':{}}]
DATA_TYPE={'id':40,'name':'integer code','rule_type':'data_type','columns':['code'],'config':{'type':'integer'}}


def test_fingerprint_legacy_golden_hashes():
    # Recorded from the pre-data_type implementation, independent of this code.
    assert fingerprint(SNAP)=='rules-v1:798fc76cd02327f705b04b96028863252e5f34a64a437cf4e9954d131afa4c3a'
    assert fingerprint([])=='rules-v1:9c7c062bdbb3b49c775b7d545cce0684f41f63682ca766e413c1a6d5e9041e39'


def test_fingerprint_data_type_config_columns_and_multiplicity():
    snapshot=deepcopy(SNAP)+[deepcopy(DATA_TYPE)]
    expected=fingerprint(snapshot)
    assert expected.startswith('rules-v2:')
    assert fingerprint([DATA_TYPE]).startswith('rules-v2:')
    same=deepcopy(snapshot[::-1])
    for rule in same:rule.update(id=999,name='renamed')
    same[1]['columns'].reverse()
    same[2]['config']={'max':'1e2','min':'-0.000'}
    assert fingerprint(same)==expected
    for kind in ('decimal','boolean'):
        changed=deepcopy(snapshot)
        changed[-1]['config']={'type':kind}
        assert fingerprint(changed)!=expected
    changed=deepcopy(snapshot)
    changed[-1]['columns']=['amount']
    assert fingerprint(changed)!=expected
    assert fingerprint(snapshot+[DATA_TYPE])!=expected
    assert fingerprint(snapshot+[SNAP[0]])!=expected


@pytest.mark.parametrize('config',[
    {},None,[],{'type':None},{'type':True},{'type':1},{'type':['integer']},
    {'type':'Integer'},{'type':'float'},{'type':'integer','scale':2},
])
def test_fingerprint_rejects_invalid_data_type_config(config):
    rule={**DATA_TYPE,'config':config}
    with pytest.raises(RunError) as exc:fingerprint(SNAP+[rule])
    assert exc.value.status==500 and exc.value.code=='INVALID_RULE_SNAPSHOT'


@pytest.mark.parametrize('columns',[[],['code','amount'],['code','code'],[''],[None],'code'])
def test_fingerprint_rejects_invalid_data_type_columns(columns):
    with pytest.raises(RunError) as exc:fingerprint([{**DATA_TYPE,'columns':columns}])
    assert exc.value.code=='INVALID_RULE_SNAPSHOT'


@pytest.mark.parametrize('kind',['allowed_values','pattern','unknown'])
def test_fingerprint_does_not_enable_other_proposed_types(kind):
    with pytest.raises(RunError) as exc:fingerprint([{**DATA_TYPE,'rule_type':kind}])
    assert exc.value.code=='INVALID_RULE_SNAPSHOT'


def test_fingerprint_equivalence_precision_and_duplicates():
    same=deepcopy(SNAP[::-1])
    for rule in same:rule.update(id=999,name='renamed')
    same[0]['columns'].reverse();same[1]['config']={'max':'1e2','min':'-0.000'}
    assert fingerprint(same)==fingerprint(SNAP)
    assert fingerprint(SNAP+[SNAP[0]])!=fingerprint(SNAP)
    for field,value in [('rule_type','unique'),('columns',['different']),('config',{'min':'0','max':'101'})]:
        changed=deepcopy(SNAP)
        target=1 if field=='config' else 0
        changed[target][field]=value
        assert fingerprint(changed)!=fingerprint(SNAP)
    with localcontext() as ctx:
        ctx.prec=2
        long='0.123456789012345678901234567890123456789'
        assert decimal_key(long)==decimal_key(long+'000')
        assert decimal_key(long)!=decimal_key(long[:-1]+'8')
        assert decimal_key('1e999999999')==decimal_key('10e999999998')
        assert len(str(decimal_key('1e999999999')))<40
        assert decimal_key('-0')==decimal_key('0e999999999')
    assert fingerprint(SNAP).startswith('rules-v1:')
    with pytest.raises(RunError):fingerprint([{'rule_type':'numeric_range','columns':['a'],'config':{'min':'NaN','max':'1'}}])


def add_run(c,version,when,snapshot=SNAP,status='completed',engine_version='quality-v1'):
    fields=dict(dataset_version_id=version,status=status,started_at=when,rule_snapshot=snapshot,engine_version=engine_version)
    if status=='completed':fields.update(finished_at=when+timedelta(seconds=1),total_rows=3,error_row_count=1,violation_count=2,error_row_rate=Decimal('33.3333'))
    elif status=='failed':fields.update(finished_at=when+timedelta(seconds=1),failure_code='RUN_FAILED',failure_message='failed')
    return c.execute(insert(QualityRun).values(**fields).returning(QualityRun.id)).scalar_one()


def test_trend_mixed_snapshot_fingerprints_and_engine_versions(setup):
    engine,dataset,version,user,token=setup
    when=datetime(2026,1,1,tzinfo=timezone.utc)
    mixed=deepcopy(SNAP)+[deepcopy(DATA_TYPE)]
    dated={'id':50,'name':'stored date','rule_type':'date_format','columns':['code'],'config':{'format':'DD/MM/YYYY'}}
    with engine.begin() as c:
        old=add_run(c,version,when)
        legacy_v2=add_run(c,version,when+timedelta(seconds=2),engine_version='quality-v2')
        new=add_run(c,version,when+timedelta(seconds=4),snapshot=mixed,engine_version='quality-v2')
        same_config_v3=add_run(c,version,when+timedelta(seconds=6),snapshot=mixed,engine_version='quality-v3')
        date_v3=add_run(c,version,when+timedelta(seconds=8),snapshot=mixed+[dated],engine_version='quality-v3')
        c.execute(insert(QualityRule).values(dataset_id=dataset,name='live data type',rule_type='data_type',columns=['code'],config={'type':'boolean'}))
    with client_for(token) as client:
        response=client.get(f'/api/datasets/{dataset}/quality-trend')
        assert response.status_code==200
        points=response.json()['points']
        assert [p['run_id'] for p in points]==[old,legacy_v2,new,same_config_v3,date_v3]
        assert [p['engine_version'] for p in points]==['quality-v1','quality-v2','quality-v2','quality-v3','quality-v3']
        assert points[0]['rule_set_fingerprint']==points[1]['rule_set_fingerprint']==fingerprint(SNAP)
        assert points[2]['rule_set_fingerprint']==fingerprint(mixed)
        assert points[2]['rule_count']==4
        assert points[2]['rule_set_fingerprint']==points[3]['rule_set_fingerprint']
        assert (points[2]['engine_version'],points[2]['rule_set_fingerprint'])!=(points[3]['engine_version'],points[3]['rule_set_fingerprint'])
        assert points[4]['rule_set_fingerprint']==fingerprint(mixed+[dated])
        assert points[4]['rule_set_fingerprint']!=points[3]['rule_set_fingerprint']
        assert quality_history.run_detail(dataset,new)['rule_snapshot']==mixed
        with engine.begin() as c:c.execute(update(QualityRule).values(config={'type':'decimal'}))
        assert client.get(f'/api/datasets/{dataset}/quality-trend').json()==response.json()


@pytest.mark.parametrize('role',['admin','data_steward'])
def test_trend_order_filter_history_and_snapshot(setup,role):
    engine,dataset,version,user,token=setup
    when=datetime(2026,1,1,tzinfo=timezone.utc)
    with engine.begin() as c:
        from app.models import User
        c.execute(update(User).where(User.id==user).values(role=role))
        v2=c.execute(insert(DatasetVersion).values(**current_version_values(c, dataset_id=dataset,version_number=2,original_filename='v2.csv',file_size_bytes=1,row_count=1,inferred_types=[])).returning(DatasetVersion.id)).scalar_one()
        old=add_run(c,version,when)
        a=add_run(c,v2,when+timedelta(days=2))
        b=add_run(c,version,when+timedelta(days=2))
        add_run(c,version,when+timedelta(days=5),status='running')
        add_run(c,version,when+timedelta(days=6),status='failed')
        c.execute(insert(QualityRule).values(dataset_id=dataset,name='unrelated live rule',rule_type='required',columns=['code'],config={}))
    with client_for(token) as client:
        base=f'/api/datasets/{dataset}/quality-trend'
        result=client.get(base,params={'limit':2}).json()
        assert result['total_completed']==3 and result['truncated']
        assert [x['run_id'] for x in result['points']]==[a,b]
        assert result['points'][0]['version_number']==2
        assert result['points'][0]['pass_rate']=='66.6667'
        assert result['points'][0]['error_row_rate']=='33.3333'
        assert result['points'][0]['rule_count']==3
        assert result['points'][0]['rule_set_fingerprint']==fingerprint(SNAP)
        assert 'rule_snapshot' not in result['points'][0]
        assert set(result['points'][0])=={'run_id','version_id','version_number','started_at','finished_at','engine_version','total_rows','error_row_count','violation_count','error_row_rate','pass_rate','rule_count','rule_set_fingerprint'}
        all_points=client.get(base).json()
        assert [x['run_id'] for x in all_points['points']]==[old,a,b] and not all_points['truncated']
        filtered=client.get(base,params={'version_id':version}).json()
        assert filtered['total_completed']==2 and [x['run_id'] for x in filtered['points']]==[old,b]
        # Existing read-only history contract remains unchanged; never run engine.
        history=quality_history.list_runs(dataset,None,1,20)
        assert history['total']==5 and history['items'][0]['status']=='failed'
        assert quality_history.run_detail(dataset,old)['rule_snapshot']==SNAP
        with engine.begin() as c:c.execute(update(QualityRule).values(name='changed',columns=['empty']))
        assert client.get(base).json()==all_points


def test_empty_queries_auth_and_errors(setup,monkeypatch):
    engine,dataset,version,user,token=setup
    base=f'/api/datasets/{dataset}/quality-trend'
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as anon:assert anon.get(base).status_code==401
    with client_for(token) as client:
        assert client.get(base).json()=={'dataset_id':dataset,'version_id':None,'limit':30,'total_completed':0,'truncated':False,'points':[]}
        for params in [{'limit':0},{'limit':101},{'limit':'x'},{'version_id':0}]:assert client.get(base,params=params).status_code==422
        assert client.get('/api/datasets/999999/quality-trend').status_code==404
        with engine.begin() as c:
            other=c.execute(insert(Dataset).values(name='other').returning(Dataset.id)).scalar_one()
        assert client.get(f'/api/datasets/{other}/quality-trend',params={'version_id':version}).status_code==404
        assert client.get(base,params={'version_id':999999}).status_code==404
        original=access.find_session
        def forbidden(*args):return {**original(*args),'role':'outside_allowlist'}
        with monkeypatch.context() as m:
            m.setattr(access,'find_session',forbidden)
            assert client.get(base).status_code==403
        @contextmanager
        def unavailable():
            raise ConnectionError('private details')
            yield
        monkeypatch.setattr(quality_trend,'catalog_connection',unavailable)
        response=client.get(base)
        assert response.status_code==503 and 'private' not in response.text


def test_count_points_repeatable_read(setup):
    engine,dataset,version,user,token=setup
    when=datetime(2026,1,1,tzinfo=timezone.utc)
    with engine.begin() as c:old=add_run(c,version,when)
    fired=[False]
    def concurrent(conn,cursor,statement,parameters,context,executemany):
        if not fired[0] and statement.startswith('SELECT count') and 'quality_runs' in statement:
            fired[0]=True
            with engine.begin() as c:add_run(c,version,when+timedelta(days=1))
    event.listen(engine.__class__,'after_cursor_execute',concurrent)
    try:result=quality_trend.quality_trend(dataset)
    finally:event.remove(engine.__class__,'after_cursor_execute',concurrent)
    assert fired[0] and result['total_completed']==1 and len(result['points'])==1
    assert result['points'][0]['run_id']==old
    assert quality_trend.quality_trend(dataset)['total_completed']==2


def test_rate_boundaries_and_limit_one(setup):
    engine,dataset,version,user,token=setup
    when=datetime(2026,1,1,tzinfo=timezone.utc)
    with engine.begin() as c:
        first=add_run(c,version,when);last=add_run(c,version,when)
        c.execute(update(QualityRun).where(QualityRun.id==first).values(error_row_count=0,violation_count=0,error_row_rate=Decimal('0')))
        c.execute(update(QualityRun).where(QualityRun.id==last).values(error_row_count=3,violation_count=3,error_row_rate=Decimal('100')))
    with client_for(token) as client:
        base=f'/api/datasets/{dataset}/quality-trend'
        response=client.get(base,params={'limit':100}).json()
        assert [x['pass_rate'] for x in response['points']]==['100.0000','0.0000']
        one=client.get(base,params={'limit':1}).json()
        assert one['points'][0]['run_id']==last and one['total_completed']==2 and one['truncated']


def test_fingerprint_long_bounds_without_context_rounding():
    a=deepcopy(SNAP);b=deepcopy(SNAP)
    value='0.123456789012345678901234567890123456789'
    a[1]['config']={'min':value,'max':'1e999999999'}
    b[1]['config']={'min':value+'000','max':'10e999999998'}
    with localcontext() as ctx:
        ctx.prec=2
        assert fingerprint(a)==fingerprint(b)
        b[1]['config']['min']=value[:-1]+'8'
        assert fingerprint(a)!=fingerprint(b)
