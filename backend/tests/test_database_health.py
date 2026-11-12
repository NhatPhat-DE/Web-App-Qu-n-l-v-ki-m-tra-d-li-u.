from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app import database
from app.main import app


@pytest.mark.parametrize("available", [True, False])
def test_database_health_contract(monkeypatch, available):
    monkeypatch.setattr("app.routers.health.check_database", lambda: available)
    with TestClient(app) as client:
        response = client.get("/api/health/db")
        assert response.status_code == (200 if available else 503)
        assert response.json() == (
            {"status": "ok", "database": "ok"}
            if available
            else {"status": "error", "database": "unavailable"}
        )
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/health").status_code == 200


@pytest.mark.parametrize("fails", [False, True])
def test_select_one_and_connection_cleanup(monkeypatch, fails):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://test:secret@127.0.0.1/test"
    )
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    if fails:
        connection.execute.side_effect = OperationalError(
            "SELECT 1", {}, Exception("secret connection details")
        )
    else:
        connection.execute.return_value.scalar_one.return_value = 1
    factory = MagicMock(return_value=engine)
    monkeypatch.setattr(database, "create_engine", factory)

    assert database.check_database() is (not fails)
    assert str(connection.execute.call_args.args[0]) == "SELECT 1"
    engine.connect.return_value.__exit__.assert_called_once()
    engine.dispose.assert_called_once()
    assert factory.call_args.kwargs["connect_args"]["connect_timeout"] == 3


@pytest.mark.parametrize("url", [None, "invalid-url", "sqlite://"])
def test_missing_or_invalid_configuration(monkeypatch, url):
    if url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", url)
    assert database.check_database() is False
