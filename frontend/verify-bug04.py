"""Real BUG-04 browser/HTTP test in a disposable database, no application writes."""
from pathlib import Path
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(ROOT/'scripts'))
from app.config import get_database_url
from sqlalchemy import create_engine,select,text
from sqlalchemy.engine import make_url
from nv01_migrate import snapshot


def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


def main():
    url=make_url(get_database_url())
    application=create_engine(url,hide_parameters=True)
    before=snapshot(application)
    import csv,io
    from app.models import QualityRun,DatasetRow
    with application.connect() as c:
        qa_runs=[dict(r) for r in c.execute(select(QualityRun).where(QualityRun.id.in_([66,67])).order_by(QualityRun.id)).mappings()]
        assert [(r['total_rows'],r['error_row_count'],r['violation_count']) for r in qa_runs]==[(12,6,9),(12,6,8)]
        source_rows=c.execute(select(DatasetRow.values).where(DatasetRow.version_id==qa_runs[0]['dataset_version_id']).order_by(DatasetRow.row_number)).scalars().all()
    source=io.StringIO(newline='');writer=csv.writer(source);writer.writerow([col['name'] for col in qa_runs[0]['schema_snapshot']]);writer.writerows(source_rows)
    source_bytes=source.getvalue().encode('utf-8')
    backend={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for directory in ('backend/app','backend/migrations') for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    admin=create_engine(url,isolation_level='AUTOCOMMIT',hide_parameters=True)
    name='webb_bug04_test_'+uuid4().hex
    artifacts=ROOT/'frontend/test-artifacts/bug04'
    artifacts.mkdir(parents=True,exist_ok=True)
    process=None
    engine=None
    try:
        with admin.connect() as c:c.execute(text(f'CREATE DATABASE "{name}"'))
        test_url=url.set(database=name)
        os.environ.update(DATABASE_URL=test_url.render_as_string(hide_password=False),AUTH_CSRF_SECRET=secrets.token_hex(32),AUTH_COOKIE_SECURE='false')
        backend_port,frontend_port=port(),port()
        origin=f'http://127.0.0.1:{frontend_port}'
        os.environ['AUTH_ALLOWED_ORIGINS']=origin
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'head')
        from app.models import QualityRun,DatasetVersion
        from app.services.accounts import bootstrap_admin
        from app.services.quality_rules import rule_connection,create_rule,patch_rule
        from app.services.auth_sessions import create_session
        from app.services.dataset_import import import_dataset,import_version
        from app.services.csv_reader import parse_csv
        from app.services.data_batches import create_batch,patch_batch
        from app.services.quality_execution import execute_run
        ds=import_dataset(parse_csv(source_bytes),'qa-copy.csv',dict(name='BUG-04 Snapshot riêng',owner='QA',source='Bản sao chỉ đọc QA',description='Database tạm, không sửa dataset 55'))
        dataset,jan=ds['dataset_id'],ds['batch_id']
        patch_batch(dataset,jan,dict(name='BUG-04 Đợt tái lập QA'))
        range_id=None
        for rule in qa_runs[0]['rule_snapshot']:
            created=create_rule(dataset,{**{k:rule[k] for k in ('name','rule_type','columns','config')},'is_active':True},jan)
            if rule['rule_type']=='numeric_range':range_id=created['id']
        r1=execute_run(dataset,ds['version_id'])
        expected_range=next(rule['config'] for rule in qa_runs[1]['rule_snapshot'] if rule['rule_type']=='numeric_range')
        patch_rule(dataset,range_id,{'config':expected_range},jan)
        r2=execute_run(dataset,ds['version_id'])
        assert [(r['total_rows'],r['error_row_count'],r['violation_count']) for r in (r1,r2)]==[(12,6,9),(12,6,8)]
        scratch=import_dataset(parse_csv(b'id,value\r\n1,ABC\r\n2,DEF\r\n'),'scratch.csv',dict(name='BUG-04 Thử form',owner='QA',source='Fixture riêng',description='Form quy tắc và guard'))
        patch_batch(scratch['dataset_id'],scratch['batch_id'],dict(name='BUG-04 Đợt thử form'))
        upload_file=artifacts/'scratch.csv';upload_file.write_bytes(b'id,value\r\n1,ABC\r\n2,DEF\r\n')
        user=bootstrap_admin('bug04_admin',secrets.token_urlsafe(24))
        with rule_connection() as c:token=create_session(c,user)['token']
        engine=create_engine(test_url,hide_parameters=True)
        with engine.connect() as c:
            originals=[dict(row) for row in c.execute(select(QualityRun).order_by(QualityRun.id)).mappings()]
        with (artifacts/'backend.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(backend_port)],cwd=ROOT/'backend',env=os.environ.copy(),stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(100):
                try:
                    with urlopen(f'http://127.0.0.1:{backend_port}/api/health',timeout=1) as r:
                        if r.status==200:break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('Disposable backend did not start')
            qa=dict(dataset=dataset,jan=jan,raw_run=r1['run_id'],fixed_run=r2['run_id'],scratch=scratch['dataset_id'],scratch_batch=scratch['batch_id'],upload_file=str(upload_file),account_password=secrets.token_urlsafe(18))
            result=subprocess.run(['node','verify-bug04.mjs'],cwd=ROOT/'frontend',input=json.dumps(dict(origin=origin,backendOrigin=f'http://127.0.0.1:{backend_port}',token=token,qa=qa)),text=True)
            if result.returncode:raise RuntimeError('BUG-04 browser verification failed; inspect test-artifacts/bug04')
        with engine.connect() as c:
            assert [dict(row) for row in c.execute(select(QualityRun).where(QualityRun.id.in_([r['id'] for r in originals])).order_by(QualityRun.id)).mappings()]==originals
            from app.models import QualityRule,Dataset
            rules=c.execute(select(QualityRule).where(QualityRule.dataset_id==scratch['dataset_id'])).mappings().all()
            assert len(rules)==4
            assert all(r['config'].get('pattern') not in ('[',r'\1') for r in rules)
            created=c.execute(select(Dataset.id).where(Dataset.name=='BUG-04 Tạo dataset thành công')).scalars().all()
            assert len(created)==1
        print('QA snapshot replay: 12/6/9 and 12/6/8; original snapshots unchanged; exactly one dataset created, invalid rules not persisted.')
    finally:
        if process:process.terminate();process.wait(timeout=15)
        if engine:engine.dispose()
        with admin.connect() as c:c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
        after=snapshot(application);application.dispose()
        code_unchanged=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest for p,digest in backend.items())
        proof=dict(application_data_unchanged=before==after,backend_code_unchanged=code_unchanged,test_database_removed=True,before=before,after=after)
        (artifacts/'preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
        assert before==after and code_unchanged,'Application preservation failed'
        print('Preserved application database and NV-01 backend; removed disposable test database.')


if __name__=='__main__':main()
