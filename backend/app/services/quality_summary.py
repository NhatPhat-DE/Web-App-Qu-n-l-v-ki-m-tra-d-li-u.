"""Read-only aggregates of persisted violations, never quality evaluation."""
from sqlalchemy import select, text

from app.models import Dataset, DatasetVersion
from app.services.dataset_catalog import catalog_connection, CatalogNotFound
from app.services.quality_comparison import _side
from app.services.quality_execution import RunError
from app.services.quality_history import find_run


DIMENSIONS = (
    ('completeness', 'Completeness'),
    ('uniqueness', 'Uniqueness'),
    ('validity', 'Validity'),
    ('domain_conformance', 'Domain conformance'),
)

# A run's own JSONB snapshot is the driving relation: rules with zero errors
# remain present. Columns are ordered arrays, never exploded into individual
# columns; a composite unique rule therefore contributes to exactly one scope.
_RULES = """
WITH snapshot_rules AS (
    SELECT s.ordinality::integer AS rule_order,
           (s.value->>'id')::integer AS rule_id,
           s.value->>'rule_type' AS rule_type,
           s.value->'columns' AS columns
    FROM quality_runs AS q
    CROSS JOIN LATERAL jsonb_array_elements(q.rule_snapshot)
         WITH ORDINALITY AS s(value, ordinality)
    WHERE q.id = :run_id
), rules AS (
    SELECT *, CASE rule_type
        WHEN 'required' THEN 'completeness'
        WHEN 'unique' THEN 'uniqueness'
        WHEN 'data_type' THEN 'validity'
        WHEN 'date_format' THEN 'validity'
        WHEN 'pattern' THEN 'validity'
        WHEN 'numeric_range' THEN 'domain_conformance'
        WHEN 'allowed_values' THEN 'domain_conformance'
    END AS dimension
    FROM snapshot_rules
)
"""


def invalid_result():
    return RunError(500, 'INVALID_RUN_RESULT',
                    'Kết quả lần chạy không hợp lệ; không thể tổng hợp số liệu.')


