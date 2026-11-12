from nv01_fixtures import batch_rule_path
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path

import pytest
from sqlalchemy import select,update,delete,insert,event
from fastapi.testclient import TestClient
from fastapi.encoders import jsonable_encoder
from app.main import app
from app.models import Dataset,DatasetRow,DatasetVersion,QualityRule,QualityRun,QualityViolation,User
from app.services import quality_history,quality_engine,report_excel,dataset_catalog
from app.services.quality_execution import RunError
from test_data_type_backend import context
from test_dataset_import import isolated_database
from test_sessions_csrf import settings
from xlsx_reader import read_xlsx,NS


@pytest.fixture
def exported(context):
    engine,client,_,user=context
    csv=b'code,amount,status,event_date\n001,1.234567890123456789012345,NEW,2024-02-29\n001,-1,new,2023-02-29\n"",2,DONE,2026-2-01\n001,3,NEW,2026-12-31\n'
    imported=client.post(batch_rule_path(client, '/api/datasets/import'),data={'name':'Excel isolated'},files={'file':('report.csv',csv)}).json()
    dataset,version=imported['dataset_id'],imported['version_id']
    base=f'/api/datasets/{dataset}'
    cases=[('required',['code'],{}),('unique',['code','status'],{}),('numeric_range',['amount'],{'min':'0.000000000000000000000001','max':'2.000000000000000000000001'}),('data_type',['amount'],{'type':'integer'}),('date_format',['event_date'],{'format':'YYYY-MM-DD'}),('allowed_values',['status'],{'values':['NEW','DONE']})]
    rules=[]
    for kind,columns,config in cases:
        response=client.post(batch_rule_path(client, base+'/rules'),json={'name':kind,'rule_type':kind,'columns':columns,'config':config})
        assert response.status_code==201;rules.append(response.json())
    response=client.post(batch_rule_path(client, base+f'/versions/{version}/runs'));assert response.status_code==201
    run=response.json()['run_id'];url=base+f'/runs/{run}/report'
    return engine,client,dataset,version,run,rules,url,user


def test_six_types_snapshot_metadata_json_and_workbook(exported,monkeypatch):
    engine,client,dataset,version,run,rules,url,_=exported
    original=quality_history.export_report(dataset,run)
    def no_engine(*args,**kwargs):raise AssertionError('Export must not run engine')
    monkeypatch.setattr(quality_engine,'check_quality',no_engine)
    with engine.begin() as c:
        c.execute(update(Dataset).where(Dataset.id==dataset).values(name='=SUM(1,2)',description='  Tiếng Việt 日本語 😀  ',source=None,owner='@owner'))
        c.execute(update(QualityRule).where(QualityRule.dataset_id==dataset).values(name='changed',config={}))
    expected=quality_history.export_report(dataset,run)
    fixed=deepcopy(expected)
    monkeypatch.setattr(quality_history,'export_report',lambda *a,**k:deepcopy(fixed))
    response=client.get(batch_rule_path(client, url))
    assert response.status_code==200 and response.json()==jsonable_encoder(fixed)
    assert response.content==json.dumps(jsonable_encoder(fixed),ensure_ascii=False,allow_nan=False,indent=2).encode()
    assert 'Tiếng Việt'.encode() in response.content and b'\n  "report_schema_version"' in response.content
    response=client.get(batch_rule_path(client, url+'.xlsx'),params={'page_size':1,'row_number':999,'rule_id_snapshot':999})
    assert response.status_code==200
    assert response.headers['content-type']==report_excel.XLSX_MIME
    assert response.headers['content-disposition']==f'attachment; filename="dataset-{dataset}-run-{run}-report.xlsx"'
    sheets=read_xlsx(response.content)
    assert list(sheets)==['Tổng quan','Chi tiết lỗi','Quy tắc đã áp dụng']
    overview=dict(sheets['Tổng quan']['rows'][1:]);assert overview['Tên dataset']=='=SUM(1,2)'
    assert overview['Nguồn tại thời điểm xuất']=='null' and overview['Mô tả tại thời điểm xuất']=='  Tiếng Việt 日本語 😀  '
    assert 'tại thời điểm xuất' in overview['Nguồn metadata'] and 'nhiều vi phạm' in overview['Lưu ý thống kê']
    assert overview['Tỷ lệ lỗi']==expected['run']['error_row_rate']+'%'
    assert datetime.fromisoformat(overview['Bắt đầu']).utcoffset() is not None
    assert datetime.fromisoformat(overview['Thời điểm xuất']).utcoffset() is not None
    error_rows=sheets['Chi tiết lỗi']['rows'][1:];assert len(error_rows)==len(expected['violations'])
    snapshots=original['rule_snapshot'];by_id={s['id']:s for s in snapshots}
    for row,item in zip(error_rows,expected['violations']):
        assert row[0]==str(item['row_number']) and row[1]==by_id[item['rule_id_snapshot']]['name']
        assert json.loads(row[3])==item['columns'] and json.loads(row[4])==item['values']
        assert row[5]==report_excel.expected_condition(by_id[item['rule_id_snapshot']])
        assert row[6:]==[item['error_code'],item['message']]
    unique=[row for row in error_rows if '(unique)' in row[2]]
    assert len(unique)==2 and all(json.loads(row[3])==['code','status'] for row in unique)
    rule_rows=sheets['Quy tắc đã áp dụng']['rows'][1:];assert len(rule_rows)==6
    assert [json.loads(row[5]) for row in rule_rows]==[s['config'] for s in snapshots]
    assert all(s['pane'].attrib['topLeftCell']=='A2' for s in sheets.values())
    for name in ['Chi tiết lỗi','Quy tắc đã áp dụng']:assert sheets[name]['filter'] is not None


