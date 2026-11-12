"""Back up the local database, upgrade, and verify all pre-existing row values.

No credentials or connection URL are printed. Run with backend/.venv Python.
"""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import subprocess
import sys
from sqlalchemy import create_engine, text

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.config import get_database_url
from alembic import command
from alembic.config import Config


def snapshot(engine, original=None):
    output={}
    with engine.connect() as c:
        tables=original.keys() if original else c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename<>'alembic_version' ORDER BY tablename")).scalars().all()
        for table in tables:
            assert table.replace('_','').isalnum()
            columns=original[table]['columns'] if original else c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:t ORDER BY ordinal_position"),{'t':table}).scalars().all()
            cols=','.join('"'+col+'"' for col in columns)
            max_id=original[table]['max_id'] if original else c.execute(text(f'SELECT coalesce(max(id),0) FROM "{table}"')).scalar_one()
            rows=c.execute(text(f'SELECT row_to_json(t)::text FROM (SELECT {cols} FROM "{table}" WHERE id<=:maximum ORDER BY id) t'),{'maximum':max_id}).scalars().all()
            output[table]=dict(columns=list(columns),max_id=max_id,count=len(rows),sha256=hashlib.sha256('\n'.join(rows).encode()).hexdigest())
    return output


if __name__=='__main__':
    engine=create_engine(get_database_url(),hide_parameters=True)
    with engine.connect() as c: current=c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
    if current!='0009': raise SystemExit(f'Expected 0009 before controlled NV-01 migration; found {current}. No changes.')
    before=snapshot(engine)
    folder=ROOT/'.backups'/('nv01-db-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True,exist_ok=False)
    backup=folder/'database.dump'
    with backup.open('wb') as target:
        result=subprocess.run(['docker','exec','webb-postgres-1','sh','-c','pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'],stdout=target,stderr=subprocess.PIPE)
    if result.returncode or backup.stat().st_size<100: raise SystemExit('Database backup failed. Migration was not applied.')
    command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'head')
    after=snapshot(engine,before)
    evidence=dict(original_rows_unchanged=before==after,before=before,after=after,backup=str(backup.relative_to(ROOT)))
    (ROOT/'.runtime'/'nv01-migration-preservation.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    engine.dispose()
    if before!=after: raise SystemExit('Original row verification differs; inspect evidence before continuing.')
    print('Migration 0010 applied. All original row values/IDs preserved. Backup:',backup.relative_to(ROOT))
