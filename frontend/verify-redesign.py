"""Run real backend/browser verification without writing to the application database.

Uses the same disposable-database pattern as backend/tests/test_dataset_import.py.
No passwords, CSRF secrets or connection URLs are written to files or stdout.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
os.chdir(ROOT / 'backend')
from app.config import get_database_url
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(get_database_url())
name = 'webb_frontend_test_' + uuid4().hex
assert name.startswith('webb_frontend_test_') and name.replace('_', '').isalnum()
admin = create_engine(url, isolation_level='AUTOCOMMIT', hide_parameters=True)
completion = '--completion' in sys.argv
artifacts = ROOT / 'frontend' / 'test-artifacts' / ('completion' if completion else 'redesign')
artifacts.mkdir(parents=True, exist_ok=True)
tables = ['datasets', 'dataset_columns', 'dataset_versions', 'dataset_rows', 'quality_rules', 'quality_runs', 'quality_violations', 'users', 'user_sessions']
def application_snapshot():
    engine = create_engine(url, hide_parameters=True)
    try:
        with engine.begin() as connection:
            connection.execute(text('SET TRANSACTION READ ONLY'))
            return {table: dict(connection.execute(text(f"SELECT count(*) AS count, md5(coalesce(string_agg(row_to_json(t)::text, '|' ORDER BY id),'')) AS checksum FROM {table} t")).mappings().one()) for table in tables}
    finally:
        engine.dispose()

before = application_snapshot()
backend_files = {str(file.relative_to(ROOT)): hashlib.sha256(file.read_bytes()).hexdigest() for directory in ['backend/app', 'backend/migrations'] for file in (ROOT / directory).rglob('*') if file.is_file() and '__pycache__' not in file.parts}
backend_files['backend/.env'] = hashlib.sha256((ROOT / 'backend/.env').read_bytes()).hexdigest()
process = None
try:
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    os.environ['DATABASE_URL'] = url.set(database=name).render_as_string(hide_password=False)
    os.environ['AUTH_ALLOWED_ORIGINS'] = 'http://127.0.0.1:5174'
    os.environ['AUTH_CSRF_SECRET'] = secrets.token_hex(32)
    os.environ['AUTH_COOKIE_SECURE'] = 'false'
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(ROOT / 'backend/alembic.ini')), 'head')
    from app.services.accounts import bootstrap_admin
    password = secrets.token_urlsafe(24)
    bootstrap_admin('frontend_test_admin', password)
    with (artifacts / 'test-backend.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8011'], cwd=ROOT / 'backend', env=os.environ.copy(), stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        for _ in range(100):
            try:
                with urlopen('http://127.0.0.1:8011/api/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('Disposable test backend did not start.')
        result = subprocess.run(['node', '--experimental-strip-types', 'verify-redesign.mjs'], cwd=ROOT / 'frontend', input=json.dumps({'username': 'frontend_test_admin', 'password': password, 'completion': completion}), text=True)
        if result.returncode:
            raise RuntimeError('Browser verification failed; see test-artifacts/redesign/failure.txt')
finally:
    if process:
        process.terminate()
        process.wait(timeout=15)
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin.dispose()
    after = application_snapshot()
    unchanged_backend = all(hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == checksum for file, checksum in backend_files.items())
    evidence = {'application_database_unchanged': before == after, 'backend_source_and_environment_unchanged': unchanged_backend, 'tables': after, 'test_database_removed': True}
    (artifacts / 'preservation.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    assert before == after, 'Application business tables changed during verification.'
    assert unchanged_backend, 'Backend source or environment changed.'
    print('Preservation confirmed: 9 application tables (including accounts/sessions), backend source and .env unchanged; disposable test database removed.')
