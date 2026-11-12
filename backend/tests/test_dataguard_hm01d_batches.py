from nv01_fixtures import batch_rule_path
"""HM-01D: DataBatch and Version Lifecycle Tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytest
from src01_fixtures import SupplierTestClient as TestClient
from test_dataset_import import isolated_database
from app.main import app


def test_create_batch_in_dataset(isolated_database):
    """DG-301 & DG-302: Tạo Batch mới trong Dataset bằng metadata."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Khách hàng Doanh nghiệp"}).json()
        dataset_id = ds["id"]

        # Create batch
        body = {
            "name": "Khách hàng tháng 10/2026",
            "description": "Dữ liệu tiếp nhận đợt 1 tháng 10 từ phòng kinh doanh",
            "period_label": "10/2026",
        }
        res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json=body)
        assert res.status_code == 201
        batch = res.json()
        assert batch["id"] > 0
        assert batch["dataset_id"] == dataset_id
        assert batch["name"] == body["name"]
        assert batch["description"] == body["description"]
        assert batch["period_label"] == body["period_label"]
        assert batch["version_count"] == 0
        assert batch["latest_version"] is None
        assert "created_at" in batch and "updated_at" in batch


def test_batch_validation(isolated_database):
    """DG-302: Kiểm tra validation metadata của Batch."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Sản phẩm"}).json()
        dataset_id = ds["id"]

        # Blank or whitespace name
        for bad_name in ["", "   ", "\t\n", None]:
            res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": bad_name})
            assert res.status_code in (422, 400)

        # Name with NUL character
        res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": "Batch\x00Name"})
        assert res.status_code in (422, 400)

        # Name exceeding 200 chars
        res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": "B" * 201})
        assert res.status_code == 422


def test_list_and_search_batches(isolated_database):
    """DG-302: Liệt kê Batch theo Dataset, hỗ trợ phân trang và tìm kiếm q."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Đơn hàng"}).json()
        dataset_id = ds["id"]

        for i in range(1, 6):
            client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={
                "name": f"Đợt {i} Tháng 10/2026",
                "period_label": f"10/{2026 + i}",
            })

        # List all
        res = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches?page=1&page_size=3"))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["page"] == 1

        # Search q
        res_search = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches?q=Đợt 3"))
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert search_data["total"] == 1
        assert search_data["items"][0]["name"] == "Đợt 3 Tháng 10/2026"


