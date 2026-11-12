"""Allow pattern without discarding historical snapshots.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def _replace_type_constraints(include_pattern):
    kinds = "'required', 'unique', 'numeric_range', 'data_type', 'date_format', 'allowed_values'"
    if include_pattern:
        kinds += ", 'pattern'"
    for table, constraint in (('quality_rules', 'ck_quality_rules_type'),
                              ('quality_violations', 'ck_quality_violations_type')):
        op.drop_constraint(constraint, table, type_='check')
        op.create_check_constraint(constraint, table, f'rule_type IN ({kinds})')


def upgrade():
    _replace_type_constraints(True)


def downgrade():
    if op.get_context().as_sql:
        raise RuntimeError('Cannot downgrade 0008 offline: pattern rules, violations and snapshots require PostgreSQL preflight.')
    # Prevent a writer inserting history between the preflight and CHECK changes.
    op.execute('LOCK TABLE quality_rules, quality_violations, quality_runs IN ACCESS EXCLUSIVE MODE')
    blocked = op.get_bind().execute(sa.text("""
        SELECT EXISTS (SELECT 1 FROM quality_rules WHERE rule_type = 'pattern')
        OR EXISTS (SELECT 1 FROM quality_violations WHERE rule_type = 'pattern')
        OR EXISTS (SELECT 1 FROM quality_runs WHERE jsonb_path_exists(
            rule_snapshot, '$[*] ? (@.rule_type == "pattern")'))
    """)).scalar_one()
    if blocked:
        raise RuntimeError('Cannot downgrade 0008: pattern remains in quality_rules, quality_violations or quality_runs.rule_snapshot. No data has been deleted.')
    _replace_type_constraints(False)
