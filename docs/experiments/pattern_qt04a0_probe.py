"""QT-04A0 feasibility probe only; no product imports, database or network.
Run with the dedicated Windows CPython 3.11 RE2 trial virtualenv.
Every stress case runs in a spawned process with a parent deadline.
"""
import ctypes
from ctypes import wintypes
import hashlib
import importlib.metadata
import json
import multiprocessing as mp
from pathlib import Path
import platform
import statistics
import struct
import sys
import time
import re2

MIB = 1024 * 1024

def memory():
    class Counters(ctypes.Structure):
        _fields_ = [('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)] + [(key,ctypes.c_size_t) for key in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
    counters= Counters();counters.cb=ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):raise ctypes.WinError(ctypes.get_last_error())
    return {key:getattr(counters,key) for key in ('WorkingSetSize','PeakWorkingSetSize','PrivateUsage','PeakPagefileUsage')}

def options(budget=8*MIB):
    opt=re2.Options();opt.max_mem=budget;opt.log_errors=False;opt.case_sensitive=True;opt.dot_nl=False
    return opt

def child(conn,mode,data):
    try:
        if mode=='bench':
            pattern,n=data
            expression=re2.compile(pattern,options=options())
            value='a'*n+'!'
            durations=[]
            for _ in range(5):
                started=time.perf_counter();matched=expression.fullmatch(value) is not None;durations.append(time.perf_counter()-started)
                assert not matched
            conn.send({'median_seconds':statistics.median(durations),'samples_seconds':durations,'input_codepoints':len(value),'memory':memory()})
        elif mode=='memory':
            count,budget=data
            before=memory()
            # Retain distinct compiled expressions; total process memory is not one RE2 budget.
            expressions=[re2.compile(f'[a-z]{{1000}}x{i}',options=options(budget)) for i in range(count)]
            for i,expression in enumerate(expressions):assert expression.fullmatch('a'*1000+'x'+str(i)) is not None
            conn.send({'count':len(expressions),'per_pattern_max_mem':budget,'before':before,'after':memory()})
        elif mode=='python_re_compare':
            import re
            expression=re.compile(data);value='a'*4096+'!'
            conn.send({'ready':True,'engine':'Python re isolated comparison','pattern':data,'input_codepoints':len(value)})
            expression.fullmatch(value)
            conn.send({'unexpectedly_completed':True})
        elif mode=='cancel':
            expression=re2.compile('(a|aa)+$',options=options())
            value='a'*(4*MIB)+'!'
            conn.send({'ready':True,'memory':memory()})
            while True:expression.fullmatch(value)
        else:raise ValueError(mode)
    except BaseException as error:
        conn.send({'error_type':type(error).__name__,'error':str(error)})
    finally:conn.close()

def invoke(mode,data=None,deadline=10):
    ctx=mp.get_context('spawn');parent,worker=ctx.Pipe(duplex=False)
    process=ctx.Process(target=child,args=(worker,mode,data));process.start();worker.close()
    try:
        if not parent.poll(deadline):
            process.terminate();process.join(3)
            raise AssertionError(f'{mode} exceeded {deadline}s deadline; killed={not process.is_alive()}')
        result=parent.recv()
        if mode in ('cancel','python_re_compare'):
            assert result.get('ready')
            # A continuous RE2-only workload, not a sleeping dummy process.
            process.join(0.15);assert process.is_alive()
            started=time.perf_counter();process.terminate();process.join(3)
            result.update({'terminate_join_seconds':time.perf_counter()-started,'exitcode':process.exitcode,'alive_after_join':process.is_alive()})
            assert not process.is_alive() and process.exitcode != 0
        else:
            process.join(3);assert not process.is_alive() and process.exitcode==0
            assert 'error' not in result,result
        return result
    finally:
        if process.is_alive():process.kill();process.join(3)
        parent.close();process.close()

def main():
    assert sys.platform=='win32' and sys.version_info[:2]==(3,11)
    report={'environment':{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'windows_version':list(sys.getwindowsversion()),'machine':platform.machine(),'bits':struct.calcsize('P')*8,'package':'google-re2','version':importlib.metadata.version('google-re2'),'default_max_mem':re2.Options().max_mem},'semantics':[],'compile':[],'budgets':[],'benchmarks':[],'memory':[],'cancellation':[],'traditional_engine_comparison':[]}
    cases=[
        ('[A-Z]{2}-[0-9]{4}','AB-1234',True),('[A-Z]{2}-[0-9]{4}','ab-1234',False),
        ('a','a\n',False),('a$','a\n',False),('^a$','a\n',False),('a','aa',False),('a',' a',False),('a','a ',False),
        (r'\d+','123',True),(r'\d+','１２３',False),(r'\d+','١٢٣',False),
        (r'\w+','Az_09',True),(r'\w+','é',False),(r'\w+','中',False),
        (r'\s+',' \t\r\n\f',True),(r'\s','\v',False),(r'\s','\u00a0',False),
        ('é','é',True),('é','e\u0301',False),('.','😀',True),('.','中',True),('.','\n',False),('[\n]','\n',True),
        ('a*','',True),('','',True),('a+','',False),(' +','   ',True),
        # Library acceptance is broader than the proposed product dialect.
        ('(?i)abc','ABC',True),(r'\p{L}+','TiếngViệt',True),('[[:alpha:]]+','ABC',True),
    ]
    for pattern,value,expected in cases:
        matched=re2.compile(pattern,options=options()).fullmatch(value) is not None
        report['semantics'].append({'pattern':pattern,'value':value,'expected':expected,'actual':matched})
        assert matched==expected,(pattern,repr(value),matched,expected)
    for pattern in [r'(a)\1','(?=a)a','(?!a)b','(?<=a)b','(?<!a)b','[','a{1001}',r'\Z',r'\ud800']:
        try:
            re2.compile(pattern,options=options());outcome={'pattern':pattern,'compiled':True}
        except Exception as error:outcome={'pattern':pattern,'compiled':False,'error_type':type(error).__name__,'error':str(error)}
        report['compile'].append(outcome)
    # Actual lone surrogate, independently of the literal unsupported escape above.
    try:re2.compile('\ud800',options=options());raise AssertionError('surrogate accepted')
    except UnicodeEncodeError as error:report['compile'].append({'pattern':'lone surrogate','compiled':False,'error_type':type(error).__name__})
    assert all(not item['compiled'] for item in report['compile'])
    for pattern in ['a','[a-z]{1000}','([a-z]{1000})'*30]:
        for budget in [0,1024,65536,8*MIB]:
            try:
                re2.purge();started=time.perf_counter()
                compiled=re2.compile(pattern,options=options(budget));elapsed=time.perf_counter()-started;row={'pattern':pattern,'max_mem':budget,'compiled':True,'programsize':compiled.programsize,'compile_seconds':elapsed}
                assert compiled.options.max_mem==budget
            except re2.error as error:row={'pattern':pattern,'max_mem':budget,'compiled':False,'error':str(error)}
            report['budgets'].append(row)
    assert any(not row['compiled'] and row['max_mem']==1024 for row in report['budgets'])
    assert any(row['compiled'] and row['max_mem']==8*MIB for row in report['budgets'])
    for pattern in ['(a+)+$','(a|aa)+$']:
        for n in [4096,65536,MIB]:report['benchmarks'].append({'pattern':pattern,**invoke('bench',(pattern,n))})
    for count in [1,10,100]:report['memory'].append(invoke('memory',(count,8*MIB)))
    for _ in range(3):report['cancellation'].append(invoke('cancel'))
    for pattern in ['(a+)+$','(a|aa)+$']:report['traditional_engine_comparison'].append(invoke('python_re_compare',pattern))
    report['summary']={'semantic_cases':len(report['semantics']),'compile_rejections':len(report['compile']),'budget_probes':len(report['budgets']),'adversarial_cases':len(report['benchmarks']),'memory_processes':len(report['memory']),'terminated_processes':len(report['cancellation']),'traditional_comparisons_killed':len(report['traditional_engine_comparison']),'status':'PASS','note':'Feasibility only; no product dialect validator, worker scheduler or hard OS memory limit implemented.'}
    output=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).with_name('pattern_qt04a0_results.json')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['summary']))

if __name__=='__main__':main()
