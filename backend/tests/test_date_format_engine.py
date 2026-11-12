from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path

import pytest

from app.services.csv_reader import parse_csv
from app.services.quality_engine import ENGINE_VERSION, QualityInputError, check_quality, validate_rules
from app.services.quality_execution import RunError
from app.services.quality_trend import fingerprint

FORMATS = ('YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY')


def rule(fmt='YYYY-MM-DD', identifier=1):
    return {'rule_id': identifier, 'rule_type': 'date_format', 'columns': ['event_date'], 'config': {'format': fmt}}


def spelling(iso, fmt):
    year, month, day = iso.split('-')
    return iso if fmt == 'YYYY-MM-DD' else f'{day}/{month}/{year}' if fmt == 'DD/MM/YYYY' else f'{month}/{day}/{year}'


@pytest.mark.parametrize('fmt', FORMATS)
@pytest.mark.parametrize('iso,code', [
    ('2000-02-29', None), ('1900-02-29', 'DATE_VALUE_INVALID'), ('2024-02-29', None),
    ('2023-02-29', 'DATE_VALUE_INVALID'), ('2026-04-31', 'DATE_VALUE_INVALID'),
    ('0001-01-01', None), ('9999-12-31', None), ('0000-01-01', 'DATE_VALUE_INVALID'),
    ('2026-00-10', 'DATE_VALUE_INVALID'), ('2026-13-01', 'DATE_VALUE_INVALID'),
    ('2026-01-00', 'DATE_VALUE_INVALID'), ('2026-01-32', 'DATE_VALUE_INVALID'),
])
def test_gregorian_dates_all_formats(fmt, iso, code):
    original = spelling(iso, fmt)
    result = check_quality(['event_date'], [[original]], [rule(fmt)])
    assert result['violation_count'] == (0 if code is None else 1)
    if code:
        error = result['errors'][0]
        assert error['code'] == code and error['values'] == [original]
        assert fmt in error['message']


@pytest.mark.parametrize('fmt', FORMATS)
@pytest.mark.parametrize('mutation', ['leading_space', 'trailing_space', 'newline', 'datetime', 'timezone', 'unicode_digits', 'short', 'wrong_separator'])
def test_full_original_spelling_not_permissive_date_parser(fmt, mutation):
    original = spelling('2026-01-02', fmt)
    value = {
        'leading_space': ' ' + original, 'trailing_space': original + ' ', 'newline': original + '\n',
        'datetime': original + 'T00:00:00', 'timezone': original + 'Z',
        'unicode_digits': original.translate(str.maketrans('0123456789', '０１２３４５６７８９')),
        'short': original[:-1], 'wrong_separator': original.replace('-', '/').replace('/', '.'),
    }[mutation]
    result = check_quality(['event_date'], [[value]], [rule(fmt)])
    assert len(result['errors']) == 1
    assert result['errors'][0]['code'] == 'DATE_FORMAT_MISMATCH'
    assert result['errors'][0]['values'] == [value]
    assert fmt in result['errors'][0]['message']


@pytest.mark.parametrize('fmt', FORMATS)
@pytest.mark.parametrize('value', [None, '', ' ', '\t\r\n', '\u00a0'])
def test_existing_missing_definition_skips_date_check(fmt, value):
    assert check_quality(['event_date'], [[value]], [rule(fmt)])['errors'] == []


@pytest.mark.parametrize('value', ['NULL', 'null', 'NaN', '2026-2-01', '026-01-01', '10000-01-01', '2026-01-01 00:00:00', 20260101, True, Decimal('2026')])
def test_non_missing_invalid_values_are_not_cast(value):
    result = check_quality(['event_date'], [[value]], [rule()])
    assert result['errors'][0]['code'] == 'DATE_FORMAT_MISMATCH'
    assert result['errors'][0]['values'] == [value]


@pytest.mark.parametrize('fmt,value,code', [
    ('DD/MM/YYYY', '01/02/2026', None), ('MM/DD/YYYY', '01/02/2026', None),
    ('DD/MM/YYYY', '13/02/2026', None), ('MM/DD/YYYY', '13/02/2026', 'DATE_VALUE_INVALID'),
    ('DD/MM/YYYY', '02/13/2026', 'DATE_VALUE_INVALID'), ('MM/DD/YYYY', '02/13/2026', None),
    ('DD/MM/YYYY', '1/02/2026', 'DATE_FORMAT_MISMATCH'), ('MM/DD/YYYY', '01/2/2026', 'DATE_FORMAT_MISMATCH'),
])
def test_ambiguous_dates_use_config_only(fmt, value, code):
    errors = check_quality(['event_date'], [[value]], [rule(fmt)])['errors']
    assert ([error['code'] for error in errors]) == ([] if code is None else [code])


