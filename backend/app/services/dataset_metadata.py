from datetime import datetime, timezone
from sqlalchemy import select, update, insert
from app.models import Dataset, DatasetColumn, DataBatch
from app.services.quality_rules import rule_connection
from app.services.dataset_catalog import CatalogNotFound


def create_dataset(metadata: dict) -> dict:
    with rule_connection() as connection:
        return dict(connection.execute(
            insert(Dataset).values(**metadata).returning(*Dataset.__table__.columns)
        ).mappings().one())


def patch_dataset(dataset_id, changes):
    with rule_connection() as connection:
        if connection.execute(select(Dataset.id).where(Dataset.id == dataset_id).with_for_update()).first() is None:
            raise CatalogNotFound()
        return dict(connection.execute(update(Dataset).where(Dataset.id == dataset_id)
            .values(**changes, updated_at=datetime.now(timezone.utc))
            .returning(*Dataset.__table__.columns)).mappings().one())


def patch_column(dataset_id, column_id, changes):
    with rule_connection() as connection:
        if connection.execute(select(Dataset.id).where(Dataset.id == dataset_id).with_for_update()).first() is None:
            raise CatalogNotFound()
        if connection.execute(select(DataBatch.id).where(DataBatch.dataset_id==dataset_id,DataBatch.business_state=='COMPLETED')).first():
            from app.services.issue_workflow import reject
            reject(409,'BATCH_COMPLETED','Cần mở lại đợt hoàn tất trước khi đổi mô tả cấu trúc được dùng trong kiểm tra.')
        column = connection.execute(select(DatasetColumn.id).where(DatasetColumn.id == column_id,
                                     DatasetColumn.dataset_id == dataset_id)).first()
        if column is None:
            raise CatalogNotFound()
        result = connection.execute(update(DatasetColumn).where(DatasetColumn.id == column_id)
                                    .values(**changes).returning(*DatasetColumn.__table__.columns)).mappings().one()
        connection.execute(update(Dataset).where(Dataset.id == dataset_id).values(updated_at=datetime.now(timezone.utc)))
        return dict(result)
