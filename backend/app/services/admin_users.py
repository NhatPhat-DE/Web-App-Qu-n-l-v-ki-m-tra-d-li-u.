from contextlib import contextmanager
from sqlalchemy import select, insert, update, func, text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.models import User, Session
from app.services import accounts
from app.services.auth_sessions import utc_now

PUBLIC_COLUMNS = tuple(getattr(User, name) for name in ('id', 'username', 'role', 'is_active', 'created_at', 'updated_at'))


def reject(status, code, message):
    raise HTTPException(status, detail={'code': code, 'message': message})


def lock_accounts(connection):
    # Same transaction-level lock as CLI bootstrap; acquire before any User row lock.
    connection.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': accounts.BOOTSTRAP_LOCK})


def create_user(connection, data):
    try:
        username = accounts.normalize_username(data['username'])
        password_hash = accounts.hash_password(data['password'])
    except accounts.AccountError:
        reject(422, 'INVALID_USER_INPUT', 'Tên đăng nhập hoặc mật khẩu không hợp lệ.')
    try:
        return dict(connection.execute(insert(User).values(username=username, password_hash=password_hash,
            role=data['role']).returning(*PUBLIC_COLUMNS)).mappings().one())
    except IntegrityError as exc:
        if getattr(getattr(exc.orig, 'diag', None), 'constraint_name', None) == 'uq_users_username':
            reject(409, 'USERNAME_EXISTS', 'Tên đăng nhập đã tồn tại.')
        raise


def list_users(connection, page, page_size):
    total = connection.execute(select(func.count()).select_from(User)).scalar_one()
    rows = connection.execute(select(*PUBLIC_COLUMNS).order_by(User.id).limit(page_size)
                              .offset((page - 1) * page_size)).mappings().all()
    return {'items': [dict(row) for row in rows], 'total': total, 'page': page, 'page_size': page_size}


def patch_user(connection, actor_id, user_id, changes):
    # Caller holds lock_accounts for the entire transaction, including revocation.
    if not changes or any(value is None for value in changes.values()):
        reject(422, 'INVALID_USER_PATCH', 'Cần role hoặc is_active hợp lệ, không được null.')
    old = connection.execute(select(*PUBLIC_COLUMNS).where(User.id == user_id).with_for_update()).mappings().first()
    if old is None:
        reject(404, 'USER_NOT_FOUND', 'Không tìm thấy tài khoản.')
    role = changes.get('role', old['role'])
    active = changes.get('is_active', old['is_active'])
    if actor_id == user_id and (role != 'admin' or not active):
        reject(409, 'SELF_ADMIN_CHANGE', 'Không được tự vô hiệu hóa hoặc tự hạ quyền.')
    removing_admin = old['role'] == 'admin' and old['is_active'] and (role != 'admin' or not active)
    if removing_admin:
        count = connection.execute(select(func.count()).select_from(User).where(
            User.role == 'admin', User.is_active.is_(True))).scalar_one()
        if count <= 1:
            reject(409, 'LAST_ACTIVE_ADMIN', 'Phải giữ ít nhất một admin đang hoạt động.')
    if role == old['role'] and active == old['is_active']:
        return dict(old)
    now = utc_now()
    result = dict(connection.execute(update(User).where(User.id == user_id).values(
        role=role, is_active=active, updated_at=now).returning(*PUBLIC_COLUMNS)).mappings().one())
    if role != old['role'] or not active:
        connection.execute(update(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
                           .values(revoked_at=func.greatest(Session.created_at, now)))
    return result
