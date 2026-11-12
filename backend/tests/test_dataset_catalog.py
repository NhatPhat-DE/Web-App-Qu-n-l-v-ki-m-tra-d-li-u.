from nv01_fixtures import current_version_values
from datetime import datetime, timezone

import pytest
from authenticated_client import TestClient
from sqlalchemy import insert

from app.main import app
from app.models import Dataset, DatasetColumn, DatasetVersion, DatasetRow
from app.services import dataset_catalog
from sqlalchemy import event, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from fastapi.testclient import TestClient as AnonymousClient
from test_dataset_import import isolated_database  # Reuse isolated PostgreSQL fixture.


@pytest.fixture
def catalog_data(isolated_database):
    with isolated_database.begin() as connection:
        ids = [connection.execute(insert(Dataset).values(
            name=f"dataset {index}", description="Mô tả", source="CSV", owner="Owner",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)).returning(Dataset.id)).scalar_one()
               for index in range(3)]
        dataset = ids[0]
        connection.execute(insert(DatasetColumn), [
            {"dataset_id": dataset, "name": "note", "position": 2},
            {"dataset_id": dataset, "name": "code", "position": 1}])
        versions = [connection.execute(insert(DatasetVersion).values(**current_version_values(connection, 
            dataset_id=dataset, version_number=number, original_filename=f"v{number}.csv",
            file_size_bytes=100, row_count=5, inferred_types=[])).returning(DatasetVersion.id)).scalar_one()
                    for number in [1, 2]]
        values = [[f"00{index}", "  Tiếng Việt\nmultiline  "] for index in range(5)]
        connection.execute(insert(DatasetRow), [
            {"version_id": versions[0], "row_number": index + 1, "values": row}
            for index, row in reversed(list(enumerate(values)))])
    return ids, versions, values


def test_empty_catalog(isolated_database):
    with TestClient(app) as client:
        assert client.get("/api/datasets").json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


def test_list_and_detail(catalog_data):
    ids, versions, _ = catalog_data
    with TestClient(app) as client:
        first = client.get("/api/datasets?page_size=2").json()
        assert first["total"] == 3 and first["page"] == 1 and first["page_size"] == 2
        assert [item["id"] for item in first["items"]] == ids[:0:-1]
        assert set(first["items"][0]) == {"id", "name", "description", "source", "owner", "created_at", "version_count", "batch_count"}
        second = client.get("/api/datasets?page=2&page_size=2").json()
        assert [item["id"] for item in second["items"]] == [ids[0]]
        assert second["items"][0]["version_count"] == 2
        assert client.get("/api/datasets?page=99").json()["items"] == []
        assert client.get("/api/datasets?page=99").json()["total"] == 3
        response = client.get(f"/api/datasets/{ids[0]}")
        assert response.status_code == 200
        detail = response.json()
        assert detail["name"] == "dataset 0" and detail["description"] == "Mô tả"
        assert detail["source"] == "CSV" and detail["owner"] == "Owner"
        assert [column["name"] for column in detail["columns"]] == ["code", "note"]
        assert [column["position"] for column in detail["columns"]] == [1, 2]
        assert [version["id"] for version in detail["versions"]] == versions[::-1]
        assert [version["version_number"] for version in detail["versions"]] == [2, 1]
        assert set(detail["versions"][0]) == {"id", "dataset_id", "batch_id", "is_current", "version_number", "original_filename", "file_size_bytes", "row_count", "imported_at", "inferred_types"}
        assert detail["versions"][0]["inferred_types"] == []
        assert "rows" not in detail


def test_rows_pagination_and_errors(catalog_data):
    ids, versions, values = catalog_data
    base = f"/api/datasets/{ids[0]}/versions/{versions[0]}/rows"
    with TestClient(app) as client:
        collected = []
        for page in [1, 2, 3, 4]:
            response = client.get(base, params={"page": page, "page_size": 2})
            assert response.status_code == 200
            result = response.json()
            assert result["header"] == ["code", "note"]
            assert result["total"] == 5 and result["page"] == page and result["page_size"] == 2
            collected.extend(result["items"])
        assert collected == [{"row_number": index + 1, "values": value} for index, value in enumerate(values)]
        for path in ["/api/datasets/999999", f"/api/datasets/{ids[0]}/versions/999999/rows",
                     f"/api/datasets/{ids[1]}/versions/{versions[0]}/rows",
                     f"/api/datasets/999999/versions/{versions[0]}/rows"]:
            assert client.get(path).status_code == 404
        for params in [{"page": 0}, {"page": -1}, {"page": "abc"}, {"page_size": 0}, {"page_size": 101}, {"page_size": "x"}]:
            for path in ["/api/datasets", base]:
                assert client.get(path, params=params).status_code == 422


