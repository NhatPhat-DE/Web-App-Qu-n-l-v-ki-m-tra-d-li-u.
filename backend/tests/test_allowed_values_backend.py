from nv01_fixtures import saved_run_fields
from nv01_fixtures import batch_rule_path
from copy import deepcopy
import json
from pathlib import Path

import pytest
from sqlalchemy import insert, select, update

from app.models import DatasetRow, DatasetVersion, QualityRule, QualityRun, User
from app.services.quality_results import complete_run, ResultValidationError
from app.services.quality_trend import fingerprint
from test_data_type_backend import context, counts
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

SAMPLES = Path(__file__).resolve().parents[1] / 'samples'
EXPECTED = json.loads((SAMPLES / 'allowed_values_qt03a_expected.json').read_text(encoding='utf-8'))


@pytest.fixture
def valued(context):
    engine, client, _, user = context
    response = client.post(batch_rule_path(client, '/api/datasets/import'), data={'name': 'Allowed values isolated'},
        files={'file': ('allowed_values_qt03a.csv', (SAMPLES / 'allowed_values_qt03a.csv').read_bytes())})
    assert response.status_code == 201
    return engine, client, response.json(), user


def create_rule(client, dataset, values=None):
    response = client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'), json={
        'name': 'Allowed status', 'rule_type': 'allowed_values', 'columns': ['status'], 'config': {'values': ['NEW','DONE','HOLD'] if values is None else values}})
    assert response.status_code == 201
    return response.json()


def test_allowed_config_and_columns_post_patch_transactions(valued):
    engine, client, imported, _ = valued
    base = f"/api/datasets/{imported['dataset_id']}/rules"
    rule = create_rule(client, imported['dataset_id'])
    response = client.patch(batch_rule_path(client, base + f"/{rule['id']}"), json={'config': {'values':['HOLD','NEW','DONE']}})
    assert response.status_code == 200 and response.json()['config']['values'] == ['HOLD','NEW','DONE']
    original = client.get(batch_rule_path(client, base)).json()
    for config in ({}, None, [], {'values': None}, {'values': []}, {'values': [1]}, {'values':['NEW','NEW']}, {'values':['']}, {'values':['   ']}, {'values':['NEW'],'extra':1}, {'values':['x'*257]}, {'values':[str(i) for i in range(101)]}):
        body = {'name': 'invalid set', 'rule_type': 'allowed_values', 'columns': ['status'], 'config': config}
        assert client.post(batch_rule_path(client, base), json=body).status_code == 422
        assert client.patch(batch_rule_path(client, base + f"/{rule['id']}"), json={'config': config}).status_code == 422
        assert client.get(batch_rule_path(client, base)).json() == original
    for columns in ([], ['missing'], ['status', 'status'], ['status', 'integer_value']):
        body = {'name': 'invalid set', 'rule_type': 'allowed_values', 'columns': columns, 'config': EXPECTED['config']}
        assert client.post(batch_rule_path(client, base), json=body).status_code == 422
        assert client.patch(batch_rule_path(client, base + f"/{rule['id']}"), json={'columns': columns}).status_code == 422
    assert client.get(batch_rule_path(client, base)).json() == original and counts(engine) == [1, 0, 0]


def test_allowed_full_lifecycle_original_values_and_immutable_snapshot(valued):
    engine, client, imported, _ = valued
    dataset, version = imported['dataset_id'], imported['version_id']
    base = f'/api/datasets/{dataset}'
    rule = create_rule(client, dataset)
    snapshot = [{key: rule[key] for key in ('id', 'name', 'rule_type', 'columns', 'config')}]
    with engine.connect() as c:
        inferred = c.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == version)).scalar_one()
    response = client.post(batch_rule_path(client, base + f'/versions/{version}/runs'))
    assert response.status_code == 201
    result = response.json(); run = result['run_id']
    for key, value in EXPECTED['statistics'].items():
        assert result[key] == value
    detail = client.get(batch_rule_path(client, base + f'/runs/{run}')).json()
    assert detail['engine_version'] == 'quality-v6' and detail['rule_snapshot'] == snapshot
    violations = []
    for page in (1, 2, 3):
        batch = client.get(batch_rule_path(client, base + f'/runs/{run}/violations'), params={'page_size': 2, 'page': page}).json()
        assert batch['total'] == 5
        violations.extend(batch['items'])
    assert [{key: item[key] for key in EXPECTED['violations'][0]} for item in violations] == EXPECTED['violations']
    assert all('NEW' in item['message'] and item['rule_name'] == rule['name'] for item in violations)
    report = client.get(batch_rule_path(client, base + f'/runs/{run}/report')).json()
    assert report['report_schema_version'] == '1' and report['rule_snapshot'] == snapshot and report['violations'] == violations
    assert client.get(batch_rule_path(client, base + '/runs')).json()['items'][0]['run_id'] == run
    filtered = client.get(batch_rule_path(client, base + f'/runs/{run}/violations'), params={'rule_id_snapshot': rule['id'], 'row_number': 5}).json()
    assert filtered['total'] == 1 and filtered['items'][0]['values'] == [' NEW']
    point = client.get(batch_rule_path(client, base + '/quality-trend')).json()['points'][0]
    assert point['engine_version'] == 'quality-v6' and point['rule_set_fingerprint'] == fingerprint(snapshot)
    assert point['pass_rate'] == '50.0000'
    assert client.patch(batch_rule_path(client, base + f"/rules/{rule['id']}"), json={'name': 'Current set changed', 'config': {'values':['CANCELLED']}, 'is_active': False}).status_code == 200
    assert saved_run_fields(client.get(batch_rule_path(client, base + f'/runs/{run}')).json()) == saved_run_fields(detail)
    again = client.get(batch_rule_path(client, base + f'/runs/{run}/report')).json()
    assert again['rule_snapshot'] == report['rule_snapshot'] and again['violations'] == report['violations'] and again['run'] == report['run']
    assert client.get(batch_rule_path(client, base + '/quality-trend')).json()['points'] == [point]
    with engine.connect() as c:
        assert c.execute(select(DatasetRow.values).where(DatasetRow.version_id == version).order_by(DatasetRow.row_number)).scalars().all() == EXPECTED['rows']
        assert c.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == version)).scalar_one() == inferred


