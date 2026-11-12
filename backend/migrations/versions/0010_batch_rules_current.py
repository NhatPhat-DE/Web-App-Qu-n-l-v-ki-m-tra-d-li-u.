"""NV-01: independent batch rules and atomic current version.

Existing rule IDs and run snapshots stay untouched. Dataset rules become templates;
their independent copies seed every existing batch. No business month is inferred.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    bad = bind.execute(sa.text('''SELECT count(*) FROM dataset_versions v
        LEFT JOIN data_batches b ON b.id=v.batch_id
        WHERE b.id IS NULL OR b.dataset_id<>v.dataset_id''')).scalar_one()
    if bad:
        raise RuntimeError('NV-01: inconsistent version/batch membership. Resolve explicitly before migration; no data changed.')
    op.add_column('data_batches', sa.Column('rules_revision', sa.Integer(), nullable=False, server_default='1'))
    op.create_unique_constraint('uq_data_batches_id_dataset', 'data_batches', ['id', 'dataset_id'])
    op.add_column('dataset_versions', sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute('''UPDATE dataset_versions v SET is_current=true WHERE NOT EXISTS
        (SELECT 1 FROM dataset_versions newer WHERE newer.batch_id=v.batch_id AND newer.version_number>v.version_number)''')
    op.create_index('uq_dataset_versions_current', 'dataset_versions', ['batch_id'], unique=True, postgresql_where=sa.text('is_current'))
    op.create_foreign_key('fk_version_batch_dataset', 'dataset_versions', 'data_batches', ['batch_id','dataset_id'], ['id','dataset_id'])
    op.add_column('quality_rules', sa.Column('batch_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_quality_rules_batch', 'quality_rules', 'data_batches', ['batch_id'], ['id'])
    op.create_foreign_key('fk_rule_batch_dataset', 'quality_rules', 'data_batches', ['batch_id','dataset_id'], ['id','dataset_id'])
    op.create_index('ix_quality_rules_batch_id', 'quality_rules', ['batch_id'])
    op.execute('''INSERT INTO quality_rules (dataset_id,batch_id,name,rule_type,columns,config,is_active)
        SELECT r.dataset_id,b.id,r.name,r.rule_type,r.columns,r.config,r.is_active
        FROM quality_rules r JOIN data_batches b ON b.dataset_id=r.dataset_id WHERE r.batch_id IS NULL''')
    op.add_column('quality_runs', sa.Column('batch_rules_revision', sa.Integer(), nullable=True))
    op.add_column('quality_runs', sa.Column('schema_snapshot', postgresql.JSONB(), nullable=True))
    # Deferred: upload may clear old current and insert new current in one transaction.
    # The partial unique index enforces at most one immediately; this enforces at least one.
    op.execute('''CREATE FUNCTION nv01_check_current() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE target integer;
    BEGIN
      FOR target IN SELECT DISTINCT x FROM unnest(ARRAY[
        CASE WHEN TG_OP <> 'INSERT' THEN OLD.batch_id END,
        CASE WHEN TG_OP <> 'DELETE' THEN NEW.batch_id END]) x WHERE x IS NOT NULL
      LOOP
        PERFORM id FROM data_batches WHERE id=target FOR UPDATE;
        IF EXISTS(SELECT 1 FROM dataset_versions WHERE batch_id=target)
          AND (SELECT count(*) FROM dataset_versions WHERE batch_id=target AND is_current) <> 1 THEN
          RAISE EXCEPTION 'Batch must have exactly one current version' USING ERRCODE='23514';
        END IF;
      END LOOP;
      RETURN NULL;
    END $$''')
    op.execute('''CREATE CONSTRAINT TRIGGER nv01_current_version
        AFTER INSERT OR UPDATE OR DELETE ON dataset_versions DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION nv01_check_current()''')


def downgrade():
    # Only an empty schema can safely roll back (e.g. historical migration tests).
    if op.get_context().as_sql:
        raise RuntimeError('NV-01 downgrade requires an online empty-database check.')
    c=op.get_bind()
    if c.execute(sa.text('SELECT (SELECT count(*) FROM dataset_versions)+(SELECT count(*) FROM quality_rules)+(SELECT count(*) FROM quality_runs)')).scalar_one():
        raise RuntimeError('NV-01 downgrade blocked: preserve batch rules/history; restore a verified backup if rollback is required.')
    op.execute('DROP TRIGGER nv01_current_version ON dataset_versions')
    op.execute('DROP FUNCTION nv01_check_current()')
    op.drop_column('quality_runs','schema_snapshot')
    op.drop_column('quality_runs','batch_rules_revision')
    op.drop_index('ix_quality_rules_batch_id',table_name='quality_rules')
    op.drop_constraint('fk_rule_batch_dataset','quality_rules',type_='foreignkey')
    op.drop_constraint('fk_quality_rules_batch','quality_rules',type_='foreignkey')
    op.drop_column('quality_rules','batch_id')
    op.drop_constraint('fk_version_batch_dataset','dataset_versions',type_='foreignkey')
    op.drop_index('uq_dataset_versions_current',table_name='dataset_versions')
    op.drop_column('dataset_versions','is_current')
    op.drop_constraint('uq_data_batches_id_dataset','data_batches',type_='unique')
    op.drop_column('data_batches','rules_revision')