def quality_summary(dataset_id, run_id, rule_page=1, column_page=1, page_size=20):
    with catalog_connection() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        if connection.execute(select(Dataset.id).where(Dataset.id == dataset_id)).first() is None:
            raise CatalogNotFound()
        run = find_run(connection, dataset_id, run_id)
        if run['status'] not in ('completed', 'running', 'failed'):
            raise invalid_result()
        if run['status'] != 'completed':
            raise RunError(409, 'RUN_NOT_COMPLETED',
                           'Chỉ có thể tổng hợp lần chạy đã hoàn tất.')
        version = connection.execute(select(
            DatasetVersion.id, DatasetVersion.version_number, DatasetVersion.original_filename
        ).where(DatasetVersion.id == run['dataset_version_id'],
                DatasetVersion.dataset_id == dataset_id)).mappings().first()
        try:
            side = _side(run, version)
        except RunError:
            raise invalid_result() from None

        params = {'run_id': run_id, 'total_rows': side['total_rows'],
                  'page_size': page_size, 'rule_offset': (rule_page - 1) * page_size,
                  'column_offset': (column_page - 1) * page_size}
        # Check membership and cardinalities without materializing raw values or
        # violations in Python. Counts must agree with the stored completed run.
        totals = connection.execute(text(_RULES + """
            SELECT count(*) AS violation_count,
                   count(DISTINCT v.row_number) AS violating_row_count,
                   coalesce(bool_or(r.rule_order IS NULL
                       OR v.rule_id_snapshot <> r.rule_id
                       OR v.rule_type <> r.rule_type OR v.columns <> r.columns
                       OR v.row_number > :total_rows
                       OR jsonb_array_length(v.values) <> jsonb_array_length(r.columns)), false) AS invalid
            FROM quality_violations AS v
            LEFT JOIN rules AS r ON r.rule_order = v.rule_order
            WHERE v.run_id = :run_id
        """), params).mappings().one()
        if (totals['invalid'] or totals['violation_count'] != side['violation_count']
                or totals['violating_row_count'] != side['error_row_count']):
            raise invalid_result()

        dimension_counts = {row['dimension']: row for row in connection.execute(text(_RULES + """
            SELECT r.dimension, count(DISTINCT r.rule_order) AS rule_count,
                   count(v.id) AS violation_count,
                   count(DISTINCT v.row_number) AS violating_row_count
            FROM rules AS r
            LEFT JOIN quality_violations AS v
              ON v.run_id = :run_id AND v.rule_order = r.rule_order
            GROUP BY r.dimension
        """), params).mappings()}
        dimensions = []
        for key, label in DIMENSIONS:
            counts = dimension_counts.get(key)
            dimensions.append({'dimension': key, 'label': label,
                'rule_count': counts['rule_count'] if counts else 0,
                'violation_count': counts['violation_count'] if counts else 0,
                'violating_row_count': counts['violating_row_count'] if counts else 0,
                'assessment_status': 'configured' if counts else 'not_assessed'})

        rule_counts = connection.execute(text(_RULES + """
            SELECT r.rule_order, r.dimension, count(v.id) AS violation_count,
                   count(DISTINCT v.row_number) AS violating_row_count
            FROM rules AS r
            LEFT JOIN quality_violations AS v
              ON v.run_id = :run_id AND v.rule_order = r.rule_order
            GROUP BY r.rule_order, r.dimension
            ORDER BY r.rule_order
            LIMIT :page_size OFFSET :rule_offset
        """), params).mappings().all()
        rules = []
        for counts in rule_counts:
            rule = side['rule_snapshot'][counts['rule_order'] - 1]
            rules.append({'rule_order': counts['rule_order'],
                'rule_id_snapshot': rule['id'], 'name': rule['name'],
                'rule_type': rule['rule_type'], 'columns': rule['columns'],
                'config': rule['config'], 'dimension': counts['dimension'],
                'violation_count': counts['violation_count'],
                'violating_row_count': counts['violating_row_count']})

        column_total = connection.execute(text(_RULES + """
            SELECT count(*) FROM (SELECT columns FROM rules GROUP BY columns) AS scopes
        """), params).scalar_one()
        scopes = connection.execute(text(_RULES + """
            , scopes AS (
                SELECT columns, min(rule_order) AS first_rule_order,
                       count(*) AS rule_count,
                       array_agg(rule_id ORDER BY rule_order) AS rule_ids
                FROM rules GROUP BY columns
            ), counts AS (
                SELECT r.columns, count(v.id) AS violation_count,
                       count(DISTINCT v.row_number) AS violating_row_count
                FROM rules AS r
                LEFT JOIN quality_violations AS v
                  ON v.run_id = :run_id AND v.rule_order = r.rule_order
                GROUP BY r.columns
            )
            SELECT s.columns, s.rule_count, s.rule_ids,
                   c.violation_count, c.violating_row_count
            FROM scopes AS s JOIN counts AS c ON c.columns = s.columns
            ORDER BY s.first_rule_order
            LIMIT :page_size OFFSET :column_offset
        """), params).mappings().all()
        columns = [{'scope_kind': 'column' if len(row['columns']) == 1 else 'column_group',
                    **dict(row)} for row in scopes]

        return {'summary_schema_version': '1',
            'context': {'dataset_id': dataset_id, 'version_id': side['version']['id'],
                'version_number': side['version']['version_number'],
                'original_filename': side['version']['original_filename'],
                'run_id': run_id, 'status': side['status'],
                'started_at': side['started_at'], 'finished_at': side['finished_at'],
                'engine_version': side['engine_version'],
                'rule_set_fingerprint': side['rule_set_fingerprint'],
                'rule_snapshot_source': 'saved_run'},
            'overall': {key: side[key] for key in ('total_rows', 'error_row_count',
                'violation_count', 'error_row_rate', 'pass_rate')},
            'dimensions': dimensions,
            'rules': {'items': rules, 'total': len(side['rule_snapshot']),
                      'page': rule_page, 'page_size': page_size},
            'column_scopes': {'items': columns, 'total': column_total,
                             'page': column_page, 'page_size': page_size},
            'breakdown_note': 'Chỉ đếm vi phạm và bản ghi có vi phạm. Chưa có mẫu số đủ điều kiện; không trả tỷ lệ chi tiết. Không cộng số bản ghi giữa các nhóm thành tổng bản ghi lỗi.'}
