"""QT-04A actual production-worker timings; no database or network."""
import json
from pathlib import Path
import platform
import sys
import time
from importlib.metadata import version
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.pattern_worker import preflight, admission, evaluate


def main():
    workloads=[('adversarial_nested_50MiB', '(a+)+$', 12800,4096,1),
               ('adversarial_alternation_50MiB','(a|aa)+$',12800,4096,1),
               ('ten_rules_50MiB','a+',1280,4096,10),
               ('large_result_800000_bytes','y',100000,1,1)]
    results=[]
    for name,pattern,count,length,rule_count in workloads:
        rows=[['a'*(length-1)+'!']] * count
        rules=[{'rule_id':i,'rule_type':'pattern','columns':['value'],'config':{'pattern':pattern,'dialect':'re2-v1'}} for i in range(rule_count)]
        start=time.perf_counter();patterns=preflight(['value'],rows,rules);preflight_seconds=time.perf_counter()-start
        with admission(True):
            start=time.perf_counter();failures=evaluate(['value'],rows,patterns);elapsed=time.perf_counter()-start
        assert sum(map(len,failures.values()))==count*rule_count
        results.append({'workload':name,'rows':count,'rule_count':rule_count,'input_codepoints_per_value':length,'actual_match_utf8_bytes':count*length*rule_count,'mismatches':count*rule_count,'binary_result_bytes':count*rule_count*8,'phase_seconds_including_cleanup':elapsed,'preflight_seconds':preflight_seconds})
    data={'platform':platform.platform(),'python':platform.python_version(),'google_re2':version('google-re2'),'start_method':'spawn','deadline_seconds':5,'max_mem_per_expression':8*1024*1024,'hard_process_ram_cap':False,'single_measurement_not_throughput_guarantee':True,'workloads':results}
    path=Path(__file__).resolve().parents[2]/'docs/experiments/pattern_qt04a_benchmark.json'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
