from datetime import datetime, timezone
from sqlalchemy import create_engine, insert, select, func, update
from sqlalchemy.pool import NullPool

from app.config import get_database_url
from app.models import Dataset, DataBatch, DatasetColumn, DatasetRow, DatasetVersion
from app.services.csv_reader import ParsedCSV
from app.services.quality_rules import rule_connection
from app.services.dataset_catalog import CatalogNotFound
from app.services.csv_reader import CSVValidationError
from app.services.type_inference import infer_types


def import_version(dataset_id: int, parsed: ParsedCSV, filename: str, batch_id: int | None = None) -> dict:
    inferred = infer_types(parsed.header, parsed.rows)
    with rule_connection() as connection:
        if connection.execute(select(Dataset.id).where(Dataset.id == dataset_id).with_for_update()).first() is None:
            raise CatalogNotFound()

        target_batch_id = batch_id
        if target_batch_id is None:
            # Find the latest batch for this dataset
            latest_batch = connection.execute(
                select(DataBatch.id).where(DataBatch.dataset_id == dataset_id)
                .order_by(DataBatch.created_at.desc(), DataBatch.id.desc()).with_for_update()
            ).first()
            if latest_batch is None:
                # Auto-create initial legacy/default batch
                target_batch_id = connection.execute(
                    insert(DataBatch).values(
                        dataset_id=dataset_id,
                        name="Đợt 1",
                        description="Đợt dữ liệu mặc định",
                        period_label="Khởi tạo",
                    ).returning(DataBatch.id)
                ).scalar_one()
            else:
                target_batch_id = latest_batch[0]
        else:
            # Verify batch exists and belongs to this dataset, with lock
            batch_row = connection.execute(
                select(DataBatch.id, DataBatch.dataset_id)
                .where(DataBatch.id == target_batch_id)
                .with_for_update()
            ).first()
            if batch_row is None or batch_row.dataset_id != dataset_id:
                raise CatalogNotFound()

        from app.services.issue_workflow import assert_batch_open
        assert_batch_open(connection,target_batch_id)

        # Schema verification
        existing_columns = connection.execute(
            select(DatasetColumn.name).where(DatasetColumn.dataset_id == dataset_id).order_by(DatasetColumn.position)
        ).scalars().all()

        if not existing_columns:
            connection.execute(insert(DatasetColumn), [
                {"dataset_id": dataset_id, "name": name, "position": position}
                for position, name in enumerate(parsed.header, 1)
            ])
            header = parsed.header
        else:
            if parsed.header != existing_columns:
                raise CSVValidationError('CSV_SCHEMA_MISMATCH', 'Tên và thứ tự cột phải khớp bộ dữ liệu. Hãy tạo bộ dữ liệu khác nếu cấu trúc thay đổi.')
            header = existing_columns

        # Number starts from 1 per batch
        number = (connection.execute(
            select(func.max(DatasetVersion.version_number)).where(DatasetVersion.batch_id == target_batch_id)
        ).scalar_one() or 0) + 1

        connection.execute(update(DatasetVersion).where(DatasetVersion.batch_id == target_batch_id,
            DatasetVersion.is_current.is_(True)).values(is_current=False))
        version_id = connection.execute(
            insert(DatasetVersion).values(
                dataset_id=dataset_id,
                batch_id=target_batch_id,
                version_number=number,
                is_current=True,
                original_filename=filename,
                file_size_bytes=parsed.file_size_bytes,
                row_count=parsed.row_count,
                inferred_types=inferred,
            ).returning(DatasetVersion.id)
        ).scalar_one()

        for start in range(0, parsed.row_count, 1000):
            connection.execute(insert(DatasetRow), [
                {'version_id': version_id, 'row_number': index + 1, 'values': parsed.rows[index]}
                for index in range(start, min(start + 1000, parsed.row_count))
            ])

        connection.execute(update(DataBatch).where(DataBatch.id == target_batch_id).values(updated_at=func.now()))
        connection.execute(update(Dataset).where(Dataset.id == dataset_id).values(updated_at=func.now()))

        return {
            'dataset_id': dataset_id,
            'batch_id': target_batch_id,
            'version_id': version_id,
            'version_number': number,
            'column_count': len(header),
            'row_count': parsed.row_count,
        }


def import_dataset(parsed: ParsedCSV, filename: str, metadata: dict) -> dict:
    inferred = infer_types(parsed.header, parsed.rows)
    url = get_database_url()
    if not url or not url.startswith("postgresql+psycopg://"):
        raise ConnectionError("Database configuration unavailable")
    engine = create_engine(url, hide_parameters=True, poolclass=NullPool,
                           connect_args={"connect_timeout": 3, "options": "-c timezone=UTC -c statement_timeout=10000"})
    try:
        with engine.begin() as connection:
            dataset_id = connection.execute(insert(Dataset).values(**metadata).returning(Dataset.id)).scalar_one()
            batch_id = connection.execute(insert(DataBatch).values(
                dataset_id=dataset_id,
                name="Đợt 1",
                description="Đợt tải dữ liệu đầu tiên",
                period_label=None,
            ).returning(DataBatch.id)).scalar_one()
            connection.execute(insert(DatasetColumn), [
                {"dataset_id": dataset_id, "name": name, "position": position}
                for position, name in enumerate(parsed.header, 1)
            ])
            version_id = connection.execute(insert(DatasetVersion).values(
                dataset_id=dataset_id,
                batch_id=batch_id,
                version_number=1,
                is_current=True,
                original_filename=filename,
                file_size_bytes=parsed.file_size_bytes,
                row_count=parsed.row_count,
                inferred_types=inferred,
            ).returning(DatasetVersion.id)).scalar_one()
            for start in range(0, parsed.row_count, 1000):
                connection.execute(insert(DatasetRow), [
                    {"version_id": version_id, "row_number": index + 1, "values": parsed.rows[index]}
                    for index in range(start, min(start + 1000, parsed.row_count))
                ])
        return {
            "dataset_id": dataset_id,
            "batch_id": batch_id,
            "version_id": version_id,
            "version_number": 1,
            "name": metadata["name"],
            "column_count": len(parsed.header),
            "row_count": parsed.row_count,
        }
    finally:
        engine.dispose()
