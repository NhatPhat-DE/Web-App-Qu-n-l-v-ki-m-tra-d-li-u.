from nv01_fixtures import saved_run_fields
from nv01_fixtures import batch_rule_path
"""Authenticated PostgreSQL coverage for the manual data_type lifecycle."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, update

from app.main import app
from app.models import DatasetRow, DatasetVersion, QualityRule, QualityRun, QualityViolation, User
from app.services.auth_sessions import create_session
from app.services.csrf import session_csrf_token
from app.services.quality_results import complete_run, ResultValidationError
from app.services.quality_trend import fingerprint
from app.services.quality_engine import ENGINE_VERSION
from test_dataset_import import isolated_database
from test_sessions_csrf import settings

SAMPLES = Path(__file__).resolve().parents[1] / 'samples'
EXPECTED = json.loads((SAMPLES / 'data_type_qt01a_expected.json').read_text(encoding='utf-8'))
ORIGIN = 'http://127.0.0.1:5173'


@pytest.fixture
def context(isolated_database, settings):
    with isolated_database.begin() as connection:
        user = connection.execute(insert(User).values(username='data_type_tester', password_hash='test-only',
            role='admin').returning(User.id)).scalar_one()
        token = create_session(connection, user)['token']
    with TestClient(app) as client:
        client.cookies.set('datalens_session', token, path='/api')
        client.headers.update({'Origin': ORIGIN, 'X-CSRF-Token': session_csrf_token(token)})
        response = client.post(batch_rule_path(client, '/api/datasets/import'), data={'name': 'QT-01A isolated'},
            files={'file': ('data_type_qt01a.csv', (SAMPLES / 'data_type_qt01a.csv').read_bytes())})
        assert response.status_code == 201
        yield isolated_database, client, response.json(), user


def create_rules(client, dataset):
    rules = []
    for kind, column in zip(('integer', 'decimal', 'boolean'), EXPECTED['columns']):
        response = client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'), json={
            'name': f'Check {kind}', 'rule_type': 'data_type', 'columns': [column], 'config': {'type': kind}})
        assert response.status_code == 201
        rules.append(response.json())
    return rules


def counts(engine):
    with engine.connect() as connection:
        return [connection.execute(select(func.count()).select_from(model)).scalar_one()
                for model in (QualityRule, QualityRun, QualityViolation)]


def test_data_type_create_patch_validation_atomic(context):
    engine, client, imported, _ = context
    base = f"/api/datasets/{imported['dataset_id']}/rules"
    rules = create_rules(client, imported['dataset_id'])
    original = client.get(batch_rule_path(client, base)).json()
    assert original['items'] == rules and original['total'] == 3
    bad_configs = [{}, {'type': None}, {'type': True}, {'type': 1}, {'type': []}, {'type': {}},
        {'type': 'Integer'}, {'type': 'float'}, {'type': ' integer '}, {'type': 'integer', 'scale': 2},
        {'type': 'x' * 17000}, {'type': 'integer', 'extra': '界' * 6000}]
    for config in bad_configs:
        body = {'name': 'invalid', 'rule_type': 'data_type', 'columns': ['integer_value'], 'config': config}
        for method, url, payload in [('POST', base, body),
                                     ('PATCH', base + f"/{rules[0]['id']}", {'config': config})]:
            response = client.request(method, batch_rule_path(client, url), json=payload)
            assert response.status_code == 422, (config, response.text)
            if len(json.dumps(config, ensure_ascii=False).encode('utf-8')) > 16384:
                assert response.json()['error']['code'] == 'INVALID_CONFIG'
            assert client.get(batch_rule_path(client, base)).json() == original
    for columns in ([], ['missing'], ['integer_value', 'decimal_value'], ['integer_value', 'integer_value']):
        response = client.post(batch_rule_path(client, base), json={'name': 'bad column', 'rule_type': 'data_type',
            'columns': columns, 'config': {'type': 'integer'}})
        assert response.status_code == 422
        assert client.patch(batch_rule_path(client, base + f"/{rules[0]['id']}"), json={'columns': columns}).status_code == 422
    for changes in ({'config': None}, {'config': 'integer'}, {'is_active': 'true'}, {'config': {'type': 'boolean'}, 'columns': None}):
        assert client.patch(batch_rule_path(client, base + f"/{rules[0]['id']}"), json=changes).status_code == 422
    assert client.get(batch_rule_path(client, base)).json() == original
    response = client.patch(batch_rule_path(client, base + f"/{rules[0]['id']}"), json={'config': {'type': 'boolean'}, 'is_active': False})
    assert response.status_code == 200 and response.json()['config'] == {'type': 'boolean'}
    assert response.json()['is_active'] is False and counts(engine) == [3, 0, 0]


def test_data_type_full_lifecycle_matches_precomputed_answers(context):
    engine, client, imported, _ = context
    dataset, version = imported['dataset_id'], imported['version_id']
    rules = create_rules(client, dataset)
    base = f'/api/datasets/{dataset}'
    with engine.connect() as connection:
        inferred_before = connection.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == version)).scalar_one()
    response = client.post(batch_rule_path(client, base + f'/versions/{version}/runs'))
    assert response.status_code == 201
    result = response.json()
    for key, value in EXPECTED['statistics'].items():
        assert result[key] == value
    run = result['run_id']
    detail = client.get(batch_rule_path(client, base + f'/runs/{run}')).json()
    snapshot = [{key: rule[key] for key in ('id', 'name', 'rule_type', 'columns', 'config')} for rule in rules]
    assert detail['rule_snapshot'] == snapshot and detail['engine_version'] == ENGINE_VERSION
    errors = []
    for page in range(1, 7):
        response = client.get(batch_rule_path(client, base + f'/runs/{run}/violations'), params={'page': page, 'page_size': 2})
        assert response.status_code == 200 and response.json()['total'] == 11
        errors.extend(response.json()['items'])
    assert [{key: item[key] for key in EXPECTED['violations'][0]} for item in errors] == EXPECTED['violations']
    for error in errors:
        assert error['rule_name'] == rules[error['rule_order'] - 1]['name']
        assert error['rule_id_snapshot'] == rules[error['rule_order'] - 1]['id']
        assert error['message'].strip()
    filtered = client.get(batch_rule_path(client, base + f'/runs/{run}/violations'), params={
        'rule_id_snapshot': rules[1]['id'], 'row_number': 6}).json()
    assert filtered['total'] == 1 and filtered['items'][0]['values'] == ['1,2']
    report = client.get(batch_rule_path(client, base + f'/runs/{run}/report')).json()
    assert report['report_schema_version'] == '1' and report['rule_snapshot'] == snapshot
    assert report['violations'] == errors
    assert client.get(batch_rule_path(client, base + '/runs')).json()['items'][0]['run_id'] == run
    point = client.get(batch_rule_path(client, base + '/quality-trend')).json()['points'][0]
    assert point['engine_version'] == ENGINE_VERSION
    assert point['rule_set_fingerprint'] == fingerprint(snapshot)
    assert point['rule_set_fingerprint'].startswith('rules-v2:') and point['pass_rate'] == '60.0000'
    assert client.patch(batch_rule_path(client, base + f"/rules/{rules[0]['id']}"), json={
        'name': 'changed current rule', 'config': {'type': 'boolean'}, 'is_active': False}).status_code == 200
    assert saved_run_fields(client.get(batch_rule_path(client, base + f'/runs/{run}')).json()) == saved_run_fields(detail)
    again = client.get(batch_rule_path(client, base + f'/runs/{run}/report')).json()
    assert again['rule_snapshot'] == report['rule_snapshot'] and again['violations'] == report['violations']
    assert again['run'] == report['run']
    assert client.get(batch_rule_path(client, base + '/quality-trend')).json()['points'] == [point]
    with engine.connect() as connection:
        assert connection.execute(select(DatasetRow.values).where(DatasetRow.version_id == version)
            .order_by(DatasetRow.row_number)).scalars().all() == EXPECTED['rows']
        assert connection.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == version)).scalar_one() == inferred_before


def test_data_type_with_required_counts_distinct_error_rows(context):
    _, client, imported, _ = context
    dataset = imported['dataset_id']
    create_rules(client, dataset)
    assert client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'), json={'name': 'Required integer',
        'rule_type': 'required', 'columns': ['integer_value'], 'config': {}}).status_code == 201
    result = client.post(batch_rule_path(client, f"/api/datasets/{dataset}/versions/{imported['version_id']}/runs")).json()
    assert (result['total_rows'], result['error_row_count'], result['violation_count'], result['error_row_rate']) == (10, 6, 13, '60.0000')


def test_decimal_representation_error_is_a_violation_not_failed_run(context):
    _, client, _, _ = context
    extreme = '1e999999999999999999999999'
    imported = client.post(batch_rule_path(client, '/api/datasets/import'), data={'name': 'Decimal representation'},
        files={'file': ('decimal.csv', f'value\n{extreme}\n1.234567'.encode())})
    assert imported.status_code == 201
    dataset, version = imported.json()['dataset_id'], imported.json()['version_id']
    rule = client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'), json={'name': 'Decimal type',
        'rule_type': 'data_type', 'columns': ['value'], 'config': {'type': 'decimal'}})
    assert rule.status_code == 201
    response = client.post(batch_rule_path(client, f'/api/datasets/{dataset}/versions/{version}/runs'))
    assert response.status_code == 201
    result = response.json()
    assert result['status'] == 'completed'
    assert (result['total_rows'], result['error_row_count'], result['violation_count'], result['error_row_rate']) == (2, 1, 1, '50.0000')
    errors = client.get(batch_rule_path(client, f"/api/datasets/{dataset}/runs/{result['run_id']}/violations")).json()['items']
    assert len(errors) == 1 and errors[0]['error_code'] == 'DATA_TYPE_DECIMAL_INVALID'
    assert errors[0]['row_number'] == 1 and errors[0]['values'] == [extreme]


@pytest.mark.parametrize('role', ['admin', 'data_steward'])
def test_data_type_access_and_csrf(context, role):
    engine, client, imported, user = context
    with engine.begin() as connection:
        connection.execute(update(User).where(User.id == user).values(role=role))
    dataset = imported['dataset_id']
    rules = create_rules(client, dataset)
    url = f'/api/datasets/{dataset}/rules'
    payload = {'name': 'guarded', 'rule_type': 'data_type', 'columns': ['integer_value'], 'config': {'type': 'integer'}}
    before = counts(engine)
    with TestClient(app) as anonymous:
        assert anonymous.post(url, json=payload).status_code == 401
        assert anonymous.get(url).status_code == 401
    original_headers = dict(client.headers)
    for bad in ({'Origin': ORIGIN}, {'Origin': 'http://evil', 'X-CSRF-Token': original_headers['x-csrf-token']},
                {'Origin': ORIGIN, 'X-CSRF-Token': 'wrong'}, {'X-CSRF-Token': original_headers['x-csrf-token']}):
        client.headers.clear()
        client.headers.update(bad)
        assert client.post(batch_rule_path(client, url), json=payload).status_code == 403
        assert client.patch(batch_rule_path(client, url + f"/{rules[0]['id']}"), json={'is_active': False}).status_code == 403
        assert client.post(batch_rule_path(client, f"/api/datasets/{dataset}/versions/{imported['version_id']}/runs")).status_code == 403
        assert counts(engine) == before
    client.headers.clear()
    client.headers.update(original_headers)
    assert client.get(batch_rule_path(client, url)).status_code == 200
    assert client.patch(batch_rule_path(client, url + f"/{rules[0]['id']}"), json={'name': 'updated'}).status_code == 200


@pytest.mark.parametrize('mutation', ['subtype_code', 'value', 'engine_version'])
def test_data_type_result_rejection_is_atomic(context, mutation):
    engine, client, imported, _ = context
    rules = create_rules(client, imported['dataset_id'])
    snapshot = [{key: rule[key] for key in ('id', 'name', 'rule_type', 'columns', 'config')} for rule in rules]
    with engine.begin() as connection:
        run = connection.execute(insert(QualityRun).values(dataset_version_id=imported['version_id'],
            rule_snapshot=snapshot, engine_version='quality-v2' if mutation == 'engine_version' else ENGINE_VERSION)
            .returning(QualityRun.id)).scalar_one()
    result = {'row_count': 10, 'error_row_count': 4, 'violation_count': 11, 'errors': [
        {'rule_id': rules[item['rule_order'] - 1]['id'], 'rule_type': 'data_type',
         'row_number': item['row_number'], 'columns': item['columns'], 'values': item['values'],
         'code': item['error_code'], 'message': 'Giá trị không đúng kiểu cấu hình.'}
        for item in deepcopy(EXPECTED['violations'])]}
    if mutation == 'subtype_code':
        result['errors'][0]['code'] = 'DATA_TYPE_DECIMAL_INVALID'
    elif mutation == 'value':
        result['errors'][0]['values'] = ['coerced']
    with pytest.raises(ResultValidationError):
        complete_run(run, result)
    assert counts(engine) == [3, 1, 0]
    with engine.connect() as connection:
        saved = connection.execute(select(QualityRun).where(QualityRun.id == run)).mappings().one()
        assert saved['status'] == 'running' and saved['rule_snapshot'] == snapshot
        assert saved['total_rows'] is None and saved['violation_count'] is None
