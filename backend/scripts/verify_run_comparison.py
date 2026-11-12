"""MR-02B: authenticated GET demo28/run2/run5, no business data writes."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
from sqlalchemy import create_engine, select
from app.config import get_database_url
from app.models import Dataset, DatasetColumn, DatasetVersion, DatasetRow, QualityRule, QualityRun, QualityViolation, User
from app.services.auth_sessions import create_session, revoke_session

ROOT = Path(__file__).resolve().parents[2]


def main():
    engine=create_engine(get_database_url(),hide_parameters=True)
    models=(Dataset,DatasetColumn,DatasetVersion,DatasetRow,QualityRule,QualityRun,QualityViolation)
    def checksums():
        with engine.connect() as c:
            return {m.__tablename__:hashlib.sha256(json.dumps([dict(r) for r in c.execute(
                select(m).order_by(m.id)).mappings()],ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()
                for m in models}
    before=checksums()
    # Expected response recorded in MR-02A before implementation, not calculated by this service.
    spec=(ROOT/'docs/RUN_COMPARISON_SPEC.md').read_text(encoding='utf-8')
    expected=json.loads(spec.split('```json\n',1)[1].split('\n```',1)[0])
    with engine.begin() as c:
        admin=c.execute(select(User.id).where(User.is_active.is_(True),User.role=='admin').order_by(User.id)).scalars().first()
        assert admin
        session=create_session(c,admin)
    try:
        with httpx.Client(base_url='http://127.0.0.1:5173',timeout=30) as client:
            client.cookies.set('datalens_session',session['token'],path='/api')
            response=client.get('/api/datasets/28/run-comparison',params={'a_run_id':2,'b_run_id':5})
            assert response.status_code==200,response.status_code
            actual=response.json()
            # ISO8601 Z and +00:00 both express the same UTC instant.
            for side in ('a','b'):
                for field in ('started_at','finished_at'):
                    actual[side][field]=actual[side][field].replace('Z','+00:00')
            assert actual==expected
            swapped=client.get('/api/datasets/28/run-comparison',params={'a_run_id':5,'b_run_id':2})
            assert swapped.status_code==200
            assert swapped.json()['delta']==dict(total_rows=0,error_row_count=2,violation_count=3,
                error_row_rate='50.0000',pass_rate='-50.0000')
            same=client.get('/api/datasets/28/run-comparison',params={'a_run_id':2,'b_run_id':2})
            assert same.status_code==200 and same.json()['same_run']
            assert same.json()['delta']==dict(total_rows=0,error_row_count=0,violation_count=0,
                error_row_rate='0.0000',pass_rate='0.0000')
        assert before==checksums()
        artifact={'verified_by':'authenticated HTTP GET via Vite proxy, not browser acceptance',
                  'dataset_id':28,'pairs':[[2,5],[5,2],[2,2]],'response':actual,
                  'seven_business_tables_unchanged':True,'business_checksums':before,
                  'temporary_auth_session_revoked_in_finally':True}
    finally:
        with engine.begin() as c:revoke_session(c,session['token'])
        engine.dispose()
    (ROOT/'docs/samples/mr02b_comparison_verification.json').write_text(
        json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS: demo28 A2/B5 matches complete MR-02A oracle; reverse/same-run exact; seven business tables unchanged; session revoked.')


if __name__=='__main__':main()
