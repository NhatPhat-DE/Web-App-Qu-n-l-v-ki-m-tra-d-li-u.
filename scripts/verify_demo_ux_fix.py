"""Verify existing QA40 read-only, plus explicitly labeled GET-only UI simulation."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts')]
from sqlalchemy import create_engine, select, delete
from app.config import get_database_url
from app.models import User, Session
from app.services.auth_sessions import create_session
from app.services.quality_rules import rule_connection
from nv01_migrate import snapshot


def backend_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for base in ['backend/app', 'backend/migrations'] for p in (ROOT / base).rglob('*.py')}


def main():
    engine = create_engine(get_database_url(), hide_parameters=True)
    before, backend_before = snapshot(engine), backend_hashes()
    source = (ROOT / 'frontend/verify-demo-ui-local.mjs').read_text(encoding='utf-8')
    prefix = source[:source.index(" if(phase==='before')")]
    suffix = source[source.index('}catch(error){'):]
    body = (ROOT / 'frontend/verify-demo-ux-fix.body.js').read_text(encoding='utf-8')
    with rule_connection() as c:
        user = c.execute(select(User.id).where(User.username == 'admin', User.is_active.is_(True), User.role == 'admin')).scalar_one()
        session = create_session(c, user)
    try:
        config = dict(origin='http://127.0.0.1:5173', token=session['token'], phase='demo-ux-fix')
        result = subprocess.run(['node', '--input-type=module', '-e', prefix + body + suffix], cwd=ROOT / 'frontend', input=json.dumps(config), text=True, encoding='utf-8')
        if result.returncode:
            raise RuntimeError('Browser verification failed; see frontend/test-artifacts/demo-ui-demo-ux-fix/failure.txt')
    finally:
        with rule_connection() as c:
            c.execute(delete(Session).where(Session.id == session['id'], Session.user_id == user))
        after = snapshot(engine)
        output = ROOT / 'frontend/test-artifacts/demo-ui-demo-ux-fix'
        output.mkdir(parents=True, exist_ok=True)
        proof = dict(application_rows_unchanged=before == after, backend_files_unchanged=backend_before == backend_hashes(), own_session_removed=True, before=before, after=after)
        (output / 'preservation.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
        assert before == after and proof['backend_files_unchanged'], 'Application data or backend changed'
        engine.dispose()


if __name__ == '__main__':
    main()