def test_more_than_page_exact_values_and_formula_text(exported):
    engine,client,_,_,run,rules,url,_=exported
    values=['001', '  x\r\ny  ',None,'','   ','=SUM(1,2)','+12','-001','@a','123456789012345678901234567890','1.00000000000000000000001','日本語 😀','_x000D_']
    with engine.begin() as c:
        c.execute(delete(QualityViolation).where(QualityViolation.run_id==run))
        c.execute(update(QualityRun).where(QualityRun.id==run).values(total_rows=26,error_row_count=26,violation_count=26,error_row_rate=100))
        c.execute(insert(QualityViolation),[dict(run_id=run,rule_id_snapshot=rules[1]['id'],rule_type='unique',rule_order=2,row_number=i+1,columns=['code','status'],values=[values[i%len(values)],'001'],error_code='UNIQUE_DUPLICATE',message='=không thay\r\n + - @ _x000D_') for i in range(26)])
    response=client.get(batch_rule_path(client, url+'.xlsx'),params={'page_size':1});assert response.status_code==200
    rows=read_xlsx(response.content)['Chi tiết lỗi']['rows'][1:]
    assert len(rows)==26
    for i,row in enumerate(rows):
        assert json.loads(row[4])==[values[i%len(values)],'001']
        assert row[7]=='=không thay\r\n + - @ _x000D_'
    assert len(client.get(batch_rule_path(client, url)).json()['violations'])==26


