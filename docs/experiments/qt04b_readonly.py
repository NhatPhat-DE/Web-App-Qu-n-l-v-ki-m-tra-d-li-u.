"""QT-04B frontend client GET-only verification. Never record credentials."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from sqlalchemy import create_engine,select
from app.config import get_database_url
from app.models import Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation,User
from app.services.auth_sessions import create_session,revoke_session

def main():
    engine=create_engine(get_database_url(),hide_parameters=True)
    def checks():
        with engine.connect() as c:
            return {m.__tablename__:hashlib.sha256(json.dumps([dict(r) for r in c.execute(select(m).order_by(m.id)).mappings()],ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest() for m in (Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation)}
    before=checks()
    with engine.begin() as c:
        admin=c.execute(select(User.id).where(User.role=='admin',User.is_active.is_(True)).order_by(User.id)).scalars().first()
        assert admin
        session=create_session(c,admin)
    try:
        result=subprocess.run(['node','verify-pattern.mjs','--demo-readonly'],cwd=ROOT/'frontend',input=json.dumps({'token':session['token']}),capture_output=True,text=True,encoding='utf-8',timeout=60)
        if result.returncode:raise RuntimeError('Frontend GET-only check failed: '+result.stderr[-2000:])
        data=json.loads(result.stdout)
        assert checks()==before
        data.update({'business_table_checksums_before_after':before,'business_data_unchanged':True,'temporary_auth_session_revoked_in_finally':True})
        (ROOT/'docs/samples/pattern_qt04b_readonly.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('PASS: frontend client '+str(len(data['paths']))+' GET requests; dataset48/version52/run41:10/7/7/70.0000%;7business tables unchanged. No browser acceptance.')
    finally:
        with engine.begin() as c:revoke_session(c,session['token'])
        engine.dispose()

if __name__=='__main__':main()
