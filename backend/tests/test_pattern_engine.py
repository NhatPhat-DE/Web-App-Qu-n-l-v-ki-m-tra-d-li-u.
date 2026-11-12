import copy
import multiprocessing
import os
from pathlib import Path
import tempfile
import time

import pytest
from app.services.pattern_dialect import validate_config, PatternSyntaxError
from app.services import pattern_worker as worker
from app.services.quality_engine import check_quality, validate_rules, QualityInputError
from app.services.quality_trend import fingerprint


def rule(pattern='SP[0-9]{4}', identifier=1):
    return {'rule_id': identifier, 'rule_type': 'pattern', 'columns': ['value'],
            'config': {'pattern': pattern, 'dialect': 're2-v1'}}


@pytest.mark.parametrize('pattern', [r'[A-Z]{2}-[0-9]{4}', r'(a|aa)+$', r'(a+)+$',
    r'^a.*$', r'\d\w\s', r'[\d_]+', r'[a-zA-Z0-9-]', r'[^x]', r'\[\]\{\}\(\)\+\*\?\|\.\^\$\\\-',
    r'a{0}', r'a{1000}', r'a{1,}', r'a{0,1000}', r'\n\r\t\f\v', 'é|e\u0301', '(a|)', '()'])
def test_positive_grammar(pattern):
    assert validate_config({'pattern': pattern, 'dialect': 're2-v1'}) == pattern


@pytest.mark.parametrize('pattern', [r'(?=x)', r'(?!x)', r'(?<=x)', r'(?<!x)', r'(?:x)', r'(?i)x',
    r'(?P<n>x)', r'(x)\1', r'\p{L}', r'\P{L}', r'\D', r'\W', r'\S', r'\b', r'\x41', r'\141',
    r'\Qx\E', r'\u0041', r'\z', r'\Z', r'[[:alpha:]]', r'[a-\d]', r'[z-a]', r'[]', r'[x',
    r'a{1001}', r'a{1,1001}', r'a{2,1}', r'a{01}', r'a{,2}', r'a**', r'a+?', r'a++', 'a)', '(a', chr(92), '^*', 'a}', '\x00'])
def test_reject_outside_grammar(pattern):
    with pytest.raises(PatternSyntaxError): validate_config({'pattern':pattern,'dialect':'re2-v1'})


@pytest.mark.parametrize('config', [{}, None, [], {'pattern':'x'}, {'pattern':'x','dialect':None},
    {'pattern':None,'dialect':'re2-v1'}, {'pattern':1,'dialect':'re2-v1'}, {'pattern':'x','dialect':'RE2'},
    {'pattern':'x','dialect':'re2-v1','flags':0}, {'pattern':'','dialect':'re2-v1'},
    {'pattern':'x'*513,'dialect':'re2-v1'}, {'pattern':'\ud800','dialect':'re2-v1'}], ids=lambda v:str(type(v)))
def test_config_invalid(config):
    with pytest.raises(QualityInputError): validate_rules(['value'],[{**rule(),'config':config}])


def test_pattern_size_boundaries():
    validate_config({'pattern':'😀'*512,'dialect':'re2-v1'})  # 2048 UTF-8 bytes
    with pytest.raises(PatternSyntaxError): validate_config({'pattern':'😀'*513,'dialect':'re2-v1'})
    # Config budget cannot be approached with the exact two bounded fields.
    for columns in ([],['missing'],['value','value']):
        with pytest.raises(QualityInputError): validate_rules(['value'],[{**rule(),'columns':columns}])


def test_real_spawn_fullmatch_missing_raw_and_ascii():
    rows=[[v] for v in ['SP0001','SP9999','sp0001','SP123',' SP0001','SP0001 ','SP00001','',None,'   ','NULL','SP0001\n']]
    before=copy.deepcopy(rows)
    result=check_quality(['value'],rows,[rule()])
    assert [e['row_number'] for e in result['errors']]==[3,4,5,6,7,11,12]
    assert rows==before and all(e['code']=='PATTERN_MISMATCH' and 'SP[0-9]{4}' in e['message'] for e in result['errors'])
    checks=[(r'\d+',['12','１２'],[2]),(r'\w+',['a_1','é'],[2]),
            (r'a\sb',['a b','a\tb','a\nb','a\vb','a\u00a0b'],[4,5]),
            ('é',['é','e\u0301'],[2]),('^a$',['a','a\n'],[2]),('a.*',['ab','a\nb'],[2])]
    for expression,values,errors in checks:
        assert [e['row_number'] for e in check_quality(['value'],[[v] for v in values],[rule(expression)])['errors']]==errors


