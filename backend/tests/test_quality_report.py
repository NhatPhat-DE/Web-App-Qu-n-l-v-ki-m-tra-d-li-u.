import json
from datetime import datetime, timezone
from authenticated_client import TestClient
from sqlalchemy import select, update, insert, delete, event
from app.main import app
from app.models import Dataset, DatasetVersion, QualityRule, QualityRun, QualityViolation
from app.services.quality_results import complete_run
from app.services import dataset_catalog
from test_quality_results import stored
from test_dataset_import import isolated_database


def ids(stored):
    engine, run, version, _, _ = stored
    with engine.connect() as connection:
        dataset = connection.execute(select(DatasetVersion.dataset_id).where(DatasetVersion.id == version)).scalar_one()
    return dataset, run


def test_report_snapshot_metadata_and_full_errors(stored):
    engine, run, version, snapshot, result = stored
    dataset, _ = ids(stored)
    complete_run(run, result)
    with engine.begin() as connection:
        connection.execute(update(Dataset).where(Dataset.id == dataset).values(name='Hiện tại 日本語', description='', source=None, owner='  chủ\nsở hữu  '))
        connection.execute(update(QualityRule).values(name='changed', config={}))
    with TestClient(app) as client:
        response = client.get(f'/api/datasets/{dataset}/runs/{run}/report')
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/json'
    assert response.headers['content-disposition'] == f'attachment; filename="dataset-{dataset}-run-{run}-report.json"'
    report = json.loads(response.content)
    assert report['report_schema_version'] == '1'
    assert datetime.fromisoformat(report['exported_at']).utcoffset().total_seconds() == 0
    assert report['dataset_metadata_source'] == 'current_at_export'
    assert 'không phải snapshot' in report['dataset_metadata_note']
    assert report['dataset'] == dict(id=dataset, name='Hiện tại 日本語', description='', source=None, owner='  chủ\nsở hữu  ')
    assert report['version']['id'] == version and report['version']['row_count'] == 4
    assert report['rule_snapshot'] == snapshot
    assert [report['run'][key] for key in ['id','status','total_rows','error_row_count','violation_count','error_row_rate']] == [run,'completed',4,2,3,'50.0000']
    assert [(v['row_number'], v['rule_order'], v['values'], v['rule_name']) for v in report['violations']] == [(1,1,[''],'required a'),(1,2,['101'],'range amount'),(2,2,['-1'],'range amount')]


def test_all_violations_and_original_json_values(stored):
    engine, run, _, snapshot, result = stored
    dataset, _ = ids(stored)
    complete_run(run, result)
    values = ['001', '日本語', '  x\ny  ', None, '']
    # Read fixture created directly in the isolated DB to cover all JSON value forms.
    with engine.begin() as connection:
        connection.execute(delete(QualityViolation).where(QualityViolation.run_id == run))
        connection.execute(update(QualityRun).where(QualityRun.id == run).values(total_rows=25,error_row_count=25,violation_count=25,error_row_rate='100.0000'))
        connection.execute(insert(QualityViolation), [dict(run_id=run,rule_id_snapshot=snapshot[0]['id'],rule_type='required',rule_order=1,row_number=n,columns=['a'],values=[values[(n-1)%5]],error_code='REQUIRED_MISSING',message='Lỗi mẫu') for n in range(25,0,-1)])
    with TestClient(app) as client:
        report = client.get(f'/api/datasets/{dataset}/runs/{run}/report').json()
    assert len(report['violations']) == 25
    assert [v['row_number'] for v in report['violations']] == list(range(1,26))
    assert [v['values'] for v in report['violations']] == [[values[(n-1)%5]] for n in range(1,26)]


def test_empty_status_not_found_and_connection(stored, monkeypatch):
    engine, run, version, snapshot, _ = stored
    dataset, _ = ids(stored)
    base = f'/api/datasets/{dataset}/runs/{run}/report'
    with TestClient(app) as client:
        assert client.get(base).status_code == 409
        with engine.begin() as connection:
            connection.execute(update(QualityRun).where(QualityRun.id == run).values(status='failed', finished_at=datetime.now(timezone.utc),failure_code='RUN_FAILED',failure_message='safe'))
        assert client.get(base).json()['error']['code'] == 'RUN_NOT_COMPLETED'
        with engine.begin() as connection:
            connection.execute(update(QualityRun).where(QualityRun.id == run).values(status='running',finished_at=None,failure_code=None,failure_message=None))
        complete_run(run, dict(row_count=4,error_row_count=0,violation_count=0,errors=[]))
        assert client.get(base).json()['violations'] == []
        other = client.post('/api/datasets/import',data={'name':'other'},files={'file':('a.csv',b'a\n1')}).json()['dataset_id']
        for url in [f'/api/datasets/{other}/runs/{run}/report',f'/api/datasets/999999/runs/{run}/report',f'/api/datasets/{dataset}/runs/999999/report']:
            assert client.get(url).status_code == 404
        monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://test:secret@127.0.0.1:65432/test')
        response = client.get(base)
        assert response.status_code == 503 and 'secret' not in response.text and 'SELECT' not in response.text


def test_one_repeatable_read_snapshot(stored, monkeypatch):
    engine, run, _, _, result = stored
    dataset, _ = ids(stored)
    complete_run(run,result)
    original_factory = dataset_catalog.create_engine
    changed = []
    def factory(*args, **kwargs):
        assert kwargs['isolation_level'] == 'REPEATABLE READ'
        target = original_factory(*args, **kwargs)
        @event.listens_for(target, 'after_cursor_execute')
        def change_after_first_read(connection,cursor,statement,parameters,context,executemany):
            if not changed and 'quality_runs' in statement:
                changed.append(True)
                with engine.begin() as writer:
                    writer.execute(update(Dataset).where(Dataset.id == dataset).values(name='concurrent update'))
        return target
    monkeypatch.setattr(dataset_catalog,'create_engine',factory)
    with TestClient(app) as client:
        response = client.get(f'/api/datasets/{dataset}/runs/{run}/report')
    assert response.status_code == 200
    assert response.json()['dataset']['name'] == 'results test'
    assert changed == [True]
