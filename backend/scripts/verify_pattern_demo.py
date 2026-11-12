"""Create only the authorized QT-04A demo; protect all pre-existing business rows."""
import hashlib,json,sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'tests')]
import httpx
from sqlalchemy import create_engine,select
from app.config import get_database_url
from app.models import Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation,User
from app.services.auth_sessions import create_session,revoke_session
from app.services.csrf import session_csrf_token
from app.services.csv_reader import parse_csv
from app.services.quality_trend import fingerprint
from app.services.report_excel import XLSX_MIME,expected_condition
from xlsx_reader import read_xlsx

ROOT=Path(__file__).resolve().parents[1]/'samples'
MODELS=(Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation)


def main():
    artifact=ROOT/'pattern_qt04a_verification.json'
    assert not artifact.exists(),'Demo already recorded; refuse duplicate creation.'
    expected=json.loads((ROOT/'pattern_qt04a_expected.json').read_text(encoding='utf-8'))
    before=json.loads((ROOT/'pattern_qt04a_before.json').read_text(encoding='utf-8'))
    parsed=parse_csv((ROOT/'pattern_qt04a.csv').read_bytes())
    assert parsed.rows==expected['rows'] and parsed.row_count==10
    engine=create_engine(get_database_url(),hide_parameters=True)
    with engine.begin() as c:
        assert not c.execute(select(QualityRun.id).where(QualityRun.status=='running')).all()
        admin=c.execute(select(User.id).where(User.role=='admin',User.is_active.is_(True)).order_by(User.id)).scalars().first()
        assert admin
        session=create_session(c,admin)
    try:
        with httpx.Client(base_url='http://127.0.0.1:5173',timeout=60) as client:
            client.cookies.set('datalens_session',session['token'],path='/api')
            client.headers.update({'Origin':'http://127.0.0.1:5173','X-CSRF-Token':session_csrf_token(session['token'])})
            def request(method,path,**kwargs):
                response=client.request(method,path,**kwargs)
                assert response.is_success,(method,path,response.status_code,response.text[:200])
                return response.json()
            assert request('GET','/api/auth/me')['user']['role']=='admin'
            imported=request('POST','/api/datasets/import',data={'name':'QT-04A Pattern RE2 Demo','source':'samples/pattern_qt04a.csv'},files={'file':('pattern_qt04a.csv',(ROOT/'pattern_qt04a.csv').read_bytes(),'text/csv')})
            dataset,version=imported['dataset_id'],imported['version_id'];base=f'/api/datasets/{dataset}'
            rule=request('POST',base+'/rules',json={'name':'Product code SP + four ASCII digits','rule_type':'pattern','columns':['product_code'],'config':expected['config'],'is_active':True})
            assert request('GET',base+'/rules')['items']==[rule]
            result=request('POST',base+f'/versions/{version}/runs')
            assert all(result[k]==v for k,v in expected['statistics'].items())
            run=result['run_id'];path=base+f'/runs/{run}'
            detail=request('GET',path)
            snapshot=[{k:rule[k] for k in ('id','name','rule_type','columns','config')}]
            assert detail['rule_snapshot']==snapshot and detail['engine_version']=='quality-v5'
            violations=[]
            for page in range(1,5):
                response=request('GET',path+'/violations',params={'page_size':2,'page':page})
                assert response['total']==7
                violations+=response['items']
            assert [v['row_number'] for v in violations]==expected['error_rows']
            for v in violations:
                assert v['error_code']=='PATTERN_MISMATCH' and v['values']==expected['rows'][v['row_number']-1]
                assert 'SP[0-9]{4}' in v['message'] and 're2-v1' in v['message']
            assert request('GET',base+'/runs')['items'][0]['run_id']==run
            assert [r['values'] for r in request('GET',base+f'/versions/{version}/rows',params={'page_size':100})['items']]==expected['rows']
            json_response=client.get(path+'/report');assert json_response.status_code==200
            report=json_response.json()
            assert report['violations']==violations and report['rule_snapshot']==snapshot and report['report_schema_version']=='1'
            assert json_response.headers['content-disposition']==f'attachment; filename="dataset-{dataset}-run-{run}-report.json"'
            excel=client.get(path+'/report.xlsx');assert excel.status_code==200 and excel.headers['content-type']==XLSX_MIME
            assert excel.headers['content-disposition']==f'attachment; filename="dataset-{dataset}-run-{run}-report.xlsx"'
            sheets=read_xlsx(excel.content);assert len(sheets)==3
            rows=sheets['Chi tiết lỗi']['rows'][1:];assert len(rows)==7
            for row,v in zip(rows,violations):
                assert row[0]==str(v['row_number']) and json.loads(row[4])==v['values'] and row[5]==expected_condition(snapshot[0]) and row[6:]==[v['error_code'],v['message']]
            assert json.loads(sheets['Quy tắc đã áp dụng']['rows'][1][5])==expected['config']
            point=request('GET',base+'/quality-trend')['points'][0]
            assert point['rule_set_fingerprint']==fingerprint(snapshot) and point['engine_version']=='quality-v5'
            (ROOT/f'dataset-{dataset}-run-{run}-report.json').write_bytes(json_response.content)
            (ROOT/f'dataset-{dataset}-run-{run}-report.xlsx').write_bytes(excel.content)
        checks={}
        with engine.connect() as c:
            for model in MODELS:
                saved=before[model.__tablename__]
                rows=[dict(r) for r in c.execute(select(model).where(model.id.in_(saved['ids'])).order_by(model.id)).mappings()]
                digest=hashlib.sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
                assert digest==saved['sha256'],model.__tablename__
                checks[model.__tablename__]=digest
            for row in c.execute(select(QualityRun.id,QualityRun.engine_version,QualityRun.rule_snapshot).where(QualityRun.id.in_([int(i) for i in before['fingerprints']]))):
                assert {'engine_version':row.engine_version,'fingerprint':fingerprint(row.rule_snapshot)}==before['fingerprints'][str(row.id)]
        artifact.write_text(json.dumps({'dataset_name':'QT-04A Pattern RE2 Demo','dataset_id':dataset,'version_id':version,'rule_id':rule['id'],'run_id':run,'statistics':expected['statistics'],'error_rows':expected['error_rows'],'snapshot':snapshot,'fingerprint':point['rule_set_fingerprint'],'parser_raw_preserved':True,'history_violations_json_xlsx_verified':True,'xlsx_verified_by':'stdlib ZIP/XML reader, all cells text; not manual Excel/LibreOffice','old_business_row_checksums':checks,'old_fingerprints_unchanged':True,'session_revoked_in_finally':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'PASS dataset={dataset}, version={version}, rule={rule["id"]}, run={run}:10/7/7/70.0000%; old rows/fingerprints unchanged.')
    finally:
        with engine.begin() as c: revoke_session(c,session['token'])
        engine.dispose()

if __name__=='__main__':main()