def test_empty_completed_and_not_completed_not_found(exported):
    engine,client,dataset,_,run,_,url,_=exported
    with engine.begin() as c:
        c.execute(delete(QualityViolation).where(QualityViolation.run_id==run))
        c.execute(update(QualityRun).where(QualityRun.id==run).values(error_row_count=0,violation_count=0,error_row_rate=0))
    response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==200
    sheets=read_xlsx(response.content);assert len(sheets)==3
    assert sheets['Chi tiết lỗi']['rows'][1]==['Không phát hiện vi phạm.']
    assert dict(sheets['Tổng quan']['rows'][1:])['Tỷ lệ đạt']=='100.0000%'
    for path in [f'/api/datasets/999999/runs/{run}/report.xlsx',f'/api/datasets/{dataset}/runs/999999/report.xlsx']:
        assert client.get(batch_rule_path(client, path)).status_code==404
    other=client.post(batch_rule_path(client, '/api/datasets/import'),data={'name':'other'},files={'file':('other.csv',b'a\n1')}).json()['dataset_id']
    assert client.get(batch_rule_path(client, f'/api/datasets/{other}/runs/{run}/report.xlsx')).status_code==404
    with engine.begin() as c:
        c.execute(update(QualityRun).where(QualityRun.id==run).values(status='running',finished_at=None,total_rows=None,error_row_count=None,violation_count=None,error_row_rate=None))
    assert client.get(batch_rule_path(client, url+'.xlsx')).status_code==409
    with engine.begin() as c:
        c.execute(update(QualityRun).where(QualityRun.id==run).values(status='failed',finished_at=datetime.now(timezone.utc),failure_code='RUN_FAILED',failure_message='private'))
    assert client.get(batch_rule_path(client, url+'.xlsx')).status_code==409


@pytest.mark.parametrize('role',['admin','data_steward'])
def test_permissions_database_and_safe_library_failure(exported,monkeypatch,role):
    engine,client,_,_,_,_,url,user=exported
    with engine.begin() as c:c.execute(update(User).where(User.id==user).values(role=role))
    assert client.get(batch_rule_path(client, url+'.xlsx'),headers={'Origin':'http://evil','X-CSRF-Token':'not-required-for-get'}).status_code==200
    with TestClient(app) as anon:assert anon.get(url+'.xlsx').status_code==401
    with monkeypatch.context() as m:
        m.setattr(report_excel,'workbook_bytes',lambda data:(_ for _ in ()).throw(OSError('secret SQL SELECT')))
        response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==503
        assert response.json()['error']['code']=='XLSX_EXPORT_FAILED' and 'secret' not in response.text and 'SELECT' not in response.text
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://test:secret@127.0.0.1:65432/test')
    response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==503 and 'secret' not in response.text


@pytest.mark.parametrize('bad,code',[('x'*32768,'XLSX_CELL_LIMIT'),('😀'*16384,'XLSX_CELL_LIMIT'),('a\n'*254,'XLSX_CELL_LIMIT'),('bad\x0b','XLSX_INVALID_CHARACTER'),('bad\uffff','XLSX_INVALID_CHARACTER'),('bad\ud800','XLSX_INVALID_CHARACTER')],ids=['long_ascii','long_emoji','linefeeds','vertical_tab','noncharacter','surrogate'])
def test_cell_limits_fail_with_json_guidance(exported,monkeypatch,bad,code):
    _,client,dataset,_,run,_,url,_=exported
    data=quality_history.export_report(dataset,run);data['violations'][0]['message']=bad
    monkeypatch.setattr(quality_history,'export_report',lambda *a,**k:data)
    response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==422
    assert response.json()['error']['code']==code and 'JSON' in response.json()['error']['message']
    assert 'content-disposition' not in response.headers


def test_row_source_and_output_limits_do_not_truncate(exported,monkeypatch):
    _,client,dataset,_,run,_,url,_=exported
    for limits in [{'violations':1,'rules':100,'bytes':9999999},{'violations':100,'rules':1,'bytes':9999999},{'violations':100,'rules':100,'bytes':1}]:
        monkeypatch.setattr(report_excel,'EXPORT_LIMITS',limits)
        response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==413 and response.json()['error']['code']=='XLSX_EXPORT_LIMIT'
        assert len(client.get(batch_rule_path(client, url)).json()['violations'])>1
    monkeypatch.setattr(report_excel,'EXPORT_LIMITS',{'violations':100,'rules':100,'bytes':9999999})
    with monkeypatch.context() as m:
        m.setattr(report_excel,'EXCEL_ROWS',2)
        assert client.get(batch_rule_path(client, url+'.xlsx')).json()['error']['code']=='XLSX_ROW_LIMIT'
    with monkeypatch.context() as m:
        m.setattr(report_excel,'MAX_RENDERED_BYTES',1000)
        response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==413 and response.json()['error']['code']=='XLSX_EXPORT_LIMIT'
        assert 'content-disposition' not in response.headers
    monkeypatch.setattr(report_excel,'MAX_OUTPUT_BYTES',1)
    assert client.get(batch_rule_path(client, url+'.xlsx')).json()['error']['code']=='XLSX_EXPORT_LIMIT'


