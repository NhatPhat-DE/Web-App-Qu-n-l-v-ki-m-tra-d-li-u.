"""Backup before SRC-01 additive migration; verify all original cells untouched."""
from pathlib import Path
from datetime import datetime
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'scripts')]
from sqlalchemy import create_engine,text
from app.config import get_database_url
from nv01_migrate import snapshot
from alembic import command
from alembic.config import Config

engine=create_engine(get_database_url(),hide_parameters=True)
with engine.connect() as c:assert c.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0012'
before=snapshot(engine)
folder=ROOT/'.backups'/('src01-'+datetime.now().strftime('%Y%m%d-%H%M%S'));folder.mkdir(parents=True,exist_ok=False)
with (folder/'database.dump').open('wb') as output:
    result=subprocess.run(['docker','exec','webb-postgres-1','sh','-c','pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'],stdout=output,stderr=subprocess.PIPE)
assert result.returncode==0 and (folder/'database.dump').stat().st_size>100
with (folder/'database.dump').open('rb') as source:
    result=subprocess.run(['docker','exec','-i','webb-postgres-1','pg_restore','--file=/dev/null'],stdin=source,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
assert result.returncode==0
(folder/'RESTORE.md').write_text('Backup PostgreSQL custom format trước migration0013. Dùng pg_restore --exit-on-error --single-transaction --no-owner --dbname=<database_phuc_hoi_rieng> database.dump. Tạo database riêng, kiểm tra manifest rồi đối chiếu thay đổi sau backup trước khi chuyển ứng dụng; không restore đè database đang dùng. Nội dung CSV nằm trong dataset_rows. Migration không sửa snapshot hoặc file nguồn. Downgrade bị chặn nếu đã có danh mục/lịch sử nguồn.\n',encoding='utf-8')
(folder/'before.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'0013')
after=snapshot(engine,before)
assert before==after,'Original data changed'
with engine.connect() as c:assert c.execute(text('SELECT count(*) FROM data_batches WHERE store_id IS NOT NULL')).scalar_one()==0
proof=dict(backup=str(folder),original_cells_unchanged=True,old_batches_unassigned=True,before=before,after=after)
(ROOT/'.runtime/src01-migration.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
print(json.dumps(dict(backup=str(folder),migration='0013',original_cells_unchanged=True)))
