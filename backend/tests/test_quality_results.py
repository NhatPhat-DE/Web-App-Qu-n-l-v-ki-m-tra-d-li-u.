from nv01_fixtures import current_version_values
from copy import deepcopy
from decimal import Decimal
import pytest
from sqlalchemy import insert, select, update, func, event, create_engine
from sqlalchemy.exc import IntegrityError
from psycopg.errors import CheckViolation
from app.models import Dataset, DatasetColumn, DatasetVersion, DatasetRow, QualityRule, QualityRun, QualityViolation
from app.services.quality_results import complete_run, ResultValidationError
from app.services.quality_engine import ENGINE_VERSION
from app.services import quality_rules
from test_dataset_import import isolated_database


@pytest.fixture
def stored(isolated_database):
    with isolated_database.begin() as connection:
        dataset = connection.execute(insert(Dataset).values(name='results test').returning(Dataset.id)).scalar_one()
        connection.execute(insert(DatasetColumn), [{'dataset_id':dataset,'name':'a','position':1}, {'dataset_id':dataset,'name':'amount','position':2}])
        version = connection.execute(insert(DatasetVersion).values(**current_version_values(connection, dataset_id=dataset,version_number=1,original_filename='sample.csv',file_size_bytes=100,row_count=4,inferred_types=[])).returning(DatasetVersion.id)).scalar_one()
        connection.execute(insert(DatasetRow), [{'version_id':version,'row_number':number,'values':values} for number,values in enumerate([['','101'],['001','-1'],['日本語','0'],['  x\ny  ','100']],1)])
        snapshots=[]
        batch = connection.execute(select(DatasetVersion.batch_id).where(DatasetVersion.id==version)).scalar_one()
        for name,kind,columns,config in [('required a','required',['a'],{}),('range amount','numeric_range',['amount'],{'min':'0','max':'100'})]:
            identifier=connection.execute(insert(QualityRule).values(dataset_id=dataset,batch_id=batch,name=name,rule_type=kind,columns=columns,config=config).returning(QualityRule.id)).scalar_one()
            snapshots.append({'id':identifier,'name':name,'rule_type':kind,'columns':columns,'config':config})
        run=connection.execute(insert(QualityRun).values(dataset_version_id=version,rule_snapshot=snapshots,engine_version=ENGINE_VERSION).returning(QualityRun.id)).scalar_one()
    errors=[
        {'rule_id':snapshots[0]['id'],'rule_type':'required','row_number':1,'columns':['a'],'values':[''],'code':'REQUIRED_MISSING','message':'Giá trị bắt buộc đang thiếu.'},
        {'rule_id':snapshots[1]['id'],'rule_type':'numeric_range','row_number':1,'columns':['amount'],'values':['101'],'code':'NUMERIC_OUT_OF_RANGE','message':'Giá trị nằm ngoài khoảng đóng cho phép.'},
        {'rule_id':snapshots[1]['id'],'rule_type':'numeric_range','row_number':2,'columns':['amount'],'values':['-1'],'code':'NUMERIC_OUT_OF_RANGE','message':'Giá trị nằm ngoài khoảng đóng cho phép.'},
    ]
    return isolated_database,run,version,snapshots,{'row_count':4,'error_row_count':2,'violation_count':3,'error_row_rate':50.0,'errors':errors}


def test_save_full_result_and_snapshot(stored):
    engine,run,_,snapshot,result=stored
    original=deepcopy(result)
    saved=complete_run(run,result)
    assert saved['status']=='completed' and saved['finished_at'] is not None
    assert (saved['total_rows'],saved['error_row_count'],saved['violation_count'],saved['error_row_rate'])==(4,2,3,Decimal('50.0000'))
    with engine.begin() as connection:
        violations=connection.execute(select(QualityViolation).where(QualityViolation.run_id==run).order_by(QualityViolation.row_number,QualityViolation.rule_order)).mappings().all()
        actual=[{'rule_id':row['rule_id_snapshot'],'rule_type':row['rule_type'],'row_number':row['row_number'],'columns':row['columns'],'values':row['values'],'code':row['error_code'],'message':row['message']} for row in violations]
        assert actual==result['errors']
        connection.execute(update(QualityRule).where(QualityRule.id==snapshot[0]['id']).values(name='changed',is_active=False))
    with engine.connect() as connection:
        assert connection.execute(select(QualityRun.rule_snapshot).where(QualityRun.id==run)).scalar_one()==snapshot
        assert connection.execute(select(func.count()).select_from(QualityViolation).where(QualityViolation.run_id==run)).scalar_one()==3
    assert result==original
    with pytest.raises(ResultValidationError): complete_run(run,result)


