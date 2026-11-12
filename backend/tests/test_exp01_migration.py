from pathlib import Path
import sys,pytest
from sqlalchemy import text
from alembic import command
from alembic.config import Config
from test_dataset_import import isolated_database


def test_export_snapshot_migration_preserves_legacy_and_blocks_history_loss(isolated_database):
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    command.downgrade(cfg,'0011')
    engine=isolated_database
    with engine.begin() as c:
        c.execute(text("INSERT INTO datasets(id,name) VALUES(1,'EXP legacy')"))
        c.execute(text("INSERT INTO data_batches(id,dataset_id,name) VALUES(1,1,'Legacy')"))
        c.execute(text("INSERT INTO dataset_versions(id,dataset_id,batch_id,version_number,is_current,original_filename,file_size_bytes,row_count,inferred_types) VALUES(1,1,1,1,true,'old.csv',6,1,'[]')"))
        c.execute(text("INSERT INTO quality_runs(id,dataset_version_id,rule_snapshot,engine_version,status,finished_at,total_rows,error_row_count,violation_count,error_row_rate) VALUES(1,1,'[]','quality-v6','completed',now(),1,0,0,0)"))
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
    from nv01_migrate import snapshot
    before=snapshot(engine);command.upgrade(cfg,'0012')
    assert snapshot(engine,before)==before
    with engine.connect() as c:assert c.execute(text('SELECT export_context_snapshot FROM quality_runs')).scalar_one() is None
    command.downgrade(cfg,'0011');assert snapshot(engine,before)==before
    command.upgrade(cfg,'0012')
    with engine.begin() as c:c.execute(text('UPDATE quality_runs SET export_context_snapshot=CAST(:body AS jsonb) WHERE id=1'),{'body':'{"identity":null}'})
    with pytest.raises(RuntimeError,match='must not be discarded'):command.downgrade(cfg,'0011')
    with engine.connect() as c:assert c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0012'
