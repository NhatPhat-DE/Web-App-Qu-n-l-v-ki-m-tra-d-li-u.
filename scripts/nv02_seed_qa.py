"""Create only new, clearly named NV-02 QA data. Does not touch QA52/55."""
from pathlib import Path
import json,sys
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from sqlalchemy import create_engine,select
from app.config import get_database_url
from app.models import User
from app.services import issue_workflow as work
from app.services.dataset_import import import_dataset,import_version
from app.services.csv_reader import parse_csv
from app.services.data_batches import create_batch,patch_batch
from app.services.quality_rules import create_rule
from app.services.quality_execution import execute_run
from nv01_migrate import snapshot

RAW=b'id,part,amount,name\nA,X,-1,\nB,X,5,Bee\nC,X,20,Cee\n'
V2=b'id,part,amount,name\nC,X,8,Cee\nA,X,2,\nB,X,-2,Bee\n'
CLEAN=b'id,part,amount,name\nB,X,3,Bee\nC,X,8,Cee\nA,X,2,Able\n'
MISSING=b'id,part,amount,name\nB,X,3,Bee\nC,X,8,Cee\nA,,2,Able\n'
DUPLICATE=b'id,part,amount,name\nA,X,3,Bee\nC,X,8,Cee\nA,X,2,Able\n'
LOST=b'id,part,amount,name\nB,X,3,Bee\nC,X,8,Cee\n'

