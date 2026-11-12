"""Live browser SRC-01 on explicitly new QA; original rows remain byte-identical."""
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'scripts')]
from sqlalchemy import create_engine,select,insert,delete,text
from app.config import get_database_url
from app.models import User,Session,DatasetColumn
from app.services.auth_sessions import create_session
from app.services.quality_rules import rule_connection,create_rule
from app.services.dataset_metadata import create_dataset
from app.services import suppliers
from nv01_migrate import snapshot


def main():
    engine=create_engine(get_database_url(),hide_parameters=True)
    baseline=json.loads((ROOT/'.runtime/src01-migration.json').read_text())['before']
    manifest=ROOT/'.runtime/src01-qa.json'
    with rule_connection() as c:
        user=c.execute(select(User.id).where(User.username=='admin',User.role=='admin',User.is_active)).scalar_one()
        session=create_session(c,user)
    actor={'user_id':user,'role':'admin','username':'admin'}
    try:
        if manifest.exists():qa=json.loads(manifest.read_text())
        else:
            brands=[suppliers.save('brand',dict(code='SRC01_QA_'+k,name='SRC01 QA Brand '+k,is_active=True),actor) for k in ['A','B']]
            stores=[suppliers.save('store',dict(code='SRC01_SHOP_'+k,name='SRC01 QA Store '+k,is_active=True,brand_id=brand['id']),actor) for k,brand in zip(['A','B'],brands)]
            ds=create_dataset(dict(name='SRC-01 QA — Nguồn riêng từng đợt',source='Chữ tham khảo, không phải cửa hàng',description='QA riêng SRC-01. Không sửa QA52/55/57/58/40.',owner='QA SRC-01'))
            with rule_connection() as c:c.execute(insert(DatasetColumn),[dict(dataset_id=ds['id'],name=n,position=i) for i,n in enumerate(['id','name'],1)])
            create_rule(ds['id'],dict(name='SRC01 tên bắt buộc',rule_type='required',columns=['name'],config={},is_active=True))
            qa=dict(dataset=ds['id'],brands=[b['id'] for b in brands],stores=[s['id'] for s in stores],period='SRC01 11/2026')
            manifest.write_text(json.dumps(qa,indent=2),encoding='utf-8')
        # Resume a partially completed browser run without creating extra batches.
        with engine.connect() as c:
            existing=list(c.execute(text('SELECT id,store_id FROM data_batches WHERE dataset_id=:ds AND store_id IS NOT NULL ORDER BY id'),{'ds':qa['dataset']}).mappings())
            if len(existing)==2:
                qa['batches']=[next(b['id'] for b in existing if b['store_id']==s) for s in qa['stores']]
                qa['runs']=[c.execute(text('SELECT min(r.id) FROM quality_runs r JOIN dataset_versions v ON v.id=r.dataset_version_id WHERE v.batch_id=:b'),{'b':b}).scalar_one() for b in qa['batches']]
                qa['fixedRun']=c.execute(text('SELECT r.id FROM quality_runs r JOIN dataset_versions v ON v.id=r.dataset_version_id WHERE v.batch_id=:b AND v.is_current AND v.version_number>1 AND r.status=\'completed\' ORDER BY r.id DESC LIMIT 1'),{'b':qa['batches'][0]}).scalar_one_or_none()
                manifest.write_text(json.dumps(qa,indent=2),encoding='utf-8')
        source=(ROOT/'frontend/verify-demo-ui-local.mjs').read_text(encoding='utf-8')
        prefix=source[:source.index(" if(phase==='before')")]
        # This task authorizes writes to the new QA; remove ONLY the old GET-only
        # harness guard, and enforce the new fixture allowlist in the test body.
        prefix='\n'.join(line for line in prefix.splitlines() if "source:`(()=>{const original=window.fetch" not in line)
        suffix=source[source.index('}catch(error){'):]
        body=(ROOT/'frontend/verify-src01.body.js').read_text(encoding='utf-8')
        config=dict(origin='http://127.0.0.1:5173',token=session['token'],phase='src01',qa=qa)
        result=subprocess.run(['node','--input-type=module','-e',prefix+body+suffix],cwd=ROOT/'frontend',input=json.dumps(config),text=True,encoding='utf-8')
        if result.returncode:raise RuntimeError('SRC01 browser failed; inspect frontend/test-artifacts/demo-ui-src01/failure.txt')
    finally:
        with rule_connection() as c:c.execute(delete(Session).where(Session.id==session['id'],Session.user_id==user))
        after=snapshot(engine,baseline)
        with engine.connect() as c:
            old_sources=c.execute(text('SELECT count(*) FROM data_batches WHERE id<=:maximum AND store_id IS NOT NULL'),{'maximum':baseline['data_batches']['max_id']}).scalar_one()
        proof=dict(original_cells_unchanged=baseline==after,old_batches_still_unassigned=old_sources==0,before=baseline,after=after)
        (ROOT/'.runtime/src01-preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
        assert baseline==after and old_sources==0,'Existing QA changed'
        engine.dispose()


if __name__=='__main__':main()
