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


from nv01_migrate import snapshot


if __name__=='__main__':
    engine=create_engine(get_database_url(),hide_parameters=True)
    with engine.connect() as c: current=c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
    if current!='0010': raise SystemExit(f'Expected 0010 before controlled NV-02 migration; found {current}. No changes.')
    before=snapshot(engine)
    folder=ROOT/'.backups'/('nv02-db-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(parents=True,exist_ok=False)
    backup=folder/'database.dump'
    with backup.open('wb') as target:
        result=subprocess.run(['docker','exec','webb-postgres-1','sh','-c','pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'],stdout=target,stderr=subprocess.PIPE)
    if result.returncode or backup.stat().st_size<100: raise SystemExit('Database backup failed. Migration was not applied.')
    command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'head')
    after=snapshot(engine,before)
    evidence=dict(original_rows_unchanged=before==after,before=before,after=after,backup=str(backup.relative_to(ROOT)))
    (ROOT/'.runtime'/'nv02-migration-preservation.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    engine.dispose()
    if before!=after: raise SystemExit('Original row verification differs; inspect evidence before continuing.')
    print('Migration 0011 applied. All original row values/IDs preserved. Backup:',backup.relative_to(ROOT))