@pytest.mark.parametrize('config', [
    {}, None, [], 'YYYY-MM-DD', {'format': None}, {'format': True}, {'format': 1},
    {'format': ['YYYY-MM-DD']}, {'format': {}}, {'format': '%Y-%m-%d'},
    {'format': 'DD/MM/YY'}, {'format': 'yyyy-mm-dd'}, {'format': ' YYYY-MM-DD '},
    {'format': 'YYYY-MM-DD', 'timezone': 'UTC'}, {'format': 'YYYY-MM-DD\x00'}, {'format': '\ud800'},
])
def test_strict_date_config(config):
    candidate = rule(); candidate['config'] = config
    with pytest.raises(QualityInputError) as exc:
        validate_rules(['event_date'], [candidate])
    assert exc.value.code == 'INVALID_CONFIG'


def test_config_budget_utf8_bytes_and_no_legacy_retroactive_limit():
    candidate = rule(); candidate['config'] = {'format': '界' * 6000}
    with pytest.raises(QualityInputError, match='16 KiB'):
        validate_rules(['event_date'], [candidate])
    legacy = {'rule_id': 2, 'rule_type': 'numeric_range', 'columns': ['event_date'],
              'config': {'min': '0' * 17000, 'max': '1'}}
    assert not check_quality(['event_date'], [[' 0.5 ']], [legacy])['errors']


@pytest.mark.parametrize('columns', [[], ['missing'], ['event_date', 'other'], ['event_date', 'event_date'], [None]])
def test_one_existing_column(columns):
    candidate = rule(); candidate['columns'] = columns
    with pytest.raises(QualityInputError) as exc:
        validate_rules(['event_date', 'other'], [candidate])
    assert exc.value.code == 'INVALID_COLUMNS'


def test_parser_and_written_answers_keep_empty_seventh_record_and_inputs():
    samples = Path(__file__).resolve().parents[1] / 'samples'
    expected = json.loads((samples / 'date_format_qt02a_expected.json').read_text(encoding='utf-8'))
    parsed = parse_csv((samples / 'date_format_qt02a.csv').read_bytes())
    assert parsed.row_count == 8 and parsed.rows[6] == [''] and parsed.rows == expected['rows']
    inputs = (parsed.header, parsed.rows, [rule()]); original = deepcopy(inputs)
    result = check_quality(*inputs)
    assert inputs == original
    assert (result['row_count'], result['error_row_count'], result['violation_count'], result['error_row_rate']) == (8, 5, 5, 62.5)
    assert [error['code'] for error in result['errors']] == [item['error_code'] for item in expected['violations']]
    rules = [rule(), rule('DD/MM/YYYY', 2), {'rule_id': 3, 'rule_type': 'required', 'columns': ['event_date'], 'config': {}}]
    combined = check_quality(parsed.header, parsed.rows, rules)
    assert (combined['error_row_count'], combined['violation_count']) == (8, 13)
    assert ENGINE_VERSION == 'quality-v6'


def test_fingerprint_keeps_old_v2_golden_and_exact_date_format():
    old = {'rule_type': 'data_type', 'columns': ['value'], 'config': {'type': 'integer'}}
    assert fingerprint([old]) == 'rules-v2:876ac2aba426af88f58eefe24f59d10b89f7b5055ce7e2059b28ad2cff284957'
    saved = json.loads((Path(__file__).resolve().parents[1] / 'samples/dataset-42-run-28-data-type-report.json').read_text(encoding='utf-8'))
    assert fingerprint(saved['rule_snapshot']) == 'rules-v2:d117607915d5ae940764ef39ac9089a141e8182b00a36f3fcb5b9d482aafef90'
    hashes = {fingerprint([rule(fmt)]) for fmt in FORMATS}
    assert len(hashes) == 3 and all(value.startswith('rules-v2:') for value in hashes)
    mixed = [old, rule()]
    assert fingerprint(mixed) == fingerprint([{**rule(), 'rule_id': 99, 'name': 'renamed'}, old])
    assert fingerprint(mixed) != fingerprint(mixed + [rule()])
    for config in ({}, {'format': None}, {'format': []}, {'format': '%Y-%m-%d'}, {'format': 'YYYY-MM-DD', 'extra': True}):
        with pytest.raises(RunError):
            fingerprint([{**rule(), 'config': config}])
