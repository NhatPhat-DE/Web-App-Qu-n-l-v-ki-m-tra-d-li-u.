from nv01_fixtures import current_version_values
"""Real PostgreSQL migration checks; every case uses a new disposable DB."""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from psycopg.errors import CheckViolation
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import IntegrityError

from app.models import Dataset, DatasetVersion, QualityRule, QualityRun, QualityViolation
from test_dataset_import import isolated_database


def _config():
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


def _snapshot(rule_type="required"):
    return [{
        "id": 1,
        "name": "stored rule",
        "rule_type": rule_type,
        "columns": ["value"],
        "config": {"type": "integer"} if rule_type == "data_type" else {},
    }]


def _seed_run(engine, snapshot=None):
    with engine.begin() as connection:
        dataset = connection.execute(
            insert(Dataset).values(name="data_type migration test").returning(Dataset.id)
        ).scalar_one()
        version = connection.execute(insert(DatasetVersion).values(**current_version_values(connection, 
            dataset_id=dataset,
            version_number=1,
            original_filename="migration.csv",
            file_size_bytes=8,
            row_count=1,
            inferred_types=[],
        )).returning(DatasetVersion.id)).scalar_one()
        now = datetime.now(timezone.utc)
        run = connection.execute(insert(QualityRun).values(
            dataset_version_id=version,
            status="completed",
            started_at=now,
            finished_at=now,
            rule_snapshot=_snapshot() if snapshot is None else snapshot,
            engine_version="quality-v1" if snapshot is None else "quality-v2",
            total_rows=1,
            error_row_count=0,
            violation_count=0,
            error_row_rate=0,
        ).returning(QualityRun.id)).scalar_one()
    return dataset, run


def _rule_values(dataset, rule_type):
    return dict(
        dataset_id=dataset,
        name="stored rule",
        rule_type=rule_type,
        columns=["value"],
        config={"type": "integer"} if rule_type == "data_type" else {},
    )


def _violation_values(run, rule_type, rule_order=50):
    return dict(
        run_id=run,
        rule_id_snapshot=1,
        rule_type=rule_type,
        rule_order=rule_order,
        row_number=1,
        columns=["value"],
        values=["bad"],
        error_code="DATA_TYPE_INTEGER_INVALID" if rule_type == "data_type" else "REQUIRED_MISSING",
        message="Stored explanation.",
    )


def _assert_type_constraints(engine, dataset, run, data_type_allowed):
    with engine.begin() as connection:
        for rule_type in ("required", "unique", "numeric_range", "data_type", "unknown"):
            allowed = rule_type != "unknown" and (rule_type != "data_type" or data_type_allowed)
            for model, values, constraint in (
                (QualityRule, _rule_values(dataset, rule_type), "ck_quality_rules_type"),
                (QualityViolation, _violation_values(run, rule_type), "ck_quality_violations_type"),
            ):
                savepoint = connection.begin_nested()
                try:
                    if allowed:
                        connection.execute(insert(model).values(**values))
                    else:
                        with pytest.raises(IntegrityError) as error:
                            connection.execute(insert(model).values(**values))
                        assert isinstance(error.value.orig, CheckViolation)
                        assert error.value.orig.diag.constraint_name == constraint
                finally:
                    savepoint.rollback()


def _database_state(engine):
    with engine.connect() as connection:
        return {
            "revision": connection.execute(text(
                "SELECT version_num FROM alembic_version"
            )).scalar_one(),
            "constraints": connection.execute(text("""
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conname IN ('ck_quality_rules_type', 'ck_quality_violations_type')
                ORDER BY conname
            """)).all(),
            "counts": [connection.execute(select(func.count()).select_from(model)).scalar_one()
                       for model in (QualityRule, QualityRun, QualityViolation)],
            "snapshots": connection.execute(
                select(QualityRun.rule_snapshot).order_by(QualityRun.id)
            ).scalars().all(),
        }


def test_upgrade_extends_both_checks_and_preserves_legacy(isolated_database):
    engine = isolated_database
    command.downgrade(_config(), "0004")
    dataset, run = _seed_run(engine)
    with engine.begin() as connection:
        connection.execute(insert(QualityRule).values(**_rule_values(dataset, "required")))
        connection.execute(insert(QualityViolation).values(**_violation_values(run, "required", rule_order=1)))
        connection.execute(update(QualityRun).where(QualityRun.id == run).values(
            error_row_count=1, violation_count=1, error_row_rate=100,
        ))
    before = _database_state(engine)
    assert before["revision"] == "0004"
    _assert_type_constraints(engine, dataset, run, data_type_allowed=False)

    command.upgrade(_config(), "0005")
    after = _database_state(engine)
    assert after["revision"] == "0005"
    assert after["counts"] == before["counts"]
    assert after["snapshots"] == before["snapshots"]
    assert len(after["constraints"]) == 2
    _assert_type_constraints(engine, dataset, run, data_type_allowed=True)


def test_clean_downgrade_restores_both_checks_and_upgrades_again(isolated_database):
    engine = isolated_database
    command.downgrade(_config(), "0005")
    dataset, run = _seed_run(engine)
    with engine.begin() as connection:
        connection.execute(insert(QualityRule).values(**_rule_values(dataset, "required")))
        connection.execute(insert(QualityViolation).values(**_violation_values(run, "required", rule_order=1)))
        connection.execute(update(QualityRun).where(QualityRun.id == run).values(
            error_row_count=1, violation_count=1, error_row_rate=100,
        ))
    before = _database_state(engine)

    command.downgrade(_config(), "0004")
    downgraded = _database_state(engine)
    assert downgraded["revision"] == "0004"
    assert downgraded["counts"] == before["counts"]
    assert downgraded["snapshots"] == before["snapshots"]
    assert len(downgraded["constraints"]) == 2
    _assert_type_constraints(engine, dataset, run, data_type_allowed=False)

    command.upgrade(_config(), "0005")
    assert _database_state(engine) == before
    _assert_type_constraints(engine, dataset, run, data_type_allowed=True)


@pytest.mark.parametrize("blocker", ["rule", "violation", "snapshot_only"])
def test_downgrade_refuses_any_data_type_without_changing_constraints(isolated_database, blocker):
    engine = isolated_database
    command.downgrade(_config(), "0005")
    dataset, run = _seed_run(engine, _snapshot("data_type") if blocker == "snapshot_only" else None)
    with engine.begin() as connection:
        if blocker == "rule":
            connection.execute(insert(QualityRule).values(**_rule_values(dataset, "data_type")))
        elif blocker == "violation":
            connection.execute(insert(QualityViolation).values(**_violation_values(run, "data_type", rule_order=1)))
            connection.execute(update(QualityRun).where(QualityRun.id == run).values(
                error_row_count=1, violation_count=1, error_row_rate=100,
            ))
        else:
            stored_run = connection.execute(select(QualityRun.status, QualityRun.error_row_count, QualityRun.violation_count).where(QualityRun.id == run)).mappings().one()
            assert stored_run["status"] == "completed"
            assert stored_run["error_row_count"] == stored_run["violation_count"] == 0
            assert connection.execute(select(func.count()).select_from(QualityViolation)).scalar_one() == 0
            assert connection.execute(select(func.count()).select_from(QualityRule)).scalar_one() == 0
    before = _database_state(engine)

    with pytest.raises(RuntimeError, match="Cannot downgrade 0005: data_type remains"):
        command.downgrade(_config(), "0004")

    assert _database_state(engine) == before
    assert before["revision"] == "0005"
    assert len(before["constraints"]) == 2
    _assert_type_constraints(engine, dataset, run, data_type_allowed=True)
