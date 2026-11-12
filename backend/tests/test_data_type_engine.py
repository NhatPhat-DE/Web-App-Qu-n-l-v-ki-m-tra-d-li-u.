from copy import deepcopy
from decimal import Decimal, localcontext

import pytest

from app.services.quality_engine import ENGINE_VERSION, QualityInputError, check_quality, validate_rules


def data_type_rule(data_type="integer", *, columns=None, config=None, identifier="type"):
    return {"rule_id": identifier, "rule_type": "data_type", "columns": ["a"] if columns is None else columns,
            "config": {"type": data_type} if config is None else config}


def check_value(data_type, value):
    return check_quality(["a"], [[value]], [data_type_rule(data_type)])


@pytest.mark.parametrize("value", ["0", "00", "0012", "+12", "-0", "-123", "+0", "9" * 10000])
def test_integer_ascii_spelling_without_int_conversion(value):
    assert check_value("integer", value)["errors"] == []


@pytest.mark.parametrize("value", [
    "1.0", "1e3", ".5", "1,000", "1_000", " 1", "1 ", "1\n", "1\t", "+", "--1", "1 0",
    "١٢", "１２", "²", "NULL", "NaN", "Infinity", "1\x00", 1, 0, 1.0, True, False, Decimal("12"),
])
def test_integer_rejects_non_contract_values_and_keeps_original(value):
    result = check_value("integer", value)
    assert result["violation_count"] == 1
    assert result["errors"][0]["code"] == "DATA_TYPE_INTEGER_INVALID"
    assert result["errors"][0]["values"] == [value]


@pytest.mark.parametrize("value", [
    "0", "01", "+12", "-0", "1.", ".5", "-.5", "-0.00", "+1.2e-3", "1E+3", "1e0",
    "1.23456789012345678901234567890123456789", "9" * 10000, "1e999999", "1e-999999",
])
def test_decimal_finite_syntax_without_precision_or_scale_checks(value):
    with localcontext() as context:
        context.prec = 2
        assert check_value("decimal", value)["errors"] == []


@pytest.mark.parametrize("value", [
    "NaN", "sNaN", "Infinity", "-Infinity", "inf", "1,5", "1,000", "1_0", " 1", "1 ", "1\n",
    ".", "+", "1e", "1e+", "١.٢", "１.２", "1.2.3", "NULL", "1\x00", 1, 1.25,
    float("inf"), True, False, Decimal("1.25"),
])
def test_decimal_rejects_invalid_spelling_and_non_strings(value):
    result = check_value("decimal", value)
    assert result["violation_count"] == 1
    assert result["errors"][0]["code"] == "DATA_TYPE_DECIMAL_INVALID"
    assert result["errors"][0]["values"] == [value]


@pytest.mark.parametrize("value", ["1e" + "9" * 1000, "1e-" + "9" * 1000])
def test_decimal_representation_error_is_one_violation_and_run_continues(value):
    result = check_quality(["a"], [[value], ["2.5"]], [data_type_rule("decimal")])
    assert result["row_count"] == 2
    assert result["error_row_count"] == result["violation_count"] == 1
    assert [(error["row_number"], error["code"]) for error in result["errors"]] == [
        (1, "DATA_TYPE_DECIMAL_INVALID")]


@pytest.mark.parametrize("value", ["true", "false"])
def test_boolean_exact_lowercase_strings(value):
    assert check_value("boolean", value)["errors"] == []


@pytest.mark.parametrize("value", [
    "TRUE", "False", "True", "FALSE", "1", "0", "yes", "no", " true", "false ", "true\n",
    "NULL", "true\x00", True, False, 1, 0, 1.0, Decimal("0"),
])
def test_boolean_rejects_other_strings_and_scalars(value):
    result = check_value("boolean", value)
    assert result["violation_count"] == 1
    assert result["errors"][0]["code"] == "DATA_TYPE_BOOLEAN_INVALID"
    assert result["errors"][0]["values"] == [value]


@pytest.mark.parametrize("data_type", ["integer", "decimal", "boolean"])
@pytest.mark.parametrize("value", [None, "", " ", "\t\n", "\u2003"])
def test_data_type_uses_existing_missing_definition(data_type, value):
    assert check_value(data_type, value)["errors"] == []