def test_allowed_multiple_rules_and_required_counts(valued):
    _, client, imported, _ = valued
    dataset, version = imported['dataset_id'], imported['version_id']
    create_rule(client, dataset)
    create_rule(client, dataset, ['NEW'])
    assert client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'), json={'name':'Required status','rule_type':'required','columns':['status'],'config':{}}).status_code == 201
    result=client.post(batch_rule_path(client, f'/api/datasets/{dataset}/versions/{version}/runs')).json()
    assert (result['total_rows'],result['error_row_count'],result['violation_count'],result['error_row_rate'])==(10,9,14,'90.0000')


@pytest.mark.parametrize('role', ['admin', 'data_steward'])
def test_allowed_roles_origin_csrf(valued, role):
    from fastapi.testclient import TestClient
    from app.main import app
    engine, client, imported, user = valued
    with engine.begin() as c:
        c.execute(update(User).where(User.id == user).values(role=role))
    rule = create_rule(client, imported['dataset_id'])
    base = f"/api/datasets/{imported['dataset_id']}"
    payload = {key: rule[key] for key in ('name', 'rule_type', 'columns', 'config')}
    with TestClient(app) as anon:
        assert anon.post(base + '/rules', json=payload).status_code == 401
        assert anon.get(base + '/rules').status_code == 401
    headers = dict(client.headers); before = counts(engine)
    for bad in ({'Origin': 'http://127.0.0.1:5173'}, {'Origin': 'http://evil', 'X-CSRF-Token': headers['x-csrf-token']},
                {'Origin': 'http://127.0.0.1:5173', 'X-CSRF-Token': 'wrong'}, {'X-CSRF-Token': headers['x-csrf-token']}):
        client.headers.clear(); client.headers.update(bad)
        assert client.post(batch_rule_path(client, base + '/rules'), json=payload).status_code == 403
        assert client.patch(batch_rule_path(client, base + f"/rules/{rule['id']}"), json={'config': {'values':['DONE']}}).status_code == 403
        assert client.post(batch_rule_path(client, base + f"/versions/{imported['version_id']}/runs")).status_code == 403
        assert counts(engine) == before
    client.headers.clear(); client.headers.update(headers)
    assert client.get(batch_rule_path(client, base + '/rules')).status_code == 200


@pytest.mark.parametrize('mutation', ['code', 'value', 'duplicate', 'old_engine'])
def test_allowed_result_invalid_input_is_atomic(valued, mutation):
    engine, client, imported, _ = valued
    rule = create_rule(client, imported['dataset_id'])
    snapshot = [{key: rule[key] for key in ('id', 'name', 'rule_type', 'columns', 'config')}]
    with engine.begin() as c:
        run = c.execute(insert(QualityRun).values(dataset_version_id=imported['version_id'], rule_snapshot=snapshot,
            engine_version='quality-v3' if mutation == 'old_engine' else 'quality-v5').returning(QualityRun.id)).scalar_one()
    result = {'row_count': 10, 'error_row_count': 5, 'violation_count': 5, 'errors': [
        {'rule_id': rule['id'], 'rule_type': 'allowed_values', 'row_number': item['row_number'], 'columns': item['columns'],
         'values': item['values'], 'code': item['error_code'], 'message': 'Không đạt YYYY-MM-DD.'}
        for item in deepcopy(EXPECTED['violations'])]}
    if mutation == 'code': result['errors'][0]['code'] = 'DATA_TYPE_INTEGER_INVALID'
    elif mutation == 'value': result['errors'][0]['values'] = ['changed']
    elif mutation == 'duplicate': result['errors'].append(deepcopy(result['errors'][0])); result['violation_count'] = 6
    with pytest.raises(ResultValidationError): complete_run(run, result)
    assert counts(engine) == [1, 1, 0]
    with engine.connect() as c:
        saved = c.execute(select(QualityRun).where(QualityRun.id == run)).mappings().one()
        assert saved['status'] == 'running' and saved['rule_snapshot'] == snapshot and saved['total_rows'] is None


@pytest.mark.parametrize('values', [
    [str(i) for i in range(100)], ['😀'*256], ['NEW','new',' NEW','NEW ','é','e\u0301'],
    [chr(65+i)+'x'*255 for i in range(63)]+['z'*51],
])
def test_config_boundaries_unicode_and_order_round_trip(valued, values):
    _, client, imported, _ = valued
    rule=create_rule(client,imported['dataset_id'],values)
    assert rule['config']=={'values':values}
    base=f"/api/datasets/{imported['dataset_id']}/rules"
    assert client.get(batch_rule_path(client, base)).json()['items'][0]['config']=={'values':values}
    reverse=list(reversed(values))
    changed=client.patch(batch_rule_path(client, base+f"/{rule['id']}"),json={'config':{'values':reverse}})
    assert changed.status_code==200 and changed.json()['config']=={'values':reverse}
    assert fingerprint([rule])==fingerprint([changed.json()])
    before=client.get(batch_rule_path(client, base)).json()
    oversized={'values':[chr(65+i)+'x'*255 for i in range(63)]+['z'*52]}
    assert client.patch(batch_rule_path(client, base+f"/{rule['id']}"),json={'config':oversized}).status_code==422
    assert client.get(batch_rule_path(client, base)).json()==before
