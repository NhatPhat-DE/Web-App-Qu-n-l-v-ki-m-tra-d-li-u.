import hashlib
import hmac
import re
import secrets
from app.auth_config import get_auth_settings, valid_origin
from app.services.auth_sessions import token_hash, utc_now, SessionError


class CSRFError(ValueError):
    pass


def signature(secret, label, value):
    return hmac.new(secret, (label + ':' + value).encode('ascii'), hashlib.sha256).hexdigest()


def validate_origin(origin):
    settings = get_auth_settings()
    if not valid_origin(origin) or origin not in settings.allowed_origins:
        raise CSRFError('Origin không được phép.')


def create_challenge(now=None):
    settings = get_auth_settings()
    issued = int(utc_now(now).timestamp())
    payload = f'{secrets.token_urlsafe(32)}.{issued}.{issued + 900}'
    return payload + '.' + signature(settings.csrf_secret, 'preauth-signature-v1', payload)


def preauth_csrf_token(challenge, now=None):
    settings = get_auth_settings()
    if not isinstance(challenge, str) or len(challenge) > 150 or not re.fullmatch(r'[A-Za-z0-9_-]{43}\.[0-9]{1,12}\.[0-9]{1,12}\.[0-9a-f]{64}', challenge):
        raise CSRFError('Challenge không hợp lệ.')
    nonce, issued, expiry, mac = challenge.split('.')
    payload = f'{nonce}.{issued}.{expiry}'
    if not hmac.compare_digest(mac, signature(settings.csrf_secret, 'preauth-signature-v1', payload)):
        raise CSRFError('Challenge không hợp lệ.')
    current = utc_now(now).timestamp()
    if int(expiry) - int(issued) != 900 or not int(issued) <= current < int(expiry):
        raise CSRFError('Challenge không còn hiệu lực.')
    return signature(settings.csrf_secret, 'preauth-csrf-v1', challenge)


def session_csrf_token(token):
    settings = get_auth_settings()
    try: token_hash(token)
    except SessionError: raise CSRFError('Token phiên không hợp lệ.') from None
    return signature(settings.csrf_secret, 'session-csrf-v1', token)


def compare_token(expected, supplied):
    if not isinstance(supplied, str) or not re.fullmatch(r'[0-9a-f]{64}', supplied) or not hmac.compare_digest(expected, supplied):
        raise CSRFError('Token CSRF không hợp lệ.')


def validate_preauth_csrf(challenge, supplied, now=None):
    compare_token(preauth_csrf_token(challenge, now), supplied)


def validate_session_csrf(token, supplied):
    # Caller must also authenticate the session with find_session; HMAC alone is not authentication.
    compare_token(session_csrf_token(token), supplied)
