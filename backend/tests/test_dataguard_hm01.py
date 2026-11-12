from nv01_fixtures import batch_rule_path
"""HM-01B: Standalone Dataset Creation and Version Ingestion Integration Tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytest
from authenticated_client import TestClient
from fastapi.testclient import TestClient as RawClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from psycopg.errors import CheckViolation
from app.main import app
from app.services import quality_rules
from test_dataset_import import isolated_database


def test_dg101_create_dataset_metadata_only(isolated_database):
    """1. Tạo Dataset chỉ bằng metadata."""
    with TestClient(app) as client:
        body = {
            "name": "Danh sách khách hàng",
            "description": "Dữ liệu khách hàng từ phòng kinh doanh",
            "source": "Phòng kinh doanh",
            "owner": "Nhân viên phụ trách"
        }
        response = client.post(batch_rule_path(client, "/api/datasets"), json=body)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data and isinstance(data["id"], int)
        assert data["name"] == body["name"]
        assert data["description"] == body["description"]
        assert data["source"] == body["source"]
        assert data["owner"] == body["owner"]
        assert "created_at" in data and "updated_at" in data
        assert datetime.fromisoformat(data["created_at"]) is not None


def test_dg101_reject_empty_or_whitespace_name(isolated_database):
    """2. Từ chối tên rỗng hoặc chỉ có khoảng trắng."""
    with TestClient(app) as client:
        for bad_name in ["", "   ", "\t\n", None]:
            body = {"name": bad_name}
            response = client.post(batch_rule_path(client, "/api/datasets"), json=body)
            assert response.status_code == 422
        # NUL character
        response = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "test\x00dataset"})
        assert response.status_code == 422


def test_dg101_reject_oversized_name_and_metadata(isolated_database):
    """3. Từ chối tên vượt giới hạn 200 ký tự."""
    with TestClient(app) as client:
        response = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "a" * 201})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_NAME"

        response = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "valid", "description": "d" * 201})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_METADATA"


def test_dg101_access_control_and_csrf(isolated_database):
    """4. Kiểm tra quyền truy cập: unauthenticated, missing CSRF, bad origin."""
    with RawClient(app) as raw_client:
        # No session cookie -> 401
        res = raw_client.post("/api/datasets", json={"name": "test"})
        assert res.status_code == 401

    with TestClient(app) as client:
        # Invalid CSRF header
        res = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "test"}, headers={"X-CSRF-Token": "bad_token"})
        assert res.status_code == 403

        # Invalid Origin
        res = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "test"}, headers={"Origin": "http://evil.com"})
        assert res.status_code == 403


def test_dg102_empty_dataset_state_across_apis(isolated_database):
    """5. Dataset mới không có phiên bản, cột hay lượt kiểm tra; các API phụ trợ trả lỗi an toàn."""
    with TestClient(app) as client:
        create_res = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Dataset Rỗng", "source": "Finance"}).json()
        dataset_id = create_res["id"]

        # GET detail
        detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}")).json()
        assert detail["id"] == dataset_id
        assert detail["columns"] == []
        assert detail["versions"] == []

        # GET catalog list
        catalog = client.get(batch_rule_path(client, "/api/datasets")).json()
        item = next(it for it in catalog["items"] if it["id"] == dataset_id)
        assert item["version_count"] == 0

        # GET rules -> empty
        rules = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/rules")).json()
        assert rules["items"] == [] and rules["total"] == 0

        # POST rules -> rejected because no columns exist
        rule_res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/rules"), json={
            "name": "col_req", "rule_type": "required", "columns": ["missing_col"], "config": {}
        })
        assert rule_res.status_code == 422
        assert rule_res.json()["error"]["code"] == "INVALID_HEADER"

        # GET runs -> empty
        runs = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/runs")).json()
        assert runs["items"] == [] and runs["total"] == 0

        # GET quality trend -> points empty, total_completed == 0
        trend = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/quality-trend")).json()
        assert trend["points"] == [] and trend["total_completed"] == 0

        # POST AI preview -> 404 because no version exists
        ai_res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/ai-rule-suggestions/preview"), json={
            "version_id": 1, "columns": ["any"], "include_descriptions": True, "include_statistics": True
        })
        assert ai_res.status_code == 404


def test_dg103_import_csv_first_version_v1(isolated_database):
    """6. Import CSV đầu tiên tạo v1, sinh columns và rows."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Khách Hàng v1"}).json()
        dataset_id = ds["id"]

        csv_content = b"customer_id,name,email\n101,Nguyen Van A,a@example.com\n102,Tran Van B,b@example.com"
        res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("customers.csv", csv_content)})
        assert res.status_code == 201
        data = res.json()
        assert data["dataset_id"] == dataset_id
        assert data["version_number"] == 1
        assert data["column_count"] == 3
        assert data["row_count"] == 2

        # Check detail
        detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}")).json()
        col_names = [c["name"] for c in detail["columns"]]
        assert col_names == ["customer_id", "name", "email"]
        assert len(detail["versions"]) == 1
        assert detail["versions"][0]["version_number"] == 1
        assert detail["versions"][0]["row_count"] == 2

        # Check rows
        rows = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/{data['version_id']}/rows")).json()
        assert rows["total"] == 2
        assert rows["items"][0]["values"] == ["101", "Nguyen Van A", "a@example.com"]


