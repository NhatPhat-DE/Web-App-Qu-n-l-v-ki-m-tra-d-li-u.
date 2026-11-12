"""Upgrade a populated 0009 database; application DB is never migrated here."""
import os
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from alembic import command
from alembic.config import Config
from app.config import get_database_url


@pytest.mark.parametrize('corrupt_membership', [False, True])
def test_upgrade_preserves_legacy_batches_rules_and_snapshots(monkeypatch, corrupt_membership):
    if os.getenv('RUN_POSTGRES_TESTS')!='1': pytest.skip('PostgreSQL opt-in')
    original=make_url(get_database_url())
    name='webb_nv01_migration_'+uuid4().hex
    admin=create_engine(original,isolation_level='AUTOCOMMIT',hide_parameters=True)
    engine=None
    try:
        with admin.connect() as c:c.execute(text(f'CREATE DATABASE "{name}"'))
        url=original.set(database=name)
        monkeypatch.setenv('DATABASE_URL',url.render_as_string(hide_password=False))
        cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
        command.upgrade(cfg,'0009')
        engine=create_engine(url,hide_parameters=True)
        with engine.begin() as c:
            c.execute(text("INSERT INTO datasets(id,name) VALUES (1,'Legacy')"))
            c.execute(text("INSERT INTO data_batches(id,dataset_id,name) VALUES (10,1,'Known January'),(20,1,'Known February')"))
            c.execute(text("INSERT INTO dataset_columns(dataset_id,name,position) VALUES(1,'code',1)"))
            c.execute(text("INSERT INTO dataset_versions(id,dataset_id,batch_id,version_number,original_filename,file_size_bytes,row_count,inferred_types) VALUES(11,1,10,1,'a.csv',8,1,'[]'),(12,1,10,2,'b.csv',8,1,'[]'),(21,1,20,1,'c.csv',8,1,'[]')"))
            c.execute(text('''INSERT INTO dataset_rows(version_id,row_number,values) VALUES(11,1,'["A"]'),(12,1,'["B"]'),(21,1,'["A"]')'''))
            c.execute(text('''INSERT INTO quality_rules(id,dataset_id,name,rule_type,columns,config,is_active) VALUES(100,1,'Original','required','["code"]','{}',true)'''))
            # Explicit ID to ensure the copy sequence never accidentally overwrites original.
            c.execute(text("SELECT setval(pg_get_serial_sequence('quality_rules','id'),100)"))
            c.exec_driver_sql('''INSERT INTO quality_runs(id,dataset_version_id,engine_version,rule_snapshot) VALUES(50,11,'quality-v5','[{"id":100,"name":"Original","rule_type":"required","columns":["code"],"config":{}}]')''')
            before=c.execute(text('SELECT rule_snapshot FROM quality_runs WHERE id=50')).scalar_one()
            if corrupt_membership:
                c.execute(text("INSERT INTO datasets(id,name) VALUES(2,'Other dataset')"))
                c.execute(text('UPDATE dataset_versions SET dataset_id=2 WHERE id=11'))
        if corrupt_membership:
            with pytest.raises(RuntimeError, match='inconsistent version/batch membership'):
                command.upgrade(cfg,'head')
            with engine.connect() as c:
                assert c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0009'
                assert c.execute(text('SELECT dataset_id FROM dataset_versions WHERE id=11')).scalar_one()==2
                assert c.execute(text('SELECT count(*) FROM quality_rules')).scalar_one()==1
            return
        command.upgrade(cfg,'head')
        with engine.connect() as c:
            assert c.execute(text('SELECT id,batch_id FROM dataset_versions ORDER BY id')).all()==[(11,10),(12,10),(21,20)]
            assert c.execute(text('SELECT id FROM dataset_versions WHERE is_current ORDER BY id')).scalars().all()==[12,21]
            assert c.execute(text('SELECT count(*) FROM data_batches')).scalar_one()==2
            assert c.execute(text('SELECT rule_snapshot FROM quality_runs WHERE id=50')).scalar_one()==before
            assert c.execute(text('SELECT schema_snapshot FROM quality_runs WHERE id=50')).scalar_one() is None
            assert c.execute(text('SELECT count(*) FROM quality_rules WHERE batch_id IS NULL')).scalar_one()==1
            assert c.execute(text('SELECT batch_id FROM quality_rules WHERE batch_id IS NOT NULL ORDER BY batch_id')).scalars().all()==[10,20]
            assert c.execute(text('SELECT count(*) FROM dataset_rows')).scalar_one()==3
    finally:
        if engine:engine.dispose()
        with admin.connect() as c:c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
