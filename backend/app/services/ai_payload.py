"""Internal AI data preparation. No network, persistence or logging."""
import json
from sqlalchemy import select
from app.models import DatasetColumn, DatasetRow, DatasetVersion
from app.services.dataset_catalog import catalog_connection, CatalogNotFound
from app.services.quality_engine import is_missing

MAX_COLUMNS = 30
MAX_NAME = 256
MAX_DESCRIPTION = 500
MAX_PAYLOAD_BYTES = 32 * 1024
TYPES = {'integer', 'decimal', 'boolean', 'date', 'text', 'unknown'}


class AIPayloadError(ValueError):
    def __init__(self, code='INVALID_AI_PAYLOAD'):
        self.code = code
        super().__init__('Invalid AI payload input or internal data.')


def bounded_text(value, limit, allow_empty=False):
    if not isinstance(value, str) or len(value) > limit or '\x00' in value or (not allow_empty and not value.strip()):
        raise AIPayloadError()
    try:
        value.encode('utf-8', errors='strict')
    except UnicodeError:
        raise AIPayloadError() from None
    return value


def selected_columns(columns):
    if not isinstance(columns, list) or not 1 <= len(columns) <= MAX_COLUMNS:
        raise AIPayloadError()
    for name in columns:
        bounded_text(name, MAX_NAME)
    if len(set(columns)) != len(columns):
        raise AIPayloadError()
    return columns


def serialize_payload(payload):
    """Canonical wire representation; future caller must send these exact bytes."""
    try:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, UnicodeError):
        raise AIPayloadError() from None
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise AIPayloadError('AI_PAYLOAD_TOO_LARGE')
    return raw


def build_payload(dataset_id, version_id, columns, include_descriptions=True, include_statistics=True):
    selected_columns(columns)
    if type(include_descriptions) is not bool or type(include_statistics) is not bool:
        raise AIPayloadError()
    if type(dataset_id) is not int or dataset_id <= 0 or type(version_id) is not int or version_id <= 0:
        raise AIPayloadError()
    request = dict(dataset_id=dataset_id, version_id=version_id, columns=columns,
                   include_descriptions=include_descriptions, include_statistics=include_statistics)
    if len(serialize_payload(request)) > 8 * 1024:
        raise AIPayloadError('AI_INPUT_TOO_LARGE')
    # REPEATABLE READ gives metadata and rows the same snapshot. No commits/writes.
    with catalog_connection() as connection:
        version = connection.execute(select(DatasetVersion.inferred_types, DatasetVersion.row_count).where(
            DatasetVersion.id == version_id, DatasetVersion.dataset_id == dataset_id)).mappings().first()
        if version is None:
            raise CatalogNotFound()
        header = connection.execute(select(DatasetColumn.name, DatasetColumn.position, DatasetColumn.description)
            .where(DatasetColumn.dataset_id == dataset_id).order_by(DatasetColumn.position)).mappings().all()
        by_name = {item['name']: item for item in header}
        if any(name not in by_name for name in columns):
            raise AIPayloadError()
        inferred = {}
        for item in version['inferred_types']:
            if not isinstance(item, dict) or not isinstance(item.get('column_name'), str):
                raise AIPayloadError()
            name, kind = item['column_name'], item.get('inferred_type')
            if name in inferred or not isinstance(kind, str) or kind not in TYPES:
                raise AIPayloadError()
            inferred[name] = kind
        output = []
        for name in columns:
            entry = {'name': name, 'inferred_type': inferred.get(name, 'unknown')}
            description = by_name[name]['description']
            if include_descriptions and description is not None:
                entry['description'] = bounded_text(description, MAX_DESCRIPTION, allow_empty=True)
            output.append(entry)
        payload = {'schema_version': 1, 'columns': output}
        if include_statistics:
            missing = [0] * len(columns)
            indexes = [item['name'] for item in header]
            indexes = [indexes.index(name) for name in columns]
            count = 0
            rows = connection.execute(select(DatasetRow.values).where(DatasetRow.version_id == version_id)
                                      .execution_options(stream_results=True, yield_per=500))
            try:
                for (values,) in rows:
                    if not isinstance(values, list) or len(values) != len(header):
                        raise AIPayloadError()
                    count += 1
                    for index, position in enumerate(indexes):
                        missing[index] += int(is_missing(values[position]))
            finally:
                rows.close()
            if count != version['row_count']:
                raise AIPayloadError('AI_STATISTICS_INCONSISTENT')
            payload['row_count'] = count
            for entry, count_missing in zip(output, missing):
                entry['missing_count'] = count_missing
        serialize_payload(payload)
        return payload
