from nv01_fixtures import current_version_values
"""PostgreSQL-only summary checks against prewritten, persisted answers."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.models import (Dataset, DatasetColumn, DatasetRow, DatasetVersion,
                        QualityRule, QualityRun, QualityViolation, User)
from app.services import quality_summary as summary
from app.services.auth_sessions import create_session, revoke_session
from test_dataset_import import isolated_database
from test_sessions_csrf import settings


HEADER = ['region', 'code', 'qty', 'event_date', 'status']
ROWS = [
    ['N', 'SP0001', '10', '2024-02-29', 'NEW'],
    ['N', 'SP0001', '101', '2023-02-29', 'new'],
    ['', 'BAD', '', '2026-2-01', 'DONE'],
    ['   ', 'SP0004', '   ', '', ''],
    ['S', '', '1.5', '2026-12-31', 'HOLD'],
    ['S', 'SP0006', 'NULL', '0000-01-01', 'NULL'],
    ['T', 'AB0001', '-1', '2026-01-01', 'NEW'],
    ['T', 'SP0008', '0', '9999-12-31', 'DONE'],
]
DEFINITIONS = [
    ('required', ['qty'], {}, [3, 4]),
    ('unique', ['region', 'code'], {}, [1, 2]),
    ('numeric_range', ['qty'], {'min': '0', 'max': '100'}, [2, 6, 7]),
    ('data_type', ['qty'], {'type': 'integer'}, [5, 6]),
    ('date_format', ['event_date'], {'format': 'YYYY-MM-DD'}, [2, 3, 6]),
    ('allowed_values', ['status'], {'values': ['NEW', 'DONE', 'HOLD']}, [2, 6]),
    ('pattern', ['code'], {'pattern': 'SP[0-9]{4}', 'dialect': 're2-v1'}, [3, 7]),
]
WHEN = datetime(2026, 1, 1, tzinfo=timezone.utc)


def add_run(c, version, snapshot, errors=7, violations=16, rate='87.5000', status='completed'):
    fields = dict(dataset_version_id=version, status=status, started_at=WHEN,
                  engine_version='quality-v5', rule_snapshot=deepcopy(snapshot))
    if status == 'completed':
        fields.update(finished_at=WHEN + timedelta(seconds=1), total_rows=8,
                      error_row_count=errors, violation_count=violations,
                      error_row_rate=Decimal(rate))
    elif status == 'failed':
        fields.update(finished_at=WHEN + timedelta(seconds=1), failure_code='RUN_FAILED',
                      failure_message='Safe failure')
    return c.execute(insert(QualityRun).values(**fields).returning(QualityRun.id)).scalar_one()


def violation_code(kind, row):
    return {'required': 'REQUIRED_MISSING', 'unique': 'UNIQUE_DUPLICATE',
            'numeric_range': 'NUMERIC_INVALID' if row == 6 else 'NUMERIC_OUT_OF_RANGE',
            'data_type': 'DATA_TYPE_INTEGER_INVALID',
            'date_format': 'DATE_FORMAT_MISMATCH' if row == 3 else 'DATE_VALUE_INVALID',
            'allowed_values': 'ALLOWED_VALUE_NOT_IN_SET', 'pattern': 'PATTERN_MISMATCH'}[kind]


@pytest.fixture
def stored_summary(isolated_database, settings):
    engine = isolated_database
    with engine.begin() as c:
        dataset = c.execute(insert(Dataset).values(name='Summary fixture').returning(Dataset.id)).scalar_one()
        c.execute(insert(DatasetColumn), [dict(dataset_id=dataset, name=name, position=i)
                                         for i, name in enumerate(HEADER, 1)])
        versions = []
        for number, rows in [(1, ROWS), (2, [['N', f'SP{i:04}', '10', '2024-02-29', 'NEW'] for i in range(1, 9)])]:
            version = c.execute(insert(DatasetVersion).values(**current_version_values(c, dataset_id=dataset,
                version_number=number, original_filename=f'v{number}.csv', file_size_bytes=100,
                row_count=8, inferred_types=[])).returning(DatasetVersion.id)).scalar_one()
            c.execute(insert(DatasetRow), [dict(version_id=version, row_number=i, values=row)
                                          for i, row in enumerate(rows, 1)])
            versions.append(version)
        snapshot = []
        for kind, columns, config, _ in DEFINITIONS:
            rule_id = c.execute(insert(QualityRule).values(dataset_id=dataset, name=f'Saved {kind}',
                rule_type=kind, columns=columns, config=config).returning(QualityRule.id)).scalar_one()
            snapshot.append(dict(id=rule_id, name=f'Saved {kind}', rule_type=kind, columns=columns, config=config))
        run = add_run(c, versions[0], snapshot)
        empty = add_run(c, versions[1], snapshot, errors=0, violations=0, rate='0.0000')
        for order, (rule, definition) in enumerate(zip(snapshot, DEFINITIONS), 1):
            for row in definition[3]:
                c.execute(insert(QualityViolation).values(run_id=run, rule_order=order,
                    rule_id_snapshot=rule['id'], rule_type=rule['rule_type'], row_number=row,
                    columns=rule['columns'], values=[ROWS[row - 1][HEADER.index(col)] for col in rule['columns']],
                    error_code=violation_code(rule['rule_type'], row), message=f'Saved reason for row {row}'))
        user = c.execute(insert(User).values(username='summary_user', password_hash='fixture-only',
                                            role='admin').returning(User.id)).scalar_one()
        token = create_session(c, user)['token']
    return engine, dataset, versions, run, empty, snapshot, user, token


def client_for(token):
    client = TestClient(app)
    client.cookies.set('datalens_session', token, path='/api')
    return client


def path(dataset, run):
    return f'/api/datasets/{dataset}/runs/{run}/quality-summary'


def assert_no_detail_rates(value):
    if isinstance(value, dict):
        assert not any('rate' in key or 'eligible' in key or 'evaluated' in key or 'skipped' in key for key in value)
        for child in value.values():
            assert_no_detail_rates(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_detail_rates(child)


def test_all_dimensions_rules_and_composite_distinct(stored_summary):
    engine, dataset, versions, run, empty, snapshot, user, token = stored_summary
    with client_for(token) as client:
        for role in ('admin', 'data_steward'):
            with engine.begin() as c:
                c.execute(update(User).where(User.id == user).values(role=role))
            response = client.get(path(dataset, run))
            assert response.status_code == 200, response.text
            body = response.json()
            assert body['overall'] == dict(total_rows=8, error_row_count=7, violation_count=16,
                                          error_row_rate='87.5000', pass_rate='12.5000')
            assert body['context']['version_id'] == versions[0]
            assert body['context']['engine_version'] == 'quality-v5'
            assert body['context']['rule_snapshot_source'] == 'saved_run'
            assert [(x['dimension'], x['violation_count'], x['violating_row_count']) for x in body['dimensions']] == [
                ('completeness', 2, 2), ('uniqueness', 2, 2), ('validity', 7, 5), ('domain_conformance', 5, 3)]
            assert sum(x['violating_row_count'] for x in body['dimensions']) != 7
            assert [(x['rule_type'], x['violation_count'], x['violating_row_count']) for x in body['rules']['items']] == [
                (kind, len(rows), len(rows)) for kind, _, _, rows in DEFINITIONS]
            scopes = {tuple(x['columns']): x for x in body['column_scopes']['items']}
            assert body['column_scopes']['total'] == 5
            assert (scopes[('qty',)]['violation_count'], scopes[('qty',)]['violating_row_count']) == (7, 6)
            assert scopes[('qty',)]['rule_ids'] == [snapshot[i]['id'] for i in (0, 2, 3)]
            assert scopes[('region', 'code')]['scope_kind'] == 'column_group'
            assert (scopes[('region', 'code')]['violation_count'], scopes[('region', 'code')]['violating_row_count']) == (2, 2)
            assert ('region',) not in scopes
            assert scopes[('code',)]['rule_ids'] == [snapshot[6]['id']]
            for key in ('dimensions', 'rules', 'column_scopes'):
                assert_no_detail_rates(body[key])


def test_no_errors_and_zero_rule_groups_still_present(stored_summary):
    _, dataset, _, _, empty, snapshot, _, token = stored_summary
    with client_for(token) as client:
        response = client.get(path(dataset, empty))
        assert response.status_code == 200
        body = response.json()
        assert body['overall']['pass_rate'] == '100.0000'
        assert body['overall']['error_row_count'] == body['overall']['violation_count'] == 0
        assert body['rules']['total'] == len(snapshot) == len(body['rules']['items'])
        assert body['column_scopes']['total'] == 5
        for x in body['dimensions'] + body['rules']['items'] + body['column_scopes']['items']:
            assert x['violation_count'] == x['violating_row_count'] == 0


def test_unconfigured_dimension_and_empty_legacy_snapshot(stored_summary):
    engine, dataset, versions, _, _, snapshot, _, token = stored_summary
    with engine.begin() as c:
        run = add_run(c, versions[1], snapshot[:1], errors=0, violations=0, rate='0.0000')
        legacy = add_run(c, versions[1], [], errors=0, violations=0, rate='0.0000')
    one = summary.quality_summary(dataset, run)
    assert [x['assessment_status'] for x in one['dimensions']] == ['configured', 'not_assessed', 'not_assessed', 'not_assessed']
    none = summary.quality_summary(dataset, legacy)
    assert none['rules']['total'] == none['column_scopes']['total'] == 0
    assert all(x['assessment_status'] == 'not_assessed' for x in none['dimensions'])


def test_snapshot_immutable_after_rule_changes_and_pages(stored_summary):
    engine, dataset, _, run, _, snapshot, _, token = stored_summary
    before = summary.quality_summary(dataset, run)
    with engine.begin() as c:
        c.execute(update(QualityRule).where(QualityRule.dataset_id == dataset).values(
            name='Changed now', is_active=False, columns=['code'], config={}))
    assert summary.quality_summary(dataset, run) == before
    with client_for(token) as client:
        rules, columns = [], []
        for page in range(1, 9):
            r = client.get(path(dataset, run), params={'rule_page': page, 'column_page': page, 'page_size': 1}).json()
            assert r['overall'] == before['overall'] and r['dimensions'] == before['dimensions']
            assert r['rules']['total'] == 7 and r['column_scopes']['total'] == 5
            rules.extend(r['rules']['items']); columns.extend(r['column_scopes']['items'])
        assert rules == before['rules']['items'] and columns == before['column_scopes']['items']
        assert [x['name'] for x in rules] == [x['name'] for x in snapshot]
        independent = client.get(path(dataset, run), params={'rule_page': 99, 'column_page': 1}).json()
        assert independent['rules']['items'] == [] and len(independent['column_scopes']['items']) == 5


def test_many_composite_rules_are_paged_and_not_double_counted(stored_summary):
    engine, dataset, _, run, _, snapshot, _, token = stored_summary
    expanded = deepcopy(snapshot)
    with engine.begin() as c:
        for number in range(24):
            rule = dict(name=f'Additional unique {number}', rule_type='unique',
                        columns=['region', 'code'], config={})
            rule['id'] = c.execute(insert(QualityRule).values(dataset_id=dataset, **rule)
                                   .returning(QualityRule.id)).scalar_one()
            expanded.append(rule)
            for row in (1, 2):
                c.execute(insert(QualityViolation).values(run_id=run, rule_order=len(expanded),
                    rule_id_snapshot=rule['id'], rule_type='unique', row_number=row,
                    columns=rule['columns'], values=ROWS[row - 1][:2],
                    error_code='UNIQUE_DUPLICATE', message='Saved duplicate'))
        c.execute(update(QualityRun).where(QualityRun.id == run).values(
            rule_snapshot=expanded, violation_count=64))
    with client_for(token) as client:
        first = client.get(path(dataset, run)).json()
        second = client.get(path(dataset, run), params={'rule_page': 2}).json()
        assert first['rules']['total'] == 31
        assert len(first['rules']['items']) == 20 and len(second['rules']['items']) == 11
        assert first['overall']['error_row_count'] == 7 and first['overall']['violation_count'] == 64
        group = next(x for x in first['column_scopes']['items'] if x['scope_kind'] == 'column_group')
        assert group['rule_count'] == 25 and group['violation_count'] == 50
        assert group['violating_row_count'] == 2 and len(group['rule_ids']) == 25
        assert first['column_scopes'] == second['column_scopes']


@pytest.mark.parametrize('status', ['running', 'failed'])
def test_missing_membership_and_incomplete(stored_summary, status):
    engine, dataset, versions, run, _, snapshot, _, token = stored_summary
    with engine.begin() as c:
        other = c.execute(insert(Dataset).values(name='Other').returning(Dataset.id)).scalar_one()
        incomplete = add_run(c, versions[0], snapshot, status=status)
    with client_for(token) as client:
        for d, r in [(999999, run), (dataset, 999999), (other, run)]:
            assert client.get(path(d, r)).status_code == 404
        response = client.get(path(dataset, incomplete))
        assert response.status_code == 409 and response.json()['error']['code'] == 'RUN_NOT_COMPLETED'


@pytest.mark.parametrize('params', [{'rule_page': 0}, {'column_page': -1}, {'page_size': 0}, {'page_size': 101}, {'rule_page': 'x'}])
def test_query_validation(stored_summary, params):
    _, dataset, _, run, _, _, _, token = stored_summary
    with client_for(token) as client:
        assert client.get(path(dataset, run), params=params).status_code == 422
        assert client.get(path(-1, run)).status_code == 422
        assert client.get(path(dataset, 0)).status_code == 422


def test_access_and_database_errors(stored_summary, monkeypatch):
    engine, dataset, _, run, _, _, _, token = stored_summary
    with TestClient(app) as client:
        assert client.get(path(dataset, run)).status_code == 401
    from app import access
    original = access.find_session
    monkeypatch.setattr(access, 'find_session', lambda *args: {'role': 'unauthorized'})
    with client_for(token) as client:
        assert client.get(path(dataset, run)).status_code == 403
    monkeypatch.setattr(access, 'find_session', original)
    def broken():
        raise ConnectionError('SECRET password SELECT')
    monkeypatch.setattr(summary, 'catalog_connection', broken)
    with client_for(token) as client:
        response = client.get(path(dataset, run))
        assert response.status_code == 503 and response.json()['error']['code'] == 'DATABASE_UNAVAILABLE'
        assert 'SECRET' not in response.text
    def sql_error():
        raise SQLAlchemyError('SECRET SELECT')
    monkeypatch.setattr(summary, 'catalog_connection', sql_error)
    with client_for(token) as client:
        response = client.get(path(dataset, run))
        assert response.status_code == 500 and response.json()['error']['code'] == 'DATABASE_ERROR'
        assert 'SELECT' not in response.text
    with engine.begin() as c:
        revoke_session(c, token)
    with client_for(token) as client:
        assert client.get(path(dataset, run)).status_code == 401


@pytest.mark.parametrize('mutation', ['count', 'snapshot', 'rule_id', 'rule_type', 'columns', 'order', 'row', 'values'])
def test_corrupt_results_fail_safely(stored_summary, mutation):
    engine, dataset, _, run, _, snapshot, _, token = stored_summary
    with engine.begin() as c:
        first = c.execute(select(QualityViolation.id).where(QualityViolation.run_id == run).order_by(QualityViolation.id).limit(1)).scalar_one()
        if mutation == 'count':
            c.execute(update(QualityRun).where(QualityRun.id == run).values(violation_count=17))
        elif mutation == 'snapshot':
            c.execute(update(QualityRun).where(QualityRun.id == run).values(rule_snapshot=[{'secret': 'SECRET'}]))
        else:
            change = {'rule_id': {'rule_id_snapshot': 999999}, 'rule_type': {'rule_type': 'unique'},
                'columns': {'columns': ['region']}, 'order': {'rule_order': 99},
                'row': {'row_number': 99}, 'values': {'values': []}}[mutation]
            c.execute(update(QualityViolation).where(QualityViolation.id == first).values(**change))
    with client_for(token) as client:
        response = client.get(path(dataset, run))
        assert response.status_code == 500 and response.json()['error']['code'] == 'INVALID_RUN_RESULT'
        assert 'SECRET' not in response.text and 'SELECT' not in response.text


def test_constant_queries_read_only_and_repeatable_read(stored_summary, monkeypatch):
    engine, dataset, _, run, _, _, _, _ = stored_summary
    from app.services import quality_engine, quality_execution, quality_history, pattern_worker
    def forbidden(*args, **kwargs):
        raise AssertionError('Summary must not execute checks, worker or report')
    monkeypatch.setattr(quality_engine, 'check_quality', forbidden)
    monkeypatch.setattr(quality_execution, 'execute_run', forbidden)
    monkeypatch.setattr(quality_history, 'export_report', forbidden)
    monkeypatch.setattr(pattern_worker, 'evaluate', forbidden)
    statements, writes = [], []
    @contextmanager
    def connection():
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as c:
            @event.listens_for(c, 'after_cursor_execute')
            def read(c, cursor, statement, parameters, context, executemany):
                statements.append(statement)
                assert not any(name in statement.lower() for name in ('dataset_rows', 'quality_rules', 'dataset_columns'))
                if statement.startswith('SELECT quality_runs.') and not writes:
                    assert c.exec_driver_sql('SHOW transaction_read_only').scalar_one() == 'on'
                    with engine.begin() as writer:
                        writer.execute(update(QualityViolation).where(QualityViolation.run_id == run).values(rule_id_snapshot=999999))
                    writes.append(True)
            yield c
    monkeypatch.setattr(summary, 'catalog_connection', connection)
    body = summary.quality_summary(dataset, run, page_size=1)
    assert body['overall']['violation_count'] == 16
    assert body['rules']['total'] == 7 and len(body['rules']['items']) == 1
    assert body['column_scopes']['total'] == 5 and len(body['column_scopes']['items']) == 1
    assert len(statements) == 10  # SET + eight SELECTs + the test's SHOW.
    assert not any(s.lstrip().upper().startswith(('UPDATE', 'INSERT', 'DELETE')) for s in statements)
    with pytest.raises(Exception) as error:
        summary.quality_summary(dataset, run)
    assert error.value.code == 'INVALID_RUN_RESULT'


def test_stored_rate_spelling_not_recomputed(stored_summary):
    engine, dataset, _, run, _, _, _, _ = stored_summary
    with engine.begin() as c:
        c.execute(update(QualityRun).where(QualityRun.id == run).values(error_row_rate=Decimal('87.5001')))
    with localcontext() as context:
        context.prec = 2
        body = summary.quality_summary(dataset, run)
    assert body['overall']['error_row_rate'] == '87.5001'
    assert body['overall']['pass_rate'] == '12.4999'