def main():
    folder=ROOT/'qa_test_data/nv02';folder.mkdir(parents=True,exist_ok=True)
    manifest_path=folder/'manifest.json'
    if manifest_path.exists():raise SystemExit('QA manifest already exists; refusing accidental duplicate seed.')
    engine=create_engine(get_database_url(),hide_parameters=True);before=snapshot(engine)
    with engine.connect() as c:
        user=c.execute(select(User).where(User.role=='admin',User.is_active).order_by(User.id)).mappings().first()
        if not user:raise SystemExit('An active admin is required; no accounts changed.')
        actor={'user_id':user['id'],'username':user['username'],'role':user['role']}
    for name,content in [('v1.csv',RAW),('v2-reordered.csv',V2),('v3-clean.csv',CLEAN),('missing-key.csv',MISSING),('duplicate-key.csv',DUPLICATE),('record-disappeared.csv',LOST)]: (folder/name).write_bytes(content)
    created=import_dataset(parse_csv(RAW),'nv02-v1.csv',dict(name='NV-02 QA — Vòng đời xử lý lỗi',owner='QA NV-02',source='Dữ liệu giả lập NV-02 riêng',description='Khóa tổ hợp id + part. Không dùng hoặc sửa QA52/55.'))
    ds=created['dataset_id'];work.configure_identity(ds,['id','part'],actor)
    output={'created_at':datetime.now().astimezone().isoformat(),'dataset_id':ds,'identity_columns':['id','part'],'batches':[]}
    def setup(name,existing=None):
        if existing:
            bid=created['batch_id'];version=created['version_id'];patch_batch(ds,bid,dict(name=name))
        else:
            bid=create_batch(ds,dict(name=name,copy_template_rules=False))['id'];version=import_version(ds,parse_csv(RAW),'nv02-v1.csv',bid)['version_id']
        for body in [dict(name='Điểm 0–10',rule_type='numeric_range',columns=['amount'],config={'min':'0','max':'10'}),dict(name='Tên bắt buộc',rule_type='required',columns=['name'],config={})]:create_rule(ds,{**body,'is_active':True},bid)
        work.activate(ds,bid,actor)
        entry={'id':bid,'name':name,'url':f'http://127.0.0.1:5173/#/datasets/{ds}/batches/{bid}?issues=1','stages':[]};output['batches'].append(entry)
        return bid,version,entry
    def stage(entry,bid,version,label):
        result=execute_run(ds,version);s=work.state(ds,bid);items=work.issue_list(ds,bid)['items']
        entry['stages'].append({'label':label,'version_id':version,'run_id':result['run_id'],'results_url':f'http://127.0.0.1:5173/#/datasets/{ds}/runs/{result["run_id"]}',
            'quality':{k:result[k] for k in ('total_rows','error_row_count','violation_count')},'counts':s['counts'],'reconciliation':s['reconciliations'][0],
            'issues':[{'id':i['id'],'key_values':i['key_values'],'rule':i['rule_snapshot']['name'],'columns':i['rule_snapshot']['columns'],'status':i['status'],'uncertain_reason':i['uncertain_reason']} for i in items]})
        return items
    def progress(bid):
        for item in work.issue_list(ds,bid)['items']:
            work.change_issue(ds,bid,item['id'],'IN_PROGRESS','QA: đang sửa dữ liệu',item['status_revision'],actor)
            detail=work.issue_detail(ds,bid,item['id'])['issue']
            work.change_issue(ds,bid,item['id'],'PENDING_RECHECK','QA: đã gửi bản sửa, chờ kiểm tra lại',detail['status_revision'],actor)
    bid,version,entry=setup('NV-02 A — Đã đối soát và hoàn tất',True)
    stage(entry,bid,version,'v1: OPEN 3');progress(bid)
    version=import_version(ds,parse_csv(V2),'nv02-v2-reordered.csv',bid)['version_id'];stage(entry,bid,version,'v2 đảo dòng: RESOLVED 2 / OPEN 2')
    assert work.state(ds,bid)['counts']==dict(OPEN=2,IN_PROGRESS=0,PENDING_RECHECK=0,RESOLVED=2,IGNORED=0)
    version=import_version(ds,parse_csv(CLEAN),'nv02-v3-clean.csv',bid)['version_id'];stage(entry,bid,version,'v3: RESOLVED 4 / 0 vi phạm')
    work.finish(ds,bid,'QA NV-02: xác nhận bản sạch và bằng chứng đối soát',False,actor)
    assert work.state(ds,bid)['business_state']=='COMPLETED'
    bid,version,entry=setup('NV-02 B — Thực hành tải bản sửa')
    stage(entry,bid,version,'v1: 3 lỗi cần xử lý');progress(bid)
    assert work.state(ds,bid)['counts']['PENDING_RECHECK']==3
    bid,version,entry=setup('NV-02 C — Thiếu khóa, chưa thể đối soát')
    stage(entry,bid,version,'v1: OPEN 3');version=import_version(ds,parse_csv(MISSING),'nv02-missing-key.csv',bid)['version_id']
    stage(entry,bid,version,'v2 sạch theo quy tắc nhưng thiếu khóa: OPEN 3 / UNKNOWN 3')
    assert work.state(ds,bid)['reconciliations'][0]['counts']['UNKNOWN']==3
    assert not work.state(ds,bid)['completion']['can_complete']
    bid,version,entry=setup('NV-02 D — Hoàn tất có ngoại lệ rõ ràng')
    items=stage(entry,bid,version,'v1: 3 vi phạm giữ nguyên')
    for item in items:work.change_issue(ds,bid,item['id'],'IGNORED','QA NV-02: ngoại lệ được phê duyệt để minh họa, không phải dữ liệu đã sửa',item['status_revision'],actor)
    work.finish(ds,bid,'QA NV-02: xác nhận cả 3 ngoại lệ, giữ nguyên 3 vi phạm trong kết quả',True,actor)
    for entry in output['batches']:
        final=work.state(ds,entry['id']);entry['final']={'business_state':final['business_state'],'counts':final['counts'],'events':final['events']}
    after=snapshot(engine,before);output['pre_existing_rows_unchanged']=before==after
    manifest_path.write_text(json.dumps(output,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (ROOT/'.runtime/nv02-qa-preservation.json').write_text(json.dumps(dict(original_rows_unchanged=before==after,before=before,after=after),indent=2),encoding='utf-8')
    assert before==after,'Pre-existing rows differ; inspect preservation evidence'
    engine.dispose();print(json.dumps({'dataset_id':ds,'batches':[{'id':b['id'],'name':b['name']} for b in output['batches']],'original_rows_unchanged':True},ensure_ascii=False))

if __name__=='__main__':main()
