from datetime import datetime, timezone
from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Text, UniqueConstraint, Numeric, Index, func, text
from decimal import Decimal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint("username ~ '^[a-z0-9][a-z0-9_.-]{2,63}$'", name='ck_users_username'),
        CheckConstraint("role IN ('admin', 'data_steward', 'data_owner')", name='ck_users_role'),
        CheckConstraint('updated_at >= created_at', name='ck_users_timestamps'),
        UniqueConstraint('username', name='uq_users_username'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default='true')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc))


class Session(Base):
    __tablename__ = 'user_sessions'
    __table_args__ = (
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name='ck_user_sessions_token_hash'),
        CheckConstraint('expires_at > created_at', name='ck_user_sessions_expiry'),
        CheckConstraint('revoked_at IS NULL OR revoked_at >= created_at', name='ck_user_sessions_revocation'),
        UniqueConstraint('token_hash', name='uq_user_sessions_token_hash'),
        Index('ix_user_sessions_user_id', 'user_id'),
        Index('ix_user_sessions_expires_at', 'expires_at'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    token_hash: Mapped[str] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (CheckConstraint("name ~ '[^[:space:]]'", name="ck_datasets_name_nonblank"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc))


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"
    __table_args__ = (
        UniqueConstraint("dataset_id", "name", name="uq_dataset_columns_name"),
        UniqueConstraint("dataset_id", "position", name="uq_dataset_columns_position"),
        CheckConstraint("position >= 1", name="ck_dataset_columns_position"),
        CheckConstraint("name <> ''", name="ck_dataset_columns_name"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    name: Mapped[str] = mapped_column(Text)
    position: Mapped[int]
    description: Mapped[str | None] = mapped_column(Text)


class Brand(Base):
    __tablename__ = 'source_brands'
    __table_args__ = (UniqueConstraint('code', name='uq_source_brands_code'),
        CheckConstraint("code ~ '^[A-Z0-9][A-Z0-9_-]{0,49}$'", name='ck_source_brands_code'),
        CheckConstraint("length(btrim(name)) BETWEEN 1 AND 200", name='ck_source_brands_name'))
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default='true')


class Store(Base):
    __tablename__ = 'source_stores'
    __table_args__ = (UniqueConstraint('code', name='uq_source_stores_code'),
        CheckConstraint("code ~ '^[A-Z0-9][A-Z0-9_-]{0,49}$'", name='ck_source_stores_code'),
        CheckConstraint("length(btrim(name)) BETWEEN 1 AND 200", name='ck_source_stores_name'))
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey('source_brands.id'))
    code: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(server_default='true')


class SourceEvent(Base):
    __tablename__ = 'source_events'
    __table_args__ = (CheckConstraint('num_nonnulls(brand_id,store_id,batch_id)=1',name='ck_source_events_scope'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey('source_brands.id'))
    store_id: Mapped[int | None] = mapped_column(ForeignKey('source_stores.id'))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey('data_batches.id'))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())


