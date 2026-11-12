from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext

from sqlalchemy import select, insert, update, func
from app.models import QualityRun, QualityViolation, DatasetVersion, DatasetRow
from app.services.quality_rules import rule_connection, dataset_header, validate
from app.services.quality_engine import ENGINE_VERSION


class ResultValidationError(ValueError):
    pass


def reject():
    raise ResultValidationError("Kết quả không khớp phiên bản dữ liệu hoặc snapshot quy tắc.")


def complete_run(run_id: int, result: dict) -> dict:
    """Persist supplied engine output atomically; never run the engine here."""
    with rule_connection() as connection:
        from app.services.issue_workflow import lock_batch, sync_run
        scope=connection.execute(select(DatasetVersion.dataset_id,DatasetVersion.batch_id).join(QualityRun,QualityRun.dataset_version_id==DatasetVersion.id).where(QualityRun.id==run_id)).first()
        if scope:lock_batch(connection,scope.dataset_id,scope.batch_id)
        run = connection.execute(select(QualityRun).where(QualityRun.id == run_id).with_for_update()).mappings().first()
        if run is None or run["status"] != "running":
            raise ResultValidationError("Chỉ được hoàn tất một lần chạy đang running.")
        if run["engine_version"] != ENGINE_VERSION:
            raise ResultValidationError("Phiên bản engine không được hỗ trợ.")
        version = connection.execute(select(DatasetVersion).where(DatasetVersion.id == run["dataset_version_id"])).mappings().one()
        header = dataset_header(connection, version["dataset_id"])
        snapshot = run["rule_snapshot"]
        if not snapshot:
            reject()
        rules = {}
        for order, rule in enumerate(snapshot, 1):
            if not isinstance(rule, dict) or set(rule) != {"id", "name", "rule_type", "columns", "config"}:
                reject()
            if type(rule["id"]) is not int or rule["id"] < 1 or rule["id"] in rules:
                reject()
            validate(header, rule, compile_pattern=False)
            rules[rule["id"]] = (order, rule)
        if not isinstance(result, dict) or any(type(result.get(key)) is not int for key in ("row_count", "error_row_count", "violation_count")):
            reject()
        total = result["row_count"]
        actual = connection.execute(select(func.count()).select_from(DatasetRow).where(DatasetRow.version_id == version["id"])).scalar_one()
        if total <= 0 or total != version["row_count"] or actual != total or not 0 <= result["error_row_count"] <= total:
            reject()
        errors = result.get("errors")
        if not isinstance(errors, list) or len(errors) != result["violation_count"]:
            reject()
        error_rows = set()
        seen = set()
        entries = []
        allowed = {"pattern": {"PATTERN_MISMATCH"}, "allowed_values": {"ALLOWED_VALUE_NOT_IN_SET"}, "required": {"REQUIRED_MISSING"}, "unique": {"UNIQUE_DUPLICATE"},
                   "numeric_range": {"NUMERIC_INVALID", "NUMERIC_OUT_OF_RANGE"},
                   "date_format": {"DATE_FORMAT_MISMATCH", "DATE_VALUE_INVALID", "DATE_OUT_OF_RANGE"}}
        row_cache = {}
        for error in errors:
            if not isinstance(error, dict) or type(error.get("rule_id")) is not int or error["rule_id"] not in rules:
                reject()
            order, rule = rules[error["rule_id"]]
            number = error.get("row_number")
            if type(number) is not int or not 1 <= number <= total or (number, order) in seen:
                reject()
            if rule['rule_type'] == 'data_type':
                data_type_code = {'integer': 'DATA_TYPE_INTEGER_INVALID',
                                  'decimal': 'DATA_TYPE_DECIMAL_INVALID',
                                  'boolean': 'DATA_TYPE_BOOLEAN_INVALID'}[rule['config']['type']]
                allowed_codes = {data_type_code}
            else:
                allowed_codes = allowed[rule['rule_type']]
            if error.get("rule_type") != rule["rule_type"] or error.get("columns") != rule["columns"] or error.get("code") not in allowed_codes:
                reject()
            if not isinstance(error.get("message"), str) or not error["message"].strip() or "\x00" in error["message"]:
                reject()
            if number not in row_cache:
                row_cache[number] = connection.execute(select(DatasetRow.values).where(DatasetRow.version_id == version["id"], DatasetRow.row_number == number)).scalar_one_or_none()
            row = row_cache[number]
            if row is None or error.get("values") != [row[header.index(column)] for column in rule["columns"]]:
                reject()
            error_rows.add(number)
            seen.add((number, order))
            entries.append({"run_id": run_id, "rule_id_snapshot": rule["id"], "rule_type": rule["rule_type"],
                            "rule_order": order, "row_number": number, "columns": error["columns"],
                            "values": error["values"], "error_code": error["code"], "message": error["message"]})
        if len(error_rows) != result["error_row_count"] or result["violation_count"] < len(error_rows):
            reject()
        if connection.execute(select(QualityViolation.id).where(QualityViolation.run_id == run_id).limit(1)).first():
            reject()
        with localcontext() as context:
            context.prec = max(28, len(str(total)) + 10)
            rate = (Decimal(len(error_rows)) * 100 / Decimal(total)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        entries.sort(key=lambda entry: (entry["row_number"], entry["rule_order"]))
        for start in range(0, len(entries), 1000):
            connection.execute(insert(QualityViolation), entries[start:start + 1000])
        saved = dict(connection.execute(update(QualityRun).where(QualityRun.id == run_id).values(
            status="completed", finished_at=datetime.now(timezone.utc), total_rows=total,
            error_row_count=len(error_rows), violation_count=len(entries), error_row_rate=rate,
        ).returning(*QualityRun.__table__.columns)).mappings().one())
        sync_run(connection,run_id)
        return saved
