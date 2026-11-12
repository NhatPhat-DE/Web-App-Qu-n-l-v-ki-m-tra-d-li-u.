import csv
import io
import re
from dataclasses import dataclass
from threading import Lock

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
_FIELD_LIMIT_LOCK = Lock()
# csv.reader(strict=True) still permits quotes inside unquoted fields.
# Validate the consumed record's quote syntax; parsing remains csv.reader's job.
_FIELD = r'(?:"[^"]*(?:""[^"]*)*"|[^",\r\n]*)'
_RECORD = re.compile(_FIELD + r'(?:,' + _FIELD + r')*(?:\r\n|\r|\n)?\Z')


@dataclass
class ParsedCSV:
    header: list[str]
    rows: list[list[str]]
    row_count: int
    file_size_bytes: int


class CSVValidationError(ValueError):
    def __init__(self, code: str, message: str, row_number: int | None = None):
        self.code = code
        self.row_number = row_number
        self.message = message if row_number is None else f"Bản ghi {row_number}: {message}"
        super().__init__(self.message)


def parse_csv(content: bytes) -> ParsedCSV:
    """Return original CSV strings or a stable, localized validation error."""
    size = len(content)
    if size > MAX_FILE_BYTES:
        raise CSVValidationError("FILE_TOO_LARGE", "File vượt giới hạn 5 MiB.")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CSVValidationError("INVALID_ENCODING", "File phải dùng UTF-8 hoặc UTF-8 BOM.") from None
    if not decoded:
        raise CSVValidationError("EMPTY_FILE", "File CSV rỗng, không có header.")

    # Temporarily lift the stdlib's default 128 KiB field limit to our file limit.
    with _FIELD_LIMIT_LOCK:
        previous_limit = csv.field_size_limit(MAX_FILE_BYTES)
        try:
            return _parse(decoded, size)
        finally:
            csv.field_size_limit(previous_limit)


def _parse(decoded: str, size: int) -> ParsedCSV:
    stream = io.StringIO(decoded, newline="")
    reader = csv.reader(stream, delimiter=",", strict=True)
    header: list[str] | None = None
    rows: list[list[str]] = []
    while True:
        row_number = None if header is None else len(rows) + 1
        start = stream.tell()
        try:
            record = next(reader)
        except StopIteration:
            break
        except csv.Error:
            raise CSVValidationError("INVALID_CSV_SYNTAX", "Cú pháp CSV hoặc dấu ngoặc kép không hợp lệ.", row_number) from None
        raw_record = decoded[start:stream.tell()]
        if "\x00" in raw_record:
            raise CSVValidationError("NUL_CHARACTER", "CSV chứa ký tự NUL không được hỗ trợ.", row_number)
        if not _RECORD.fullmatch(raw_record):
            raise CSVValidationError("INVALID_CSV_SYNTAX", "Cú pháp CSV hoặc dấu ngoặc kép không hợp lệ.", row_number)
        if header is None:
            if not record or any(not name.strip() for name in record):
                raise CSVValidationError("EMPTY_HEADER", "Tên cột không được rỗng hoặc chỉ có khoảng trắng.")
            if len(set(record)) != len(record):
                raise CSVValidationError("DUPLICATE_HEADER", "Tên cột bị trùng nguyên bản.")
            header = record
            continue
        if not record:
            raise CSVValidationError("BLANK_RECORD", "Không được có dòng vật lý hoàn toàn trống ngoài trường có ngoặc kép.", row_number)
        if len(record) != len(header):
            raise CSVValidationError("COLUMN_COUNT_MISMATCH", f"Có {len(record)} cột, cần {len(header)} cột.", row_number)
        if len(rows) == MAX_ROWS:
            raise CSVValidationError("TOO_MANY_ROWS", "File vượt giới hạn 10.000 bản ghi.", row_number)
        rows.append(record)
    if not rows:
        raise CSVValidationError("NO_RECORDS", "CSV phải có ít nhất một bản ghi ngoài header.")
    return ParsedCSV(header=header, rows=rows, row_count=len(rows), file_size_bytes=size)