def test_no_errors(stored):
    _,run,_,_,_=stored
    saved=complete_run(run,{'row_count':4,'error_row_count':0,'violation_count':0,'errors':[]})
    assert saved['status']=='completed'
    assert saved['total_rows']==4 and saved['error_row_count']==saved['violation_count']==0
    assert saved['error_row_rate']==Decimal('0.0000')


def test_decimal_rounding(stored):
    engine,run,version,_,result=stored
    with engine.begin() as connection:
        connection.execute(DatasetRow.__table__.delete().where(DatasetRow.version_id==version,DatasetRow.row_number==4))
        connection.execute(update(DatasetVersion).where(DatasetVersion.id==version).values(row_count=3))
    result.update(row_count=3,error_row_count=1,violation_count=1,errors=result['errors'][:1],error_row_rate=99.0)
    assert complete_run(run,result)['error_row_rate']==Decimal('33.3333')


@pytest.mark.parametrize('mutation',['counts','rows','rule','columns','values','duplicate'])
def test_invalid_result_preserves_running(stored,mutation):
    engine,run,_,_,result=stored
    if mutation=='counts': result['violation_count']=2
    elif mutation=='rows': result['row_count']=5
    elif mutation=='rule': result['errors'][0]['rule_id']=999999
    elif mutation=='columns': result['errors'][0]['columns']=['amount']
    elif mutation=='values': result['errors'][0]['values']=['changed']
    else:
        result['errors'].append(deepcopy(result['errors'][0]));result['violation_count']=4
    with pytest.raises(ResultValidationError): complete_run(run,result)
    with engine.connect() as connection:
        saved=connection.execute(select(QualityRun).where(QualityRun.id==run)).mappings().one()
        assert saved['status']=='running' and saved['total_rows'] is None and saved['error_row_rate'] is None
        assert connection.execute(select(func.count()).select_from(QualityViolation)).scalar_one()==0


def test_write_failure_rollback(stored,monkeypatch):
    engine,run,_,_,result=stored
    def factory(*args,**kwargs):
        target=create_engine(*args,**kwargs)
        @event.listens_for(target,'before_cursor_execute')
        def fail_update(connection,cursor,statement,parameters,context,executemany):
            if statement.startswith('UPDATE quality_runs'):
                raise IntegrityError('private',{},CheckViolation('private'))
        return target
    monkeypatch.setattr(quality_rules,'create_engine',factory)
    with pytest.raises(IntegrityError): complete_run(run,result)
    with engine.connect() as connection:
        saved=connection.execute(select(QualityRun).where(QualityRun.id==run)).mappings().one()
        assert saved['status']=='running' and saved['finished_at'] is None and saved['violation_count'] is None
        assert connection.execute(select(func.count()).select_from(QualityViolation)).scalar_one()==0


def test_original_error_strings(stored):
    engine,run,version,snapshot,_=stored
    original=['001','001','  Việt\n日本語  ','  Việt\n日本語  ']
    unique={'id':snapshot[0]['id'],'name':'unique a','rule_type':'unique','columns':['a'],'config':{}}
    with engine.begin() as connection:
        connection.execute(update(QualityRun).where(QualityRun.id==run).values(rule_snapshot=[unique]))
        for number,value in enumerate(original,1):
            connection.execute(update(DatasetRow).where(DatasetRow.version_id==version,DatasetRow.row_number==number).values(values=[value,'0']))
    result={'row_count':4,'error_row_count':4,'violation_count':4,'errors':[
        {'rule_id':unique['id'],'rule_type':'unique','row_number':number,'columns':['a'],'values':[value],'code':'UNIQUE_DUPLICATE','message':'Giá trị bị trùng.'}
        for number,value in enumerate(original,1)]}
    complete_run(run,result)
    with engine.connect() as connection:
        assert connection.execute(select(QualityViolation.values).where(QualityViolation.run_id==run).order_by(QualityViolation.row_number)).scalars().all()==[[value] for value in original]


def test_database_lifecycle_constraints(stored):
    engine,run,_,_,_=stored
    with engine.begin() as connection:
        for changes in [{'status':'completed'}, {'total_rows':0}, {'status':'failed'}, {'status':'unknown'}]:
            with pytest.raises(IntegrityError):
                with connection.begin_nested():
                    connection.execute(update(QualityRun).where(QualityRun.id==run).values(**changes))
