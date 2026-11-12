from datetime import datetime, timezone
from sqlalchemy import select, func, or_, text, update, insert
from app.models import Dataset, DataBatch, DatasetVersion, DatasetColumn, QualityRun, QualityRule
from app.services.dataset_catalog import (
    catalog_connection,
    CatalogNotFound,
    prepare_search_query,
)
from app.services.quality_rules import rule_connection


def serialize_dt(obj):
    if isinstance(obj, dict):
        return {k: serialize_dt(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_dt(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def validate_batch_name(name: str | None) -> str:
    if name is None or not name.strip():
        raise ValueError("Tên đợt dữ liệu không được để trống hoặc chỉ chứa khoảng trắng.")
    name = name.strip()
    if len(name) > 200:
        raise ValueError("Tên đợt dữ liệu tối đa 200 ký tự.")
    if "\x00" in name:
        raise ValueError("Tên đợt dữ liệu không được chứa ký tự NUL.")
    return name


def validate_batch_metadata(data: dict) -> dict:
    cleaned = {}
    if "name" in data:
        cleaned["name"] = validate_batch_name(data["name"])

    for field, max_len in [("description", 2000), ("period_label", 100)]:
        if field in data:
            val = data[field]
            if val is not None:
                if not isinstance(val, str):
                    raise ValueError(f"Trường {field} phải là chuỗi ký tự.")
                val = val.strip() or None
                if val is not None:
                    if len(val) > max_len:
                        raise ValueError(f"Trường {field} tối đa {max_len} ký tự.")
                    if "\x00" in val:
                        raise ValueError(f"Trường {field} không được chứa ký tự NUL.")
            cleaned[field] = val
    return cleaned


def create_batch(dataset_id: int, data: dict, actor=None) -> dict:
    if data.get('store_id') is None:
        from app.services.suppliers import fail
        fail('STORE_REQUIRED','Chọn cửa hàng cung cấp cho đợt mới.')
    cleaned = validate_batch_metadata(data)
    if "name" not in cleaned:
        raise ValueError("Tên đợt dữ liệu là bắt buộc.")

    with rule_connection() as connection:
        ds = connection.execute(
            select(Dataset.id).where(Dataset.id == dataset_id).with_for_update()
        ).first()
        if ds is None:
            raise CatalogNotFound()

        from app.services.suppliers import active_store,event
        if data.get('store_id') is not None:active_store(connection,data['store_id'])

        batch_id = connection.execute(
            insert(DataBatch).values(
                dataset_id=dataset_id,
                name=cleaned["name"],
                description=cleaned.get("description"),
                period_label=cleaned.get("period_label"),
                store_id=data.get('store_id'),
            ).returning(DataBatch.id)
        ).scalar_one()
        if data.get('store_id') is not None:event(connection,'batch',batch_id,None,{'store_id':data['store_id']},actor)

        if data.get('copy_template_rules', True):
            templates = connection.execute(select(QualityRule).where(
                QualityRule.dataset_id == dataset_id, QualityRule.batch_id.is_(None))).mappings().all()
            for rule in templates:
                connection.execute(insert(QualityRule).values(dataset_id=dataset_id, batch_id=batch_id,
                    **{key: rule[key] for key in ('name','rule_type','columns','config','is_active')}))

        connection.execute(
            update(Dataset).where(Dataset.id == dataset_id).values(updated_at=func.now())
        )

        row = connection.execute(
            select(DataBatch).where(DataBatch.id == batch_id)
        ).mappings().first()

        res = dict(row)
        from app.services.suppliers import supplier_map
        res['supplier']=supplier_map(connection).get(res['store_id'])
        res["version_count"] = 0
        res["latest_version"] = None
        return serialize_dt(res)


def list_batches(dataset_id: int, page: int = 1, page_size: int = 20, q: str | None = None) -> dict:
    q = prepare_search_query(q)
    with catalog_connection() as connection:
        ds = connection.execute(select(Dataset.id).where(Dataset.id == dataset_id)).first()
        if ds is None:
            raise CatalogNotFound()

        predicates = [DataBatch.dataset_id == dataset_id]
        if q is not None:
            literal = q.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            predicates.append(
                or_(
                    func.normalize(DataBatch.name).ilike("%" + literal + "%", escape="!"),
                    func.normalize(DataBatch.description).ilike("%" + literal + "%", escape="!"),
                    func.normalize(DataBatch.period_label).ilike("%" + literal + "%", escape="!"),
                )
            )

        total = connection.execute(
            select(func.count()).select_from(DataBatch).where(*predicates)
        ).scalar_one()

        version_count_sub = (
            select(func.count())
            .select_from(DatasetVersion)
            .where(DatasetVersion.batch_id == DataBatch.id)
            .correlate(DataBatch)
            .scalar_subquery()
        )

        batches = connection.execute(
            select(
                DataBatch.id,
                DataBatch.dataset_id,
                DataBatch.name,
                DataBatch.description,
                DataBatch.period_label,
                DataBatch.store_id,
                DataBatch.rules_revision,
                DataBatch.business_state,
                DataBatch.workflow_enabled,
                DataBatch.created_at,
                DataBatch.updated_at,
                version_count_sub.label("version_count"),
            )
            .where(*predicates)
            .order_by(DataBatch.created_at.desc(), DataBatch.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()

        from app.services.suppliers import supplier_map
        sources=supplier_map(connection)
        items = []
        for b in batches:
            b_dict = dict(b)
            b_dict['supplier']=sources.get(b_dict['store_id'])
            # Find latest version for this batch
            latest_v = connection.execute(
                select(
                    DatasetVersion.id,
                    DatasetVersion.version_number,
                    DatasetVersion.original_filename,
                    DatasetVersion.file_size_bytes,
                    DatasetVersion.row_count,
                    DatasetVersion.imported_at,
                    DatasetVersion.is_current,
                )
                .where(DatasetVersion.batch_id == b_dict["id"], DatasetVersion.is_current.is_(True))
                .order_by(DatasetVersion.version_number.desc())
                .limit(1)
            ).mappings().first()

            if latest_v:
                v_dict = dict(latest_v)
                # Find latest run for this version
                latest_run = connection.execute(
                    select(
                        QualityRun.id.label("run_id"),
                        QualityRun.status,
                        QualityRun.started_at,
                        QualityRun.error_row_count,
                        QualityRun.violation_count,
                        QualityRun.total_rows,
                        QualityRun.batch_rules_revision,
                        QualityRun.engine_version,
                    )
                    .where(QualityRun.dataset_version_id == v_dict["id"])
                    .order_by(QualityRun.id.desc())
                    .limit(1)
                ).mappings().first()
                v_dict["latest_run"] = dict(latest_run) if latest_run else None
                if latest_run: v_dict['latest_run']['rules_changed'] = latest_run['batch_rules_revision'] != b_dict['rules_revision']
                b_dict["latest_version"] = v_dict
            else:
                b_dict["latest_version"] = None

            items.append(b_dict)

        return serialize_dt({
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        })


def get_batch(dataset_id: int, batch_id: int) -> dict:
    with catalog_connection() as connection:
        batch = connection.execute(
            select(DataBatch).where(
                DataBatch.id == batch_id,
                DataBatch.dataset_id == dataset_id,
            )
        ).mappings().first()

        if batch is None:
            raise CatalogNotFound()

        b_dict = dict(batch)
        from app.services.suppliers import supplier_map
        b_dict['supplier']=supplier_map(connection).get(b_dict['store_id'])

        # Versions in this batch
        versions = connection.execute(
            select(
                DatasetVersion.id,
                DatasetVersion.dataset_id,
                DatasetVersion.batch_id,
                DatasetVersion.version_number,
                DatasetVersion.original_filename,
                DatasetVersion.file_size_bytes,
                DatasetVersion.row_count,
                DatasetVersion.imported_at,
                DatasetVersion.inferred_types,
                DatasetVersion.is_current,
            )
            .where(DatasetVersion.batch_id == batch_id)
            .order_by(DatasetVersion.version_number.desc())
        ).mappings().all()

        v_items = []
        for v in versions:
            v_dict = dict(v)
            # Latest run for this version
            latest_run = connection.execute(
                select(
                    QualityRun.id.label("run_id"),
                    QualityRun.status,
                    QualityRun.started_at,
                    QualityRun.error_row_count,
                    QualityRun.violation_count,
                    QualityRun.total_rows,
                    QualityRun.batch_rules_revision,
                    QualityRun.engine_version,
                )
                .where(QualityRun.dataset_version_id == v_dict["id"])
                .order_by(QualityRun.id.desc())
                .limit(1)
            ).mappings().first()
            v_dict["latest_run"] = dict(latest_run) if latest_run else None
            if latest_run: v_dict['latest_run']['rules_changed'] = latest_run['batch_rules_revision'] != b_dict['rules_revision']
            v_items.append(v_dict)

        b_dict["versions"] = v_items
        b_dict["version_count"] = len(v_items)
        return serialize_dt(b_dict)


def patch_batch(dataset_id: int, batch_id: int, changes: dict, actor=None) -> dict:
    if 'store_id' in changes and changes['store_id'] is None:
        from app.services.suppliers import fail
        fail('STORE_REQUIRED','Không được bỏ nguồn cung cấp; chọn cửa hàng hợp lệ.')
    cleaned = validate_batch_metadata(changes)
    if 'store_id' in changes:cleaned['store_id']=changes['store_id']
    if not cleaned:
        raise ValueError("Cần ít nhất một trường để cập nhật.")

    with rule_connection() as connection:
        from app.services.issue_workflow import lock_batch
        batch=lock_batch(connection,dataset_id,batch_id)
        if 'store_id' in changes and changes['store_id']!=batch['store_id']:
            from app.services.suppliers import active_store,event,fail
            if connection.execute(select(DatasetVersion.id).where(DatasetVersion.batch_id==batch_id).limit(1)).first():
                fail('BATCH_SOURCE_LOCKED','Đợt đã có phiên bản; không được đổi cửa hàng cung cấp. Tạo đợt riêng cho nguồn khác.',409)
            if changes['store_id'] is not None:active_store(connection,changes['store_id'])
            event(connection,'batch',batch_id,{'store_id':batch['store_id']},{'store_id':changes['store_id']},actor)

        connection.execute(
            update(DataBatch)
            .where(DataBatch.id == batch_id)
            .values(**cleaned, updated_at=func.now())
        )

        connection.execute(
            update(Dataset).where(Dataset.id == dataset_id).values(updated_at=func.now())
        )

        updated = connection.execute(
            select(DataBatch).where(DataBatch.id == batch_id)
        ).mappings().first()

        return serialize_dt(dict(updated))


def list_batch_versions(dataset_id: int, batch_id: int) -> dict:
    batch_detail = get_batch(dataset_id, batch_id)
    return serialize_dt({
        "items": batch_detail["versions"],
        "total": batch_detail["version_count"],
    })
