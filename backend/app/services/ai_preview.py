"""Signed five-minute preview consent; no provider calls or persistence."""
import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timezone
from collections import deque
from threading import Lock
from math import ceil
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.models import DatasetColumn
from app.services.ai_payload import build_payload, serialize_payload, AIPayloadError
from app.services.auth_sessions import find_session, SessionError, token_hash
from app.services.quality_rules import rule_connection
from app.services.dataset_catalog import CatalogNotFound


class PreviewError(ValueError):
    def __init__(self, status=409, code='AI_PREVIEW_INVALID', retry_after=None):
        self.status, self.code, self.retry_after = status, code, retry_after
        super().__init__('Preview unavailable or invalid; request a new preview before confirming.')


def secret():
    value = os.getenv('AI_PREVIEW_SECRET', '')
    if not re.fullmatch(r'(?:[a-fA-F0-9]{2}){32,128}', value) or value.lower() == os.getenv('AUTH_CSRF_SECRET', '').lower():
        raise PreviewError(503, 'AI_PREVIEW_NOT_CONFIGURED')
    return bytes.fromhex(value)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate key')
        result[key] = value
    return result


def current_user(user_id, session_token):
    if type(user_id) is not int or user_id <= 0: raise PreviewError()
    try:
        with rule_connection() as c: session = find_session(c, session_token)
        if session['user_id'] != user_id: raise PreviewError(409)
        if session['role'] not in {'admin', 'data_steward'}: raise PreviewError(403, 'FORBIDDEN')
    except SessionError:
        raise PreviewError(401, 'UNAUTHENTICATED') from None
    except (SQLAlchemyError, ConnectionError):
        raise PreviewError(503, 'DATABASE_UNAVAILABLE') from None


def column_ids(dataset_id, names):
    with rule_connection() as c:
        lookup = dict(c.execute(select(DatasetColumn.name, DatasetColumn.id).where(DatasetColumn.dataset_id == dataset_id)).all())
    if any(name not in lookup for name in names): raise PreviewError()
    return [lookup[name] for name in names]


def column_names(dataset_id, identifiers):
    with rule_connection() as c:
        lookup = dict(c.execute(select(DatasetColumn.id, DatasetColumn.name).where(DatasetColumn.dataset_id == dataset_id)).all())
    if any(identifier not in lookup for identifier in identifiers): raise PreviewError()
    return [lookup[identifier] for identifier in identifiers]


def issue_preview(dataset_id, version_id, columns, include_descriptions, include_statistics, user_id, session_token, now=None):
    key = secret()
    if type(dataset_id) is not int or dataset_id <= 0 or type(version_id) is not int or version_id <= 0: raise PreviewError(422, 'INVALID_AI_INPUT')
    current_user(user_id, session_token)
    payload = build_payload(dataset_id, version_id, columns, include_descriptions, include_statistics)
    issued = int(time.time() if now is None else now)
    from app.services.gemini_adapter import provider_info
    target=provider_info()
    claims = dict(v=1,target=target, user=user_id, session=token_hash(session_token), dataset=dataset_id, version=version_id,
                  columns=column_ids(dataset_id, columns), descriptions=include_descriptions, statistics=include_statistics,
                  payload_hash=hashlib.sha256(serialize_payload(payload)).hexdigest(), issued=issued, expires=issued+300)
    data = base64.urlsafe_b64encode(canonical(claims)).rstrip(b'=')
    signature = hmac.new(key, b'ai-preview-v1.'+data, hashlib.sha256).hexdigest()
    current_user(user_id, session_token)
    return dict(payload=payload, preview_token=data.decode('ascii')+'.'+signature,
                expires_at=datetime.fromtimestamp(issued+300, timezone.utc).isoformat(),
                **target)


def confirm_preview(preview_token, user_id, session_token, dataset_id, version_id, now=None):
    key = secret()
    if type(dataset_id) is not int or dataset_id <= 0 or type(version_id) is not int or version_id <= 0: raise PreviewError(422, 'INVALID_AI_INPUT')
    current_user(user_id, session_token)
    try:
        if not isinstance(preview_token, str) or len(preview_token) > 4096: raise ValueError()
        data, signature = preview_token.split('.')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',data) or not re.fullmatch(r'[a-f0-9]{64}',signature): raise ValueError()
        expected = hmac.new(key,b'ai-preview-v1.'+data.encode('ascii'),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature,expected): raise ValueError()
        claims = json.loads(base64.b64decode(data+'='*(-len(data)%4),altchars=b'-_',validate=True),object_pairs_hook=unique_object)
        if set(claims) != {'v','target','user','session','dataset','version','columns','descriptions','statistics','payload_hash','issued','expires'}: raise ValueError()
        if any(type(claims[field]) is not int for field in ['v','user','dataset','version','issued','expires']): raise ValueError()
        from app.services.gemini_adapter import provider_info
        if claims['target'] != provider_info(): raise ValueError()
        if claims['v'] != 1 or claims['user'] != user_id or claims['dataset'] != dataset_id or claims['version'] != version_id: raise ValueError()
        if not isinstance(claims['session'],str) or not hmac.compare_digest(claims['session'],token_hash(session_token)): raise ValueError()
        if type(claims['descriptions']) is not bool or type(claims['statistics']) is not bool: raise ValueError()
        ids=claims['columns']
        if not isinstance(ids,list) or not 1 <= len(ids) <= 30 or any(type(x) is not int or x<=0 for x in ids) or len(set(ids)) != len(ids): raise ValueError()
        if not isinstance(claims['payload_hash'],str) or not re.fullmatch(r'[a-f0-9]{64}',claims['payload_hash']): raise ValueError()
        current = time.time() if now is None else now
        if claims['expires']-claims['issued'] != 300 or current < claims['issued'] or current >= claims['expires']: raise ValueError()
    except (ValueError,TypeError,KeyError,RecursionError,SessionError):
        raise PreviewError() from None
    try:
        payload = build_payload(dataset_id,version_id,column_names(dataset_id,ids),claims['descriptions'],claims['statistics'])
    except (AIPayloadError,CatalogNotFound):
        raise PreviewError(409,'AI_PREVIEW_CHANGED') from None
    except (SQLAlchemyError,ConnectionError):
        raise PreviewError(503,'DATABASE_UNAVAILABLE') from None
    if not hmac.compare_digest(hashlib.sha256(serialize_payload(payload)).hexdigest(),claims['payload_hash']):
        raise PreviewError(409,'AI_PREVIEW_CHANGED')
    current_user(user_id,session_token)
    return payload


class PreviewLimiter:
    def __init__(self, clock=time.monotonic, capacity=10000):
        self.clock,self.capacity=clock,capacity
        self.lock=Lock()
        self.counters={}
    def reserve(self,user_id):
        with self.lock:
            now=self.clock()
            for key in list(self.counters):
                values=self.counters[key]
                while values and values[0]<=now-60: values.popleft()
                if not values: del self.counters[key]
            values=self.counters.get(user_id)
            if values and len(values)>=10: raise PreviewError(429,'AI_PREVIEW_LIMITED',max(1,ceil(values[0]+60-now)))
            if values is None and len(self.counters)>=self.capacity: raise PreviewError(429,'AI_PREVIEW_LIMITED',60)
            self.counters.setdefault(user_id,deque()).append(now)


preview_limiter=PreviewLimiter()
