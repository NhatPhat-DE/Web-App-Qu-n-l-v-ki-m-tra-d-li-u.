"""HM-01D: Implement DataBatch model and version lifecycle.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create table data_batches
    op.create_table(
        'data_batches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('dataset_id', sa.Integer(), sa.ForeignKey('datasets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('period_label', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_check_constraint('ck_data_batches_name_nonblank', 'data_batches', "name ~ '[^[:space:]]'")
    op.create_check_constraint('ck_data_batches_timestamps', 'data_batches', 'updated_at >= created_at')
    op.create_index('ix_data_batches_dataset_created', 'data_batches', ['dataset_id', 'created_at'])

    # 2. Add nullable batch_id to dataset_versions
    op.add_column('dataset_versions', sa.Column('batch_id', sa.Integer(), nullable=True))

    # 3. Backfill legacy batches for datasets that already have versions
    op.execute(sa.text("""
        INSERT INTO data_batches (dataset_id, name, description, period_label, created_at, updated_at)
        SELECT d.id, 'Đợt khởi tạo (Kế thừa)', 'Đợt dữ liệu được tạo tự động từ các phiên bản lịch sử trước khi nâng cấp mô hình Đợt dữ liệu.', 'Khởi tạo', NOW(), NOW()
        FROM datasets d
        WHERE EXISTS (SELECT 1 FROM dataset_versions dv WHERE dv.dataset_id = d.id);
    """))

    op.execute(sa.text("""
        UPDATE dataset_versions dv
        SET batch_id = b.id
        FROM data_batches b
        WHERE b.dataset_id = dv.dataset_id AND b.name = 'Đợt khởi tạo (Kế thừa)';
    """))

    # Verify no orphaned versions without batch_id
    bind = op.get_bind()
    unmapped = bind.execute(sa.text("SELECT COUNT(*) FROM dataset_versions WHERE batch_id IS NULL")).scalar_one()
    if unmapped > 0:
        raise RuntimeError(f"Backfill incomplete: {unmapped} versions have no batch_id.")

    # 4. Make batch_id NOT NULL and add foreign key
    op.alter_column('dataset_versions', 'batch_id', nullable=False)
    op.create_foreign_key(
        'fk_dataset_versions_batch_id',
        'dataset_versions',
        'data_batches',
        ['batch_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # 5. Drop old unique constraint on (dataset_id, version_number)
    op.drop_constraint('uq_dataset_versions_number', 'dataset_versions', type_='unique')

    # 6. Add new unique constraint on (batch_id, version_number)
    op.create_unique_constraint(
        'uq_dataset_versions_batch_number',
        'dataset_versions',
        ['batch_id', 'version_number'],
    )
    op.create_index('ix_dataset_versions_batch_id', 'dataset_versions', ['batch_id'])


def downgrade():
    bind = op.get_bind()

    # Preflight check: verify that no dataset has duplicate version_number across batches before restoring old constraint
    duplicates = bind.execute(sa.text("""
        SELECT dataset_id, version_number, COUNT(*)
        FROM dataset_versions
        GROUP BY dataset_id, version_number
        HAVING COUNT(*) > 1
    """)).all()
    if duplicates:
        raise RuntimeError(
            f"Cannot downgrade migration 0009: multiple batches contain identical version numbers for the same dataset ({duplicates})."
        )

    op.drop_index('ix_dataset_versions_batch_id', table_name='dataset_versions')
    op.drop_constraint('uq_dataset_versions_batch_number', 'dataset_versions', type_='unique')
    op.create_unique_constraint('uq_dataset_versions_number', 'dataset_versions', ['dataset_id', 'version_number'])
    op.drop_constraint('fk_dataset_versions_batch_id', 'dataset_versions', type_='foreignkey')
    op.drop_column('dataset_versions', 'batch_id')
    op.drop_index('ix_data_batches_dataset_created', table_name='data_batches')
    op.drop_constraint('ck_data_batches_timestamps', 'data_batches', type_='check')
    op.drop_constraint('ck_data_batches_name_nonblank', 'data_batches', type_='check')
    op.drop_table('data_batches')

