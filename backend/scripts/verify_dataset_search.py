"""MR-01B: authenticated GET only; temporary auth session, no business writes."""
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import create_engine, select
from app.config import get_database_url
from app.models import Dataset, DatasetColumn, DatasetRow, DatasetVersion, QualityRule, QualityRun, QualityViolation, User
from app.services.auth_sessions import create_session, revoke_session


def main():
    engine = create_engine(get_database_url(), hide_parameters=True)
    models = (Dataset, DatasetColumn, DatasetRow, DatasetVersion, QualityRule, QualityRun, QualityViolation)

    def checksum():
        with engine.connect() as c:
            return {m.__tablename__: hashlib.sha256(json.dumps(
                [dict(r) for r in c.execute(select(m).order_by(m.id)).mappings()],
                ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest() for m in models}

    before = checksum()
    with engine.begin() as c:
        admin = c.execute(select(User.id).where(User.is_active.is_(True), User.role == 'admin')
                          .order_by(User.id)).scalars().first()
        assert admin, 'No active authorized admin'
        session = create_session(c, admin)
    try:
        with engine.connect() as c:
            datasets = [dict(r) for r in c.execute(select(Dataset).order_by(
                Dataset.created_at.desc(), Dataset.id.desc())).mappings()]
        assert datasets
        # Expected matches are derived from actual stored metadata, before HTTP.
        queries = [None, datasets[0]['name'][:min(8, len(datasets[0]['name']))],
                   'MR01B_NO_RESULT_5ac5d257a84b']
        with httpx.Client(base_url='http://127.0.0.1:5173', timeout=30) as client:
            client.cookies.set('datalens_session', session['token'], path='/api')
            assert client.get('/api/auth/me').status_code == 200
            for q in queries:
                expected = [d['id'] for d in datasets if q is None or any(
                    unicodedata.normalize('NFC', q).lower() in unicodedata.normalize('NFC', d[k]).lower()
                    for k in ('name', 'description', 'source', 'owner') if d[k] is not None)]
                collected = []
                page = 1
                while True:
                    params = {'page': page, 'page_size': 20}
                    if q is not None:
                        params['q'] = q
                    response = client.get('/api/datasets', params=params)
                    assert response.status_code == 200, response.status_code
                    body = response.json()
                    assert body['total'] == len(expected)
                    collected.extend(r['id'] for r in body['items'])
                    if len(collected) >= body['total']:
                        break
                    assert body['items'], 'Missing page'
                    page += 1
                assert collected == expected
                print(('unfiltered' if q is None else 'match' if expected else 'no_match'),
                      'total=', len(expected), 'ids=', collected)
        assert checksum() == before, 'Business data changed during verification'
        print('PASS: authenticated proxy GET, all metadata matches, seven business tables unchanged.')
    finally:
        with engine.begin() as c:
            revoke_session(c, session['token'])
        engine.dispose()


if __name__ == '__main__':
    main()
