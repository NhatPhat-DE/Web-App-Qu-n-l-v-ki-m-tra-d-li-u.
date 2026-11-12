"""Create the explicitly requested QT-03A demo once via authenticated HTTP.

Run from backend after migration/restart. Refuse duplicate execution when the
verification artifact exists. Temporary local admin session is always revoked.
"""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from sqlalchemy import create_engine, select
from app.config import get_database_url
from app.models import Dataset, DatasetColumn, DatasetVersion, DatasetRow, QualityRule, QualityRun, QualityViolation, User
from app.services.auth_sessions import create_session, revoke_session
from app.services.csrf import session_csrf_token
from app.services.csv_reader import parse_csv
from app.services.quality_trend import fingerprint

SAMPLES = Path(__file__).resolve().parents[1] / 'samples'
artifact = SAMPLES / 'allowed_values_qt03a_verification.json'
if artifact.exists():
    raise SystemExit('Demo already recorded; refusing to create another dataset.')
expected = json.loads((SAMPLES / 'allowed_values_qt03a_expected.json').read_text(encoding='utf-8'))
before = json.loads((SAMPLES / 'allowed_values_qt03a_before.json').read_text(encoding='utf-8'))
parsed = parse_csv((SAMPLES / 'allowed_values_qt03a.csv').read_bytes())
assert parsed.row_count == 10 and parsed.rows == expected['rows']
engine = create_engine(get_database_url(), hide_parameters=True)
with engine.begin() as c:
    assert not c.execute(select(QualityRun.id).where(QualityRun.status == 'running')).all()
    admin = c.execute(select(User.id).where(User.role == 'admin', User.is_active.is_(True)).order_by(User.id)).scalars().first()
    assert admin is not None
    session = create_session(c, admin)
try:
    with httpx.Client(base_url='http://127.0.0.1:5173', timeout=60) as client:
        client.cookies.set('datalens_session', session['token'], path='/api')
        client.headers.update({'Origin': 'http://127.0.0.1:5173', 'X-CSRF-Token': session_csrf_token(session['token'])})
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            assert response.is_success, (method, path, response.status_code)
            return response.json()
        assert request('GET', '/api/auth/me')['user']['role'] == 'admin'
        imported = request('POST', '/api/datasets/import', data={'name': 'QT-03A Allowed Values Demo', 'source': 'samples/allowed_values_qt03a.csv'}, files={'file': ('allowed_values_qt03a.csv', (SAMPLES / 'allowed_values_qt03a.csv').read_bytes(), 'text/csv')})
        dataset, version = imported['dataset_id'], imported['version_id']
        assert imported['row_count'] == 10
        base = f'/api/datasets/{dataset}'
        rule = request('POST', base + '/rules', json={'name':'Allowed status NEW DONE HOLD','rule_type':'allowed_values','columns':['status'],'config':expected['config'],'is_active':True})
        assert request('GET', base + '/rules')['items'] == [rule]
        result = request('POST', base + f'/versions/{version}/runs')
        for key, value in expected['statistics'].items(): assert result[key] == value
        run = result['run_id']
        detail = request('GET', base + f'/runs/{run}')
        snapshot = [{key:rule[key] for key in ('id','name','rule_type','columns','config')}]
        assert detail['rule_snapshot'] == snapshot and detail['engine_version'] == 'quality-v4'
        violations = []
        for page in (1,2,3):
            batch = request('GET', base + f'/runs/{run}/violations', params={'page_size':2,'page':page})
            assert batch['total'] == 5
            violations.extend(batch['items'])
        assert [{key:item[key] for key in expected['violations'][0]} for item in violations] == expected['violations']
        assert all('NEW' in item['message'] for item in violations)
        history = request('GET', base + '/runs')
        assert history['items'][0]['run_id'] == run
        report = request('GET', base + f'/runs/{run}/report')
        assert report['report_schema_version'] == '1' and report['violations'] == violations and report['rule_snapshot'] == snapshot
        rows = request('GET', base + f'/versions/{version}/rows', params={'page_size':100})
        assert [item['values'] for item in rows['items']] == expected['rows']
        point = request('GET', base + '/quality-trend')['points'][0]
        assert point['rule_set_fingerprint'] == fingerprint(snapshot) and point['pass_rate'] == '50.0000' and point['engine_version']=='quality-v4'
        for old_id, saved in before['fingerprints'].items():
            with engine.connect() as c:
                old = c.execute(select(QualityRun.dataset_version_id,QualityRun.status).where(QualityRun.id==int(old_id))).one()
                old_dataset = c.execute(select(DatasetVersion.dataset_id).where(DatasetVersion.id==old.dataset_version_id)).scalar_one()
            old_detail = request('GET',f'/api/datasets/{old_dataset}/runs/{old_id}')
            assert old_detail['engine_version']==saved['engine_version'] and fingerprint(old_detail['rule_snapshot'])==saved['fingerprint']
            if old.status=='completed':
                old_report = request('GET',f'/api/datasets/{old_dataset}/runs/{old_id}/report')
                assert fingerprint(old_report['rule_snapshot'])==saved['fingerprint']
        checks={}
        with engine.connect() as c:
            for model in [Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation]:
                saved=before['tables'][model.__tablename__]
                data=[dict(r) for r in c.execute(select(model).where(model.id.in_(saved['ids'])).order_by(model.id)).mappings()]
                digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
                assert digest==saved['sha256'] and len(data)==saved['count']
                checks[model.__tablename__]={'old_count':len(data),'old_sha256':digest,'unchanged':True}
        report_path=SAMPLES/f'dataset-{dataset}-run-{run}-allowed-values-report.json'
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        verified={'dataset_id':dataset,'name':imported['name'],'version_id':version,'rule_id':rule['id'],'run_id':run,'statistics':expected['statistics'],'engine_version':detail['engine_version'],'fingerprint':point['rule_set_fingerprint'],'parser_rows':parsed.rows,'violations':violations,'old_run_count':len(before['fingerprints']),'old_data_checks':checks,'report_file':report_path.name}
        artifact.write_text(json.dumps(verified,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({key:verified[key] for key in ('dataset_id','name','version_id','rule_id','run_id','statistics','engine_version','fingerprint','old_run_count')},ensure_ascii=False))
finally:
    with engine.begin() as c: revoke_session(c,session['token'])
    engine.dispose()
