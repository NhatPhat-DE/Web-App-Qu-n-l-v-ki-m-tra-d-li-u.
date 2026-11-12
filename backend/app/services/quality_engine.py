"""Deterministic in-memory checks, independent of HTTP and persistence."""
import json
import re
from datetime import date
from decimal import Decimal, DecimalException, InvalidOperation

ENGINE_VERSION = "quality-v6"

_NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')
_INTEGER = re.compile(r'[+-]?[0-9]+\Z')
_DATA_TYPE_CONFIG_MAX_BYTES = 16 * 1024
_DATA_TYPES = ("integer", "decimal", "boolean")
_DATE_FORMATS = {
    'YYYY-MM-DD': re.compile(r'(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})\Z'),
    'DD/MM/YYYY': re.compile(r'(?P<day>[0-9]{2})/(?P<month>[0-9]{2})/(?P<year>[0-9]{4})\Z'),
    'MM/DD/YYYY': re.compile(r'(?P<month>[0-9]{2})/(?P<day>[0-9]{2})/(?P<year>[0-9]{4})\Z'),
}
_MESSAGES = {
    "PATTERN_MISMATCH": "Giá trị không khớp toàn chuỗi với mẫu được cấu hình.",
    "ALLOWED_VALUE_NOT_IN_SET": "Giá trị không thuộc tập cho phép.",
    "REQUIRED_MISSING": "Giá trị bắt buộc đang thiếu.",
    "UNIQUE_DUPLICATE": "Giá trị hoặc tổ hợp giá trị bị trùng.",
    "NUMERIC_INVALID": "Giá trị không phải số hữu hạn hợp lệ.",
    "NUMERIC_OUT_OF_RANGE": "Giá trị nằm ngoài khoảng đóng cho phép.",
    "DATA_TYPE_INTEGER_INVALID": "Giá trị phải là số nguyên ASCII, không có khoảng trắng ngoài.",
    "DATA_TYPE_DECIMAL_INVALID": "Giá trị phải là số thập phân hữu hạn theo cú pháp được hỗ trợ, không có khoảng trắng ngoài.",
    "DATA_TYPE_BOOLEAN_INVALID": "Giá trị phải là true hoặc false viết thường, không có khoảng trắng ngoài.",
    "DATE_FORMAT_MISMATCH": "Giá trị không đúng định dạng {format}; cần đúng số chữ số và dấu phân cách, không có khoảng trắng ngoài.",
    "DATE_VALUE_INVALID": "Ngày theo định dạng {format} không tồn tại trong lịch Gregorian (năm 0001 đến 9999).",
    "DATE_OUT_OF_RANGE": "Ngày nằm ngoài khoảng ngày đã cấu hình.",
}


class QualityInputError(ValueError):
    def __init__(self, code: str, message: str, row_number: int | None = None):
        self.code = code
        self.row_number = row_number
        super().__init__(message)


def is_missing(value):
    return value is None or isinstance(value, str) and not value.strip()