def test_patch_batch_metadata(isolated_database):
    """DG-302: Cập nhật tên, mô tả và kỳ dữ liệu của Batch."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Chi phí"}).json()
        dataset_id = ds["id"]

        batch = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": "Tạm tính"}).json()
        batch_id = batch["id"]

        # Patch name and period_label
        patch_res = client.patch(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch_id}"), json={
            "name": "Chi phí chính thức T10",
            "period_label": "T10/2026",
            "description": "Đã đối soát kế toán"
        })
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["name"] == "Chi phí chính thức T10"
        assert updated["period_label"] == "T10/2026"
        assert updated["description"] == "Đã đối soát kế toán"


def test_cross_dataset_batch_boundary_isolation(isolated_database):
    """DG-302: Không thể truy cập hoặc thao tác Batch thuộc Dataset khác."""
    with TestClient(app) as client:
        ds1 = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "DS 1"}).json()
        ds2 = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "DS 2"}).json()

        batch1 = client.post(batch_rule_path(client, f"/api/datasets/{ds1['id']}/batches"), json={"name": "Batch của DS1"}).json()
        batch1_id = batch1["id"]

        # Access batch1 via ds2 should return 404
        assert client.get(batch_rule_path(client, f"/api/datasets/{ds2['id']}/batches/{batch1_id}")).status_code == 404
        assert client.patch(batch_rule_path(client, f"/api/datasets/{ds2['id']}/batches/{batch1_id}"), json={"name": "Hack"}).status_code == 404
        assert client.post(batch_rule_path(client, f"/api/datasets/{ds2['id']}/batches/{batch1_id}/versions/import"), files={"file": ("test.csv", b"a,b\n1,2")}).status_code == 404


def test_upload_v1_and_v2_in_same_batch(isolated_database):
    """DG-303: Tải v1 và bản sửa v2 trong cùng một Batch."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Bán lẻ"}).json()
        dataset_id = ds["id"]

        batch = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={
            "name": "Tháng 10/2026",
            "period_label": "10/2026"
        }).json()
        batch_id = batch["id"]

        # Upload v1 (original file)
        csv_v1 = b"sku,qty,price\nSKU01,10,1000\nSKU02,5,2000"
        res_v1 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch_id}/versions/import"), files={"file": ("sales_oct_raw.csv", csv_v1)})
        assert res_v1.status_code == 201
        v1 = res_v1.json()
        assert v1["batch_id"] == batch_id
        assert v1["version_number"] == 1
        assert v1["row_count"] == 2
        assert v1["column_count"] == 3

        # Upload v2 (fixed file in same batch)
        csv_v2 = b"sku,qty,price\nSKU01,10,1000\nSKU02,5,2000\nSKU03,8,1500"
        res_v2 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch_id}/versions/import"), files={"file": ("sales_oct_fixed.csv", csv_v2)})
        assert res_v2.status_code == 201
        v2 = res_v2.json()
        assert v2["batch_id"] == batch_id
        assert v2["version_number"] == 2
        assert v2["row_count"] == 3

        # Check batch detail contains both versions
        b_detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch_id}")).json()
        assert b_detail["version_count"] == 2
        assert b_detail["versions"][0]["version_number"] == 2
        assert b_detail["versions"][1]["version_number"] == 1


def test_independent_versioning_across_batches(isolated_database):
    """DG-301 & DG-303: Mỗi Batch có chu kỳ phiên bản bắt đầu từ 1 độc lập."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Nhân sự"}).json()
        dataset_id = ds["id"]

        # Batch 1: Tháng 10
        b1 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": "Tháng 10"}).json()
        b1_v1 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{b1['id']}/versions/import"), files={"file": ("t10_v1.csv", b"emp_id,name\nE1,Nam")}).json()
        b1_v2 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{b1['id']}/versions/import"), files={"file": ("t10_v2.csv", b"emp_id,name\nE1,Nam\nE2,Bac")}).json()

        assert b1_v1["version_number"] == 1
        assert b1_v2["version_number"] == 2

        # Batch 2: Tháng 11
        b2 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": "Tháng 11"}).json()
        b2_v1 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{b2['id']}/versions/import"), files={"file": ("t11_v1.csv", b"emp_id,name\nE3,Dong")}).json()

        # Batch 2 version number must restart at 1!
        assert b2_v1["version_number"] == 1
        assert b2_v1["batch_id"] == b2["id"]
        assert b2_v1["version_id"] != b1_v1["version_id"]  # Unique stable version ID


def test_schema_mismatch_rejected_in_batch(isolated_database):
    """DG-303: Kiểm tra cấu trúc cột nghiêm ngặt khi upload vào batch."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Hóa đơn"}).json()
        dataset_id = ds["id"]

        batch = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": "Đợt 1"}).json()
        # v1 defines schema [inv_id, amount]
        client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch['id']}/versions/import"), files={"file": ("v1.csv", b"inv_id,amount\n1,100")})

        # v2 with different column name
        res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch['id']}/versions/import"), files={"file": ("v2.csv", b"inv_id,total\n1,100")})
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "CSV_SCHEMA_MISMATCH"


