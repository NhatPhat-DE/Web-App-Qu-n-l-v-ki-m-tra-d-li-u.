"""GET-only BC-01A demo checks; no dataset/rule/run writes, no provider calls."""
import hashlib,json,sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'tests')]
import httpx
from sqlalchemy import create_engine,select
from app.config import get_database_url
from app.models import Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation,User
from app.services.auth_sessions import create_session,revoke_session
from app.services.report_excel import XLSX_MIME,expected_condition
from xlsx_reader import read_xlsx
ROOT=Path(__file__).resolve().parents[1]/'samples'/'bc01a'
DEMOS=[(28,2),(28,5),(42,28),(44,33),(46,38)]
def digest(data):return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
def main():
    mode=sys.argv[1];assert mode in ('capture','verify');ROOT.mkdir(exist_ok=True)
    engine=create_engine(get_database_url(),hide_parameters=True)
    def checks():
        with engine.connect() as c:
            return {m.__tablename__:{'count':len(rows),'sha256':digest(rows)} for m in (Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation) for rows in [[dict(r) for r in c.execute(select(m).order_by(m.id)).mappings()]]}
    before=checks()
    with engine.begin() as c:
        assert not c.execute(select(QualityRun.id).where(QualityRun.status=='running')).all()
        admin=c.execute(select(User.id).where(User.role=='admin',User.is_active.is_(True)).order_by(User.id)).scalars().first();assert admin
        session=create_session(c,admin)
    try:
        baseline={} if mode=='capture' else json.loads((ROOT/'before.json').read_text(encoding='utf-8'))['reports']
        artifacts=[]
        with httpx.Client(base_url='http://127.0.0.1:5173',timeout=60) as client:
            client.cookies.set('datalens_session',session['token'],path='/api')
            for dataset,run in DEMOS:
                path=f'/api/datasets/{dataset}/runs/{run}/report';response=client.get(path);assert response.status_code==200
                assert response.headers['content-type']=='application/json'
                assert response.headers['content-disposition']==f'attachment; filename="dataset-{dataset}-run-{run}-report.json"'
                data=response.json();key=f'{dataset}/{run}';logical={k:v for k,v in data.items() if k!='exported_at'}
                if mode=='capture':baseline[key]=digest(logical);continue
                assert digest(logical)==baseline[key]
                assert response.content==json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2).encode()
                excel=client.get(path+'.xlsx');assert excel.status_code==200
                assert excel.headers['content-type']==XLSX_MIME
                assert excel.headers['content-disposition']==f'attachment; filename="dataset-{dataset}-run-{run}-report.xlsx"'
                sheets=read_xlsx(excel.content);assert list(sheets)==['Tổng quan','Chi tiết lỗi','Quy tắc đã áp dụng']
                rows=sheets['Chi tiết lỗi']['rows'][1:];assert len(rows)==(len(data['violations']) or 1)
                by_id={r['id']:r for r in data['rule_snapshot']}
                for row,item in zip(rows,data['violations']):
                    rule=by_id[item['rule_id_snapshot']]
                    assert row[0]==str(item['row_number']) and row[1]==rule['name']
                    assert json.loads(row[3])==item['columns'] and json.loads(row[4])==item['values']
                    assert row[5]==expected_condition(rule) and row[6:]==[item['error_code'],item['message']]
                assert [json.loads(row[5]) for row in sheets['Quy tắc đã áp dụng']['rows'][1:]]==[r['config'] for r in data['rule_snapshot']]
                overview=dict(sheets['Tổng quan']['rows'][1:]);assert overview['Tỷ lệ lỗi']==data['run']['error_row_rate']+'%'
                for label,field in [('Run ID','id'),('Tổng bản ghi','total_rows'),('Bản ghi lỗi','error_row_count'),('Tổng vi phạm','violation_count')]:assert overview[label]==str(data['run'][field])
                for extension,body in [('json',response.content),('xlsx',excel.content)]:ROOT.joinpath(f'dataset-{dataset}-run-{run}-report.{extension}').write_bytes(body)
                artifacts.append({'dataset_id':dataset,'run_id':run,'run':data['run'],'xlsx_bytes':len(excel.content),'attachment':excel.headers['content-disposition'],'mime':excel.headers['content-type'],'json_logical_unchanged':True,'ooxml_verified':True})
        assert checks()==before
        if mode=='capture':payload={'reports':baseline,'business_tables':before};filename='before.json'
        else:
            assert before==json.loads((ROOT/'before.json').read_text(encoding='utf-8'))['business_tables']
            payload={'artifacts':artifacts,'business_tables':before,'business_data_unchanged':True,'temporary_session_revoked_in_finally':True,'manual_excel_libreoffice_open':False};filename='verification.json'
        ROOT.joinpath(filename).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('PASS:',mode,'5 demo reports; GET only;7business tables unchanged; no secrets saved.')
        if artifacts:print(json.dumps([{'dataset':a['dataset_id'],'run':a['run_id'],'violations':a['run']['violation_count'],'xlsx_bytes':a['xlsx_bytes']} for a in artifacts]))
    finally:
        with engine.begin() as c:revoke_session(c,session['token'])
        engine.dispose()
if __name__=='__main__':main()
