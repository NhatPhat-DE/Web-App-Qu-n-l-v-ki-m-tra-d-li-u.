"""Provide a temporary session to Chromium without recording credentials."""
import json
from pathlib import Path
import subprocess
import sys
from sqlalchemy import select
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.models import User
from app.services.quality_rules import rule_connection
from app.services.auth_sessions import create_session,revoke_session

with rule_connection() as c:
    user=c.execute(select(User.id).where(User.role=='admin',User.is_active.is_(True)).order_by(User.id)).scalars().first()
    token=create_session(c,user)['token']
try:
    qa=json.loads((ROOT/'.runtime/nv01-qa.json').read_text())
    result=subprocess.run(['node','verify-nv01.mjs'],cwd=ROOT/'frontend',input=json.dumps(dict(token=token,qa=qa)),text=True)
finally:
    with rule_connection() as c:revoke_session(c,token)
raise SystemExit(result.returncode)
