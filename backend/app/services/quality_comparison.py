"""Read stored run summaries/snapshots without executing or modifying quality checks."""
import json
from datetime import datetime
from decimal import Decimal, localcontext

from sqlalchemy import select, text

from app.models import Dataset, DatasetVersion
from app.services.dataset_catalog import catalog_connection, CatalogNotFound
from app.services.quality_execution import RunError
from app.services.quality_history import find_run
from app.services.quality_trend import fingerprint


def invalid_result():
    return RunError(500, 'INVALID_RUN_RESULT', 'Kết quả lần chạy không hợp lệ; không thể đối chiếu.')


def _string(value):
    if not isinstance(value, str) or not value.strip() or '\x00' in value:
        raise ValueError()
    value.encode('utf-8')
    return value


def _side(row, version):
    try:
        counts = {key: row[key] for key in ('total_rows', 'error_row_count', 'violation_count')}
        if any(type(value) is not int for value in counts.values()):
            raise ValueError()
        total, errors, violations = (counts[k] for k in ('total_rows', 'error_row_count', 'violation_count'))
        if total <= 0 or not 0 <= errors <= total or violations < errors:
            raise ValueError()
        rate = row['error_row_rate']
        if not isinstance(rate, Decimal) or not rate.is_finite() or not 0 <= rate <= 100:
            raise ValueError()
        for key in ('started_at', 'finished_at'):
            value = row[key]
            if not isinstance(value, datetime) or value.utcoffset() is None:
                raise ValueError()
        if row['finished_at'] < row['started_at']:
            raise ValueError()
        engine = _string(row['engine_version'])
        snapshot = row['rule_snapshot']
        if not isinstance(snapshot, list):
            raise ValueError()
        ids = set()
        for rule in snapshot:
            if not isinstance(rule, dict) or type(rule.get('id')) is not int or rule['id'] <= 0 or rule['id'] in ids:
                raise ValueError()
            ids.add(rule['id'])
            _string(rule.get('name'))
        # Check JSON output is representable; never repair/strip stored values.
        json.dumps(snapshot, ensure_ascii=False, allow_nan=False).encode('utf-8')
        digest = fingerprint(snapshot)
        with localcontext() as ctx:
            ctx.prec = 16
            if rate != rate.quantize(Decimal('0.0001')):
                raise ValueError()
            error_rate = format(rate.copy_abs() if rate == 0 else rate, '.4f')
            passed = format(Decimal(100) - rate, '.4f')
        if type(version['id']) is not int or version['id'] != row['dataset_version_id']:
            raise ValueError()
        if type(version['version_number']) is not int or version['version_number'] <= 0:
            raise ValueError()
        _string(version['original_filename'])
        return {'run_id': row['id'], 'version': dict(version), 'status': 'completed',
                'batch_rules_revision': row['batch_rules_revision'],
                'started_at': row['started_at'], 'finished_at': row['finished_at'],
                'engine_version': engine, 'rule_set_fingerprint': digest, **counts,
                'error_row_rate': error_rate, 'pass_rate': passed, 'rule_snapshot': snapshot}
    except (ValueError, TypeError, KeyError, UnicodeError, ArithmeticError, RecursionError, RunError):
        # This endpoint's contract maps corrupt snapshots and statistics alike.
        raise invalid_result() from None


def compare_runs(dataset_id, a_run_id, b_run_id):
    with catalog_connection() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        if connection.execute(select(Dataset.id).where(Dataset.id == dataset_id)).first() is None:
            raise CatalogNotFound()
        # Resolve both scoped memberships before inspecting completion/results.
        a = find_run(connection, dataset_id, a_run_id)
        b = a if a_run_id == b_run_id else find_run(connection, dataset_id, b_run_id)
        if a['status'] not in ('completed', 'running', 'failed') or b['status'] not in ('completed', 'running', 'failed'):
            raise invalid_result()
        if a['status'] != 'completed' or b['status'] != 'completed':
            raise RunError(409, 'RUN_NOT_COMPLETED', 'Chỉ có thể đối chiếu hai lần chạy đã hoàn tất.')
        versions = {v['id']: v for v in connection.execute(select(
            DatasetVersion.id, DatasetVersion.version_number, DatasetVersion.original_filename, DatasetVersion.batch_id)
            .where(DatasetVersion.dataset_id == dataset_id,
                   DatasetVersion.id.in_([a['dataset_version_id'], b['dataset_version_id']]))).mappings()}
        if a['dataset_version_id'] not in versions or b['dataset_version_id'] not in versions:
            raise invalid_result()
        a = _side(a, versions[a['dataset_version_id']])
        b = _side(b, versions[b['dataset_version_id']])
        reasons = []
        if a['version']['batch_id'] != b['version']['batch_id']:
            reasons.append('BATCH_DIFFERENT')
        if a['batch_rules_revision'] != b['batch_rules_revision']:
            reasons.append('RULE_REVISION_DIFFERENT')
        if a['engine_version'] != b['engine_version']:
            reasons.append('ENGINE_VERSION_DIFFERENT')
        if a['rule_set_fingerprint'] != b['rule_set_fingerprint']:
            reasons.append('RULE_SET_FINGERPRINT_DIFFERENT')
        delta = None
        if not reasons:
            delta = {key: b[key] - a[key] for key in ('total_rows', 'error_row_count', 'violation_count')}
            with localcontext() as ctx:
                ctx.prec = 16
                for key in ('error_row_rate', 'pass_rate'):
                    value = Decimal(b[key]) - Decimal(a[key])
                    delta[key] = format(value.copy_abs() if value == 0 else value, '.4f')
        return {'dataset_id': dataset_id, 'a': a, 'b': b, 'same_run': a_run_id == b_run_id,
                'comparable': not reasons, 'non_comparable_reasons': reasons, 'delta': delta}
