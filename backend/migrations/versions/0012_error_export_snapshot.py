"""EXP-01: freeze export scope and identity when a run starts. No backfill."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0012'
down_revision='0011'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('quality_runs',sa.Column('export_context_snapshot',JSONB(),nullable=True))

def downgrade():
    c=op.get_bind()
    c.execute(sa.text('LOCK TABLE quality_runs IN ACCESS EXCLUSIVE MODE'))
    if c.execute(sa.text('SELECT EXISTS(SELECT 1 FROM quality_runs WHERE export_context_snapshot IS NOT NULL)')).scalar_one():
        raise RuntimeError('EXP-01 export snapshots must not be discarded; restore an explicit backup instead.')
    op.drop_column('quality_runs','export_context_snapshot')
