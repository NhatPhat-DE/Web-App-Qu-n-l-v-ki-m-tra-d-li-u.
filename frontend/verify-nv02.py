"""NV-02 browser acceptance in a disposable PostgreSQL database."""
from pathlib import Path
import json, os, secrets, socket, subprocess, sys, time
from uuid import uuid4
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'scripts')]
from sqlalchemy import create_engine,text,select
from sqlalchemy.engine import make_url
from app.config import get_database_url
from nv01_migrate import snapshot

def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]

def main():
    original=make_url(get_database_url());application=create_engine(original,hide_parameters=True)
    before=snapshot(application);admin=create_engine(original,isolation_level='AUTOCOMMIT',hide_parameters=True)
    name='webb_nv02_browser_'+uuid4().hex;process=None;engine=None
    artifacts=ROOT/'frontend/test-artifacts/nv02';artifacts.mkdir(parents=True,exist_ok=True)
    try:
        with admin.connect() as c:c.execute(text(f'CREATE DATABASE "{name}"'))
        url=original.set(database=name);bp,fp=port(),port();origin=f'http://127.0.0.1:{fp}'
        os.environ.update(DATABASE_URL=url.render_as_string(hide_password=False),AUTH_CSRF_SECRET=secrets.token_hex(32),AUTH_COOKIE_SECURE='false',AUTH_ALLOWED_ORIGINS=origin)
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'head')
        from app.services.dataset_import import import_dataset
        from app.services.csv_reader import parse_csv
        from app.services.data_batches import patch_batch
        from app.services.quality_rules import create_rule,rule_connection
        from app.services.accounts import bootstrap_admin
        from app.services.auth_sessions import create_session
        from app.models import DataBatch,DataIssue,QualityRun,BatchEvent
        raw=b'id,part,amount,name\nA,X,-1,\nB,X,5,Bee\nC,X,20,Cee\n'
        ds=import_dataset(parse_csv(raw),'v1.csv',dict(name='NV-02 Browser QA riêng',owner='QA',source='Fixture NV-02',description='Disposable database'))
        dataset,batch=ds['dataset_id'],ds['batch_id'];patch_batch(dataset,batch,dict(name='NV-02 Browser — Xử lý và hoàn tất'))
        for body in [dict(name='Điểm 0–10',rule_type='numeric_range',columns=['amount'],config={'min':'0','max':'10'}),dict(name='Tên bắt buộc',rule_type='required',columns=['name'],config={})]:create_rule(dataset,{**body,'is_active':True},batch)
        for filename,content in [('v2.csv',b'id,part,amount,name\nC,X,8,Cee\nA,X,2,\nB,X,-2,Bee\n'),('v3.csv',b'id,part,amount,name\nB,X,3,Bee\nC,X,8,Cee\nA,X,2,Able\n')]: (artifacts/filename).write_bytes(content)
        user=bootstrap_admin('nv02_browser_admin',secrets.token_urlsafe(24))
        with rule_connection() as c:token=create_session(c,user)['token']
        engine=create_engine(url,hide_parameters=True)
        with (artifacts/'backend.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(bp)],cwd=ROOT/'backend',env=os.environ.copy(),stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(100):
                try:
                    with urlopen(f'http://127.0.0.1:{bp}/api/health',timeout=1) as r:
                        if r.status==200:break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('Disposable backend failed')
            result=subprocess.run(['node','verify-nv02.mjs'],cwd=ROOT/'frontend',input=json.dumps(dict(origin=origin,backendOrigin=f'http://127.0.0.1:{bp}',token=token,qa=dict(dataset=dataset,batch=batch,version=ds['version_id']))),text=True)
            assert result.returncode==0,'Browser acceptance failed; inspect test-artifacts/nv02'
        with engine.connect() as c:
            assert c.execute(select(DataBatch.business_state).where(DataBatch.id==batch)).scalar_one()=='PROCESSING'
            assert c.execute(select(DataIssue.status)).scalars().all()==['RESOLVED']*4
            runs=c.execute(select(QualityRun).order_by(QualityRun.id)).mappings().all()
            assert [(r['total_rows'],r['error_row_count'],r['violation_count']) for r in runs]==[(3,2,3),(3,2,2),(3,0,0)]
            assert c.execute(select(BatchEvent.action).order_by(BatchEvent.id)).scalars().all()==['INITIALIZED','COMPLETED','REOPENED']
        print('Browser results independently verified in PostgreSQL: 3 runs, 4 resolved issues, completion/reopen history.')
    finally:
        if process:process.terminate();process.wait(timeout=15)
        if engine:engine.dispose()
        with admin.connect() as c:c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose();after=snapshot(application,before);application.dispose()
        (artifacts/'preservation.json').write_text(json.dumps(dict(application_data_unchanged=before==after,test_database_removed=True,before=before,after=after),indent=2),encoding='utf-8')
        assert before==after,'Application database changed during isolated browser test'
        print('Application data unchanged; disposable database removed.')

if __name__=='__main__':main()
