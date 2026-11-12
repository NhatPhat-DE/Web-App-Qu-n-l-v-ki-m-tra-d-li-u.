"""Strict untrusted model-output validation; never calls AI or writes rules."""
import json
from decimal import Decimal
from uuid import uuid4
from app.services.ai_payload import selected_columns, bounded_text, AIPayloadError
from app.services.quality_rules import validate
from app.services.quality_engine import QualityInputError

MAX_OUTPUT_BYTES = 16 * 1024
FIELDS = {'name', 'rule_type', 'columns', 'config', 'reason', 'assumptions'}
# AI scope stays closed even when the shared rule validator gains new types.
AI_RULE_TYPES = frozenset({'required', 'unique', 'numeric_range'})


class AIResponseError(ValueError):
    code = 'AI_INVALID_RESPONSE'
    def __init__(self):
        super().__init__('AI response is invalid; no suggestions accepted.')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AIResponseError()
        result[key] = value
    return result


def reject_constant(value):
    raise AIResponseError()


def parse_suggestions(raw, columns):
    """Returns only fully validated drafts. Does not verify business truth."""
    try:
        selected_columns(columns)
        if isinstance(raw, bytes):
            if len(raw) > MAX_OUTPUT_BYTES:
                raise AIResponseError()
            raw = raw.decode('utf-8', errors='strict')
        elif not isinstance(raw, str):
            raise AIResponseError()
        if len(raw.encode('utf-8', errors='strict')) > MAX_OUTPUT_BYTES:
            raise AIResponseError()
        body = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant, parse_float=Decimal)
        if not isinstance(body, dict) or set(body) != {'suggestions'}:
            raise AIResponseError()
        suggestions = body['suggestions']
        if not isinstance(suggestions, list) or len(suggestions) > 5:
            raise AIResponseError()
        for item in suggestions:
            if not isinstance(item, dict) or set(item) != FIELDS:
                raise AIResponseError()
            if not isinstance(item['rule_type'], str) or item['rule_type'] not in AI_RULE_TYPES:
                raise AIResponseError()
        # Check the entire batch's AI scope before any shared rule validation.
        for item in suggestions:
            bounded_text(item['name'], 120)
            bounded_text(item['reason'], 500)
            assumptions = item['assumptions']
            if not isinstance(assumptions, list) or not 1 <= len(assumptions) <= 5:
                raise AIResponseError()
            for assumption in assumptions:
                bounded_text(assumption, 300)
            selected_columns(item['columns'])
            if not isinstance(item['config'], dict):
                raise AIResponseError()
            if item['rule_type'] == 'numeric_range':
                for key in ('min', 'max'):
                    bounded_text(item['config'].get(key), 128)
            validate(columns, item)
        # Allocate server IDs only after all items pass; never accept provider IDs.
        return [{**item, 'suggestion_id': uuid4().hex} for item in suggestions]
    except (AIResponseError, AIPayloadError, QualityInputError, ValueError, TypeError, RecursionError, OverflowError):
        raise AIResponseError() from None
