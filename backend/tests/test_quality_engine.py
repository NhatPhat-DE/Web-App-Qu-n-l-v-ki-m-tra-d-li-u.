from copy import deepcopy
from decimal import Decimal

import pytest

from app.services.quality_engine import QualityInputError, check_quality


def rule(kind, columns=None, config=None, identifier="r"):
    return {"rule_id": identifier, "rule_type": kind, "columns": columns or ["a"], "config": config or {}}


def test_required_original_values():
    rows = [[None], [""], [" \t"], ["NULL"], ["0"], [0], [False]]
    result = check_quality(["a"], rows, [rule("required")])
    assert result["error_row_count"] == result["violation_count"] == 3
    assert result["errors"] == [
        {"rule_id": "r", "rule_type": "required", "row_number": number, "columns": ["a"],
         "values": [value], "code": "REQUIRED_MISSING", "message": "Giá trị bắt buộc đang thiếu."}
        for number, value in [(1, None), (2, ""), (3, " \t")]]


def test_full_expected_errors_and_immutable_input():
    header = ["a", "amount"]
    rows = [["", "101"], ["ok", "-1"], ["x", "0"], ["y", "100"]]
    rules = [rule("required", identifier="required-a"), rule("numeric_range", ["amount"], {"min": "0", "max": "100"}, "range")]
    original = deepcopy((header, rows, rules))
    result = check_quality(header, rows, rules)
    assert result == {"row_count": 4, "error_row_count": 2, "violation_count": 3, "error_row_rate": 50.0, "errors": [
        {"rule_id": "required-a", "rule_type": "required", "row_number": 1, "columns": ["a"], "values": [""], "code": "REQUIRED_MISSING", "message": "Giá trị bắt buộc đang thiếu."},
        {"rule_id": "range", "rule_type": "numeric_range", "row_number": 1, "columns": ["amount"], "values": ["101"], "code": "NUMERIC_OUT_OF_RANGE", "message": "Giá trị nằm ngoài khoảng đóng cho phép."},
        {"rule_id": "range", "rule_type": "numeric_range", "row_number": 2, "columns": ["amount"], "values": ["-1"], "code": "NUMERIC_OUT_OF_RANGE", "message": "Giá trị nằm ngoài khoảng đóng cho phép."}]}
    assert (header, rows, rules) == original


@pytest.mark.parametrize("rows,columns,expected", [
    ([["x"], ["x"], ["y"], ["y"], ["y"]], ["a"], [1, 2, 3, 4, 5]),
    ([["x"], ["X"], [" x"], [None], [None], [""], [" "], [0], [False]], ["a"], []),
    ([["a|b", "c"], ["a", "b|c"], ["x", "y"], ["x", "y"], ["x", " "], ["x", None]], ["a", "b"], [3, 4]),
])
def test_unique_groups(rows, columns, expected):
    result = check_quality(columns, rows, [rule("unique", columns)])
    assert result["errors"] == [
        {"rule_id": "r", "rule_type": "unique", "row_number": number, "columns": columns,
         "values": rows[number - 1], "code": "UNIQUE_DUPLICATE", "message": "Giá trị hoặc tổ hợp giá trị bị trùng."}
        for number in expected]
    assert result["violation_count"] == len(expected)


@pytest.mark.parametrize("value,code", [
    ("0", None), ("100", None), (" 1.25 ", None), ("1e2", None), (".5", None),
    (Decimal("0.1"), None), (0, None), ("", None), (None, None),
    ("-0.01", "NUMERIC_OUT_OF_RANGE"), ("100.00000000000000000001", "NUMERIC_OUT_OF_RANGE"),
    ("1,000", "NUMERIC_INVALID"), (False, "NUMERIC_INVALID"), ("NaN", "NUMERIC_INVALID"),
    ("Infinity", "NUMERIC_INVALID"), (float("inf"), "NUMERIC_INVALID"), ("1_0", "NUMERIC_INVALID"),
    ("abc", "NUMERIC_INVALID"), ("NULL", "NUMERIC_INVALID"), ("1 0", "NUMERIC_INVALID"),
])
def test_numeric(value, code):
    result = check_quality(["a"], [[value]], [rule("numeric_range", config={"min": 0, "max": 100})])
    assert result["violation_count"] == (0 if code is None else 1)
    if code is None:
        assert result["errors"] == []
    else:
        assert result["errors"][0]["code"] == code
        assert result["errors"][0]["values"] == [value]


@pytest.mark.parametrize("bad", [
    rule("unknown"), rule("required", ["missing"]), rule("unique", ["a", "a"]),
    rule("required", ["a", "b"]), rule("numeric_range", ["a", "b"], {"min": 0, "max": 1}),
    rule("numeric_range", config={"min": 2, "max": 1}),
    rule("numeric_range", config={"min": "NaN", "max": 1}),
    rule("numeric_range", config={"min": 0}), rule("numeric_range", config={"min": False, "max": 1}),
    {"rule_id": "r", "rule_type": "unique", "columns": []},
])
def test_bad_rules_rejected_before_running(bad):
    with pytest.raises(QualityInputError):
        check_quality(["a", "b"], [["", ""]], [rule("required"), bad])


@pytest.mark.parametrize("header,rows,rules,code", [
    (["a"], [], [rule("required")], "EMPTY_DATA"),
    (["a"], [["x"]], [], "NO_RULES"),
    (["a"], [["x"], []], [rule("required")], "INVALID_ROW"),
    (["a"], [["x", "y"]], [rule("required")], "INVALID_ROW"),
    (["a", "a"], [["x", "y"]], [rule("required")], "INVALID_HEADER"),
    (["a"], [[{}]], [rule("required")], "INVALID_VALUE"),
    (["a"], [["x"]], [rule("required"), rule("unique")], "INVALID_RULE_ID"),
])
def test_invalid_input(header, rows, rules, code):
    with pytest.raises(QualityInputError) as error:
        check_quality(header, rows, rules)
    assert error.value.code == code


def test_equal_decimal_bounds_and_rule_order():
    assert check_quality(["a"], [["0.100000000000000000000"]], [rule("numeric_range", config={"min": "0.1", "max": "0.1"})])["errors"] == []
    result = check_quality(["a"], [["x"], ["x"]], [rule("unique", identifier="second"), rule("unique", identifier="first")])
    assert [(error["row_number"], error["rule_id"]) for error in result["errors"]] == [(1, "second"), (1, "first"), (2, "second"), (2, "first")]
