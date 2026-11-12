import csv

import pytest

from app.services.csv_reader import CSVValidationError, MAX_FILE_BYTES, parse_csv


@pytest.fixture(params=[
    (b"a,b\n001,NULL\n", ["a", "b"], [["001", "NULL"]]),
    ("tên, note \r\nTiếng Việt,  giữ nguyên  \r\n".encode(), ["tên", " note "], [["Tiếng Việt", "  giữ nguyên  "]]),
    (b'\xef\xbb\xbfa,b\n1,2', ["a", "b"], [["1", "2"]]),
    (b'a,b,c\n"x,y","a""b","one\r\n\r\ntwo"\n', ["a", "b", "c"], [["x,y", 'a"b', "one\r\n\r\ntwo"]]),
    (b"a,b,c\n,,\n", ["a", "b", "c"], [["", "", ""]]),
    (b'a\n""\n', ["a"], [[""]]),
    (b'A,a, a\n1,2,3\n', ["A", "a", " a"], [["1", "2", "3"]]),
    (b'a\r1\r', ["a"], [["1"]]),
])
def valid_csv(request):
    """Each fixture explicitly specifies bytes, header and expected rows."""
    return request.param


def test_original_values_and_order(valid_csv):
    content, header, rows = valid_csv
    result = parse_csv(content)
    assert result.header == header
    assert result.rows == rows
    assert result.row_count == len(rows)
    assert result.file_size_bytes == len(content)


@pytest.fixture(params=[
    (b"", "EMPTY_FILE", None),
    (b"\xef\xbb\xbf", "EMPTY_FILE", None),
    (b"a,b\n", "NO_RECORDS", None),
    (b"a,b", "NO_RECORDS", None),
    (b"a\n\xff", "INVALID_ENCODING", None),
    (b"\n", "EMPTY_HEADER", None),
    (b",b\n1,2", "EMPTY_HEADER", None),
    (b"  ,b\n1,2", "EMPTY_HEADER", None),
    (b"a,a\n1,2", "DUPLICATE_HEADER", None),
    (b"a,b\n1", "COLUMN_COUNT_MISMATCH", 1),
    (b"a,b\n1,2,3", "COLUMN_COUNT_MISMATCH", 1),
    (b"a\n\n", "BLANK_RECORD", 1),
    (b"a\r\n1\r\n\r\n", "BLANK_RECORD", 2),
    (b'a\n"one\ntwo"\n\n', "BLANK_RECORD", 2),
    (b'a\n"one\ntwo"\nx,y', "COLUMN_COUNT_MISMATCH", 2),
    (b'a\n"unclosed', "INVALID_CSV_SYNTAX", 1),
    (b'a\n"closed"x', "INVALID_CSV_SYNTAX", 1),
    (b'a\nx"y', "INVALID_CSV_SYNTAX", 1),
    (b'a\n"x" "y"', "INVALID_CSV_SYNTAX", 1),
    (b'"bad\n', "INVALID_CSV_SYNTAX", None),
    (b'a\x00\n1', "NUL_CHARACTER", None),
    (b'a\n"one\ntwo"\nx\x00', "NUL_CHARACTER", 2),
])
def invalid_csv(request):
    return request.param


def test_error_code_and_logical_record_number(invalid_csv):
    content, code, row_number = invalid_csv
    with pytest.raises(CSVValidationError) as caught:
        parse_csv(content)
    assert caught.value.code == code
    assert caught.value.row_number == row_number
    assert str(caught.value) == caught.value.message
    assert caught.value.message
    if row_number is not None:
        assert caught.value.message.startswith(f"Bản ghi {row_number}:")


def test_exact_byte_limit_and_large_field():
    content = b"a\n" + b"x" * (MAX_FILE_BYTES - 2)
    previous = csv.field_size_limit()
    result = parse_csv(content)
    assert result.header == ["a"]
    assert result.rows == [["x" * (MAX_FILE_BYTES - 2)]]
    assert result.file_size_bytes == MAX_FILE_BYTES
    assert result.row_count == 1
    assert csv.field_size_limit() == previous
    with pytest.raises(CSVValidationError) as caught:
        parse_csv(content + b"x")
    assert caught.value.code == "FILE_TOO_LARGE"
    assert caught.value.row_number is None


def test_record_limit():
    content = b"a\n" + b"001\n" * 10_000
    result = parse_csv(content)
    assert result.header == ["a"]
    assert result.rows == [["001"]] * 10_000
    assert result.row_count == 10_000
    assert result.file_size_bytes == len(content)
    with pytest.raises(CSVValidationError) as caught:
        parse_csv(content + b"001\n")
    assert caught.value.code == "TOO_MANY_ROWS"
    assert caught.value.row_number == 10_001
