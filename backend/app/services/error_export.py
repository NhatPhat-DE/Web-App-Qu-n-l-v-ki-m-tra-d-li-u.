"""Immutable run export context and raw key cells from that exact version."""
from sqlalchemy import select,text
from app.models import Dataset,DatasetIdentity,DatasetVersion,QualityRun,QualityViolation,DatasetRow,WorkflowReconciliation
from app.services.quality_rules import rule_connection
from app.services.dataset_catalog import CatalogNotFound
from app.services.quality_execution import RunError


def snapshot_at_start(c,version,batch):
    from app.services.suppliers import supplier_map
    dataset=c.execute(select(Dataset).where(Dataset.id==version['dataset_id'])).mappings().one()
    config=c.execute(select(DatasetIdentity).where(DatasetIdentity.dataset_id==dataset['id'],DatasetIdentity.is_current)).mappings().first()
    return {'supplier':supplier_map(c).get(batch['store_id']), 'dataset':{'id':dataset['id'],'name':dataset['name']},
        'batch':{'id':batch['id'],'name':batch['name'],'period_label':batch['period_label']},
        'version':{'id':version['id'],'number':version['version_number'],'filename':version['original_filename']},
        'identity':{'id':config['id'],'revision':config['revision'],'columns':config['columns']} if config else None}


def context(dataset_id,run_id):
    with rule_connection() as c:
        c.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY'))
        run=c.execute(select(QualityRun).where(QualityRun.id==run_id)).mappings().first()
        version=c.execute(select(DatasetVersion).where(DatasetVersion.id==run['dataset_version_id'],DatasetVersion.dataset_id==dataset_id)).mappings().first() if run else None
        if not version:raise CatalogNotFound()
        if run['status']!='completed':raise RunError(409,'RUN_NOT_COMPLETED','Chỉ xuất lỗi của lần kiểm tra đã hoàn tất.')
        frozen=run['export_context_snapshot']
        identity=None;identity_source='not_recorded';identity_status='unavailable'
        if frozen:
            scope={k:frozen[k] for k in ('dataset','batch','version')};scope_source='run_snapshot'
            identity=frozen['identity'];identity_source='run_snapshot';identity_status='configured' if identity else 'not_configured'
        else:
            # Legacy names were never frozen: IDs and immutable version facts
            # remain reliable, current names/config must not rewrite history.
            scope={'dataset':{'id':dataset_id,'name':None},'batch':{'id':version['batch_id'],'name':None,'period_label':None},
                'version':{'id':version['id'],'number':version['version_number'],'filename':version['original_filename']}}
            scope_source='legacy_ids_only'
            first=c.execute(select(WorkflowReconciliation).where(WorkflowReconciliation.run_id==run_id).order_by(WorkflowReconciliation.id).limit(1)).mappings().first()
            if first and first['identity_config_id']:
                archived=c.execute(select(DatasetIdentity).where(DatasetIdentity.id==first['identity_config_id'])).mappings().one()
                # Reject a post-run identity revision introduced by later activation.
                newer=c.execute(select(DatasetIdentity.id).where(DatasetIdentity.dataset_id==dataset_id,
                    DatasetIdentity.created_at<=run['started_at'],DatasetIdentity.revision>archived['revision'])).first()
                if archived['created_at']<=run['started_at'] and not newer:
                    identity={'id':archived['id'],'revision':first['identity_revision'],'columns':first['identity_columns']}
                    identity_source='first_reconciliation_snapshot';identity_status='configured'
        columns=identity['columns'] if identity else []
        header=[col['name'] for col in run['schema_snapshot'] or []]
        readable=bool(columns) and all(col in header for col in columns)
        positions=[header.index(col) for col in columns] if readable else []
        row_keys=[]
        if readable:
            row_numbers=select(QualityViolation.row_number).where(QualityViolation.run_id==run_id)
            for row in c.execute(select(DatasetRow.row_number,DatasetRow.values).where(DatasetRow.version_id==version['id'],DatasetRow.row_number.in_(row_numbers)).order_by(DatasetRow.row_number)):
                row_keys.append({'row_number':row.row_number,'values':[row.values[p] for p in positions]})
        return {**scope,'supplier':frozen.get('supplier') if frozen else None,'run_id':run_id,'scope_source':scope_source,'identity':identity,'identity_status':identity_status,
            'identity_source':identity_source,'key_values_available':readable,'rows':row_keys}
