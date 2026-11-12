import re
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from sqlalchemy import select, insert, text
from sqlalchemy.exc import SQLAlchemyError
from app.models import User
from app.services.quality_rules import rule_connection

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID)
BOOTSTRAP_LOCK = 240024


class AccountError(ValueError):
    pass


def normalize_username(value):
    if not isinstance(value, str) or not value.isascii():
        raise AccountError('Tên đăng nhập chỉ dùng ký tự ASCII.')
    value = value.strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{2,63}', value):
        raise AccountError('Tên đăng nhập phải có 3–64 ký tự: chữ, số, dấu chấm, gạch dưới hoặc gạch ngang.')
    return value


def validate_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise AccountError('Mật khẩu phải có 12–128 ký tự.')


def hash_password(password):
    validate_password(password)
    return _hasher.hash(password)


def verify_password(password_hash, password):
    try:
        validate_password(password)
        return _hasher.verify(password_hash, password)
    except (AccountError, VerificationError, InvalidHashError):
        return False


def bootstrap_admin(username, password):
    username = normalize_username(username)
    password_hash = hash_password(password)
    try:
        with rule_connection() as connection:
            connection.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': BOOTSTRAP_LOCK})
            if connection.execute(select(User.id).where(User.role == 'admin').limit(1)).first():
                raise AccountError('Đã có admin; bootstrap không tạo thêm hoặc phục hồi tài khoản.')
            return connection.execute(insert(User).values(username=username, password_hash=password_hash, role='admin')
                                      .returning(User.id)).scalar_one()
    except (SQLAlchemyError, ConnectionError):
        raise AccountError('Không thể tạo admin. Kiểm tra kết nối, migration và tên đăng nhập trùng.') from None
