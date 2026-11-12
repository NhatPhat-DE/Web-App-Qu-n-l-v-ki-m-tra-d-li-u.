from nv01_fixtures import current_version_values
"""Opt-in PostgreSQL checks: rollback sample data; downgrade only a new test DB."""
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.config import get_database_url
from app.models import Dataset, DatasetColumn, DatasetRow, DatasetVersion
from test_dataset_import import isolated_database

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1", reason="Set RUN_POSTGRES_TESTS=1 for real PostgreSQL"
)


def test_storage_and_constraints_rollback(isolated_database):
    engine = create_engine(get_database_url(), hide_parameters=True,
                           connect_args={"connect_timeout": 3, "options": "-c timezone=UTC"})
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                dataset = connection.execute(insert(Dataset).values(name="demo").returning(Dataset.id)).scalar_one()
                for position, name in enumerate(["code", "label", "note"], 1):
                    connection.execute(insert(DatasetColumn).values(dataset_id=dataset, name=name, position=position))
                version_values = dict(dataset_id=dataset, version_number=1, original_filename="sample.csv",
                                      file_size_bytes=100, row_count=1, inferred_types=["string"] * 3)
                version = connection.execute(insert(DatasetVersion).values(**current_version_values(connection, **version_values)).returning(DatasetVersion.id)).scalar_one()
                values = ["00123", "Tiếng Việt 日本語", "  giữ nguyên  "]
                connection.execute(insert(DatasetRow).values(version_id=version, row_number=1, values=values))
                assert connection.execute(select(DatasetRow.values).where(DatasetRow.version_id == version)).scalar_one() == values
                assert connection.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == version)).scalar_one() == ["string"] * 3
                created = connection.execute(select(Dataset.created_at).where(Dataset.id == dataset)).scalar_one()
                assert created.utcoffset().total_seconds() == 0
                # Dataset names need not be unique.
                connection.execute(insert(Dataset).values(name="demo"))
                invalid_statements = [
                    insert(Dataset).values(name=" \t\n"),
                    insert(Dataset).values(name=None),
                    insert(DatasetColumn).values(dataset_id=-1, name="orphan", position=1),
                    insert(DatasetColumn).values(dataset_id=dataset, name="code", position=4),
                    insert(DatasetColumn).values(dataset_id=dataset, name="other", position=1),
                    insert(DatasetColumn).values(dataset_id=dataset, name="zero", position=0),
                    insert(DatasetVersion).values(**version_values),
                    insert(DatasetVersion).values(**{**version_values, "dataset_id": -1}),
                    insert(DatasetVersion).values(**{**version_values, "version_number": 0}),
                    insert(DatasetRow).values(version_id=-1, row_number=1, values=[]),
                    insert(DatasetRow).values(version_id=version, row_number=1, values=[]),
                    insert(DatasetRow).values(version_id=version, row_number=0, values=[]),
                    insert(DatasetRow).values(version_id=version, row_number=2, values=[123]),
                    insert(DatasetRow).values(version_id=version, row_number=2, values={"x": "y"}),
                    Dataset.__table__.delete().where(Dataset.id == dataset),
                    DatasetVersion.__table__.delete().where(DatasetVersion.id == version),
                ]
                for statement in invalid_statements:
                    with pytest.raises(IntegrityError):
                        with connection.begin_nested():
                            connection.execute(statement)
            finally:
                transaction.rollback()
            assert connection.execute(select(Dataset.id).where(Dataset.id == dataset)).first() is None
    finally:
        engine.dispose()


def test_migration_roundtrip_separate_database(monkeypatch):
    url = make_url(get_database_url())
    test_name = "webb_migration_test_" + uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT", hide_parameters=True,
                          connect_args={"connect_timeout": 3})
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{test_name}"'))
            created = True
        monkeypatch.setenv("DATABASE_URL", url.set(database=test_name).render_as_string(hide_password=False))
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        command.upgrade(config, "head")
        test_engine = create_engine(url.set(database=test_name), hide_parameters=True)
        try:
            with test_engine.connect() as connection:
                assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == ScriptDirectory.from_config(config).get_current_head()
        finally:
            test_engine.dispose()
    finally:
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{test_name}"'))
        admin.dispose()
