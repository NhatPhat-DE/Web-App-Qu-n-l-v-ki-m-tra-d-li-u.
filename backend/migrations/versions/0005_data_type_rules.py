"""Allow manual data_type rules and preserve their history on downgrade.

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _replace_type_constraints(include_data_type: bool) -> None:
    rule_types = "'required', 'unique', 'numeric_range'"
    if include_data_type:
        rule_types += ", 'data_type'"
    for table_name, constraint_name in (
        ("quality_rules", "ck_quality_rules_type"),
        ("quality_violations", "ck_quality_violations_type"),
    ):
        op.drop_constraint(constraint_name, table_name, type_="check")
        op.create_check_constraint(
            constraint_name, table_name, f"rule_type IN ({rule_types})"
        )


def upgrade() -> None:
    _replace_type_constraints(include_data_type=True)


def downgrade() -> None:
    if op.get_context().as_sql:
        raise RuntimeError(
            "Cannot downgrade 0005 offline: data_type rules, violations and "
            "run snapshots must be checked in PostgreSQL first."
        )

    # Hold these locks until Alembic's PostgreSQL transaction ends so a writer
    # cannot introduce data_type between the preflight and the new CHECKs.
    op.execute(
        "LOCK TABLE quality_rules, quality_violations, quality_runs "
        "IN ACCESS EXCLUSIVE MODE"
    )
    contains_data_type = op.get_bind().execute(sa.text("""
        SELECT
            EXISTS (SELECT 1 FROM quality_rules WHERE rule_type = 'data_type')
            OR EXISTS (
                SELECT 1 FROM quality_violations WHERE rule_type = 'data_type'
            )
            OR EXISTS (
                SELECT 1 FROM quality_runs
                WHERE jsonb_path_exists(
                    rule_snapshot, '$[*] ? (@.rule_type == "data_type")'
                )
            )
    """)).scalar_one()
    if contains_data_type:
        raise RuntimeError(
            "Cannot downgrade 0005: data_type remains in quality_rules, "
            "quality_violations or quality_runs.rule_snapshot. "
            "No rules, results or historical snapshots have been deleted."
        )

    _replace_type_constraints(include_data_type=False)
