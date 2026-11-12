from fastapi import HTTPException
from datetime import datetime, timezone
from app.services.pattern_worker import preflight, admission, PatternError

from sqlalchemy import select, insert, update
from sqlalchemy.exc import DBAPIError
from app.models import DataBatch, DatasetVersion, DatasetColumn, DatasetRow, QualityRule, QualityRun
from app.services.dataset_catalog import catalog_connection, CatalogNotFound
from app.services.quality_rules import rule_connection, dataset_header
from app.services.quality_engine import check_quality, validate_rules, ENGINE_VERSION, QualityInputError
from app.services.quality_results import complete_run


class RunError(Exception):
    def __init__(self, status, code, message, run_id=None, failure_recorded=None):
        self.status, self.code, self.message = status, code, message
        self.run_id, self.failure_recorded = run_id, failure_recorded


def unavailable(error):
    if isinstance(error, ConnectionError):
        return True
    if isinstance(error, DBAPIError):
        state = getattr(error.orig, 'sqlstate', None)
        return error.connection_invalidated or state is None or state.startswith('08') or state in {'57P01','57P02','57P03'}
    return False


def read_inputs(dataset_id, version_id):
    # The connection's REPEATABLE READ transaction ends before any computation.
    with catalog_connection() as connection:
        header = dataset_header(connection, dataset_id)
        version = connection.execute(select(DatasetVersion).where(DatasetVersion.id == version_id,
                                      DatasetVersion.dataset_id == dataset_id)).mappings().first()
        if version is None:
            raise CatalogNotFound()
        revision = connection.execute(select(DataBatch.rules_revision).where(DataBatch.id == version['batch_id'])).scalar_one()
        schema = [dict(item) for item in connection.execute(select(DatasetColumn.name, DatasetColumn.position,
            DatasetColumn.description).where(DatasetColumn.dataset_id == dataset_id).order_by(DatasetColumn.position)).mappings()]
        positions = connection.execute(select(DatasetColumn.position).where(DatasetColumn.dataset_id == dataset_id)
                                       .order_by(DatasetColumn.position)).scalars().all()
        records = connection.execute(select(DatasetRow.row_number, DatasetRow.values).where(DatasetRow.version_id == version_id)
                                     .order_by(DatasetRow.row_number)).all()
        rules = connection.execute(select(QualityRule.id, QualityRule.name, QualityRule.rule_type,
                                           QualityRule.columns, QualityRule.config)
                                   .where(QualityRule.dataset_id == dataset_id, QualityRule.batch_id == version['batch_id'], QualityRule.is_active.is_(True))
                                   .order_by(QualityRule.id)).mappings().all()
        if not rules:
            raise RunError(422, 'NO_ACTIVE_RULES', 'Cần ít nhất một quy tắc đang bật để chạy kiểm tra.')
        if (not header or positions != list(range(1, len(header) + 1)) or version['row_count'] <= 0
                or len(records) != version['row_count']
                or [record.row_number for record in records] != list(range(1, version['row_count'] + 1))
                or any(not isinstance(record.values, list) or len(record.values) != len(header)
                       or any(not isinstance(value, str) for value in record.values) for record in records)):
            raise RunError(500, 'DATA_INCONSISTENT', 'Dữ liệu đã lưu không nhất quán, không thể chạy kiểm tra.')
        snapshot = [dict(rule) for rule in rules]
        engine_rules = [{'rule_id': rule['id'], 'rule_type': rule['rule_type'], 'columns': rule['columns'], 'config': rule['config']} for rule in snapshot]
        validate_rules(header, engine_rules)
        return header, [record.values for record in records], snapshot, engine_rules, revision, schema


def mark_failed(run_id, code):
    with rule_connection() as connection:
        result = connection.execute(update(QualityRun).where(QualityRun.id == run_id, QualityRun.status == 'running')
                                    .values(status='failed', finished_at=datetime.now(timezone.utc),
                                            failure_code=code, failure_message='Không thể hoàn tất kiểm tra chất lượng.'))
        return result.rowcount == 1


