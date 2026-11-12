"""NV-01 integration: disposable database only, including concurrent uploads."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import pytest
from sqlalchemy import select, text, update, func, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from authenticated_client import TestClient
from test_dataset_import import isolated_database
from app.main import app
from app.models import DatasetVersion, DatasetRow, QualityRule, QualityRun, DataBatch
from app.services import dataset_import


def post(client, url, **kwargs):
    if url.endswith('/batches'):
        from src01_fixtures import batch_payload
        kwargs['json']=batch_payload(client,kwargs['json'])
    r = client.post(url, **kwargs)
    assert r.status_code == 201, (url, r.status_code, r.text)
    return r.json()


def upload(c, ds, batch, content=b'code,amount\nA,10\nA,-1\nB,20', filename='data.csv'):
    return post(c, f'/api/datasets/{ds}/batches/{batch}/versions/import', files={'file':(filename,content)})


RULE = dict(name='Mã duy nhất',rule_type='unique',columns=['code'],config={},is_active=True)


def test_A_to_K(isolated_database, monkeypatch):
    with TestClient(app) as c:
        ds=post(c,'/api/datasets',json={'name':'NV-01 isolated QA'})['id']
        jan=post(c,f'/api/datasets/{ds}/batches',json={'name':'Tháng 01','period_label':'01/2026','copy_template_rules':False})['id']
        v1=upload(c,ds,jan)
        assert c.post(f'/api/datasets/{ds}/versions/{v1["version_id"]}/runs').status_code==422
        template=post(c,f'/api/datasets/{ds}/rules',json=RULE)
        rule=post(c,f'/api/datasets/{ds}/batches/{jan}/rules',json=RULE)
        feb=post(c,f'/api/datasets/{ds}/batches',json={'name':'Tháng 02','period_label':'02/2026'})['id']
        februle=c.get(f'/api/datasets/{ds}/batches/{feb}/rules').json()['items'][0]
        assert februle['id'] not in (rule['id'],template['id'])
        assert c.patch(f'/api/datasets/{ds}/batches/{feb}/rules/{februle["id"]}',json={'is_active':False}).status_code==200
        assert c.get(f'/api/datasets/{ds}/batches/{jan}/rules').json()['items'][0]['is_active']
        assert c.get(f'/api/datasets/{ds}/rules').json()['items'][0]['is_active']
        assert c.patch(f'/api/datasets/{ds}/rules/{template["id"]}',json={'name':'Mẫu mới'}).status_code==200
        assert c.get(f'/api/datasets/{ds}/batches/{jan}/rules').json()['items'][0]['name']==RULE['name']
        assert c.get(f'/api/datasets/{ds}/batches/{feb}/rules').json()['items'][0]['name']==RULE['name']
        run1=post(c,f'/api/datasets/{ds}/versions/{v1["version_id"]}/runs')
        detail=c.get(f'/api/datasets/{ds}/runs/{run1["run_id"]}').json()
        assert detail['schema_snapshot'][0]['name']=='code'
        assert detail['batch_rules_revision']==2 and not detail['rules_changed']
        errors=c.get(f'/api/datasets/{ds}/runs/{run1["run_id"]}/violations').json()['items']
        assert [e['row_number'] for e in errors]==[1,2] and all(e['related_rows']==[1,2] for e in errors)
        v2=upload(c,ds,jan,b'code,amount\nA,10\nC,20')
        v3=upload(c,ds,jan,b'code,amount\nA,10\nC,20')
        assert [v1['version_number'],v2['version_number'],v3['version_number']]==[1,2,3]
        febv1=upload(c,ds,feb,b'code,amount\nA,30')
        assert febv1['version_number']==1
        assert c.patch(f'/api/datasets/{ds}/batches/{feb}/rules/{februle["id"]}',json={'is_active':True}).status_code==200
        februn=post(c,f'/api/datasets/{ds}/versions/{febv1["version_id"]}/runs')
        assert februn['error_row_count']==0  # A in January is not a duplicate here.
        dash=c.get(f'/api/batch-dashboard?batch_id={jan}&batch_id={feb}').json()
        assert dash['total_rows']==1 and dash['assessed_batches']==1
        assert next(i for i in dash['items'] if i['batch_id']==jan)['status']=='UNCHECKED'
        run3=post(c,f'/api/datasets/{ds}/versions/{v3["version_id"]}/runs')
        # New run of same version must not be counted twice.
        post(c,f'/api/datasets/{ds}/versions/{v3["version_id"]}/runs')
        dash=c.get(f'/api/batch-dashboard?batch_id={jan}&batch_id={feb}').json()
        assert dash['total_rows']==3 and dash['assessed_batches']==2
        assert c.patch(f'/api/datasets/{ds}/batches/{jan}/rules/{rule["id"]}',json={'name':'Mã duy nhất sửa tên'}).status_code==200
        old=c.get(f'/api/datasets/{ds}/runs/{run1["run_id"]}').json()
        assert old['rule_snapshot']==detail['rule_snapshot'] and old['rules_changed']
        after=post(c,f'/api/datasets/{ds}/versions/{v3["version_id"]}/runs')
        comparison=c.get(f'/api/datasets/{ds}/run-comparison?a_run_id={run1["run_id"]}&b_run_id={after["run_id"]}').json()
        assert not comparison['comparable'] and comparison['delta'] is None and 'RULE_REVISION_DIFFERENT' in comparison['non_comparable_reasons']
        comparison=c.get(f'/api/datasets/{ds}/run-comparison?a_run_id={run3["run_id"]}&b_run_id={februn["run_id"]}').json()
        assert not comparison['comparable'] and 'BATCH_DIFFERENT' in comparison['non_comparable_reasons']
        # G: rejected parse/schema and injected database insert failure preserve current.
        assert c.post(f'/api/datasets/{ds}/batches/{jan}/versions/import',files={'file':('bad.csv',b'other\nx')}).status_code==422
        original=dataset_import.infer_types
        def broken(*args): raise RuntimeError('test failure before commit')
        monkeypatch.setattr(dataset_import,'infer_types',broken)
        with pytest.raises(RuntimeError):
            from app.services.csv_reader import parse_csv
            dataset_import.import_version(ds,parse_csv(b'code,amount\nZ,1'),'fail.csv',jan)
        monkeypatch.setattr(dataset_import,'infer_types',original)
        def fail_rows(conn,cursor,statement,parameters,context,executemany):
            if statement.startswith('INSERT INTO dataset_rows'):
                raise RuntimeError('injected after current version switched')
        event.listen(Engine,'before_cursor_execute',fail_rows)
        try:
            with pytest.raises(RuntimeError):
                dataset_import.import_version(ds,parse_csv(b'code,amount\nZ,1'),'fail-in-transaction.csv',jan)
        finally:
            event.remove(Engine,'before_cursor_execute',fail_rows)
        with isolated_database.connect() as conn:
            assert conn.execute(select(DatasetVersion.id).where(DatasetVersion.batch_id==jan,DatasetVersion.is_current)).scalar_one()==v3['version_id']
        # H: lock/unique/deferred constraints guarantee one current at commit.
        def concurrent_upload(_):
            with TestClient(app) as other: return upload(other,ds,jan,b'code,amount\nA,1')
        with ThreadPoolExecutor(max_workers=2) as pool: uploaded=list(pool.map(concurrent_upload,range(2)))
        assert sorted(v['version_number'] for v in uploaded)==[4,5]
        versions=c.get(f'/api/datasets/{ds}/batches/{jan}').json()['versions']
        assert sum(v['is_current'] for v in versions)==1 and versions[0]['is_current']
        assert c.get(f'/api/datasets/{ds}/runs?batch_id={jan}').json()['total']==4
        assert c.get(f'/api/datasets/{ds}/versions/{v1["version_id"]}/rows').status_code==200
        assert c.get(f'/api/datasets/{ds}/runs/{run1["run_id"]}/report').status_code==200
        assert c.get(f'/api/datasets/{ds}/runs/{run1["run_id"]}/report.xlsx').status_code==200
        assert c.get(f'/api/datasets/{ds}/runs/{run1["run_id"]}/quality-summary').status_code==200
        # Existing Origin/CSRF and batch membership protections remain enforced.
        assert c.post(f'/api/datasets/{ds}/batches/{jan}/rules',json=RULE,headers={'Origin':'http://evil.invalid'}).status_code==403
        assert c.get(f'/api/datasets/{ds+1000}/batches/{jan}/rules').status_code==404
        with pytest.raises(IntegrityError):
            with isolated_database.begin() as conn:
                conn.execute(update(DatasetVersion).where(DatasetVersion.batch_id==jan).values(is_current=False))


def test_fixture_exact_answer(isolated_database):
    root=Path('D:/User_File/ChatGPT/DACN/qa_test_data')
    assert root.is_dir(), 'Reference fixture is required for this acceptance test'
    expected=json.loads((root/'expected_results.json').read_text(encoding='utf-8'))
    with TestClient(app) as c:
        ds=post(c,'/api/datasets',json={'name':'NV-01 fixture students'})['id']
        batch=post(c,f'/api/datasets/{ds}/batches',json={'name':'01/2026','copy_template_rules':False})['id']
        raw=upload(c,ds,batch,(root/'v1.0_raw.csv').read_bytes())
        columns=c.get(f'/api/datasets/{ds}').json()['columns']
        rules=[dict(name=f'{col["name"]} bắt buộc',rule_type='required',columns=[col['name']],config={}) for col in columns]
        rules += [dict(name='Mã duy nhất',rule_type='unique',columns=['ma_sinh_vien'],config={}),
            dict(name='Email trường',rule_type='pattern',columns=['email'],config={'dialect':'re2-v1','pattern':r'[A-Za-z0-9._%+-]+@hcmut\.edu\.vn'}),
            dict(name='Điện thoại',rule_type='pattern',columns=['so_dien_thoai'],config={'dialect':'re2-v1','pattern':r'0[0-9]{9}'}),
            dict(name='Ngày sinh',rule_type='date_format',columns=['ngay_sinh'],config={'format':'YYYY-MM-DD','min':'1900-01-01','max':'2026-11-08'}),
            dict(name='Điểm 0..10',rule_type='numeric_range',columns=['diem_tong_ket'],config={'min':'0','max':'10'})]
        for rule in rules: post(c,f'/api/datasets/{ds}/batches/{batch}/rules',json=rule)
        for name,version in [('v1.0_raw.csv',raw),('v1.1_fixed.csv',None)]:
            version=version or upload(c,ds,batch,(root/name).read_bytes())
            run=post(c,f'/api/datasets/{ds}/versions/{version["version_id"]}/runs')
            answer=expected[name]
            assert (run['total_rows'],run['error_row_count'],run['violation_count'])==(answer['total_rows'],answer['violated_rows'],answer['total_violations'])
            errors=c.get(f'/api/datasets/{ds}/runs/{run["run_id"]}/violations?page_size=100').json()['items']
            assert {e['row_number'] for e in errors}=={e['record'] for e in answer['errors']}
            assert run['error_row_rate']==('75.0000' if name=='v1.0_raw.csv' else '16.6667')
            counts={row['record']:row['violations'] for row in answer['errors']}
            assert {number:sum(e['row_number']==number for e in errors) for number in counts}==counts
