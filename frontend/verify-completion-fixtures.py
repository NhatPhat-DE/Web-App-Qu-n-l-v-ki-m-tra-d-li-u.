"""Fault fixtures confined to the disposable frontend test database, never app data."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.config import get_database_url
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
url = make_url(get_database_url())
assert url.database.startswith('webb_frontend_test_'), 'Only the disposable verification database is permitted.'
data = json.load(sys.stdin)
engine = create_engine(url, hide_parameters=True)
try:
    with engine.begin() as connection:
        if data['action'] == 'expire':
            connection.execute(text("UPDATE user_sessions SET created_at=now()-interval '9 hours', expires_at=now()-interval '1 second' WHERE user_id=(SELECT id FROM users WHERE username=:username) AND revoked_at IS NULL"), {'username': data['username']})
        elif data['action'] == 'install_failure':
            connection.execute(text("CREATE FUNCTION test_ui_fail_violation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Disposable UI verification fault'; END $$"))
            connection.execute(text('CREATE TRIGGER test_ui_fail BEFORE INSERT ON quality_violations FOR EACH ROW EXECUTE FUNCTION test_ui_fail_violation()'))
        elif data['action'] == 'remove_failure':
            connection.execute(text('DROP TRIGGER IF EXISTS test_ui_fail ON quality_violations'))
            connection.execute(text('DROP FUNCTION IF EXISTS test_ui_fail_violation()'))
        else:
            raise ValueError('Unknown test fixture action')
finally:
    engine.dispose()
print('{"ok":true}')
