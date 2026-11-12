from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from app.config import get_database_url
from app.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata
url = get_database_url()
if not url or not url.startswith("postgresql+psycopg://"):
    raise RuntimeError("A PostgreSQL DATABASE_URL using psycopg is required")

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=NullPool, hide_parameters=True, connect_args={"connect_timeout": 3, "options": "-c timezone=UTC -c statement_timeout=10000"})
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
