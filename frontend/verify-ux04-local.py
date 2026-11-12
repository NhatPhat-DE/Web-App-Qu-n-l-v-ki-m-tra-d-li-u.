"""Read-only browser verification of existing QA; remove only our own session."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(ROOT/'scripts'))
from sqlalchemy import create_engine, select, delete
from app.config import get_database_url
from app.models import User, Session, DatasetVersion
from app.services.auth_sessions import create_session
from app.services.quality_rules import rule_connection
from nv01_migrate import snapshot


def main():
    engine = create_engine(get_database_url(), hide_parameters=True)
    before = snapshot(engine)
    with rule_connection() as c:
        user = c.execute(select(User.id).where(User.username=='admin',User.is_active.is_(True),User.role=='admin')).scalar_one()
        session = create_session(c,user)
    try:
        config = dict(origin='http://127.0.0.1:5173',backendOrigin='http://127.0.0.1:8000',token=session['token'],qa=dict(dataset=57,batches=[34,35,36,37,38]))
        result = subprocess.run(['node','verify-ux04-local.mjs'],cwd=ROOT/'frontend',input=json.dumps(config),text=True)
        if result.returncode:
            raise RuntimeError('Read-only local browser verification failed; inspect artifacts.')
    finally:
        with rule_connection() as c:
            c.execute(delete(Session).where(Session.id==session['id'],Session.user_id==user))
        after = snapshot(engine)
        engine.dispose()
        proof = dict(application_rows_unchanged=before==after,own_test_session_removed=True,before=before,after=after)
        out = ROOT/'frontend/test-artifacts/ux04-local'
        out.mkdir(parents=True,exist_ok=True)
        (out/'preservation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
        assert before==after,'Local database rows changed.'
        print('QA52/55 and every existing row unchanged; removed own temporary session.')


if __name__=='__main__':
    main()
