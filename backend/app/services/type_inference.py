"""Type suggestions from all supplied rows; never convert original values."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

_INTEGER = re.compile(r'[+-]?[0-9]+\Z')
_DECIMAL = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')
_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\Z')


class TypeInferenceError(ValueError):
    def __init__(self, code, message, row_number=None):
        self.code, self.row_number = code, row_number
        super().__init__(message)


def classify(value: str) -> str:
    spelling = value.strip()
    if spelling.lower() in ('true', 'false'):
        return 'boolean'
    if _DECIMAL.fullmatch(spelling):
        integer_part = re.split(r'[.eE]', spelling.lstrip('+-'), maxsplit=1)[0]
        if len(integer_part) > 1 and integer_part.startswith('0'):
            return 'text'
    if _INTEGER.fullmatch(spelling):
        digits = spelling.lstrip('+-')
        return 'text' if len(digits) > 1 and digits.startswith('0') else 'integer'
    if _DECIMAL.fullmatch(spelling):
        try:
            if Decimal(spelling).is_finite():
                return 'decimal'
        except InvalidOperation:
            pass
    if _DATE.fullmatch(spelling):
        try:
            date.fromisoformat(spelling)
            return 'date'
        except ValueError:
            pass
    return 'text'


def infer_types(header: list[str], rows: list[list[str | None]]) -> list[dict]:
    if not isinstance(header, list) or not header or any(not isinstance(name, str) or not name.strip() for name in header) or len(set(header)) != len(header):
        raise TypeInferenceError('INVALID_HEADER', 'Header phải có tên cột không rỗng và không trùng.')
    if not isinstance(rows, list):
        raise TypeInferenceError('INVALID_ROWS', 'Dữ liệu phải là danh sách bản ghi.')
    for number, row in enumerate(rows, 1):
        if not isinstance(row, list) or len(row) != len(header):
            raise TypeInferenceError('INVALID_ROW', f'Bản ghi {number} sai số lượng cột.', number)
        if any(value is not None and not isinstance(value, str) for value in row):
            raise TypeInferenceError('INVALID_VALUE', f'Bản ghi {number} phải chứa chuỗi nguyên bản hoặc null.', number)
    result = []
    for index, name in enumerate(header):
        kinds = set()
        missing = 0
        for row in rows:
            value = row[index]
            if value is None or not value.strip():
                missing += 1
            else:
                kinds.add(classify(value))
        proposed = ('unknown' if not kinds else next(iter(kinds)) if len(kinds) == 1
                    else 'decimal' if kinds <= {'integer', 'decimal'} else 'text')
        result.append({'column_name': name, 'position': index + 1, 'inferred_type': proposed,
                       'non_missing_count': len(rows) - missing, 'missing_count': missing})
    return result
