"""0010 -> 0011 is additive, with no identities/issues inferred for legacy rows."""
import os
import sys
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config
from app.config import get_database_url


def test_additive_migration_preserves_all_existing_columns(monkeypatch):
    if os.getenv('RUN_POSTGRES_TESTS')!='1':pytest.skip('PostgreSQL opt-in')
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
    from nv01_migrate import snapshot
    original=make_url(get_database_url());name='webb_nv02_migration_'+uuid4().hex
    admin=create_engine(original,isolation_level='AUTOCOMMIT',hide_parameters=True);engine=None
    try:
        with admin.connect() as c:c.execute(text(f'CREATE DATABASE "{name}"'))
        url=original.set(database=name);monkeypatch.setenv('DATABASE_URL',url.render_as_string(hide_password=False))
        cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'));command.upgrade(cfg,'0010')
        engine=create_engine(url,hide_parameters=True)
        with engine.begin() as c:
            c.execute(text("INSERT INTO datasets(id,name) VALUES(1,'Legacy QA')"))
            c.execute(text("INSERT INTO data_batches(id,dataset_id,name) VALUES(1,1,'Do not infer identity')"))
            c.execute(text("INSERT INTO dataset_columns(dataset_id,name,position) VALUES(1,'code',1)"))
            c.execute(text("INSERT INTO dataset_versions(id,dataset_id,batch_id,version_number,is_current,original_filename,file_size_bytes,row_count,inferred_types) VALUES(1,1,1,1,true,'old.csv',6,1,'[]')"))
            c.execute(text('''INSERT INTO dataset_rows(version_id,row_number,values) VALUES(1,1,'["A"]')'''))
            c.execute(text("INSERT INTO quality_runs(id,dataset_version_id,rule_snapshot,engine_version,status,finished_at,total_rows,error_row_count,violation_count,error_row_rate) VALUES(1,1,'[]','quality-v6','completed',now(),1,0,0,0)"))
        before=snapshot(engine);command.upgrade(cfg,'0011')
        assert snapshot(engine,before)==before
        with engine.connect() as c:
            for table in ['dataset_identity_configs','data_issues','workflow_reconciliations','issue_events','issue_observations','reconciliation_items','batch_events']:
                assert c.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()==0
            assert c.execute(text('SELECT business_state,workflow_enabled FROM data_batches')).one()==('RECEIVING',False)
            assert c.execute(text('SELECT schema_snapshot FROM quality_runs')).scalar_one() is None
        # Empty NV-02 scope can downgrade; existing application rows survive.
        command.downgrade(cfg,'0010')
        assert snapshot(engine,before)==before
        command.upgrade(cfg,'0011')
        with engine.begin() as c:
            c.execute(text("INSERT INTO dataset_identity_configs(dataset_id,revision,columns,is_current) VALUES(1,1,'[\"code\"]',true)"))
        # Once configured, the migration must refuse to discard evidence.
        with pytest.raises(RuntimeError,match='must not be discarded'):
            command.downgrade(cfg,'0010')
        with engine.connect() as c:
            assert c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0011'
            assert c.execute(text('SELECT count(*) FROM dataset_identity_configs')).scalar_one()==1
        assert snapshot(engine,before)==before
    finally:
        if engine:engine.dispose()
        with admin.connect() as c:c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