def test_concurrent_uploads_in_same_batch_serialized(isolated_database):
    """DG-303: Hai yêu cầu upload đồng thời vào cùng một Batch không bị trùng version_number."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Đồng thời"}).json()
        dataset_id = ds["id"]
        batch = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={"name": "Batch đồng thời"}).json()
        batch_id = batch["id"]

        # Initial v1
        client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch_id}/versions/import"), files={"file": ("v1.csv", b"code,val\nA,1")})

        def do_upload(name):
            with TestClient(app) as c:
                return c.post(f"/api/datasets/{dataset_id}/batches/{batch_id}/versions/import", files={"file": (f"{name}.csv", b"code,val\nA,1\nB,2")})

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(do_upload, "worker1")
            fut2 = executor.submit(do_upload, "worker2")
            res1 = fut1.result()
            res2 = fut2.result()

        assert res1.status_code == 201
        assert res2.status_code == 201
        v_numbers = {res1.json()["version_number"], res2.json()["version_number"]}
        assert v_numbers == {2, 3}, f"Expected {2, 3}, got {v_numbers}"


def test_closed_loop_remediation_workflow(isolated_database):
    """DG-304 & DG-306: Closed-loop Remediation: Tạo Batch -> v1 -> Run -> Phát hiện lỗi -> Tải v2 sửa -> Run v2 -> So sánh v1 và v2."""
    with TestClient(app) as client:
        ds = client.post(batch_rule_path(client, "/api/datasets"), json={"name": "Kế toán Công nợ"}).json()
        dataset_id = ds["id"]

        # 1. Tạo batch
        batch = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches"), json={
            "name": "Công nợ T10",
            "period_label": "10/2026",
        }).json()
        batch_id = batch["id"]

        # 2. Upload v1 (file lỗi: amount có giá trị âm)
        csv_v1 = b"code,amount\nC01,100\nC02,-50\nC03,-20\nC04,200"
        v1 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch_id}/versions/import"), files={"file": ("cong_no_v1.csv", csv_v1)}).json()
        v1_id = v1["version_id"]

        # 3. Tạo rule: numeric_range amount >= 0
        rule_res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/rules"), json={
            "name": "Số tiền không được âm",
            "rule_type": "numeric_range",
            "columns": ["amount"],
            "config": {"min": "0", "max": "999999"}
        })
        assert rule_res.status_code == 201

        # 4. Chạy kiểm tra v1
        run_v1_res = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/{v1_id}/runs"))
        assert run_v1_res.status_code == 201
        run_v1 = run_v1_res.json()
        run_v1_id = run_v1["run_id"]

        run_v1_detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/runs/{run_v1_id}")).json()
        assert run_v1_detail["status"] == "completed"
        assert run_v1_detail["error_row_count"] == 2  # C02, C03 vi phạm

        # 5. Sửa file bên ngoài -> Upload v2 vào cùng Batch
        csv_v2 = b"code,amount\nC01,100\nC02,50\nC03,20\nC04,200"
        v2 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/batches/{batch_id}/versions/import"), files={"file": ("cong_no_v2_fixed.csv", csv_v2)}).json()
        v2_id = v2["version_id"]
        assert v2["version_number"] == 2

        # 6. Chạy kiểm tra v2
        run_v2 = client.post(batch_rule_path(client, f"/api/datasets/{dataset_id}/versions/{v2_id}/runs")).json()
        run_v2_id = run_v2["run_id"]

        run_v2_detail = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/runs/{run_v2_id}")).json()
        assert run_v2_detail["status"] == "completed"
        assert run_v2_detail["error_row_count"] == 0  # Tất cả đã được khắc phục!

        # 7. So sánh v1 và v2 qua run-comparison
        comp = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/run-comparison?a_run_id={run_v1_id}&b_run_id={run_v2_id}")).json()
        assert comp["a"]["run_id"] == run_v1_id
        assert comp["b"]["run_id"] == run_v2_id
        assert comp["a"]["error_row_count"] == 2
        assert comp["b"]["error_row_count"] == 0
        assert comp["comparable"] is True
        assert comp["delta"]["error_row_count"] == -2

        # 8. Lọc lịch sử run theo batch_id
        batch_runs = client.get(batch_rule_path(client, f"/api/datasets/{dataset_id}/runs?batch_id={batch_id}")).json()
        assert batch_runs["total"] == 2
        run_ids = {r["run_id"] for r in batch_runs["items"]}
        assert run_ids == {run_v1_id, run_v2_id}