def execute_run(dataset_id, version_id):
    run_id = None
    try:
        header, rows, snapshot, engine_rules, revision, schema = read_inputs(dataset_id, version_id)
        patterns = preflight(header, rows, engine_rules)
        with admission(bool(patterns)):
            return _execute_admitted(dataset_id, version_id, header, rows, snapshot, engine_rules, bool(patterns), revision, schema)
    except PatternError as error:
        raise RunError(error.status, error.code, error.message) from None
    except QualityInputError as error:
        raise RunError(422, error.code, 'Cấu hình quy tắc đợt không hợp lệ: ' + str(error)) from None
    except CatalogNotFound:
        raise RunError(404, 'NOT_FOUND', 'Không tìm thấy bộ dữ liệu hoặc phiên bản phù hợp.') from None
    except HTTPException as error:
        raise RunError(error.status_code,error.detail['code'],error.detail['message']) from None
    except RunError:
        raise
    except Exception as error:
        offline = unavailable(error)
        raise RunError(503 if offline else 500, 'DATABASE_UNAVAILABLE' if offline else 'RUN_FAILED',
                       'Không thể kết nối cơ sở dữ liệu.' if offline else 'Không thể hoàn tất kiểm tra chất lượng.') from None


def _execute_admitted(dataset_id, version_id, header, rows, snapshot, engine_rules, pattern_admitted, revision, schema):
    run_id = None
    try:
        with rule_connection() as connection:
            from app.services.issue_workflow import lock_batch, reject
            version=connection.execute(select(DatasetVersion).where(DatasetVersion.id==version_id,DatasetVersion.dataset_id==dataset_id)).mappings().one()
            batch=lock_batch(connection,dataset_id,version['batch_id'])
            if batch['rules_revision']!=revision:reject(409,'RULES_CHANGED_DURING_RUN_START','Quy tắc vừa thay đổi. Tải lại trước khi chạy kiểm tra.')
            from app.services.error_export import snapshot_at_start
            export_context=snapshot_at_start(connection,version,batch)
            run_id = connection.execute(insert(QualityRun).values(dataset_version_id=version_id,
                                        rule_snapshot=snapshot, engine_version=ENGINE_VERSION,
                                        batch_rules_revision=revision, schema_snapshot=schema, export_context_snapshot=export_context)
                                        .returning(QualityRun.id)).scalar_one()
        result = check_quality(header, rows, engine_rules, pattern_admitted=True) if pattern_admitted else check_quality(header, rows, engine_rules)
        saved = complete_run(run_id, result)
        return {'run_id': run_id, 'dataset_id': dataset_id, 'version_id': version_id,
                'status': saved['status'], 'total_rows': saved['total_rows'],
                'error_row_count': saved['error_row_count'], 'violation_count': saved['violation_count'],
                'error_row_rate': format(saved['error_row_rate'], '.4f'),
                'started_at': saved['started_at'], 'finished_at': saved['finished_at'],
                'duration_seconds': (saved['finished_at'] - saved['started_at']).total_seconds()}
    except CatalogNotFound:
        raise RunError(404, 'NOT_FOUND', 'Không tìm thấy bộ dữ liệu hoặc phiên bản phù hợp.') from None
    except HTTPException as error:
        raise RunError(error.status_code,error.detail['code'],error.detail['message']) from None
    except RunError:
        raise
    except Exception as error:
        offline = unavailable(error)
        code = error.code if isinstance(error, PatternError) else 'DATABASE_UNAVAILABLE' if offline else 'RUN_FAILED'
        recorded = None
        if run_id is not None:
            try:
                recorded = mark_failed(run_id, code)
            except Exception:
                recorded = False
        message = error.message if isinstance(error, PatternError) else 'Không thể kết nối cơ sở dữ liệu.' if offline else 'Không thể hoàn tất kiểm tra chất lượng.'
        if recorded is False:
            message += ' Không xác nhận được trạng thái kết thúc của lần chạy; run có thể vẫn đang running.'
        raise RunError(error.status if isinstance(error, PatternError) else 503 if offline else 500, code, message, run_id, recorded) from None
