"""Create only a new NV-01 QA dataset through real HTTP; revoke temporary session."""
from pathlib import Path
import json
import sys
import httpx
from sqlalchemy import select
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.models import User
from app.services.quality_rules import rule_connection
from app.services.auth_sessions import create_session,revoke_session
from app.services.csrf import session_csrf_token


def run():
    with rule_connection() as c:
        admin=c.execute(select(User.id).where(User.role=='admin',User.is_active.is_(True)).order_by(User.id)).scalars().first()
        if not admin:raise RuntimeError('No active admin; create first admin using CLI before QA seed.')
        token=create_session(c,admin)['token']
    root=Path('D:/User_File/ChatGPT/DACN/qa_test_data')
    try:
        with httpx.Client(base_url='http://127.0.0.1:5173',cookies={'datalens_session':token},headers={'Origin':'http://127.0.0.1:5173','X-CSRF-Token':session_csrf_token(token)},timeout=30) as client:
            def post(url,**kwargs):
                r=client.post(url,**kwargs)
                if r.status_code!=201:raise RuntimeError(f'QA request failed: {url} => {r.status_code}')
                return r.json()
            ds=post('/api/datasets',json={'name':'NV-01 QA — Sinh viên theo đợt','owner':'QA NV-01','source':'Dữ liệu thử riêng','description':'Fixture tham chiếu; không dùng cho nghiệp vụ thật.'})['id']
            jan=post(f'/api/datasets/{ds}/batches',json={'name':'NV-01 Tháng 01/2026','period_label':'01/2026','copy_template_rules':False})['id']
            def upload(batch,name):return post(f'/api/datasets/{ds}/batches/{batch}/versions/import',files={'file':(name,(root/name).read_bytes())})
            v1=upload(jan,'v1.0_raw.csv')
            columns=client.get(f'/api/datasets/{ds}').json()['columns']
            rules=[dict(name=f'{c["name"]} bắt buộc',rule_type='required',columns=[c['name']],config={}) for c in columns]
            rules += [dict(name='Mã sinh viên duy nhất',rule_type='unique',columns=['ma_sinh_vien'],config={}),
                dict(name='Email trường',rule_type='pattern',columns=['email'],config={'dialect':'re2-v1','pattern':r'[A-Za-z0-9._%+-]+@hcmut\.edu\.vn'}),
                dict(name='Điện thoại',rule_type='pattern',columns=['so_dien_thoai'],config={'dialect':'re2-v1','pattern':r'0[0-9]{9}'}),
                dict(name='Ngày sinh 1900..08/11/2026',rule_type='date_format',columns=['ngay_sinh'],config={'format':'YYYY-MM-DD','min':'1900-01-01','max':'2026-11-08'}),
                dict(name='Điểm 0..10',rule_type='numeric_range',columns=['diem_tong_ket'],config={'min':'0','max':'10'})]
            for rule in rules:
                post(f'/api/datasets/{ds}/rules',json=rule)
                post(f'/api/datasets/{ds}/batches/{jan}/rules',json=rule)
            def check(v):return post(f'/api/datasets/{ds}/versions/{v["version_id"]}/runs')
            r1=check(v1)
            v2=upload(jan,'v1.1_fixed.csv');r2=check(v2)
            v3=upload(jan,'v1.1_fixed.csv')  # Deliberately unchecked current version.
            feb=post(f'/api/datasets/{ds}/batches',json={'name':'NV-01 Tháng 02/2026','period_label':'02/2026','copy_template_rules':True})['id']
            fv1=upload(feb,'v1.0_raw.csv');fr1=check(fv1)
            februle=client.get(f'/api/datasets/{ds}/batches/{feb}/rules').json()['items'][0]
            assert client.patch(f'/api/datasets/{ds}/batches/{feb}/rules/{februle["id"]}',json={'name':februle['name']+' (revision tháng 02)'}).status_code==200
            assert (r1['total_rows'],r1['error_row_count'],r1['violation_count'])==(12,9,16)
            assert (r2['total_rows'],r2['error_row_count'],r2['violation_count'])==(12,2,2)
            evidence=dict(dataset_id=ds,january_batch_id=jan,february_batch_id=feb,january_versions=[v1,v2,v3],january_runs=[r1,r2],february_version=fv1,february_run=fr1,
                batch_url=f'http://127.0.0.1:5173/#/datasets/{ds}/batches/{jan}',comparison_url=f'http://127.0.0.1:5173/#/datasets/{ds}/compare?a={r1["run_id"]}&b={r2["run_id"]}')
            (ROOT/'.runtime'/'nv01-qa.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
            print(json.dumps({key:value for key,value in evidence.items() if key.endswith('_id') or key.endswith('_url')},ensure_ascii=False))
    finally:
        with rule_connection() as c:revoke_session(c,token)


if __name__=='__main__':run()
