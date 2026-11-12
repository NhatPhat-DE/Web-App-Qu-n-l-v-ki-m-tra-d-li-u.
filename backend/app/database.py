from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.config import get_database_url


def check_database() -> bool:
    """Execute SELECT 1 without exposing connection details or keeping a pool."""
    database_url = get_database_url()
    if not database_url:
        return False

    engine = None
    try:
        url = make_url(database_url)
        if url.drivername != "postgresql+psycopg":
            return False
        engine = create_engine(
            url,
            poolclass=NullPool,
            hide_parameters=True,
            connect_args={
                "connect_timeout": 3,
                "options": "-c statement_timeout=3000",
            },
        )
        with engine.connect() as connection:
            return connection.execute(text("SELECT 1")).scalar_one() == 1
    except (SQLAlchemyError, ValueError):
        return False
    finally:
        if engine is not None:
            engine.dispose()
