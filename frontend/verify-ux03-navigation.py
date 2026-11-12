"""Real UX-03 navigation browser/HTTP test in a disposable database, no application writes."""
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
    backend={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for directory in ('backend/app','backend/migrations') for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    admin=create_engine(url,isolation_level='AUTOCOMMIT',hide_parameters=True)
    name='webb_ux03-navigation_test_'+uuid4().hex
    artifacts=ROOT/'frontend/test-artifacts/ux03-navigation'
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
        fixture=Path('D:/User_File/ChatGPT/DACN/qa_test_data')
        raw=(fixture/'v1.0_raw.csv').read_bytes();fixed=(fixture/'v1.1_fixed.csv').read_bytes()
        ds=import_dataset(parse_csv(raw),'raw.csv',dict(name='UX-03 navigation Sinh viên',owner='QA',source='Dữ liệu thử riêng',description='Kiểm thử UX-03 navigation trong database tạm'))
        dataset,jan=ds['dataset_id'],ds['batch_id']
        patch_batch(dataset,jan,dict(name='Tháng 01/2026',period_label='01/2026'))
        rules=[dict(name=f'{c} bắt buộc',rule_type='required',columns=[c],config={}) for c in parse_csv(raw).header]
        rules += [dict(name='Mã duy nhất',rule_type='unique',columns=['ma_sinh_vien'],config={}),dict(name='Email trường',rule_type='pattern',columns=['email'],config={'dialect':'re2-v1','pattern':r'[A-Za-z0-9._%+-]+@hcmut\.edu\.vn'}),dict(name='Điện thoại',rule_type='pattern',columns=['so_dien_thoai'],config={'dialect':'re2-v1','pattern':r'0[0-9]{9}'}),dict(name='Ngày sinh',rule_type='date_format',columns=['ngay_sinh'],config={'format':'YYYY-MM-DD','min':'1900-01-01','max':'2026-11-08'}),dict(name='Điểm',rule_type='numeric_range',columns=['diem_tong_ket'],config={'min':'0','max':'10'})]
        for rule in rules:
            rule['is_active']=True
            create_rule(dataset,rule)
            create_rule(dataset,rule,jan)
        r1=execute_run(dataset,ds['version_id'])
        v2=import_version(dataset,parse_csv(fixed),'fixed.csv',jan);r2=execute_run(dataset,v2['version_id'])
        v3=import_version(dataset,parse_csv((fixture/'v1.2_clean.csv').read_bytes()),'clean.csv',jan);r3=execute_run(dataset,v3['version_id'])
        assert [(r['error_row_count'],r['violation_count']) for r in (r1,r2,r3)]==[(9,16),(2,2),(0,0)]
        from app.services.quality_rules import list_rules
        jan_rule=list_rules(dataset,1,20,jan)['items'][0]
        patch_rule(dataset,jan_rule['id'],{'name':'Quy tắc đổi tên trong đợt'},jan)
        revision_run=execute_run(dataset,v3['version_id'])
        for _ in range(8):execute_run(dataset,v3['version_id'])
        feb=create_batch(dataset,dict(name='Tháng 02/2026',period_label='02/2026',copy_template_rules=True))['id']
        fv=import_version(dataset,parse_csv(raw),'feb.csv',feb);fr=execute_run(dataset,fv['version_id'])
        from app.services.quality_rules import list_rules
        first=list_rules(dataset,1,20,feb)['items'][0]
        patch_rule(dataset,first['id'],{'name':'Quy tắc mới tháng 02'},feb)
        empty=create_batch(dataset,dict(name='Đợt chờ file',copy_template_rules=False))['id']
        no_rules=create_batch(dataset,dict(name='Đợt chờ quy tắc',copy_template_rules=False))['id']
        import_version(dataset,parse_csv(raw),'no-rules.csv',no_rules)
        single=import_dataset(parse_csv(raw),'single.csv',dict(name='UX-03 navigation Chỉ một đợt',owner='QA',source='QA',description='Không được chọn ngầm'))
        user=bootstrap_admin('ux03-navigation_admin',secrets.token_urlsafe(24))
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
            qa=dict(clean_run=r3['run_id'],revision_run=revision_run['run_id'],v1=ds['version_id'],v2=v2['version_id'],dataset=dataset,jan=jan,feb=feb,raw_run=r1['run_id'],fixed_run=r2['run_id'],feb_run=fr['run_id'],v3=v3['version_id'],empty=empty,no_rules=no_rules,single_dataset=single['dataset_id'],fixed_file=str(fixture/'v1.1_fixed.csv'),total_batches=5)
            result=subprocess.run(['node','verify-ux03-navigation.mjs'],cwd=ROOT/'frontend',input=json.dumps(dict(origin=origin,backendOrigin=f'http://127.0.0.1:{backend_port}',token=token,qa=qa)),text=True)
            if result.returncode:raise RuntimeError('UX-03 navigation browser verification failed; inspect test-artifacts/ux03-navigation')
        with engine.connect() as c:
            assert [dict(row) for row in c.execute(select(QualityRun).where(QualityRun.id.in_([r['id'] for r in originals])).order_by(QualityRun.id)).mappings()]==originals
            versions=c.execute(select(DatasetVersion).where(DatasetVersion.batch_id==jan).order_by(DatasetVersion.version_number)).mappings().all()
            assert len(versions)==3 and versions[-1]['is_current'] and sum(v['is_current'] for v in versions)==1
        print('Original snapshots unchanged; v3 stays current; browser used only GET/HEAD business requests.')
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
