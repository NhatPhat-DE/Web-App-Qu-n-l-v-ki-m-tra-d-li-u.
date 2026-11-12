"""Caller owns connection/transaction; these functions never commit."""
import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import insert, select, update
from app.models import User, Session


class SessionError(ValueError):
    pass


def utc_now(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise SessionError('Thời gian phải có timezone.')
    return now.astimezone(timezone.utc)


def token_hash(token):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        raise SessionError('Phiên không hợp lệ.')
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def create_session(connection, user_id, now=None):
    now = utc_now(now)
    user = connection.execute(select(User.id).where(User.id == user_id, User.is_active.is_(True)).with_for_update()).first()
    if user is None:
        raise SessionError('Tài khoản không khả dụng.')
    token = secrets.token_urlsafe(32)
    expires = now + timedelta(hours=8)
    identifier = connection.execute(insert(Session).values(user_id=user_id,token_hash=token_hash(token),created_at=now,expires_at=expires)
                                    .returning(Session.id)).scalar_one()
    return {'id': identifier, 'token': token, 'expires_at': expires}


def find_session(connection, token, now=None):
    now = utc_now(now)
    hashed = token_hash(token)
    result = connection.execute(select(Session.id, Session.user_id, Session.created_at, Session.expires_at,
        User.username, User.role).join(User, User.id == Session.user_id).where(Session.token_hash == hashed,
        Session.revoked_at.is_(None), Session.expires_at > now, Session.created_at <= now, User.is_active.is_(True))).mappings().first()
    if result is None:
        raise SessionError('Phiên không còn hiệu lực.')
    return dict(result)


def revoke_session(connection, token, now=None):
    now = utc_now(now)
    return connection.execute(update(Session).where(Session.token_hash == token_hash(token),
        Session.revoked_at.is_(None), Session.created_at <= now).values(revoked_at=now)).rowcount
