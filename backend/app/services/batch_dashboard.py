"""NV-01 current-version dashboard. One completed run per selected batch."""
from decimal import Decimal
from sqlalchemy import select, func
from app.models import DataBatch, Dataset, DatasetVersion, QualityRun, QualityRule
from app.services.dataset_catalog import catalog_connection, CatalogNotFound
from app.services.quality_engine import ENGINE_VERSION


def dashboard(batch_ids=None,brand_id=None,store_id=None):
    with catalog_connection() as c:
        query = select(DataBatch, Dataset.name.label('dataset_name')).join(Dataset, Dataset.id == DataBatch.dataset_id)
        if batch_ids:
            query = query.where(DataBatch.id.in_(batch_ids))
        known=c.execute(query).mappings().all()
        if batch_ids and {b['id'] for b in known} != set(batch_ids):
            raise CatalogNotFound()
        from app.models import Store
        if brand_id is not None:query=query.where(DataBatch.store_id.in_(select(Store.id).where(Store.brand_id==brand_id)))
        if store_id is not None:query=query.where(DataBatch.store_id==store_id if store_id else DataBatch.store_id.is_(None))
        batches = c.execute(query.order_by(DataBatch.id)).mappings().all()
        from app.services.suppliers import supplier_map
        sources=supplier_map(c)
        items = []
        latest_runs = {}
        totals = dict(total_rows=0, violated_rows_count=0, total_violations_count=0)
        for batch in batches:
            latest_runs[batch['id']] = None
            version = c.execute(select(DatasetVersion).where(DatasetVersion.batch_id == batch['id'],
                DatasetVersion.is_current.is_(True))).mappings().first()
            active = c.execute(select(func.count()).select_from(QualityRule).where(QualityRule.batch_id == batch['id'],
                QualityRule.is_active.is_(True))).scalar_one()
            item = dict(batch_id=batch['id'], dataset_id=batch['dataset_id'], dataset_name=batch['dataset_name'],
                supplier=sources.get(batch['store_id']),store_id=batch['store_id'],
                business_state=batch['business_state'], batch_name=batch['name'], period_label=batch['period_label'], rules_revision=batch['rules_revision'],
                active_rule_count=active, current_version=dict(version) if version else None, run=None,
                rules_changed=False, status='NO_FILE')
            if version:
                latest = c.execute(select(QualityRun).where(QualityRun.dataset_version_id == version['id'])
                    .order_by(QualityRun.started_at.desc(), QualityRun.id.desc()).limit(1)).mappings().first()
                latest_runs[batch['id']] = latest
                completed = c.execute(select(QualityRun).where(QualityRun.dataset_version_id == version['id'],
                    QualityRun.status == 'completed').order_by(QualityRun.started_at.desc(), QualityRun.id.desc()).limit(1)).mappings().first()
                item['status'] = 'NEEDS_RULES' if not active else 'UNCHECKED'
                if completed:
                    item['run'] = {key: completed[key] for key in ('id','total_rows','error_row_count','violation_count','started_at','batch_rules_revision','engine_version')}
                    item['rules_changed'] = completed['batch_rules_revision'] != batch['rules_revision'] or completed['engine_version'] != ENGINE_VERSION
                    item['status'] = 'STALE' if item['rules_changed'] else 'HAS_ERRORS' if completed['error_row_count'] else 'PASSED'
                    totals['total_rows'] += completed['total_rows']
                    totals['violated_rows_count'] += completed['error_row_count']
                    totals['total_violations_count'] += completed['violation_count']
                if latest and latest['status'] in ('running', 'failed'):
                    item['status'] = latest['status'].upper()
            items.append(item)
        from app.services.workflow_dashboard import summaries
        workflow = summaries(c, batches, items, latest_runs)
        for item in items:
            item['workflow'] = workflow[item['batch_id']]
        return dict(items=items, scope='Phiên bản hiện hành của từng đợt đã chọn; mỗi đợt lấy một lượt hoàn tất gần nhất. Tổng dòng qua các kỳ, không phải số đối tượng duy nhất.',
            selected_batch_ids=[b['id'] for b in batches], assessed_batches=sum(i['run'] is not None for i in items),
            **totals, violation_rate=(format(Decimal(totals['violated_rows_count'])*100/Decimal(totals['total_rows']), '.4f') if totals['total_rows'] else None))