class DataBatch(Base):
    __tablename__ = "data_batches"
    __table_args__ = (
        UniqueConstraint('id', 'dataset_id', name='uq_data_batches_id_dataset'),
        CheckConstraint("name ~ '[^[:space:]]'", name="ck_data_batches_name_nonblank"),
        CheckConstraint("updated_at >= created_at", name="ck_data_batches_timestamps"),
        CheckConstraint("business_state IN ('RECEIVING','PROCESSING','COMPLETED')",name='ck_batch_business_state'),
        Index("ix_data_batches_dataset_created", "dataset_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete='CASCADE'))
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    period_label: Mapped[str | None] = mapped_column(Text)
    rules_revision: Mapped[int] = mapped_column(server_default='1')
    business_state: Mapped[str] = mapped_column(Text, server_default='RECEIVING')
    workflow_enabled: Mapped[bool] = mapped_column(server_default='false')
    store_id: Mapped[int | None] = mapped_column(ForeignKey('source_stores.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc))


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        ForeignKeyConstraint(['batch_id', 'dataset_id'], ['data_batches.id', 'data_batches.dataset_id'], name='fk_version_batch_dataset'),
        Index('uq_dataset_versions_current', 'batch_id', unique=True, postgresql_where=text('is_current')),
        UniqueConstraint("batch_id", "version_number", name="uq_dataset_versions_batch_number"),
        CheckConstraint("version_number >= 1", name="ck_dataset_versions_number"),
        CheckConstraint("file_size_bytes >= 0", name="ck_dataset_versions_file_size"),
        CheckConstraint("row_count >= 1", name="ck_dataset_versions_row_count"),
        CheckConstraint("jsonb_typeof(inferred_types) = 'array'", name="ck_dataset_versions_inferred_types"),
        Index("ix_dataset_versions_batch_id", "batch_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    batch_id: Mapped[int] = mapped_column(ForeignKey("data_batches.id", ondelete='CASCADE'))
    version_number: Mapped[int]
    is_current: Mapped[bool] = mapped_column(server_default='false')
    original_filename: Mapped[str] = mapped_column(Text)
    file_size_bytes: Mapped[int]
    row_count: Mapped[int]
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    inferred_types: Mapped[list[dict]] = mapped_column(JSONB)


class DatasetRow(Base):
    __tablename__ = "dataset_rows"
    __table_args__ = (
        UniqueConstraint("version_id", "row_number", name="uq_dataset_rows_number"),
        CheckConstraint("row_number >= 1", name="ck_dataset_rows_number"),
        CheckConstraint("jsonb_typeof(values) = 'array' AND NOT jsonb_path_exists(values, '$[*] ? (@.type() != \"string\")')", name="ck_dataset_rows_string_array"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"))
    row_number: Mapped[int]
    values: Mapped[list[str]] = mapped_column(JSONB)


class QualityRule(Base):
    __tablename__ = "quality_rules"
    __table_args__ = (
        ForeignKeyConstraint(['batch_id', 'dataset_id'], ['data_batches.id', 'data_batches.dataset_id'], name='fk_rule_batch_dataset'),
        Index('ix_quality_rules_batch_id', 'batch_id'),
        CheckConstraint("name ~ '[^[:space:]]'", name="ck_quality_rules_name"),
        CheckConstraint("rule_type IN ('required', 'unique', 'numeric_range', 'data_type', 'date_format', 'allowed_values', 'pattern')", name="ck_quality_rules_type"),
        CheckConstraint("jsonb_typeof(columns) = 'array'", name="ck_quality_rules_columns"),
        CheckConstraint("jsonb_typeof(config) = 'object'", name="ck_quality_rules_config"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey('data_batches.id'))
    name: Mapped[str] = mapped_column(Text)
    rule_type: Mapped[str] = mapped_column(Text)
    columns: Mapped[list[str]] = mapped_column(JSONB)
    config: Mapped[dict] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=lambda: datetime.now(timezone.utc))


class QualityRun(Base):
    __tablename__ = "quality_runs"
    __table_args__ = (
        CheckConstraint("status IN ('running','completed','failed')", name="ck_quality_runs_status"),
        CheckConstraint("jsonb_typeof(rule_snapshot) = 'array'", name="ck_quality_runs_snapshot"),
        CheckConstraint("engine_version <> ''", name="ck_quality_runs_engine"),
        CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="ck_quality_runs_time"),
        CheckConstraint("(status = 'completed' AND finished_at IS NOT NULL AND total_rows IS NOT NULL AND error_row_count IS NOT NULL AND violation_count IS NOT NULL AND error_row_rate IS NOT NULL AND failure_code IS NULL AND failure_message IS NULL) OR (status IN ('running','failed') AND total_rows IS NULL AND error_row_count IS NULL AND violation_count IS NULL AND error_row_rate IS NULL)", name="ck_quality_runs_results"),
        CheckConstraint("(status = 'running' AND finished_at IS NULL AND failure_code IS NULL AND failure_message IS NULL) OR (status = 'failed' AND finished_at IS NOT NULL AND failure_code IS NOT NULL AND failure_message IS NOT NULL) OR status = 'completed'", name="ck_quality_runs_lifecycle"),
        CheckConstraint("total_rows > 0 AND error_row_count BETWEEN 0 AND total_rows AND violation_count >= error_row_count AND error_row_rate BETWEEN 0 AND 100", name="ck_quality_runs_counts"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    status: Mapped[str] = mapped_column(Text, server_default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rule_snapshot: Mapped[list[dict]] = mapped_column(JSONB)
    engine_version: Mapped[str] = mapped_column(Text)
    batch_rules_revision: Mapped[int | None]
    schema_snapshot: Mapped[list[dict] | None] = mapped_column(JSONB)
    export_context_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    total_rows: Mapped[int | None]
    error_row_count: Mapped[int | None]
    violation_count: Mapped[int | None]
    error_row_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))
    failure_code: Mapped[str | None] = mapped_column(Text)
    failure_message: Mapped[str | None] = mapped_column(Text)


class QualityViolation(Base):
    __tablename__ = "quality_violations"
    __table_args__ = (
        Index("ix_quality_violations_order", "run_id", "row_number", "rule_order"),
        UniqueConstraint("run_id", "row_number", "rule_order", name="uq_quality_violations_row_rule"),
        CheckConstraint("row_number >= 1 AND rule_order >= 1", name="ck_quality_violations_order"),
        CheckConstraint("rule_type IN ('required','unique','numeric_range','data_type','date_format','allowed_values','pattern')", name="ck_quality_violations_type"),
        CheckConstraint("jsonb_typeof(columns) = 'array' AND jsonb_typeof(values) = 'array'", name="ck_quality_violations_arrays"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("quality_runs.id"))
    rule_id_snapshot: Mapped[int]
    rule_type: Mapped[str] = mapped_column(Text)
    rule_order: Mapped[int]
    row_number: Mapped[int]
    columns: Mapped[list[str]] = mapped_column(JSONB)
    values: Mapped[list] = mapped_column(JSONB)
    error_code: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)


class DatasetIdentity(Base):
    __tablename__ = 'dataset_identity_configs'
    __table_args__ = (UniqueConstraint('dataset_id','revision',name='uq_identity_revision'),
        Index('uq_identity_current','dataset_id',unique=True,postgresql_where=text('is_current')),
        CheckConstraint("jsonb_typeof(columns)='array' AND jsonb_array_length(columns)>0",name='ck_identity_columns'))
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
    revision: Mapped[int]
    columns: Mapped[list] = mapped_column(JSONB)
    is_current: Mapped[bool] = mapped_column(server_default='true')
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())


class WorkflowReconciliation(Base):
    __tablename__ = 'workflow_reconciliations'
    __table_args__ = (UniqueConstraint('run_id','identity_revision',name='uq_reconciliation_run_identity'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('data_batches.id'))
    run_id: Mapped[int] = mapped_column(ForeignKey('quality_runs.id'))
    identity_config_id: Mapped[int | None] = mapped_column(ForeignKey('dataset_identity_configs.id'))
    identity_revision: Mapped[int] = mapped_column(server_default='0')
    identity_columns: Mapped[list] = mapped_column(JSONB)
    eligible: Mapped[bool]
    result: Mapped[str] = mapped_column(Text)
    reasons: Mapped[list] = mapped_column(JSONB)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())


class DataIssue(Base):
    __tablename__ = 'data_issues'
    __table_args__ = (UniqueConstraint('batch_id','issue_key',name='uq_issue_batch_key'),
        CheckConstraint("status IN ('OPEN','IN_PROGRESS','PENDING_RECHECK','RESOLVED','IGNORED')",name='ck_issue_status'),
        CheckConstraint("status<>'IGNORED' OR (ignored_note IS NOT NULL AND ignored_note ~ '[^[:space:]]')",name='ck_issue_ignore_note'),
        Index('ix_issue_batch_status','batch_id','status'))
    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
    batch_id: Mapped[int] = mapped_column(ForeignKey('data_batches.id'))
    issue_key: Mapped[str] = mapped_column(Text)
    identity_config_id: Mapped[int | None] = mapped_column(ForeignKey('dataset_identity_configs.id'))
    record_key: Mapped[str | None] = mapped_column(Text)
    key_values: Mapped[list | None] = mapped_column(JSONB)
    context_key: Mapped[str] = mapped_column(Text)
    rule_id_snapshot: Mapped[int]
    rule_snapshot: Mapped[dict] = mapped_column(JSONB)
    origin_run_id: Mapped[int] = mapped_column(ForeignKey('quality_runs.id'))
    origin_version_id: Mapped[int] = mapped_column(ForeignKey('dataset_versions.id'))
    last_run_id: Mapped[int] = mapped_column(ForeignKey('quality_runs.id'))
    status: Mapped[str] = mapped_column(Text,server_default='OPEN')
    status_revision: Mapped[int] = mapped_column(server_default='1')
    uncertain_reason: Mapped[str | None] = mapped_column(Text)
    ignored_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())


class IssueEvent(Base):
    __tablename__ = 'issue_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey('data_issues.id'))
    action: Mapped[str] = mapped_column(Text)
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    actor_label: Mapped[str] = mapped_column(Text)
    run_id: Mapped[int | None] = mapped_column(ForeignKey('quality_runs.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())


class IssueObservation(Base):
    __tablename__ = 'issue_observations'
    __table_args__ = (UniqueConstraint('issue_id','violation_id',name='uq_issue_violation'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey('data_issues.id'))
    violation_id: Mapped[int] = mapped_column(ForeignKey('quality_violations.id'))
    reconciliation_id: Mapped[int] = mapped_column(ForeignKey('workflow_reconciliations.id'))


class ReconciliationItem(Base):
    __tablename__ = 'reconciliation_items'
    __table_args__ = (UniqueConstraint('reconciliation_id','issue_id',name='uq_reconciliation_issue'),
        CheckConstraint("outcome IN ('NEW','PERSISTING','RESOLVED','UNKNOWN')",name='ck_reconciliation_outcome'))
    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_id: Mapped[int] = mapped_column(ForeignKey('workflow_reconciliations.id'))
    issue_id: Mapped[int] = mapped_column(ForeignKey('data_issues.id'))
    outcome: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    source_version_id: Mapped[int] = mapped_column(ForeignKey('dataset_versions.id'))


class BatchEvent(Base):
    __tablename__ = 'batch_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('data_batches.id'))
    action: Mapped[str] = mapped_column(Text)
    from_state: Mapped[str] = mapped_column(Text)
    to_state: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    actor_label: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
