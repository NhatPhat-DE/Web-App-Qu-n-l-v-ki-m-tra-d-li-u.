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
EXPECTED = json.loads((SAMPLES / 'date_format_qt02a_expected.json').read_text(encoding='utf-8'))


@pytest.fixture
def dated(context):
    engine, client, _, user = context
    response = client.post(batch_rule_path(client, '/api/datasets/import'), data={'name': 'Date format isolated'},
        files={'file': ('date_format_qt02a.csv', (SAMPLES / 'date_format_qt02a.csv').read_bytes())})
    assert response.status_code == 201
    return engine, client, response.json(), user


def create_rule(client, dataset, fmt='YYYY-MM-DD'):
    response = client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'), json={
        'name': 'Event date format', 'rule_type': 'date_format', 'columns': ['event_date'], 'config': {'format': fmt}})
    assert response.status_code == 201
    return response.json()


def test_date_config_and_columns_post_patch_transactions(dated):
    engine, client, imported, _ = dated
    base = f"/api/datasets/{imported['dataset_id']}/rules"
    rule = create_rule(client, imported['dataset_id'])
    for fmt in ('YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY'):
        response = client.patch(batch_rule_path(client, base + f"/{rule['id']}"), json={'config': {'format': fmt}})
        assert response.status_code == 200 and response.json()['config'] == {'format': fmt}
    original = client.get(batch_rule_path(client, base)).json()
    for config in ({}, None, [], {'format': None}, {'format': True}, {'format': 1}, {'format': ['YYYY-MM-DD']},
                   {'format': '%Y-%m-%d'}, {'format': 'YYYY-MM-DD', 'extra': 1}, {'format': '界' * 6000}):
        body = {'name': 'invalid date', 'rule_type': 'date_format', 'columns': ['event_date'], 'config': config}
        assert client.post(batch_rule_path(client, base), json=body).status_code == 422
        assert client.patch(batch_rule_path(client, base + f"/{rule['id']}"), json={'config': config}).status_code == 422
        assert client.get(batch_rule_path(client, base)).json() == original
    for columns in ([], ['missing'], ['event_date', 'event_date'], ['event_date', 'integer_value']):
        body = {'name': 'invalid date', 'rule_type': 'date_format', 'columns': columns, 'config': EXPECTED['config']}
        assert client.post(batch_rule_path(client, base), json=body).status_code == 422
        assert client.patch(batch_rule_path(client, base + f"/{rule['id']}"), json={'columns': columns}).status_code == 422
    assert client.get(batch_rule_path(client, base)).json() == original and counts(engine) == [1, 0, 0]


def test_date_full_lifecycle_original_values_and_immutable_snapshot(dated):
    engine, client, imported, _ = dated
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
    assert all('YYYY-MM-DD' in item['message'] and item['rule_name'] == rule['name'] for item in violations)
    report = client.get(batch_rule_path(client, base + f'/runs/{run}/report')).json()
    assert report['report_schema_version'] == '1' and report['rule_snapshot'] == snapshot and report['violations'] == violations
    assert client.get(batch_rule_path(client, base + '/runs')).json()['items'][0]['run_id'] == run
    filtered = client.get(batch_rule_path(client, base + f'/runs/{run}/violations'), params={'rule_id_snapshot': rule['id'], 'row_number': 5}).json()
    assert filtered['total'] == 1 and filtered['items'][0]['values'] == [' 2026-01-01 ']
    point = client.get(batch_rule_path(client, base + '/quality-trend')).json()['points'][0]
    assert point['engine_version'] == 'quality-v6' and point['rule_set_fingerprint'] == fingerprint(snapshot)
    assert point['pass_rate'] == '37.5000'
    assert client.patch(batch_rule_path(client, base + f"/rules/{rule['id']}"), json={'name': 'Current format changed', 'config': {'format': 'MM/DD/YYYY'}, 'is_active': False}).status_code == 200
    assert saved_run_fields(client.get(batch_rule_path(client, base + f'/runs/{run}')).json()) == saved_run_fields(detail)
    again = client.get(batch_rule_path(client, base + f'/runs/{run}/report')).json()
    assert again['rule_snapshot'] == report['rule_snapshot'] and again['violations'] == report['violations'] and again['run'] == report['run']
    assert client.get(batch_rule_path(client, base + '/quality-trend')).json()['points'] == [point]
    with engine.connect() as c:
        assert c.execute(select(DatasetRow.values).where(DatasetRow.version_id == version).order_by(DatasetRow.row_number)).scalars().all() == EXPECTED['rows']
        assert c.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == version)).scalar_one() == inferred


def test_date_multiple_rules_and_required_counts(dated):
    _, client, imported, _ = dated
    dataset, version = imported['dataset_id'], imported['version_id']
    create_rule(client, dataset)
    create_rule(client, dataset, 'DD/MM/YYYY')
    assert client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'), json={'name': 'Required date', 'rule_type': 'required', 'columns': ['event_date'], 'config': {}}).status_code == 201
    response = client.post(batch_rule_path(client, f'/api/datasets/{dataset}/versions/{version}/runs'))
    assert response.status_code == 201
    result = response.json()
    assert (result['total_rows'], result['error_row_count'], result['violation_count'], result['error_row_rate']) == (8, 8, 13, '100.0000')


@pytest.mark.parametrize('role', ['admin', 'data_steward'])
def test_date_roles_origin_csrf(dated, role):
    from fastapi.testclient import TestClient
    from app.main import app
    engine, client, imported, user = dated
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
        assert client.patch(batch_rule_path(client, base + f"/rules/{rule['id']}"), json={'config': {'format': 'DD/MM/YYYY'}}).status_code == 403
        assert client.post(batch_rule_path(client, base + f"/versions/{imported['version_id']}/runs")).status_code == 403
        assert counts(engine) == before
    client.headers.clear(); client.headers.update(headers)
    assert client.get(batch_rule_path(client, base + '/rules')).status_code == 200


@pytest.mark.parametrize('mutation', ['code', 'value', 'duplicate', 'old_engine'])
def test_date_result_invalid_input_is_atomic(dated, mutation):
    engine, client, imported, _ = dated
    rule = create_rule(client, imported['dataset_id'])
    snapshot = [{key: rule[key] for key in ('id', 'name', 'rule_type', 'columns', 'config')}]
    with engine.begin() as c:
        run = c.execute(insert(QualityRun).values(dataset_version_id=imported['version_id'], rule_snapshot=snapshot,
            engine_version='quality-v2' if mutation == 'old_engine' else 'quality-v5').returning(QualityRun.id)).scalar_one()
    result = {'row_count': 8, 'error_row_count': 5, 'violation_count': 5, 'errors': [
        {'rule_id': rule['id'], 'rule_type': 'date_format', 'row_number': item['row_number'], 'columns': item['columns'],
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