def test_boundary_cell_and_character_integrity():
    report_excel.check_cell('a'*32767)
    report_excel.check_cell('😀'*16383+'a')
    report_excel.check_cell('\n'*253)
    for value in ['\t','\r','\n','Tiếng Việt','  ','_x000D_']:
        report_excel.check_cell(value)
    with pytest.raises(RunError):report_excel.check_characters({'values':['\x01']})

def test_forbidden_role_and_revoked_session(exported,monkeypatch):
    from app import access
    from app.models import Session
    from app.services.auth_sessions import token_hash
    engine,client,_,_,_,_,url,_=exported
    with monkeypatch.context() as m:
        m.setattr(access,'find_session',lambda *args,**kwargs:{'role':'viewer'})
        for suffix in ['', '.xlsx']:assert client.get(batch_rule_path(client, url+suffix)).status_code==403
    with engine.begin() as c:
        c.execute(update(Session).where(Session.token_hash==token_hash(client.cookies.get('datalens_session'))).values(revoked_at=datetime.now(timezone.utc)))
    for suffix in ['', '.xlsx']:assert client.get(batch_rule_path(client, url+suffix)).status_code==401


def test_excel_repeatable_read_and_midstream_budget(exported,monkeypatch):
    engine,client,dataset,_,run,_,url,_=exported
    old=dataset_catalog.create_engine;changed=[]
    def factory(*args,**kwargs):
        assert kwargs['isolation_level']=='REPEATABLE READ'
        target=old(*args,**kwargs)
        @event.listens_for(target,'after_cursor_execute')
        def concurrent(connection,cursor,statement,parameters,context,executemany):
            if not changed and 'quality_runs' in statement:
                changed.append(True)
                with engine.begin() as c:c.execute(update(Dataset).where(Dataset.id==dataset).values(name='concurrent metadata'))
        return target
    with monkeypatch.context() as m:
        m.setattr(dataset_catalog,'create_engine',factory)
        response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==200
        assert dict(read_xlsx(response.content)['Tổng quan']['rows'][1:])['Tên dataset']=='Excel isolated'
    assert changed
    data=quality_history.export_report(dataset,run);first=data['violations'][0];data['violations']=[]
    allowance=len(json.dumps(data,ensure_ascii=False,default=str,separators=(',',':')).encode())+len(json.dumps(first,ensure_ascii=False,separators=(',',':')).encode())+1
    monkeypatch.setattr(report_excel,'EXPORT_LIMITS',{'violations':100,'rules':100,'bytes':allowance})
    response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==413 and 'JSON' in response.json()['error']['message']
    assert len(client.get(batch_rule_path(client, url)).json()['violations'])>1


def test_maximum_cells_round_trip(exported,monkeypatch):
    _,client,dataset,_,run,_,url,_=exported
    data=quality_history.export_report(dataset,run)
    for value in ['a'*32767,'😀'*16383+'a','\n'*253]:
        data['violations'][0]['message']=value
        monkeypatch.setattr(quality_history,'export_report',lambda *args,**kwargs:deepcopy(data))
        response=client.get(batch_rule_path(client, url+'.xlsx'));assert response.status_code==200
        assert read_xlsx(response.content)['Chi tiết lỗi']['rows'][1][7]==value
