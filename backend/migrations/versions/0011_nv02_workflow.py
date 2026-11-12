"""NV-02: additive identity, issues, reconciliation and batch lifecycle. No backfill."""
from alembic import op
import sqlalchemy as sa
revision='0011'
down_revision='0010'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('data_batches',sa.Column('business_state',sa.Text(),nullable=False,server_default='RECEIVING'))
    op.add_column('data_batches',sa.Column('workflow_enabled',sa.Boolean(),nullable=False,server_default=sa.text('false')))
    op.create_check_constraint('ck_batch_business_state','data_batches',"business_state IN ('RECEIVING','PROCESSING','COMPLETED')")
    op.drop_constraint('ck_users_role','users',type_='check')
    op.create_check_constraint('ck_users_role','users',"role IN ('admin','data_steward','data_owner')")
    op.execute("\nCREATE TABLE dataset_identity_configs (\n\tid SERIAL NOT NULL, \n\tdataset_id INTEGER NOT NULL, \n\trevision INTEGER NOT NULL, \n\tcolumns JSONB NOT NULL, \n\tis_current BOOLEAN DEFAULT 'true' NOT NULL, \n\tactor_id INTEGER, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_identity_revision UNIQUE (dataset_id, revision), \n\tCONSTRAINT ck_identity_columns CHECK (jsonb_typeof(columns)='array' AND jsonb_array_length(columns)>0), \n\tFOREIGN KEY(dataset_id) REFERENCES datasets (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n")
    op.execute('CREATE UNIQUE INDEX uq_identity_current ON dataset_identity_configs (dataset_id) WHERE is_current')
    op.execute("\nCREATE TABLE workflow_reconciliations (\n\tid SERIAL NOT NULL, \n\tbatch_id INTEGER NOT NULL, \n\trun_id INTEGER NOT NULL, \n\tidentity_config_id INTEGER, \n\tidentity_revision INTEGER DEFAULT '0' NOT NULL, \n\tidentity_columns JSONB NOT NULL, \n\teligible BOOLEAN NOT NULL, \n\tresult TEXT NOT NULL, \n\treasons JSONB NOT NULL, \n\tactor_id INTEGER, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_reconciliation_run_identity UNIQUE (run_id, identity_revision), \n\tFOREIGN KEY(batch_id) REFERENCES data_batches (id), \n\tFOREIGN KEY(run_id) REFERENCES quality_runs (id), \n\tFOREIGN KEY(identity_config_id) REFERENCES dataset_identity_configs (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n")
    op.execute("\nCREATE TABLE data_issues (\n\tid SERIAL NOT NULL, \n\tdataset_id INTEGER NOT NULL, \n\tbatch_id INTEGER NOT NULL, \n\tissue_key TEXT NOT NULL, \n\tidentity_config_id INTEGER, \n\trecord_key TEXT, \n\tkey_values JSONB, \n\tcontext_key TEXT NOT NULL, \n\trule_id_snapshot INTEGER NOT NULL, \n\trule_snapshot JSONB NOT NULL, \n\torigin_run_id INTEGER NOT NULL, \n\torigin_version_id INTEGER NOT NULL, \n\tlast_run_id INTEGER NOT NULL, \n\tstatus TEXT DEFAULT 'OPEN' NOT NULL, \n\tstatus_revision INTEGER DEFAULT '1' NOT NULL, \n\tuncertain_reason TEXT, \n\tignored_note TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_issue_batch_key UNIQUE (batch_id, issue_key), \n\tCONSTRAINT ck_issue_status CHECK (status IN ('OPEN','IN_PROGRESS','PENDING_RECHECK','RESOLVED','IGNORED')), \n\tCONSTRAINT ck_issue_ignore_note CHECK (status<>'IGNORED' OR (ignored_note IS NOT NULL AND ignored_note ~ '[^[:space:]]')), \n\tFOREIGN KEY(dataset_id) REFERENCES datasets (id), \n\tFOREIGN KEY(batch_id) REFERENCES data_batches (id), \n\tFOREIGN KEY(identity_config_id) REFERENCES dataset_identity_configs (id), \n\tFOREIGN KEY(origin_run_id) REFERENCES quality_runs (id), \n\tFOREIGN KEY(origin_version_id) REFERENCES dataset_versions (id), \n\tFOREIGN KEY(last_run_id) REFERENCES quality_runs (id)\n)\n\n")
    op.execute('CREATE INDEX ix_issue_batch_status ON data_issues (batch_id, status)')
    op.execute('\nCREATE TABLE issue_events (\n\tid SERIAL NOT NULL, \n\tissue_id INTEGER NOT NULL, \n\taction TEXT NOT NULL, \n\tfrom_status TEXT, \n\tto_status TEXT NOT NULL, \n\tnote TEXT NOT NULL, \n\tactor_id INTEGER, \n\tactor_label TEXT NOT NULL, \n\trun_id INTEGER, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(issue_id) REFERENCES data_issues (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id), \n\tFOREIGN KEY(run_id) REFERENCES quality_runs (id)\n)\n\n')
    op.execute('\nCREATE TABLE issue_observations (\n\tid SERIAL NOT NULL, \n\tissue_id INTEGER NOT NULL, \n\tviolation_id INTEGER NOT NULL, \n\treconciliation_id INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_issue_violation UNIQUE (issue_id, violation_id), \n\tFOREIGN KEY(issue_id) REFERENCES data_issues (id), \n\tFOREIGN KEY(violation_id) REFERENCES quality_violations (id), \n\tFOREIGN KEY(reconciliation_id) REFERENCES workflow_reconciliations (id)\n)\n\n')
    op.execute("\nCREATE TABLE reconciliation_items (\n\tid SERIAL NOT NULL, \n\treconciliation_id INTEGER NOT NULL, \n\tissue_id INTEGER NOT NULL, \n\toutcome TEXT NOT NULL, \n\treason TEXT, \n\tsource_version_id INTEGER NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_reconciliation_issue UNIQUE (reconciliation_id, issue_id), \n\tCONSTRAINT ck_reconciliation_outcome CHECK (outcome IN ('NEW','PERSISTING','RESOLVED','UNKNOWN')), \n\tFOREIGN KEY(reconciliation_id) REFERENCES workflow_reconciliations (id), \n\tFOREIGN KEY(issue_id) REFERENCES data_issues (id), \n\tFOREIGN KEY(source_version_id) REFERENCES dataset_versions (id)\n)\n\n")
    op.execute('\nCREATE TABLE batch_events (\n\tid SERIAL NOT NULL, \n\tbatch_id INTEGER NOT NULL, \n\taction TEXT NOT NULL, \n\tfrom_state TEXT NOT NULL, \n\tto_state TEXT NOT NULL, \n\tnote TEXT NOT NULL, \n\tactor_id INTEGER, \n\tactor_label TEXT NOT NULL, \n\tevidence JSONB NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(batch_id) REFERENCES data_batches (id), \n\tFOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n')

