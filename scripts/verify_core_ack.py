"""Lost upload acknowledgement + failed engine in a disposable DB/server/browser."""
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
import json,os,secrets,socket,subprocess,sys,time
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'scripts')]
from sqlalchemy import create_engine,insert,text
from sqlalchemy.engine import make_url
from app.config import get_database_url
from nv01_migrate import snapshot


def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


def main():
    phase=sys.argv[1] if len(sys.argv)>1 else 'after'
    assert phase in ('before','after')
    live_url=make_url(get_database_url())
    live=create_engine(live_url,hide_parameters=True);before=snapshot(live)
    admin=create_engine(live_url,isolation_level='AUTOCOMMIT',hide_parameters=True)
    name='webb_core_ack_test_'+uuid4().hex
    assert name!=live_url.database and name.startswith('webb_core_ack_test_')
    out=ROOT/'frontend/test-artifacts'/('core-ack-'+phase);out.mkdir(parents=True,exist_ok=True)
    process=None;engine=None
    try:
        with admin.connect() as c:c.execute(text(f'CREATE DATABASE "{name}"'))
        test_url=live_url.set(database=name)
        backend_port,frontend_port=port(),port()
        assert backend_port!=frontend_port
        origin=f'http://127.0.0.1:{frontend_port}'
        os.environ.update(DATABASE_URL=test_url.render_as_string(hide_password=False),AUTH_ALLOWED_ORIGINS=origin,AUTH_CSRF_SECRET=secrets.token_hex(32),AUTH_COOKIE_SECURE='false')
        from alembic import command
        from alembic.config import Config
        command.upgrade(Config(str(ROOT/'backend/alembic.ini')),'head')
        from app.models import DatasetColumn
        from app.services.accounts import bootstrap_admin
        from app.services.auth_sessions import create_session
        from app.services.quality_rules import rule_connection,create_rule
        from app.services import suppliers
        from app.services.dataset_metadata import create_dataset
        from app.services.data_batches import create_batch
        from app.services.dataset_import import import_version
        from app.services.csv_reader import parse_csv
        from app.services.quality_execution import execute_run,RunError
        user=bootstrap_admin('ack_admin',secrets.token_urlsafe(24));actor={'user_id':user,'role':'admin','username':'ack_admin'}
        brand=suppliers.save('brand',dict(code='ACK',name='ACK test',is_active=True),actor)
        store=suppliers.save('store',dict(code='ACK_STORE',name='ACK store',brand_id=brand['id'],is_active=True),actor)
        ds=create_dataset(dict(name='CORE ACK disposable',source=None,owner='QA',description='Disposable only'))['id']
        with rule_connection() as c:
            c.execute(insert(DatasetColumn),[dict(dataset_id=ds,name=n,position=i) for i,n in enumerate(['id','value'],1)])
            token=create_session(c,user)['token']
        batches=[];runs=[]
        for label in ['After commit','Before send','Engine failed']:
            b=create_batch(ds,dict(name=label,store_id=store['id'],period_label='ACK test',copy_template_rules=False),actor)['id'];batches.append(b)
            v=import_version(ds,parse_csv(b'id,value\nA,one\nB,two\nC,three'),'baseline.csv',b)
            create_rule(ds,dict(name='Required',rule_type='required',columns=['value'],config={},is_active=True),b)
            runs.append(execute_run(ds,v['version_id'])['run_id'])
        with patch('app.services.quality_execution.check_quality',side_effect=RuntimeError('QA forced engine failure')):
            try:execute_run(ds,v['version_id'])
            except RunError as e:assert e.failure_recorded;failed_run=e.run_id
            else:raise AssertionError('Expected recorded failure')
        qa=dict(dataset=ds,batch=batches[0],retry_batch=batches[1],failed_batch=batches[2],failed_run=failed_run,previous_clean=runs[-1])
        engine=create_engine(test_url,hide_parameters=True)
        with (out/'backend.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(backend_port)],cwd=ROOT/'backend',env=os.environ.copy(),stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(100):
                try:
                    with urlopen(f'http://127.0.0.1:{backend_port}/api/health',timeout=1) as r:
                        if r.status==200:break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('Disposable server not ready')
            source=(ROOT/'frontend/verify-bug03.mjs').read_text(encoding='utf-8')
            prefix=source[:source.index(' const dialogs=[];')]
            prefix=prefix.replace('const {origin,backendOrigin,token,qa}=','const {origin,backendOrigin,token,qa,phase}=').replace("path.resolve('test-artifacts/bug03')","path.resolve('test-artifacts/core-ack-'+phase)")
            suffix=source[source.rindex('}catch(error){'):]
            suffix=suffix.replace('fs.rmSync(profile,{recursive:true,force:true})',"assert.ok(path.resolve(profile).startsWith(path.resolve(os.tmpdir())+path.sep)&&path.basename(profile).startsWith('bug03-browser-'));fs.rmSync(profile,{recursive:true,force:true})")
            body=(ROOT/'frontend/verify-core-ack.body.js').read_text(encoding='utf-8')
            result=subprocess.run(['node','--input-type=module','-e',prefix+body+suffix],cwd=ROOT/'frontend',input=json.dumps(dict(origin=origin,backendOrigin=f'http://127.0.0.1:{backend_port}',token=token,qa=qa,phase=phase)),text=True,encoding='utf-8')
            if result.returncode:raise RuntimeError('Browser failed; inspect '+str(out/'failure.txt'))
        with engine.connect() as c:
            rows=[dict(r) for r in c.execute(text('SELECT id,batch_id,version_number,is_current,original_filename FROM dataset_versions ORDER BY id')).mappings()]
            failed=dict(c.execute(text('SELECT id,status,total_rows,error_row_count,violation_count FROM quality_runs WHERE id=:id'),{'id':failed_run}).mappings().one())
        assert failed['status']=='failed' and failed['error_row_count'] is None
        (out/'database-evidence.json').write_text(json.dumps(dict(versions=rows,failed_run=failed),indent=2),encoding='utf-8')
    finally:
        if process:
            process.terminate();process.wait(timeout=15)
        if engine:engine.dispose()
        with admin.connect() as c:c.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        after=snapshot(live)
        proof=dict(application_database_unchanged=before==after,temporary_database_dropped=True,before=before,after=after)
        (out/'preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
        assert before==after,'Application DB changed'
        admin.dispose();live.dispose()


if __name__=='__main__':main()