@pytest.mark.parametrize("config", [
    {}, {"type": "float"}, {"type": "Integer"}, {"type": " integer"}, {"type": "integer "},
    {"type": None}, {"type": True}, {"type": 1}, {"type": ["integer"]}, {"type": {"name": "integer"}},
    {"type": "integer", "scale": 2}, {"type": "integer\x00"}, {"type": "\ud800"},
    {"type": "integer", "extra": "x" * (16 * 1024)},
])
def test_data_type_config_is_strict_and_rejects_invalid_utf8(config):
    with pytest.raises(QualityInputError) as error:
        validate_rules(["a"], [data_type_rule(config=config)])
    assert error.value.code == "INVALID_CONFIG"


@pytest.mark.parametrize("config", [None, [], "integer", True, 1])
def test_data_type_config_rejects_non_objects_including_explicit_null(config):
    rule = data_type_rule()
    rule["config"] = config
    with pytest.raises(QualityInputError) as error:
        validate_rules(["a"], [rule])
    assert error.value.code == "INVALID_CONFIG"


def test_data_type_requires_config_and_applies_budget_only_to_new_type():
    rule = data_type_rule()
    del rule["config"]
    with pytest.raises(QualityInputError) as error:
        validate_rules(["a"], [rule])
    assert error.value.code == "INVALID_CONFIG"
    oversized = data_type_rule(config={"type": "integer", "extra": "x" * (16 * 1024)})
    with pytest.raises(QualityInputError, match="16 KiB"):
        validate_rules(["a"], [oversized])
    legacy = {"rule_id": "range", "rule_type": "numeric_range", "columns": ["a"],
              "config": {"min": "0" * (16 * 1024 + 1), "max": "1"}}
    assert check_quality(["a"], [[" 0.5 "]], [legacy])["errors"] == []


@pytest.mark.parametrize("columns", [[], ["missing"], ["a", "b"], ["a", "a"], "a", [None]])
def test_data_type_requires_exactly_one_existing_column(columns):
    with pytest.raises(QualityInputError) as error:
        validate_rules(["a", "b"], [data_type_rule(columns=columns)])
    assert error.value.code == "INVALID_COLUMNS"


def test_data_type_immutable_raw_values_and_distinct_error_rows():
    header = ["i", "d", "b"]
    rows = [["0012", ".5", "true"], ["1.0", "NaN", "TRUE"], ["NULL", " 1 ", "false"],
            [None, " \t", ""], ["", "2.123456789", "0"]]
    rules = [data_type_rule(kind, columns=[column], identifier=kind)
             for column, kind in zip(header, ["integer", "decimal", "boolean"])]
    rules.append({"rule_id": "required-i", "rule_type": "required", "columns": ["i"], "config": {}})
    original = deepcopy((header, rows, rules))
    result = check_quality(header, rows, rules)
    assert (header, rows, rules) == original
    assert result["row_count"] == 5
    assert result["error_row_count"] == 4
    assert result["violation_count"] == 8
    assert result["error_row_rate"] == 80.0
    assert [(error["row_number"], error["columns"], error["values"], error["code"]) for error in result["errors"]] == [
        (2, ["i"], ["1.0"], "DATA_TYPE_INTEGER_INVALID"),
        (2, ["d"], ["NaN"], "DATA_TYPE_DECIMAL_INVALID"),
        (2, ["b"], ["TRUE"], "DATA_TYPE_BOOLEAN_INVALID"),
        (3, ["i"], ["NULL"], "DATA_TYPE_INTEGER_INVALID"),
        (3, ["d"], [" 1 "], "DATA_TYPE_DECIMAL_INVALID"),
        (4, ["i"], [None], "REQUIRED_MISSING"),
        (5, ["b"], ["0"], "DATA_TYPE_BOOLEAN_INVALID"),
        (5, ["i"], [""], "REQUIRED_MISSING"),
    ]
    assert all(error["message"] for error in result["errors"])


def test_engine_version_advances_for_new_runs():
    assert ENGINE_VERSION == 'quality-v6'
