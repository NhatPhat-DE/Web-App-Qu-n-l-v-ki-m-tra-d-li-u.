import pytest
from alembic import command
from sqlalchemy import insert, select, update

from app.models import QualityRule, QualityRun, QualityViolation
from test_data_type_migration import _config, _seed_run, _snapshot, _database_state, _rule_values, _violation_values, _assert_type_constraints
from test_dataset_import import isolated_database


def date_snapshot():
    return [{**_snapshot()[0], 'rule_type': 'date_format', 'config': {'format': 'YYYY-MM-DD'}}]


def probe_date_checks(engine, dataset, run, allowed):
    from sqlalchemy.exc import IntegrityError
    with engine.begin() as c:
        for model, values, name in (
            (QualityRule, {**_rule_values(dataset, 'date_format'), 'config': {'format': 'YYYY-MM-DD'}}, 'ck_quality_rules_type'),
            (QualityViolation, {**_violation_values(run, 'date_format', rule_order=51), 'error_code': 'DATE_FORMAT_MISMATCH'}, 'ck_quality_violations_type'),
        ):
            savepoint = c.begin_nested()
            try:
                if allowed: c.execute(insert(model).values(**values))
                else:
                    with pytest.raises(IntegrityError) as exc: c.execute(insert(model).values(**values))
                    assert exc.value.orig.diag.constraint_name == name
            finally: savepoint.rollback()


def test_date_upgrade_and_clean_downgrade_preserves_data_type_history(isolated_database):
    engine = isolated_database
    command.downgrade(_config(), '0005')
    dataset, run = _seed_run(engine, _snapshot('data_type'))
    before = _database_state(engine)
    probe_date_checks(engine, dataset, run, False)
    command.upgrade(_config(), '0006')
    upgraded = _database_state(engine)
    assert upgraded['revision'] == '0006' and upgraded['counts'] == before['counts'] and upgraded['snapshots'] == before['snapshots']
    probe_date_checks(engine, dataset, run, True)
    _assert_type_constraints(engine, dataset, run, True)
    command.downgrade(_config(), '0005')
    assert _database_state(engine) == before
    probe_date_checks(engine, dataset, run, False)
    command.upgrade(_config(), '0006')
    assert _database_state(engine) == upgraded


@pytest.mark.parametrize('blocker', ['rule', 'violation', 'snapshot_only_pass'])
def test_date_downgrade_blocks_all_history_locations(isolated_database, blocker):
    engine = isolated_database
    command.downgrade(_config(), '0006')
    dataset, run = _seed_run(engine, date_snapshot() if blocker == 'snapshot_only_pass' else None)
    with engine.begin() as c:
        if blocker == 'rule':
            c.execute(insert(QualityRule).values(**{**_rule_values(dataset, 'date_format'), 'config': {'format': 'YYYY-MM-DD'}}))
        elif blocker == 'violation':
            c.execute(insert(QualityViolation).values(**{**_violation_values(run, 'date_format'), 'error_code': 'DATE_VALUE_INVALID'}))
            c.execute(update(QualityRun).where(QualityRun.id == run).values(error_row_count=1, violation_count=1, error_row_rate=100))
        else:
            saved = c.execute(select(QualityRun.status, QualityRun.violation_count).where(QualityRun.id == run)).mappings().one()
            assert saved['status'] == 'completed' and saved['violation_count'] == 0
    before = _database_state(engine)
    if blocker == 'snapshot_only_pass': assert before['counts'] == [0, 1, 0]
    with pytest.raises(RuntimeError, match='Cannot downgrade 0006: date_format remains'):
        command.downgrade(_config(), '0005')
    assert _database_state(engine) == before and before['revision'] == '0006'
    probe_date_checks(engine, dataset, run, True)


def test_date_downgrade_offline_is_explicitly_refused():
    with pytest.raises(RuntimeError, match='Cannot downgrade 0006 offline'):
        command.downgrade(_config(), '0006:0005', sql=True)