def test_read_database_unavailable(isolated_database, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:example@127.0.0.1:65432/test")
    with TestClient(app) as client:
        for path in ["/api/datasets", "/api/datasets/1", "/api/datasets/1/versions/1/rows"]:
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
            assert "example" not in response.text and "SELECT" not in response.text


@pytest.fixture
def searchable_catalog(isolated_database):
    with isolated_database.begin() as c:
        for index, values in enumerate(SEARCH_FIXTURE, 1):
            c.execute(insert(Dataset).values(id=index, **dict(zip(
                ('name', 'description', 'source', 'owner'), values)),
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
            version = c.execute(insert(DatasetVersion).values(**current_version_values(c, dataset_id=index, version_number=1,
                original_filename='FILE_NAME_ONLY.csv', file_size_bytes=10, row_count=1,
                inferred_types=[])).returning(DatasetVersion.id)).scalar_one()
            c.execute(insert(DatasetColumn).values(dataset_id=index, name='COLUMN_NAME_ONLY',
                position=1, description='COLUMN_DESC_ONLY'))
            c.execute(insert(DatasetRow).values(version_id=version, row_number=1, values=['CELL_ONLY_TOKEN']))
    return isolated_database


def test_metadata_search_oracles(searchable_catalog):
    cases = [(None, list(range(24, 0, -1))), ('', list(range(24, 0, -1))),
        (dataset_catalog.SEARCH_WHITESPACE, list(range(24, 0, -1))),
        ('kiểm kê', [1]), ('bán hàng', [21,8,7,6,3,2,1]), ('BÁN HÀNG', [21,8,7,6,3,2,1]),
        ('  bán hàng  ', [21,8,7,6,3,2,1]), ('ban hang', [4]), ('hàng bán', [5]),
        ('bán hàng POS', []), ('NGUYỄN AN', [19,3,1]), ('POS', [4,2]), ('100%', [9]),
        ('%', [22,9]), ('_', [23,10]), ('SKU_A', [10]), ("O'Brien", [11]), ("o'brien", [11]),
        ('đơn', [11]), ("' OR 1=1 --", []), ('!', [24]), ('!%', []), ('Giá + thuế', [20]),
        ('NULL', [24,17]), ('null', [24,17]), ('café', [14,13]), ('Cafe\u0301', [14,13]),
        ('cafe', [12]), ('caf', [14,13,12]), ('Kho  A', [15]), ('Kho A', [16]),
        ('COLUMN_NAME_ONLY', []), ('COLUMN_DESC_ONLY', []), ('CELL_ONLY_TOKEN', []),
        ('FILE_NAME_ONLY', []), ('KHONG_CO_KET_QUA_987', []), ('X'*200, []), ('😀'*200, []),
        ('\\', []), ('\ufeff', []), ('\u200b', [])]
    with TestClient(app) as client:
        for q, expected in cases:
            params = {'page_size':100}
            if q is not None: params['q'] = q
            response = client.get('/api/datasets', params=params)
            assert response.status_code == 200, (q, response.text)
            body=response.json()
            assert [r['id'] for r in body['items']] == expected, q
            assert body['total'] == len(expected), q
            assert all(r['version_count']==1 for r in body['items'])
        assert client.get('/api/datasets',params={'source':'POS'}).json()['total']==24
    with searchable_catalog.connect() as c:
        stored=c.execute(select(Dataset.name).order_by(Dataset.id)).scalars().all()
        assert stored==[r[0] for r in SEARCH_FIXTURE]
        environment=c.execute(text("SELECT current_setting('server_version'), current_setting('server_encoding'), datcollate, datctype, datlocprovider FROM pg_database WHERE datname=current_database()")).one()
        print('SEARCH TEST POSTGRES:', tuple(environment))


def test_search_pagination_and_literals(searchable_catalog):
    with TestClient(app) as client:
        for q,size,pages,total in [(None,20,[list(range(24,4,-1)),[4,3,2,1],[]],24),
                ('bán hàng',3,[[21,8,7],[6,3,2],[1],[]],7), ('%',1,[[22],[9],[]],2)]:
            for page,expected in enumerate(pages,1):
                params={'page':page,'page_size':size}
                if q is not None: params['q']=q
                body=client.get('/api/datasets',params=params).json()
                assert [r['id'] for r in body['items']]==expected
                assert (body['total'],body['page'],body['page_size'])==(total,page,size)
        # Positive literal backslash and combinations must not act as LIKE escapes.
        with searchable_catalog.begin() as c:
            c.execute(update(Dataset).where(Dataset.id==24).values(description='path\\item !%_'))
        for q in ['\\', 'path\\item', '!%_', '\\item !%_']:
            body=client.get('/api/datasets',params={'q':q}).json()
            assert [r['id'] for r in body['items']]==[24] and body['total']==1
        for q in ['X'*200, '😀'*200]:
            with searchable_catalog.begin() as c:
                c.execute(update(Dataset).where(Dataset.id==24).values(description=q))
            body=client.get('/api/datasets',params={'q':q}).json()
            assert [r['id'] for r in body['items']]==[24] and body['total']==1


def test_search_validation_before_database(isolated_database,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('Invalid search reached database')
    monkeypatch.setattr(dataset_catalog,'catalog_connection',forbidden)
    with TestClient(app) as client:
        for q in ['X'*201,'😀'*201,' '*201,'e\u0301'*101,'a\x00b']:
            response=client.get('/api/datasets',params={'q':q})
            assert response.status_code==422
            assert response.json()['error']['code']=='INVALID_SEARCH_QUERY'
        response=client.get('/api/datasets?q=a&q=b')
        assert response.status_code==422 and response.json()['error']['code']=='INVALID_SEARCH_QUERY'
        for params in [{'q':'ok','page':0},{'q':'ok','page_size':101},{'q':'ok','page':'x'}]:
            response=client.get('/api/datasets',params=params)
            assert response.status_code==422 and 'detail' in response.json()
    with pytest.raises(dataset_catalog.InvalidSearchQuery):
        dataset_catalog.prepare_search_query('\ud800')


def test_search_repeatable_read_with_concurrent_writer(searchable_catalog,monkeypatch):
    factory=dataset_catalog.create_engine
    writes=[]
    def instrumented(*args,**kwargs):
        engine=factory(*args,**kwargs)
        @event.listens_for(engine,'after_cursor_execute')
        def after_count(connection,cursor,statement,parameters,context,executemany):
            if statement.startswith('SELECT count(') and not writes:
                assert connection.get_isolation_level()=='REPEATABLE READ'
                assert connection.exec_driver_sql('SHOW transaction_read_only').scalar_one()=='on'
                # A separate connection commits while the reader transaction is open.
                with searchable_catalog.begin() as writer:
                    writer.execute(update(Dataset).where(Dataset.id==2).values(name='Changed away from phrase'))
                writes.append(True)
        return engine
    monkeypatch.setattr(dataset_catalog,'create_engine',instrumented)
    first=dataset_catalog.list_datasets(1,100,'bán hàng')
    assert first['total']==7 and [r['id'] for r in first['items']]==[21,8,7,6,3,2,1]
    second=dataset_catalog.list_datasets(1,100,'bán hàng')
    assert second['total']==6 and [r['id'] for r in second['items']]==[21,8,7,6,3,1]


def test_search_access_and_safe_database_errors(isolated_database,monkeypatch):
    from app.access import require_business_access
    from fastapi import HTTPException
    with AnonymousClient(app) as client:
        assert client.get('/api/datasets?q=abc').status_code==401
    def denied():
        raise HTTPException(403,detail={'code':'FORBIDDEN','message':'Denied'})
    app.dependency_overrides[require_business_access]=denied
    try:
        with AnonymousClient(app) as client:
            assert client.get('/api/datasets?q=abc').status_code==403
    finally:
        app.dependency_overrides.pop(require_business_access,None)
    def broken(*args):
        raise SQLAlchemyError('SECRET SELECT private_password')
    monkeypatch.setattr(dataset_catalog,'list_datasets',broken)
    with TestClient(app) as client:
        response=client.get('/api/datasets',params={'q':"' SQL"})
        assert response.status_code==500 and response.json()['error']['code']=='DATABASE_ERROR'
        assert 'SECRET' not in response.text and 'SELECT' not in response.text


# MR-01B: fixture copied from the pre-written MR-01A oracle, never application data.
SEARCH_FIXTURE = [
    ('Kiểm kê cuối kỳ', 'Đối chiếu bán hàng', 'Chi nhánh Bắc', 'Nguyễn An'),
    ('Bán hàng tháng 01', '', 'POS', 'Mai'),
    ('BÁN HÀNG tháng 02', 'Doanh thu', 'ERP', 'Nguyễn An'),
    ('Bao cao ban hang', None, 'POS', 'Minh'),
    ('Hàng bán trả lại', 'Chứng từ hoàn', 'ERP', ''),
    ('Tồn kho', 'Chỉ số bán hàng theo quầy', None, None),
    ('Lợi nhuận', 'Phân tích', 'Bán hàng miền Nam', 'Hà'),
    ('Chi phí', 'Phân tích', 'ERP', 'Bán hàng'),
    ('Ngân sách 100%', 'Giới hạn', 'ERP', 'Lan'),
    ('Mã SKU_A', 'Phân nhóm', 'ERP', 'Lan'),
    ("Đơn O'Brien", 'Đối chiếu', 'Chi nhánh Tây', 'An'),
    ('Cafe', None, None, None),
    ('Café', 'NFC literal', 'Quầy', 'Hà'),
    ('Café', 'NFD literal', 'Quầy', 'Hà'),
    ('Kho  A', 'Hai khoảng trắng giữa', 'WMS', 'An'),
    ('Kho A', 'Một khoảng trắng giữa', 'WMS', 'An'),
    ('Chuỗi NULL', None, None, None),
    ('Rỗng', '', '', ''),
    ('Phân công', 'Người phụ trách', 'CRM', 'Nguyễn An'),
    ('Giá + thuế', 'Tính gộp', 'ERP', 'Lan'),
    ('BÁN HÀNG kết hợp', 'Bán hàng', 'Bán hàng', 'Bán hàng'),
    ('Chỉ dấu %', 'Biểu tượng', None, None),
    ('Chỉ dấu _', 'Biểu tượng', None, None),
    ('Nhật ký tổng hợp!', 'Metadata riêng', 'BACKOFFICE', 'NULL'),
]
