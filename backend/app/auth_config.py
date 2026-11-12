import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from app import config as _config  # Load the existing stable .env path lazily, no validation at import.


class AuthConfigurationError(ValueError):
    pass


def valid_origin(value):
    if not isinstance(value, str) or len(value) > 512 or value != value.strip():
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
        return (parsed.scheme in {'http','https'} and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None and not parsed.path
                and not parsed.query and not parsed.fragment and not re.search(r'[\s,*\\?#]', value)
                and not parsed.netloc.endswith(':')
                and (port is None or 1 <= port <= 65535) and value.startswith(parsed.scheme + '://'))
    except ValueError:
        return False


@dataclass(frozen=True)
class AuthSettings:
    csrf_secret: bytes = field(repr=False)
    allowed_origins: tuple[str, ...]
    cookie_secure: bool


def get_auth_settings():
    # Require an explicitly provisioned 32-byte-or-longer hex secret; never generate one here.
    value = os.getenv('AUTH_CSRF_SECRET', '')
    origins = tuple(item.strip() for item in os.getenv('AUTH_ALLOWED_ORIGINS', '').split(','))
    secure = os.getenv('AUTH_COOKIE_SECURE', '').lower()
    if not re.fullmatch(r'(?:[0-9a-fA-F]{2}){32,128}', value):
        raise AuthConfigurationError('AUTH_CSRF_SECRET chưa được cấu hình hợp lệ.')
    if not origins or any(not valid_origin(origin) for origin in origins):
        raise AuthConfigurationError('AUTH_ALLOWED_ORIGINS chưa được cấu hình hợp lệ.')
    if secure not in {'true','false'} or (secure == 'false' and any(origin.startswith('https://') for origin in origins)):
        raise AuthConfigurationError('AUTH_COOKIE_SECURE chưa được cấu hình hợp lệ.')
    return AuthSettings(bytes.fromhex(value), origins, secure == 'true')