def test_preflight_limits(monkeypatch):
    worker.preflight(['value'],[['x'*4096]],[rule()])
    worker.preflight(['value'],[['😀'*4096]],[rule()])
    for value in ['x'*4097,'😀'*4097]:
        with pytest.raises(worker.PatternError,match='4096') as exc: worker.preflight(['value'],[[value]],[rule()])
        assert exc.value.status==422 and exc.value.code=='PATTERN_VALUE_LIMIT'
    worker.preflight(['value'],[[' ' * 100000]],[rule()])  # missing is not matched
    worker.preflight(['value'],[['x']],[rule(identifier=i) for i in range(10)])
    with pytest.raises(worker.PatternError) as exc: worker.preflight(['value'],[['x']],[rule(identifier=i) for i in range(11)])
    assert exc.value.code=='PATTERN_RULE_LIMIT'
    monkeypatch.setattr(worker,'MAX_MATCH_BYTES',8)
    worker.preflight(['value'],[['abcd']],[rule(identifier=1),rule(identifier=2)])
    with pytest.raises(worker.PatternError) as exc: worker.preflight(['value'],[['abcde']],[rule(identifier=1),rule(identifier=2)])
    assert exc.value.code=='PATTERN_BYTE_BUDGET'


def hanging(folder):
    time.sleep(60)


def crashing(folder):
    os._exit(7)


@pytest.mark.parametrize('target,code',[(hanging,'PATTERN_TIMEOUT'),(crashing,'PATTERN_WORKER_FAILED')])
def test_timeout_crash_cleanup_and_retry(monkeypatch,target,code):
    # Windows spawn/import can exceed 0.8s under full-suite load. Crash detection
    # uses the production budget; the hanging-worker timeout still tests 0.8s.
    monkeypatch.setattr(worker,'DEADLINE_SECONDS',0.8 if target is hanging else 5)
    before={p.pid for p in multiprocessing.active_children()}
    with worker.admission(True):
        with pytest.raises(worker.PatternError) as exc: worker.evaluate(['value'],[['x']],[rule()],worker_target=target)
        assert exc.value.code==code
    assert {p.pid for p in multiprocessing.active_children()}==before
    monkeypatch.setattr(worker,'DEADLINE_SECONDS',5)
    assert check_quality(['value'],[['SP0001']],[rule()])['violation_count']==0


def test_large_ipc_and_adversarial():
    # >64 KiB output, so a join-before-drain Pipe implementation would hang.
    rows=[['a'*4095+'!'] for _ in range(12800)]  # exactly 50 MiB, at per-value cap
    for expression in ['(a+)+$','(a|aa)+$']:
        with worker.admission(True):
            failures=worker.evaluate(['value'],rows,[rule(expression)])
        assert len(failures[1])==12800
    with worker.admission(True):
        assert len(worker.evaluate(['value'],[['x']]*100000,[rule('y')])[1])==100000


def test_legacy_path_no_worker(monkeypatch):
    monkeypatch.setattr(worker,'evaluate',lambda *a,**k:pytest.fail('legacy worker'))
    assert check_quality(['value'],[['x']],[{'rule_id':1,'rule_type':'required','columns':['value'],'config':{}}])['violation_count']==0


def test_pattern_fingerprint_exact_and_duplicate():
    snapshot=[{'rule_type':'pattern','columns':['value'],'config':rule()['config']}]
    key=fingerprint(snapshot)
    assert key.startswith('rules-v2:') and fingerprint(snapshot*2)!=key
    assert fingerprint([{**snapshot[0],'config':{'dialect':'re2-v1','pattern':'SP[0-9]{4}'}}])==key
    for expression in ['sp[0-9]{4}',' SP[0-9]{4}','SP[0123456789]{4}','é','e\u0301']:
        assert fingerprint([{**snapshot[0],'config':{'dialect':'re2-v1','pattern':expression}}])!=key


def test_cancel_cleanup_and_retry():
    import threading
    cancellation=threading.Event()
    token=worker.CANCEL_EVENT.set(cancellation)
    timer=threading.Timer(0.25,cancellation.set)
    before={p.pid for p in multiprocessing.active_children()}
    timer.start()
    try:
        with worker.admission(True):
            with pytest.raises(worker.PatternError) as exc:
                worker.evaluate(['value'],[['x']],[rule()],worker_target=hanging)
            assert exc.value.code=='PATTERN_CANCELLED'
    finally:
        timer.cancel()
        worker.CANCEL_EVENT.reset(token)
    assert {p.pid for p in multiprocessing.active_children()}==before
    assert check_quality(['value'],[['SP0001']],[rule()])['violation_count']==0
