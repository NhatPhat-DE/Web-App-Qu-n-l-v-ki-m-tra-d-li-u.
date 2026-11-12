import io
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import UploadFile
from authenticated_client import TestClient
from psycopg.errors import CheckViolation
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.config import get_database_url
from app.main import app
from app.models import Dataset, DatasetColumn, DatasetVersion, DatasetRow
from app.routers.datasets import upload_dataset
from app.services import dataset_import
from app.services.csv_reader import MAX_FILE_BYTES


@pytest.fixture
def isolated_database(monkeypatch):
    if os.getenv("RUN_POSTGRES_TESTS") != "1":
        pytest.skip("Enable RUN_POSTGRES_TESTS=1 for real PostgreSQL")
    url = make_url(get_database_url())
    name = "webb_import_test_" + uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT", hide_parameters=True)
    engine = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        test_url = url.set(database=name)
        monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
        command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
        engine = create_engine(test_url, hide_parameters=True)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


def counts(engine):
    with engine.connect() as connection:
        return [connection.execute(select(func.count()).select_from(model)).scalar_one()
                for model in [Dataset, DatasetColumn, DatasetVersion, DatasetRow]]


def test_upload_persists_all_tables(isolated_database):
    content = 'code,label,note\r\n001,Tiếng Việt,"  dòng 1\r\ndòng 2  "\r\n002,NULL,  \r\n'.encode()
    with TestClient(app) as client:
        response = client.post("/api/datasets/import", data={"name": "CSV test", "description": "Mô tả", "source": "test", "owner": "Người phụ trách"},
                               files={"file": ("../../sample.CSV", content, "application/octet-stream")})
    assert response.status_code == 201
    result = response.json()
    assert result == {"batch_id": result["batch_id"], "dataset_id": result["dataset_id"], "version_id": result["version_id"], "version_number": 1,
                      "name": "CSV test", "column_count": 3, "row_count": 2}
    assert counts(isolated_database) == [1, 3, 1, 2]
    with isolated_database.connect() as connection:
        dataset = connection.execute(select(Dataset)).mappings().one()
        assert dataset["description"] == "Mô tả" and dataset["owner"] == "Người phụ trách" and dataset["source"] == "test"
        assert connection.execute(select(DatasetColumn.name, DatasetColumn.position).order_by(DatasetColumn.position)).all() == [("code", 1), ("label", 2), ("note", 3)]
        version = connection.execute(select(DatasetVersion)).mappings().one()
        assert version["dataset_id"] == result["dataset_id"]
        assert version["original_filename"] == "sample.CSV"
        assert version["inferred_types"] == [
            {'column_name': 'code', 'position': 1, 'inferred_type': 'text', 'non_missing_count': 2, 'missing_count': 0},
            {'column_name': 'label', 'position': 2, 'inferred_type': 'text', 'non_missing_count': 2, 'missing_count': 0},
            {'column_name': 'note', 'position': 3, 'inferred_type': 'text', 'non_missing_count': 1, 'missing_count': 1},
        ] and version["file_size_bytes"] == len(content)
        assert version["row_count"] == 2 and version["version_number"] == 1
        assert connection.execute(select(DatasetRow.row_number, DatasetRow.values).order_by(DatasetRow.row_number)).all() == [
            (1, ["001", "Tiếng Việt", "  dòng 1\r\ndòng 2  "]), (2, ["002", "NULL", "  "])]


@pytest.mark.parametrize("data,filename,content,status,code", [
    ({"name": " \t"}, "a.csv", b'a\n1', 422, "INVALID_METADATA"),
    ({"name": "x"}, "a.txt", b'a\n1', 422, "INVALID_FILENAME"),
    ({"name": "x"}, "a.csv", b'a,b\n1', 422, "COLUMN_COUNT_MISMATCH"),
    ({"name": "x"}, "a.csv", b'a\n"oops', 422, "INVALID_CSV_SYNTAX"),
    ({"name": "x"}, "a.csv", b'x' * (MAX_FILE_BYTES + 1), 413, "FILE_TOO_LARGE"),
    ({}, "a.csv", b'a\n1', 422, None),
], ids=["blank-name", "extension", "column-count", "syntax", "oversize", "missing-name"])
def test_rejected_uploads_leave_no_data(isolated_database, data, filename, content, status, code):
    with TestClient(app) as client:
        response = client.post("/api/datasets/import", data=data, files={"file": (filename, content)})
    assert response.status_code == status
    if code:
        assert response.json()["error"]["code"] == code
    if code == "COLUMN_COUNT_MISMATCH":
        assert response.json()["error"]["row_number"] == 1
    assert counts(isolated_database) == [0, 0, 0, 0]


def test_write_failure_rolls_back_all_tables(isolated_database, monkeypatch):
    def factory(*args, **kwargs):
        engine = create_engine(*args, **kwargs)
        @event.listens_for(engine, "before_cursor_execute")
        def fail_rows(connection, cursor, statement, parameters, context, executemany):
            if statement.startswith("INSERT INTO dataset_rows"):
                raise IntegrityError("private SQL", {}, CheckViolation("private credentials"))
        return engine
    monkeypatch.setattr(dataset_import, "create_engine", factory)
    with TestClient(app) as client:
        response = client.post("/api/datasets/import", data={"name": "rollback"}, files={"file": ("a.csv", b'a\n1')})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "DATABASE_ERROR"
    assert "private" not in response.text
    assert counts(isolated_database) == [0, 0, 0, 0]


def test_database_unavailable(isolated_database, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:example@127.0.0.1:65432/test")
    with TestClient(app) as client:
        response = client.post("/api/datasets/import", data={"name": "offline"}, files={"file": ("a.csv", b'a\n1')})
        assert client.get("/api/health").status_code == 200
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert counts(isolated_database) == [0, 0, 0, 0]


def test_bounded_read_and_close():
    class TrackedFile(io.BytesIO):
        def read(self, size=-1):
            assert size == MAX_FILE_BYTES + 1
            return super().read(size)
    stream = TrackedFile(b'x' * (MAX_FILE_BYTES + 2))
    response = upload_dataset(UploadFile(stream, filename="a.csv"), "name", None, None, None)
    assert response.status_code == 413
    assert stream.closed
