from copy import deepcopy
import json
from pathlib import Path
import pytest
from app.services.quality_engine import check_quality, validate_rules, QualityInputError, ENGINE_VERSION
from app.services.quality_trend import fingerprint
from app.services.csv_reader import parse_csv


def rule(values=None, identifier=1):
    return {'rule_id': identifier, 'rule_type': 'allowed_values', 'columns': ['status'], 'config': {'values': ['NEW', 'DONE', 'HOLD'] if values is None else values}}


def validate(config):
    candidate = rule(); candidate['config'] = config
    return validate_rules(['status'], [candidate])


@pytest.mark.parametrize('config', [{}, None, [], {'values': None}, {'values': 'NEW'}, {'values': []}, {'values': [None]}, {'values': [1]}, {'values': [True]}, {'values': [[]]}, {'values': ['']}, {'values': [' \t\n']}, {'values': ['NEW','NEW']}, {'values': ['NEW'], 'extra': 1}, {'values': ['x'*257]}, {'values': ['\ud800']}, {'values': [str(i) for i in range(101)]}])
def test_invalid_config(config):
    with pytest.raises(QualityInputError) as exc: validate(config)
    assert exc.value.code == 'INVALID_CONFIG'


def test_boundaries_and_compact_utf8_budget():
    assert validate({'values': ['x']})
    assert validate({'values': [str(i) for i in range(100)]})
    assert validate({'values': ['😀'*256]})  # 256 code points / 1024 bytes
    with pytest.raises(QualityInputError): validate({'values': ['😀'*257]})
    # Compact JSON is exactly 16384 bytes, all elements individually valid.
    values = [chr(65+i)+'x'*255 for i in range(63)] + ['z'*51]
    assert len(json.dumps({'values':values},ensure_ascii=False,separators=(',',':')).encode()) == 16384
    assert validate({'values':values})
    values[-1] += 'z'
    with pytest.raises(QualityInputError, match='16 KiB'): validate({'values':values})
    with pytest.raises(QualityInputError, match='16 KiB'): validate({'values':['😀'*256+str(i) for i in range(17)]})
    assert validate({'values':['NEW','new',' NEW','NEW ','é','e\u0301']})


@pytest.mark.parametrize('columns',[[],['missing'],['status','status'],['status','other']])
def test_columns(columns):
    r=rule();r['columns']=columns
    with pytest.raises(QualityInputError): validate_rules(['status','other'],[r])


def test_exact_unicode_missing_and_originals():
    rows=[[v] for v in ['NEW','new',' NEW','NEW ','é','e\u0301','😀',None,'',' \t','NULL',1,True]]
    rules=[rule(['NEW','é','😀'])]; original=deepcopy((rows,rules))
    result=check_quality(['status'],rows,rules)
    assert [e['row_number'] for e in result['errors']] == [2,3,4,6,11,12,13]
    assert all(e['code']=='ALLOWED_VALUE_NOT_IN_SET' and 'NEW' in e['message'] for e in result['errors'])
    assert (rows,rules)==original
    combined=check_quality(['status'],rows,[*rules,rule(['NEW'],2),{'rule_id':3,'rule_type':'required','columns':['status'],'config':{}}])
    assert combined['error_row_count']==12 and combined['violation_count']==19
    assert ENGINE_VERSION=='quality-v6'


def test_parser_predeclared_demo_and_snapshot_set_fingerprint():
    samples=Path(__file__).resolve().parents[1]/'samples'
    expected=json.loads((samples/'allowed_values_qt03a_expected.json').read_text())
    parsed=parse_csv((samples/'allowed_values_qt03a.csv').read_bytes())
    assert parsed.rows==expected['rows'] and parsed.row_count==10
    result=check_quality(parsed.header,parsed.rows,[rule()])
    assert (result['error_row_count'],result['violation_count'],result['error_row_rate'])==(5,5,50)
    assert [e['row_number'] for e in result['errors']]==[4,5,6,9,10]
    r=rule(['NEW','é','e\u0301']); before=deepcopy(r)
    assert fingerprint([r])==fingerprint([rule(list(reversed(r['config']['values'])))])
    assert r==before and fingerprint([r]).startswith('rules-v2:')
    for values in (['new','é','e\u0301'],[' NEW','é','e\u0301'],['NEW','é'],['NEW','e\u0301']):
        assert fingerprint([r])!=fingerprint([rule(values)])
    assert fingerprint([r])!=fingerprint([r,r])
