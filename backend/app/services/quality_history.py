import json
from sqlalchemy import select, func
from datetime import datetime, timezone
from app.models import QualityRun, QualityViolation, DatasetVersion, Dataset, DataBatch
from app.services.dataset_catalog import catalog_connection, CatalogNotFound
from app.services.quality_rules import dataset_header
from app.services.quality_execution import RunError


def serialize(row):
    result = dict(row)
    result['run_id'] = result.pop('id')
    result['version_id'] = result.pop('dataset_version_id')
    if result['error_row_rate'] is not None:
        result['error_row_rate'] = format(result['error_row_rate'], '.4f')
    result['violated_rows_count'] = result.get('error_row_count')
    result['total_violations_count'] = result.get('violation_count')
    if 'failure_message' in result and result['status'] == 'failed':
        # Only expose allowlisted safe failures; protect against legacy/manual raw text.
        code = result['failure_code']
        result['failure_code'] = code if code in {'RUN_FAILED','DATABASE_UNAVAILABLE','PATTERN_TIMEOUT','PATTERN_RESOURCE_LIMIT','PATTERN_COMPILE_FAILED','PATTERN_WORKER_FAILED','PATTERN_CANCELLED'} else 'RUN_FAILED'
        result['failure_message'] = 'Không thể hoàn tất kiểm tra chất lượng.'
    return result


def find_run(connection, dataset_id, run_id):
    row = connection.execute(select(QualityRun, DatasetVersion.version_number, DatasetVersion.batch_id, DatasetVersion.is_current)
                             .join(DatasetVersion, QualityRun.dataset_version_id == DatasetVersion.id)
                             .where(QualityRun.id == run_id, DatasetVersion.dataset_id == dataset_id)).mappings().first()
    if row is None:
        raise CatalogNotFound()
    return row


def list_runs(dataset_id, version_id, page, page_size, batch_id=None):
    with catalog_connection() as connection:
        dataset_header(connection, dataset_id)
        if version_id is not None and connection.execute(select(DatasetVersion.id).where(
            DatasetVersion.id == version_id, DatasetVersion.dataset_id == dataset_id)).first() is None:
            raise CatalogNotFound()
        predicate = [DatasetVersion.dataset_id == dataset_id]
        if version_id is not None:
            predicate.append(QualityRun.dataset_version_id == version_id)
        if batch_id is not None:
            predicate.append(DatasetVersion.batch_id == batch_id)
        total = connection.execute(select(func.count()).select_from(QualityRun).join(DatasetVersion)
                                   .where(*predicate)).scalar_one()
        fields = [QualityRun.id, QualityRun.dataset_version_id, DatasetVersion.version_number, DatasetVersion.batch_id, QualityRun.status,
                  QualityRun.batch_rules_revision,
                  QualityRun.started_at, QualityRun.finished_at, QualityRun.total_rows, QualityRun.error_row_count,
                  QualityRun.violation_count, QualityRun.error_row_rate]
        rows = connection.execute(select(*fields).join(DatasetVersion).where(*predicate)
                                  .order_by(QualityRun.started_at.desc(), QualityRun.id.desc())
                                  .limit(page_size).offset((page-1)*page_size)).mappings().all()
        return {'items':[serialize(row) for row in rows], 'total':total, 'page':page, 'page_size':page_size}


def run_detail(dataset_id, run_id):
    with catalog_connection() as connection:
        result = serialize(find_run(connection, dataset_id, run_id))
        revision = connection.execute(select(DataBatch.rules_revision).where(DataBatch.id == result['batch_id'])).scalar_one()
        result['current_rules_revision'] = revision
        from app.services.quality_engine import ENGINE_VERSION
        result['rules_changed'] = result['batch_rules_revision'] != revision or result['engine_version'] != ENGINE_VERSION
        result['supplier']=(result.get('export_context_snapshot') or {}).get('supplier')
        return {'dataset_id':dataset_id, **result}


