"""SRC-01 supplier catalog; old batches intentionally remain unassigned."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0013'
down_revision='0012'
branch_labels=None
depends_on=None


def upgrade():
    for table in ['source_brands','source_stores']:
        cols=[sa.Column('id',sa.Integer(),primary_key=True),sa.Column('code',sa.Text(),nullable=False),
            sa.Column('name',sa.Text(),nullable=False),sa.Column('is_active',sa.Boolean(),nullable=False,server_default=sa.true())]
        if table=='source_stores':cols.append(sa.Column('brand_id',sa.Integer(),sa.ForeignKey('source_brands.id'),nullable=False))
        op.create_table(table,*cols,sa.UniqueConstraint('code',name=f'uq_{table}_code'),
            sa.CheckConstraint("code ~ '^[A-Z0-9][A-Z0-9_-]{0,49}$'",name=f'ck_{table}_code'),
            sa.CheckConstraint('length(btrim(name)) BETWEEN 1 AND 200',name=f'ck_{table}_name'))
    op.add_column('data_batches',sa.Column('store_id',sa.Integer(),nullable=True))
    op.create_foreign_key('fk_batch_store','data_batches','source_stores',['store_id'],['id'])
    op.create_index('ix_data_batches_store_id','data_batches',['store_id'])
    op.create_table('source_events',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('brand_id',sa.Integer(),sa.ForeignKey('source_brands.id')),
        sa.Column('store_id',sa.Integer(),sa.ForeignKey('source_stores.id')),
        sa.Column('batch_id',sa.Integer(),sa.ForeignKey('data_batches.id')),
        sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id')),
        sa.Column('before',JSONB),sa.Column('after',JSONB,nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.CheckConstraint('num_nonnulls(brand_id,store_id,batch_id)=1',name='ck_source_events_scope'))


def downgrade():
    c=op.get_bind()
    if c.execute(sa.text('SELECT EXISTS(SELECT 1 FROM source_brands) OR EXISTS(SELECT 1 FROM source_events) OR EXISTS(SELECT 1 FROM data_batches WHERE store_id IS NOT NULL)')).scalar_one():
        raise RuntimeError('Supplier data/history must not be discarded; restore a verified backup instead')
    op.drop_table('source_events');op.drop_index('ix_data_batches_store_id',table_name='data_batches')
    op.drop_constraint('fk_batch_store','data_batches',type_='foreignkey');op.drop_column('data_batches','store_id')
    op.drop_table('source_stores');op.drop_table('source_brands')