def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    spelling = str(value).strip()
    if not _NUMBER.fullmatch(spelling):
        return None
    try:
        result = Decimal(spelling)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def _validate_data_type_config(config):
    """Bound only the new config contract; legacy rule limits stay unchanged."""
    try:
        compact = json.dumps(config, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        raise QualityInputError("INVALID_CONFIG", "Cấu hình data_type phải là JSON UTF-8 hợp lệ.") from None
    if len(compact) > _DATA_TYPE_CONFIG_MAX_BYTES:
        raise QualityInputError("INVALID_CONFIG", "Cấu hình data_type không được vượt quá 16 KiB JSON UTF-8 dạng gọn.")
    if set(config) != {"type"} or not isinstance(config["type"], str) or config["type"] not in _DATA_TYPES:
        raise QualityInputError("INVALID_CONFIG", "Cấu hình data_type chỉ nhận type là integer, decimal hoặc boolean.")
    return config["type"]


def _matches_data_type(value, data_type):
    # Match the original spelling. Never reuse _decimal(), which strips whitespace
    # for the pre-existing numeric_range contract.
    if not isinstance(value, str):
        return False
    spelling = value
    if data_type == "integer":
        return _INTEGER.fullmatch(spelling) is not None
    if data_type == "boolean":
        return spelling in ("true", "false")
    if not _NUMBER.fullmatch(spelling):
        return False
    try:
        return Decimal(spelling).is_finite()
    except (DecimalException, ValueError, OverflowError):
        # Decimal can reject syntactically valid exponents outside its supported
        # representation. Treat them as a violation, never a failed run.
        return False


def _validate_date_format_config(config):
    try:
        compact = json.dumps(config, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        raise QualityInputError('INVALID_CONFIG', 'Cấu hình date_format phải là JSON UTF-8 hợp lệ.') from None
    if len(compact) > 16 * 1024:
        raise QualityInputError('INVALID_CONFIG', 'Cấu hình date_format không được vượt quá 16 KiB JSON UTF-8 dạng gọn.')
    if set(config) not in ({'format'}, {'format', 'min', 'max'}) or not isinstance(config['format'], str) or config['format'] not in _DATE_FORMATS:
        raise QualityInputError('INVALID_CONFIG', 'Cấu hình date_format chỉ nhận format là YYYY-MM-DD, DD/MM/YYYY hoặc MM/DD/YYYY.')
    if 'min' in config:
        try:
            for key in ('min', 'max'):
                if not isinstance(config[key], str) or not _DATE_FORMATS['YYYY-MM-DD'].fullmatch(config[key]): raise ValueError()
            if date.fromisoformat(config['min']) > date.fromisoformat(config['max']): raise ValueError()
        except (ValueError, TypeError):
            raise QualityInputError('INVALID_CONFIG', 'Hai biên ngày cần YYYY-MM-DD hợp lệ, min <= max.') from None
    return config['format']


def _validate_allowed_values_config(config):
    try:
        compact = json.dumps(config, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError):
        raise QualityInputError('INVALID_CONFIG', 'Cấu hình allowed_values phải là JSON UTF-8 hợp lệ.') from None
    if len(compact) > 16 * 1024:
        raise QualityInputError('INVALID_CONFIG', 'Cấu hình allowed_values không được vượt quá 16 KiB JSON UTF-8 dạng gọn.')
    if set(config) != {'values'} or not isinstance(config['values'], list) or not 1 <= len(config['values']) <= 100:
        raise QualityInputError('INVALID_CONFIG', 'allowed_values chỉ nhận values gồm 1 đến 100 chuỗi.')
    values = config['values']
    if any(not isinstance(value, str) or not value.strip() or len(value) > 256 or len(value.encode('utf-8')) > 1024 for value in values):
        raise QualityInputError('INVALID_CONFIG', 'Mỗi giá trị phải là chuỗi không rỗng, không chỉ whitespace, tối đa 256 Unicode code point và 1024 byte UTF-8.')
    if len(set(values)) != len(values):
        raise QualityInputError('INVALID_CONFIG', 'Các giá trị allowed_values không được trùng nguyên bản.')
    return tuple(values)


def _date_error(value, expected_format):
    match = _DATE_FORMATS[expected_format].fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return 'DATE_FORMAT_MISMATCH'
    try:
        date(**{part: int(number) for part, number in match.groupdict().items()})
    except ValueError:
        return 'DATE_VALUE_INVALID'
    return None


def validate_rules(header: list[str], rules: list[dict]) -> list[tuple]:
    if not isinstance(header, list) or not header or any(not isinstance(name, str) or not name.strip() for name in header) or len(set(header)) != len(header):
        raise QualityInputError("INVALID_HEADER", "Header phải có tên cột hợp lệ, không trùng.")
    if not isinstance(rules, list) or not rules:
        raise QualityInputError("NO_RULES", "Cần ít nhất một quy tắc để kiểm tra.")
    compiled = []
    ids = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise QualityInputError("INVALID_RULE", "Quy tắc phải là đối tượng cấu hình.")
        identifier = rule.get("rule_id")
        kind = rule.get("rule_type")
        columns = rule.get("columns")
        config = rule.get("config", {})
        if not isinstance(identifier, (str, int)) or isinstance(identifier, bool) or isinstance(identifier, str) and not identifier.strip() or identifier in ids:
            raise QualityInputError("INVALID_RULE_ID", "Mã quy tắc phải hợp lệ và không trùng.")
        ids.add(identifier)
        if kind not in ("required", "unique", "numeric_range", "data_type", "date_format", "allowed_values", "pattern"):
            raise QualityInputError("UNSUPPORTED_RULE", "Loại quy tắc không được hỗ trợ.")
        if not isinstance(columns, list) or not columns or any(not isinstance(column, str) or column not in header for column in columns):
            raise QualityInputError("INVALID_COLUMNS", "Cột quy tắc phải tồn tại trong header.")
        if len(set(columns)) != len(columns) or kind != "unique" and len(columns) != 1:
            raise QualityInputError("INVALID_COLUMNS", "Số cột không phù hợp hoặc có cột lặp.")
        if not isinstance(config, dict):
            raise QualityInputError("INVALID_CONFIG", "Cấu hình quy tắc không hợp lệ.")
        rule_option = None
        if kind == "pattern":
            from app.services.pattern_dialect import validate_config, PatternSyntaxError
            try:
                rule_option = validate_config(config)
            except PatternSyntaxError as error:
                raise QualityInputError('INVALID_CONFIG', str(error)) from None
        elif kind == "data_type":
            rule_option = _validate_data_type_config(config)
        elif kind == "allowed_values":
            rule_option = _validate_allowed_values_config(config)
        elif kind == "date_format":
            rule_option = _validate_date_format_config(config)
        elif set(config) != ({"min", "max"} if kind == "numeric_range" else set()):
            raise QualityInputError("INVALID_CONFIG", "Cấu hình quy tắc không hợp lệ.")
        lower = upper = None
        if kind == "numeric_range":
            lower, upper = _decimal(config["min"]), _decimal(config["max"])
            if lower is None or upper is None or lower > upper:
                raise QualityInputError("INVALID_RANGE", "Hai biên phải là số hữu hạn và min <= max.")
        indexes = [header.index(column) for column in columns]
        compiled.append((identifier, kind, list(columns), indexes, lower, upper, rule_option))
    return compiled


def check_quality(header: list[str], rows: list[list], rules: list[dict], *, pattern_admitted=False) -> dict:
    if not isinstance(header, list) or not header or any(not isinstance(name, str) or not name.strip() for name in header) or len(set(header)) != len(header):
        raise QualityInputError("INVALID_HEADER", "Header phải có tên cột hợp lệ, không trùng.")
    if not isinstance(rows, list) or not rows:
        raise QualityInputError("EMPTY_DATA", "Cần ít nhất một bản ghi để kiểm tra.")
    for number, row in enumerate(rows, 1):
        if not isinstance(row, list) or len(row) != len(header):
            raise QualityInputError("INVALID_ROW", f"Bản ghi {number} sai số lượng cột.", number)
        if any(value is not None and not isinstance(value, (str, int, float, bool, Decimal)) for value in row):
            raise QualityInputError("INVALID_VALUE", f"Bản ghi {number} chứa giá trị không được hỗ trợ.", number)
    compiled = []
    for identifier, kind, columns, indexes, lower, upper, rule_option in validate_rules(header, rules):
        duplicate_rows = set()
        if kind == "unique":
            groups = {}
            for number, row in enumerate(rows, 1):
                values = [row[index] for index in indexes]
                if any(is_missing(value) for value in values):
                    continue
                # Preserve scalar types as well as spelling; False is not integer 0.
                key = tuple((type(value), value) for value in values)
                groups.setdefault(key, []).append(number)
            duplicate_rows = {number for group in groups.values() if len(group) > 1 for number in group}
        compiled.append((identifier, kind, columns, indexes, lower, upper, duplicate_rows, rule_option))

    pattern_failures = {}
    if any(rule['rule_type'] == 'pattern' for rule in rules):
        from app.services.pattern_worker import preflight, admission, evaluate
        patterns = preflight(header, rows, rules)
        with admission(not pattern_admitted):
            pattern_failures = evaluate(header, rows, patterns)
    errors = []
    error_rows = set()
    for number, row in enumerate(rows, 1):
        for identifier, kind, columns, indexes, lower, upper, duplicates, rule_option in compiled:
            values = [row[index] for index in indexes]
            code = None
            if kind == "required" and is_missing(values[0]):
                code = "REQUIRED_MISSING"
            elif kind == "unique" and number in duplicates:
                code = "UNIQUE_DUPLICATE"
            elif kind == "numeric_range" and not is_missing(values[0]):
                value = _decimal(values[0])
                if value is None:
                    code = "NUMERIC_INVALID"
                elif not lower <= value <= upper:
                    code = "NUMERIC_OUT_OF_RANGE"
            elif kind == "data_type" and not is_missing(values[0]):
                if not _matches_data_type(values[0], rule_option):
                    code = f"DATA_TYPE_{rule_option.upper()}_INVALID"
            elif kind == 'date_format' and not is_missing(values[0]):
                code = _date_error(values[0], rule_option)
                if code is None:
                    config = next(r['config'] for r in rules if r['rule_id'] == identifier)
                    if 'min' in config:
                        match = _DATE_FORMATS[rule_option].fullmatch(values[0])
                        actual = date(**{part: int(v) for part, v in match.groupdict().items()})
                        if not date.fromisoformat(config['min']) <= actual <= date.fromisoformat(config['max']):
                            code = 'DATE_OUT_OF_RANGE'
            elif kind == 'allowed_values' and not is_missing(values[0]):
                if not isinstance(values[0], str) or values[0] not in rule_option:
                    code = 'ALLOWED_VALUE_NOT_IN_SET'
            if kind == 'pattern' and number in pattern_failures.get(identifier, ()):
                code = 'PATTERN_MISMATCH'
            if code:
                error_rows.add(number)
                message = _MESSAGES[code].format(format=rule_option) if kind == 'date_format' else _MESSAGES[code]
                if kind == 'pattern':
                    message = 'Giá trị không khớp toàn chuỗi với mẫu ' + json.dumps(rule_option, ensure_ascii=False) + ' (re2-v1); phân biệt hoa/thường, giữ khoảng trắng. Đối chiếu nguồn dữ liệu.'
                if kind == 'allowed_values':
                    message = 'Giá trị không thuộc tập cho phép ' + json.dumps(rule_option, ensure_ascii=False) + '; so sánh nguyên bản, phân biệt hoa/thường và khoảng trắng. Đối chiếu nguồn dữ liệu.'
                errors.append({"rule_id": identifier, "rule_type": kind, "row_number": number,
                               "columns": list(columns), "values": values, "code": code, "message": message})
    return {"row_count": len(rows), "error_row_count": len(error_rows),
            "violation_count": len(errors), "error_row_rate": len(error_rows) / len(rows) * 100,
            "errors": errors}
