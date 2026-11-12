from contextlib import contextmanager
import unicodedata

from sqlalchemy import create_engine, func, select, or_, text
from sqlalchemy.pool import NullPool

from app.config import get_database_url
from app.models import DataBatch, Dataset, DatasetColumn, DatasetRow, DatasetVersion


class CatalogNotFound(Exception):
    pass


class InvalidSearchQuery(ValueError):
    pass


SEARCH_WHITESPACE = ('\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680'
                     '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a'
                     '\u2028\u2029\u202f\u205f\u3000')


def prepare_search_query(q: str | None) -> str | None:
    if q is None:
        return None
    if len(q) > 200 or '\x00' in q:
        raise InvalidSearchQuery()
    try:
        q.encode('utf-8')
    except UnicodeEncodeError:
        raise InvalidSearchQuery() from None
    return unicodedata.normalize('NFC', q.strip(SEARCH_WHITESPACE)) or None


@contextmanager
def catalog_connection():
    url = get_database_url()
    if not url or not url.startswith("postgresql+psycopg://"):
        raise ConnectionError("Database unavailable")
    engine = create_engine(url, poolclass=NullPool, hide_parameters=True,
                           isolation_level="REPEATABLE READ",
                           connect_args={"connect_timeout": 3, "options": "-c timezone=UTC -c statement_timeout=10000"})
    try:
        with engine.connect() as connection:
            yield connection
    finally:
        engine.dispose()


def list_datasets(page: int, page_size: int, q: str | None = None):
    q = prepare_search_query(q)
    predicates = []
    if q is not None:
        literal = q.replace('!', '!!').replace('%', '!%').replace('_', '!_')
        predicates.append(or_(*(func.normalize(column).ilike('%' + literal + '%', escape='!')
                               for column in (Dataset.name, Dataset.description, Dataset.source, Dataset.owner))))
    with catalog_connection() as connection:
        connection.execute(text('SET TRANSACTION READ ONLY'))
        total = connection.execute(select(func.count()).select_from(Dataset).where(*predicates)).scalar_one()
        versions = select(func.count()).select_from(DatasetVersion).where(
            DatasetVersion.dataset_id == Dataset.id).correlate(Dataset).scalar_subquery()
        batches = select(func.count()).select_from(DataBatch).where(
            DataBatch.dataset_id == Dataset.id).correlate(Dataset).scalar_subquery()
        query = select(Dataset.id, Dataset.name, Dataset.description, Dataset.source,
                       Dataset.owner, Dataset.created_at, versions.label("version_count"),
                       batches.label("batch_count")).where(*predicates)
        items = connection.execute(query.order_by(Dataset.created_at.desc(), Dataset.id.desc())
                                   .offset((page - 1) * page_size).limit(page_size)).mappings().all()
        return {"items": [dict(item) for item in items], "total": total, "page": page, "page_size": page_size}


def dataset_detail(dataset_id: int):
    with catalog_connection() as connection:
        dataset = connection.execute(select(Dataset).where(Dataset.id == dataset_id)).mappings().first()
        if dataset is None:
            raise CatalogNotFound()
        batch_count = connection.execute(select(func.count()).select_from(DataBatch).where(
            DataBatch.dataset_id == dataset_id)).scalar_one()
        columns = connection.execute(select(DatasetColumn.id, DatasetColumn.name, DatasetColumn.position,
                                            DatasetColumn.description).where(DatasetColumn.dataset_id == dataset_id)
                                     .order_by(DatasetColumn.position)).mappings().all()
        versions = connection.execute(select(DatasetVersion.id, DatasetVersion.dataset_id,
                                             DatasetVersion.batch_id, DatasetVersion.version_number,
                                             DatasetVersion.is_current,
                                             DatasetVersion.original_filename, DatasetVersion.file_size_bytes,
                                             DatasetVersion.row_count, DatasetVersion.imported_at,
                                             DatasetVersion.inferred_types)
                                      .where(DatasetVersion.dataset_id == dataset_id)
                                      .order_by(DatasetVersion.imported_at.desc(), DatasetVersion.id.desc())).mappings().all()
        return {**dict(dataset), "batch_count": batch_count, "columns": [dict(item) for item in columns],
                "versions": [dict(item) for item in versions]}


def version_rows(dataset_id: int, version_id: int, page: int, page_size: int):
    with catalog_connection() as connection:
        version = connection.execute(select(DatasetVersion.id).where(
            DatasetVersion.id == version_id, DatasetVersion.dataset_id == dataset_id)).first()
        if version is None:
            raise CatalogNotFound()
        header = connection.execute(select(DatasetColumn.name).where(DatasetColumn.dataset_id == dataset_id)
                                    .order_by(DatasetColumn.position)).scalars().all()
        total = connection.execute(select(func.count()).select_from(DatasetRow)
                                   .where(DatasetRow.version_id == version_id)).scalar_one()
        items = connection.execute(select(DatasetRow.row_number, DatasetRow.values)
                                   .where(DatasetRow.version_id == version_id).order_by(DatasetRow.row_number)
                                   .offset((page - 1) * page_size).limit(page_size)).mappings().all()
        return {"header": header, "items": [dict(item) for item in items],
                "total": total, "page": page, "page_size": page_size}
