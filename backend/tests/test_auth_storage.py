from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import insert, select, update, func, event
from sqlalchemy.exc import IntegrityError
from app.models import User, Session
from app.services import accounts
from app.cli import create_admin
from test_dataset_import import isolated_database


@pytest.mark.parametrize('raw,expected', [(' Admin ', 'admin'),('ABC_123','abc_123'),('a.b-c','a.b-c')])
def test_username(raw, expected):
    assert accounts.normalize_username(raw) == expected


@pytest.mark.parametrize('value', ['', 'ab', 'a'*65, 'Việt', 'foo bar', '_abc', None])
def test_invalid_username(value):
    with pytest.raises(accounts.AccountError): accounts.normalize_username(value)


def test_password_exact():
    password = '  demo password  '
    hashed = accounts.hash_password(password)
    assert hashed.startswith('$argon2id$v=19$m=65536,t=3,p=4$')
    assert accounts.verify_password(hashed, password)
    assert not accounts.verify_password(hashed, password.strip())
    assert not accounts.verify_password(hashed, 'wrong password')
    for value in ['x'*11, 'x'*129, None]:
        with pytest.raises(accounts.AccountError): accounts.hash_password(value)


@pytest.mark.parametrize('answers', [['admin','demo password','not matching'], ['admin','demo password']])
def test_cli_confirmation(isolated_database, monkeypatch, answers, capsys):
    monkeypatch.setattr('sys.argv', ['create_admin'])
    values = iter(answers)
    def prompt(_):
        try: return next(values)
        except StopIteration: raise EOFError()
    monkeypatch.setattr(create_admin.getpass, 'getpass', prompt)
    assert create_admin.main() == 1
    assert 'demo password' not in capsys.readouterr().out
    with isolated_database.connect() as connection:
        assert connection.execute(select(func.count()).select_from(User)).scalar_one() == 0


def test_bootstrap_concurrent_and_disabled(isolated_database):
    def attempt(username):
        try: return accounts.bootstrap_admin(username, 'demo password')
        except accounts.AccountError: return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt,['admin_one','admin_two']))
    assert sum(item is not None for item in results) == 1
    with isolated_database.begin() as connection:
        assert connection.execute(select(func.count()).select_from(User)).scalar_one() == 1
        connection.execute(update(User).values(is_active=False))
    with pytest.raises(accounts.AccountError, match='Đã có admin'):
        accounts.bootstrap_admin('new_admin','demo password')


def test_user_and_session_constraints(isolated_database):
    now = datetime.now(timezone.utc)
    def user(**changes): return dict(username='user_one',password_hash='test fixture',role='data_steward',created_at=now,updated_at=now,**changes)
    with isolated_database.begin() as connection:
        identifier = connection.execute(insert(User).values(**user()).returning(User.id)).scalar_one()
        connection.execute(insert(Session).values(user_id=identifier,token_hash='a'*64,created_at=now,expires_at=now+timedelta(hours=8)))
    for changes in [{'username':'UPPER'}, {'username':'ab'}, {'role':'owner'}, {'updated_at':now-timedelta(seconds=1)}, {}]:
        row=user(); row.update(changes)
        with pytest.raises(IntegrityError), isolated_database.begin() as connection:
            connection.execute(insert(User).values(**row))
    base=dict(user_id=identifier,token_hash='b'*64,created_at=now,expires_at=now+timedelta(hours=8))
    for changes in [{'user_id':999999}, {'token_hash':'bad'}, {'token_hash':'A'*64}, {'token_hash':'a'*64}, {'expires_at':now}, {'revoked_at':now-timedelta(seconds=1)}]:
        row={**base,**changes}
        with pytest.raises(IntegrityError), isolated_database.begin() as connection:
            connection.execute(insert(Session).values(**row))
    with isolated_database.connect() as connection:
        stored = connection.execute(select(Session)).mappings().one()
        assert stored['expires_at']-stored['created_at'] == timedelta(hours=8)
        assert stored['created_at'].tzinfo is not None


def test_bootstrap_duplicate_and_rollback(isolated_database, monkeypatch):
    with isolated_database.begin() as connection:
        connection.execute(insert(User).values(username='taken',password_hash='fixture',role='data_steward'))
    with pytest.raises(accounts.AccountError): accounts.bootstrap_admin(' TAKEN ', 'demo password')
    @event.listens_for(isolated_database, 'commit')
    def fail_commit(connection): raise RuntimeError('simulated write failure')
    from contextlib import contextmanager
    @contextmanager
    def broken_connection():
        with isolated_database.begin() as connection: yield connection
    monkeypatch.setattr(accounts, 'rule_connection', broken_connection)
    with pytest.raises(RuntimeError): accounts.bootstrap_admin('admin','demo password')
    event.remove(isolated_database, 'commit', fail_commit)
    with isolated_database.connect() as connection:
        assert connection.execute(select(func.count()).select_from(User).where(User.role=='admin')).scalar_one() == 0


def test_two_bootstrap_processes(isolated_database):
    import subprocess, sys, json
    source = '''import sys,json
from app.services.accounts import bootstrap_admin, AccountError
data=json.load(sys.stdin)
try:
 bootstrap_admin(data[0],data[1]); print("created")
except AccountError:
 print("rejected")
'''
    processes = [subprocess.Popen([sys.executable,'-c',source],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    for i, process in enumerate(processes):
        process.stdin.write(json.dumps([f'admin_{i}','demo password']))
        process.stdin.close(); process.stdin = None
    results = [process.communicate(timeout=20)[0].strip() for process in processes]
    assert sorted(results) == ['created','rejected']
    assert all(process.returncode == 0 for process in processes)
    with isolated_database.connect() as connection:
        assert connection.execute(select(func.count()).select_from(User).where(User.role=='admin')).scalar_one() == 1


def test_cli_success_and_no_arguments(isolated_database, monkeypatch, capsys):
    monkeypatch.setattr('sys.argv',['create_admin','password'])
    assert create_admin.main() == 1
    monkeypatch.setattr('sys.argv',['create_admin'])
    values = iter([' Admin ', '  demo password  ', '  demo password  '])
    monkeypatch.setattr(create_admin.getpass,'getpass',lambda _: next(values))
    assert create_admin.main() == 0
    assert 'demo password' not in capsys.readouterr().out
    with isolated_database.connect() as connection:
        row = connection.execute(select(User)).mappings().one()
        assert row['username'] == 'admin' and row['role'] == 'admin'
        assert accounts.verify_password(row['password_hash'],'  demo password  ')
