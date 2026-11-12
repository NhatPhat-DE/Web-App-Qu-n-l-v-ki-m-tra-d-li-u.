from pathlib import Path
import sys,pytest
from sqlalchemy import text
from alembic import command
from alembic.config import Config
from test_dataset_import import isolated_database


def test_additive_migration_never_backfills_legacy_source_and_guards_downgrade(isolated_database):
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    command.downgrade(cfg,'0012')
    with isolated_database.begin() as c:
        c.execute(text("INSERT INTO datasets(id,name,source) VALUES(1,'Legacy','ERP store-looking text')"))
        c.execute(text("INSERT INTO data_batches(id,dataset_id,name) VALUES(1,1,'Old')"))
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
    from nv01_migrate import snapshot
    before=snapshot(isolated_database)
    command.upgrade(cfg,'0013')
    assert snapshot(isolated_database,before)==before
    with isolated_database.connect() as c:
        assert c.execute(text('SELECT store_id FROM data_batches')).scalar_one() is None
        assert c.execute(text('SELECT count(*) FROM source_stores')).scalar_one()==0
    with isolated_database.begin() as c:c.execute(text("INSERT INTO source_brands(code,name) VALUES('QA','QA')"))
    with pytest.raises(RuntimeError,match='must not be discarded'):command.downgrade(cfg,'0012')
    with isolated_database.connect() as c:assert c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0013'
