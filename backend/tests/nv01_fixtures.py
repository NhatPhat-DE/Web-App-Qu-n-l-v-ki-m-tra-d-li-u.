"""Explicit test fixture migration to batch scopes; never used by application code."""
import re
from sqlalchemy import inspect, insert, select, update
from app.models import DataBatch, DatasetVersion


def current_version_values(connection, **values):
    # Historical migration tests intentionally run against pre-batch schemas.
    columns={c['name'] for c in inspect(connection).get_columns('dataset_versions')}
    if 'batch_id' not in columns:return values
    batch=values.get('batch_id') or connection.execute(select(DataBatch.id).where(DataBatch.dataset_id==values['dataset_id']).order_by(DataBatch.id)).scalars().first()
    if batch is None:
        batch=connection.execute(insert(DataBatch).values(dataset_id=values['dataset_id'],name='Fixture batch').returning(DataBatch.id)).scalar_one()
    values['batch_id']=batch
    if 'is_current' in columns:
        connection.execute(update(DatasetVersion).where(DatasetVersion.batch_id==batch).values(is_current=False))
        values['is_current']=True
    return values


def batch_rule_path(client, path):
    """Domain lifecycle tests now exercise batch rules explicitly, templates tested separately."""
    match=re.fullmatch(r'(/api/datasets/(\d+))/rules(.*)',str(path))
    if not match:return path
    response=client.get(match[1])
    if response.status_code!=200:return path
    versions=response.json().get('versions',[])
    if not versions:return path
    batches={v['batch_id'] for v in versions}
    assert len(batches)==1,'Select an explicit batch in a multi-batch test'
    return f'{match[1]}/batches/{batches.pop()}/rules{match[3]}'


def saved_run_fields(body):
    """Only presentation context changes when rules/current change; stored result stays equal."""
    return {k:v for k,v in body.items() if k not in {'rules_changed','current_rules_revision','is_current'}}
