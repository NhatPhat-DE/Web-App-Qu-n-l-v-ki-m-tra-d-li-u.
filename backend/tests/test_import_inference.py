from authenticated_client import TestClient
from sqlalchemy import select, update
from app.main import app
from app.models import DatasetVersion
from app.services import dataset_catalog, dataset_import
from test_dataset_import import isolated_database


def test_version_inference_and_legacy_read(isolated_database, monkeypatch):
    header = 'code,value,flag,day,empty,label\n'
    original = (header + '001, 2 ,TRUE,2024-02-29,,日本語\n-001,3,false,2026-01-01,  ,Tiếng Việt\n').encode()
    changed = (header + '001,2.5,true,2026-02-29,,日本語\n-001,3.0,1,2026-01-01,  ,Tiếng Việt\n').encode()
    with TestClient(app) as client:
        response = client.post('/api/datasets/import', data={'name': 'Inference test'}, files={'file': ('one.csv', original)})
        assert response.status_code == 201
        dataset, first = response.json()['dataset_id'], response.json()['version_id']
        response = client.post(f'/api/datasets/{dataset}/versions/import', files={'file': ('two.csv', changed)})
        assert response.status_code == 201
        second = response.json()['version_id']
        detail = client.get(f'/api/datasets/{dataset}').json()
        names = ['code', 'value', 'flag', 'day', 'empty', 'label']
        def answer(types):
            return [dict(column_name=name, position=i+1, inferred_type=kind,
                         non_missing_count=0 if name == 'empty' else 2,
                         missing_count=2 if name == 'empty' else 0)
                    for i, (name, kind) in enumerate(zip(names, types))]
        expected_first = answer(['text', 'integer', 'boolean', 'date', 'unknown', 'text'])
        expected_second = answer(['text', 'decimal', 'text', 'text', 'unknown', 'text'])
        assert detail['versions'][0]['inferred_types'] == expected_second
        assert detail['versions'][1]['inferred_types'] == expected_first
        with isolated_database.connect() as connection:
            assert connection.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == first)).scalar_one() == expected_first
            assert connection.execute(select(DatasetVersion.inferred_types).where(DatasetVersion.id == second)).scalar_one() == expected_second
        rows = client.get(f'/api/datasets/{dataset}/versions/{first}/rows').json()['items']
        assert [row['values'] for row in rows] == [['001', ' 2 ', 'TRUE', '2024-02-29', '', '日本語'], ['-001', '3', 'false', '2026-01-01', '  ', 'Tiếng Việt']]
        before = detail
        assert client.post(f'/api/datasets/{dataset}/versions/import', files={'file': ('bad.csv', b'x\n1')}).status_code == 422
        assert client.get(f'/api/datasets/{dataset}').json() == before
        # Simulate a pre-22B version only in this disposable database.
        with isolated_database.begin() as connection:
            connection.execute(update(DatasetVersion).where(DatasetVersion.id == first).values(inferred_types=[]))
        def forbidden(*args):
            raise AssertionError('GET must not infer types')
        monkeypatch.setattr(dataset_import, 'infer_types', forbidden)
        assert client.get(f'/api/datasets/{dataset}').json()['versions'][1]['inferred_types'] == []


def test_inference_precedes_database(isolated_database, monkeypatch):
    from app.services.csv_reader import parse_csv
    parsed = parse_csv(b'a\n1')
    calls = []
    original = dataset_import.infer_types
    def infer(header, rows):
        calls.append('inference')
        return original(header, rows)
    monkeypatch.setattr(dataset_import, 'infer_types', infer)
    def blocked(*args, **kwargs):
        assert calls == ['inference']
        raise RuntimeError('stop before database')
    monkeypatch.setattr(dataset_import, 'create_engine', blocked)
    import pytest
    with pytest.raises(RuntimeError, match='stop before database'):
        dataset_import.import_dataset(parsed, 'a.csv', {'name': 'test'})
    calls.clear()
    monkeypatch.setattr(dataset_import, 'rule_connection', blocked)
    with pytest.raises(RuntimeError, match='stop before database'):
        dataset_import.import_version(1, parsed, 'a.csv')