def list_violations(dataset_id, run_id, rule_id, row_number, page, page_size):
    with catalog_connection() as connection:
        run = find_run(connection, dataset_id, run_id)
        if run['status'] != 'completed':
            raise RunError(409, 'RUN_NOT_COMPLETED', 'Lần chạy chưa hoàn tất, chưa thể xem danh sách lỗi.')
        names = {rule['id']:rule['name'] for rule in run['rule_snapshot']}
        predicate = [QualityViolation.run_id == run_id]
        if rule_id is not None:
            predicate.append(QualityViolation.rule_id_snapshot == rule_id)
        if row_number is not None:
            predicate.append(QualityViolation.row_number == row_number)
        total = connection.execute(select(func.count()).select_from(QualityViolation).where(*predicate)).scalar_one()
        rows = connection.execute(select(QualityViolation).where(*predicate)
                                  .order_by(QualityViolation.row_number, QualityViolation.rule_order, QualityViolation.id)
                                  .limit(page_size).offset((page-1)*page_size)).mappings().all()
        items = []
        for row in rows:
            item = {**dict(row), 'rule_name': names[row['rule_id_snapshot']]}
            if row['rule_type'] == 'unique':
                item['related_rows'] = connection.execute(select(QualityViolation.row_number).where(
                    QualityViolation.run_id == run_id, QualityViolation.rule_id_snapshot == row['rule_id_snapshot'],
                    QualityViolation.values == row['values']).order_by(QualityViolation.row_number)).scalars().all()
            items.append(item)
        return {'items':items,
                'total':total, 'page':page, 'page_size':page_size}


def export_report(dataset_id, run_id, *, limits=None):
    # catalog_connection uses one REPEATABLE READ transaction for all queries.
    with catalog_connection() as connection:
        run = find_run(connection, dataset_id, run_id)
        if run['status'] != 'completed':
            raise RunError(409, 'RUN_NOT_COMPLETED', 'Chỉ có thể xuất báo cáo khi lần chạy đã hoàn tất.')
        dataset = connection.execute(select(Dataset.id, Dataset.name, Dataset.description,
            Dataset.source, Dataset.owner).where(Dataset.id == dataset_id)).mappings().one()
        version = connection.execute(select(DatasetVersion.id, DatasetVersion.version_number, DatasetVersion.batch_id,
            DatasetVersion.original_filename, DatasetVersion.row_count, DatasetVersion.imported_at)
            .where(DatasetVersion.id == run['dataset_version_id'])).mappings().one()
        names = {rule['id']: rule['name'] for rule in run['rule_snapshot']}
        if limits:
            count = connection.execute(select(func.count()).select_from(QualityViolation)
                .where(QualityViolation.run_id == run_id)).scalar_one()
            if len(run['rule_snapshot']) > limits['rules'] or count > limits['violations']:
                raise RunError(413, 'XLSX_EXPORT_LIMIT', 'Báo cáo vượt giới hạn xuất Excel; hãy dùng báo cáo JSON để nhận đầy đủ dữ liệu.')
        violations_query = select(QualityViolation).where(QualityViolation.run_id == run_id).order_by(QualityViolation.row_number, QualityViolation.rule_order, QualityViolation.id)
        if limits:
            violations_query = violations_query.execution_options(stream_results=True, yield_per=500)
        violations = connection.execute(violations_query).mappings()
        run_fields = ['id', 'status', 'started_at', 'finished_at', 'engine_version',
                      'total_rows', 'error_row_count', 'violation_count']
        report = {
            'report_schema_version': '1', 'exported_at': datetime.now(timezone.utc),
            'dataset_metadata_source': 'current_at_export',
            'dataset_metadata_note': 'Metadata bộ dữ liệu hiện tại khi xuất, không phải snapshot tại thời điểm chạy.',
            'dataset': dict(dataset), 'version': dict(version),
            'supplier':(run['export_context_snapshot'] or {}).get('supplier'),
            'supplier_metadata_source':'run_snapshot' if (run['export_context_snapshot'] or {}).get('supplier') else 'not_recorded',
            'run': {**{key: run[key] for key in run_fields}, 'error_row_rate': format(run['error_row_rate'], '.4f')},
            'rule_snapshot': run['rule_snapshot'],
            'batch_rules_revision': run['batch_rules_revision'], 'schema_snapshot': run['schema_snapshot'],
            'violations': [],
        }

        # Bound the Excel path while leaving the existing JSON export unrestricted.
        used = len(json.dumps(report, ensure_ascii=False, default=str, separators=(',', ':')).encode('utf-8')) if limits else 0
        if limits and used > limits['bytes']:
            raise RunError(413, 'XLSX_EXPORT_LIMIT', 'Báo cáo vượt giới hạn xuất Excel; hãy dùng báo cáo JSON để nhận đầy đủ dữ liệu.')
        for row in violations:
            item = {**dict(row), 'rule_name': names[row['rule_id_snapshot']]}
            if limits:
                used += len(json.dumps(item, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) + 1
                if used > limits['bytes']:
                    raise RunError(413, 'XLSX_EXPORT_LIMIT', 'Báo cáo vượt giới hạn xuất Excel; hãy dùng báo cáo JSON để nhận đầy đủ dữ liệu.')
            report['violations'].append(item)
        return report
