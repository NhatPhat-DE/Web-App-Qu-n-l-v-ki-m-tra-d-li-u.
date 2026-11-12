from contextlib import contextmanager
from sqlalchemy import create_engine, select, insert, update, func
from sqlalchemy.pool import NullPool
from app.config import get_database_url
from app.models import Dataset, DataBatch, DatasetColumn, QualityRule
from app.services.dataset_catalog import CatalogNotFound
from app.services.quality_engine import QualityInputError, validate_rules


@contextmanager
def rule_connection():
    url = get_database_url()
    if not url or not url.startswith("postgresql+psycopg://"):
        raise ConnectionError("Database unavailable")
    engine = create_engine(url, poolclass=NullPool, hide_parameters=True,
                           connect_args={"connect_timeout": 3, "options": "-c timezone=UTC -c statement_timeout=10000"})
    try:
        with engine.begin() as connection:
            yield connection
    finally:
        engine.dispose()


def dataset_header(connection, dataset_id):
    if connection.execute(select(Dataset.id).where(Dataset.id == dataset_id)).first() is None:
        raise CatalogNotFound()
    return connection.execute(select(DatasetColumn.name).where(DatasetColumn.dataset_id == dataset_id)
                              .order_by(DatasetColumn.position)).scalars().all()


def validate(header, data, *, compile_pattern=True):
    if not isinstance(data["name"], str) or not data["name"].strip() or "\x00" in data["name"]:
        raise QualityInputError("INVALID_NAME", "Tên quy tắc không được rỗng hoặc chỉ có khoảng trắng.")
    validate_rules(header, [{"rule_id": 1, "rule_type": data["rule_type"], "columns": data["columns"], "config": data["config"]}])
    if compile_pattern and data['rule_type'] == 'pattern':
        import re2
        from app.services.pattern_worker import MAX_MEM
        options = re2.Options()
        options.max_mem = MAX_MEM
        options.log_errors = False
        options.case_sensitive = True
        try:
            re2.compile(data['config']['pattern'], options=options)
        except re2.error:
            raise QualityInputError('INVALID_CONFIG', 'Mẫu không biên dịch được bằng RE2 trong budget 8 MiB.') from None
        finally:
            re2.purge()
    if data["rule_type"] == "numeric_range" and any(not isinstance(data["config"][key], str) for key in ("min", "max")):
        raise QualityInputError("INVALID_RANGE_TYPE", "min và max phải là chuỗi số thập phân hữu hạn.")


def scope_batch(connection, dataset_id, batch_id, *, lock=False):
    if batch_id is None:
        # Serialize template copy with template edits and creation of batches.
        if lock:
            if connection.execute(select(Dataset.id).where(Dataset.id == dataset_id).with_for_update()).first() is None:
                raise CatalogNotFound()
        return None
    query = select(DataBatch).where(DataBatch.id == batch_id, DataBatch.dataset_id == dataset_id)
    if lock: query = query.with_for_update()
    row = connection.execute(query).mappings().first()
    if row is None: raise CatalogNotFound()
    if lock:
        from app.services.issue_workflow import assert_batch_open
        assert_batch_open(connection,batch_id)
    return row


def bump_revision(connection, batch_id):
    if batch_id is not None:
        connection.execute(update(DataBatch).where(DataBatch.id == batch_id).values(
            rules_revision=DataBatch.rules_revision + 1, updated_at=func.now()))


def create_rule(dataset_id, data, batch_id=None):
    with rule_connection() as connection:
        scope_batch(connection, dataset_id, batch_id, lock=True)
        header = dataset_header(connection, dataset_id)
        validate(header, data)
        result = dict(connection.execute(insert(QualityRule).values(dataset_id=dataset_id, batch_id=batch_id, **data)
                                       .returning(*QualityRule.__table__.columns)).mappings().one())
        bump_revision(connection, batch_id)
        return result


def list_rules(dataset_id, page, page_size, batch_id=None):
    with rule_connection() as connection:
        batch = scope_batch(connection, dataset_id, batch_id)
        dataset_header(connection, dataset_id)
        predicate = (QualityRule.dataset_id == dataset_id, QualityRule.batch_id == batch_id)
        total = connection.execute(select(func.count()).select_from(QualityRule).where(*predicate)).scalar_one()
        rows = connection.execute(select(QualityRule).where(*predicate)
                                  .order_by(QualityRule.id).limit(page_size).offset((page-1)*page_size)).mappings().all()
        return {"items": [dict(row) for row in rows], "total": total, "page": page, "page_size": page_size,
                'batch_id': batch_id, 'rules_revision': batch['rules_revision'] if batch else None, 'scope': 'batch' if batch else 'template'}


def patch_rule(dataset_id, rule_id, changes, batch_id=None):
    with rule_connection() as connection:
        scope_batch(connection, dataset_id, batch_id, lock=True)
        header = dataset_header(connection, dataset_id)
        old = connection.execute(select(QualityRule).where(QualityRule.id == rule_id, QualityRule.dataset_id == dataset_id, QualityRule.batch_id == batch_id).with_for_update()).mappings().first()
        if old is None:
            raise CatalogNotFound()
        merged = {key: old[key] for key in ("name", "rule_type", "columns", "config", "is_active")}
        merged.update(changes)
        validate(header, merged)
        if any(merged[key] != old[key] for key in merged):
            bump_revision(connection, batch_id)
        return dict(connection.execute(update(QualityRule).where(QualityRule.id == rule_id)
                                       .values(**merged).returning(*QualityRule.__table__.columns)).mappings().one())