def test_dg104_import_csv_second_version_v2(isolated_database):
    """7. Import CSV tiếp theo tạo v2 cùng schema."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Khách Hàng v2"}).json()
        dataset_id = ds["id"]

        # v1
        csv_v1 = b"customer_id,name,email\n101,Nguyen Van A,a@example.com"
        client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("v1.csv", csv_v1)})

        # v2
        csv_v2 = b"customer_id,name,email\n101,Nguyen Van A,a@example.com\n102,Tran Van B,b@example.com\n103,Le C,c@example.com"
        res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("v2.csv", csv_v2)})
        assert res.status_code == 201
        data = res.json()
        assert data["version_number"] == 2
        assert data["column_count"] == 3
        assert data["row_count"] == 3

        detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}")).json()
        assert len(detail["versions"]) == 2
        assert [v["version_number"] for v in detail["versions"]] == [2, 1]


def test_dg104_import_mismatched_schema_rejected(isolated_database):
    """8. Import sai schema trả lỗi CSV_SCHEMA_MISMATCH."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Khách Hàng Schema Mismatch"}).json()
        dataset_id = ds["id"]

        csv_v1 = b"customer_id,name,email\n101,A,a@example.com"
        client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("v1.csv", csv_v1)})

        # Changed column name: full_name instead of name
        csv_bad = b"customer_id,full_name,email\n101,A,a@example.com"
        res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("v2.csv", csv_bad)})
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "CSV_SCHEMA_MISMATCH"

        # Still only 1 version
        detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}")).json()
        assert len(detail["versions"]) == 1


def test_dg103_import_failure_rollback(isolated_database, monkeypatch):
    """9. Import thất bại phải rollback toàn bộ (không để lại cột hoặc version dang dở)."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Rollback Test"}).json()
        dataset_id = ds["id"]

        def factory(*args, **kwargs):
            target = create_engine(*args, **kwargs)
            @event.listens_for(target, "before_cursor_execute")
            def fail(connection, cursor, statement, parameters, context, executemany):
                if statement.startswith("INSERT INTO dataset_rows"):
                    raise IntegrityError("simulated_failure", {}, CheckViolation("simulated_failure"))
            return target

        with monkeypatch.context() as patch:
            patch.setattr(quality_rules, "create_engine", factory)
            res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("v1.csv", b"a,b\n1,2")})
            assert res.status_code == 500

        # Entire transaction rolled back: no columns, no versions
        detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}")).json()
        assert detail["columns"] == []
        assert detail["versions"] == []


def test_dg103_concurrent_imports_serialized(isolated_database):
    """10. Hai yêu cầu import đồng thời không làm hỏng dữ liệu (with_for_update serialize)."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Concurrent Test"}).json()
        dataset_id = ds["id"]

        csv_content = b"x,y\n1,2"
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(
                lambda _: client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("v.csv", csv_content)}),
                range(2)
            ))
        assert all(r.status_code == 201 for r in responses)
        versions = {r.json()["version_number"] for r in responses}
        assert versions == {1, 2}

        detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}")).json()
        assert [c["name"] for c in detail["columns"]] == ["x", "y"]
        assert len(detail["versions"]) == 2


def test_dg105_backward_compatibility_old_import(isolated_database):
    """11. API import cũ POST /api/datasets/import vẫn hoạt động bình thường."""
    with TestClient(app) as client:
        res = client.post(batch_rule_path(client, "/api/datasets/import"), data={
            "name": "Old Import Style",
            "source": "Legacy",
            "owner": "Steward"
        }, files={"file": ("legacy.csv", b"col1,col2\nval1,val2")})
        assert res.status_code == 201
        data = res.json()
        assert data["version_number"] == 1
        assert data["name"] == "Old Import Style"
        assert data["column_count"] == 2
        assert data["row_count"] == 1

        detail = client.get(batch_rule_path(client, f"/api/datasets/{data['dataset_id']}")).json()
        assert detail["name"] == "Old Import Style"
        assert len(detail["columns"]) == 2
        assert len(detail["versions"]) == 1


def test_dg105_quality_engine_and_history_unaffected(isolated_database):
    """12. Quality Engine và lịch sử chạy trên Dataset tạo độc lập rồi nạp CSV hoạt động chuẩn xác."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Quality Check Integration"}).json()
        dataset_id = ds["id"]

        csv_content = b"code,amount\nC001,100\nC002,-50\n,200\nC001,300"
        v1 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/import"), files={"file": ("data.csv", csv_content)}).json()
        version_id = v1["version_id"]

        # Add rules: required on code, numeric_range on amount >= 0, unique on code
        r1 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/rules"), json={
            "name": "code_required", "rule_type": "required", "columns": ["code"], "config": {}
        }).json()
        r2 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/rules"), json={
            "name": "amount_positive", "rule_type": "numeric_range", "columns": ["amount"], "config": {"min": "0", "max": "9999"}
        }).json()
        r3 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/rules"), json={
            "name": "code_unique", "rule_type": "unique", "columns": ["code"], "config": {}
        }).json()

        # Run quality check
        run = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/{version_id}/runs")).json()
        assert run["status"] == "completed"
        assert run["total_rows"] == 4
        assert run["violation_count"] >= 1
        run_id = run["run_id"]

        # Run detail includes rule_snapshot
        run_detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/runs/{run_id}")).json()
        assert len(run_detail["rule_snapshot"]) == 3

        # History and violations API
        history = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/runs")).json()
        assert history["total"] == 1
        violations = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/runs/{run_id}/violations")).json()
        assert violations["total"] == run["violation_count"]