def downgrade():
    connection=op.get_bind()
    tables=('batch_events','reconciliation_items','issue_observations','issue_events','data_issues','workflow_reconciliations','dataset_identity_configs')
    # Lock the entire scope before checking: a concurrent activation/user change
    # must not slip between the evidence check and dropping the empty tables.
    connection.execute(sa.text('LOCK TABLE '+', '.join((*tables,'data_batches','users'))+' IN ACCESS EXCLUSIVE MODE'))
    populated=any(connection.execute(sa.text(f'SELECT EXISTS(SELECT 1 FROM {table})')).scalar_one() for table in tables)
    changed=connection.execute(sa.text("SELECT EXISTS(SELECT 1 FROM data_batches WHERE workflow_enabled OR business_state<>'RECEIVING') OR EXISTS(SELECT 1 FROM users WHERE role='data_owner')")).scalar_one()
    if populated or changed:
        raise RuntimeError('NV-02 lifecycle evidence must not be discarded by downgrade; restore an explicit backup instead.')
    for table in tables:op.drop_table(table)
    op.drop_constraint('ck_batch_business_state','data_batches',type_='check')
    op.drop_column('data_batches','workflow_enabled')
    op.drop_column('data_batches','business_state')
    op.drop_constraint('ck_users_role','users',type_='check')
    op.create_check_constraint('ck_users_role','users',"role IN ('admin','data_steward')")
