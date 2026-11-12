# DATAGUARD SME — HM-01D: BACKEND IMPLEMENTATION REPORT

## 1. Tổng quan các thay đổi Backend

Backend được triển khai đầy đủ hỗ trợ nghiệp vụ quản lý dữ liệu 3 cấp (Dataset -> DataBatch -> DatasetVersion), bảo toàn 100% Quality Engine v5 và các chức năng hiện có.

---

## 2. Danh sách API Endpoints mới

| Phương thức | Đường dẫn | Tham số & Body | Mô tả nghiệp vụ |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/datasets/{id}/batches` | `{ "name": str, "period_label"?: str, "description"?: str }` | Tạo đợt dữ liệu mới trong Dataset (DG-302) |
| `GET` | `/api/datasets/{id}/batches` | Query params: `page`, `page_size`, `q` | Liệt kê danh sách đợt dữ liệu có phân trang, tìm kiếm và tổng số phiên bản |
| `GET` | `/api/datasets/{id}/batches/{batch_id}` | Path: `id`, `batch_id` | Lấy chi tiết đợt dữ liệu và toàn bộ danh sách phiên bản, kết quả kiểm tra tương ứng |
| `PATCH` | `/api/datasets/{id}/batches/{batch_id}` | `{ "name"?: str, "period_label"?: str, "description"?: str }` | Cập nhật thông tin đợt dữ liệu |
| `GET` | `/api/datasets/{id}/batches/{batch_id}/versions` | Path: `id`, `batch_id` | Lấy danh sách các phiên bản trực thuộc đợt dữ liệu |
| `POST` | `/api/datasets/{id}/batches/{batch_id}/versions/import` | `multipart/form-data: file (CSV)` | Tải file dữ liệu vào đợt (tự động cấp phát v1 nếu đợt rỗng, hoặc v2, v3... cho bản sửa) |

### Nâng cấp API Run History (DG-304):
- `GET /api/datasets/{id}/runs`: Bổ sung tham số truy vấn `batch_id: int | None = None`. Cho phép lọc lịch sử chạy kiểm tra theo từng đợt dữ liệu cụ thể.

---

## 3. Kiến trúc dịch vụ (Services Implementation)

### 3.1. Service `backend/app/services/data_batches.py`
Xử lý toàn bộ logic nghiệp vụ cho DataBatch:
- `create_batch`: Kiểm tra dataset tồn tại, validate tên không rỗng, chèn bản ghi mới.
- `list_batches`: Truy vấn danh sách đợt với subquery đếm `version_count`, tìm kiếm NFC ilike qua `name`, `period_label`, `description`, sắp xếp giảm dần theo thời gian tạo.
- `get_batch`: Truy vấn thông tin đợt kèm danh sách `versions` và `latest_run` của từng phiên bản để phục vụ hiển thị Closed-loop Remediation.
- `patch_batch`: Cập nhật metadata đợt dữ liệu.
- `list_batch_versions`: Truy vấn các phiên bản thuộc đợt.
- `serialize_dt`: Chuyển đổi an toàn các đối tượng `datetime` sang chuỗi ISO trước khi phản hồi JSON.

### 3.2. Quản lý phiên bản nguyên tử (Concurrency & Locking) in `dataset_import.py`
Trong hàm `import_version`:
1. Sử dụng khóa cấp dòng `SELECT ... FROM data_batches WHERE id = :batch_id FOR UPDATE` để ngăn chặn tranh chấp ghi (Race Condition) khi nhiều tiến trình upload file đồng thời.
2. Tự động tính toán `version_number`:
   ```python
   latest_number = connection.execute(
       select(func.max(DatasetVersion.version_number)).where(
           DatasetVersion.batch_id == batch_id
       )
   ).scalar_one_or_none()
   version_number = (latest_number or 0) + 1
   ```
3. Kiểm tra tính đồng nhất Schema: Nếu Dataset đã có schema (từ các phiên bản trước), phiên bản mới trong Batch bắt buộc phải có thứ tự và tên cột khớp 100%. Nếu không khớp, trả mã lỗi nghiệp vụ `CSV_SCHEMA_MISMATCH`.

### 3.3. Tương thích ngược với luồng cũ
- Nếu gọi `POST /api/datasets/{id}/versions/import` mà không truyền `batch_id`, hệ thống tự động tìm đợt mới nhất của Dataset hoặc tự tạo đợt mặc định `"Đợt chính"`.
- Luồng `POST /api/datasets/import` (tạo Dataset kèm file đầu tiên) tự động khởi tạo một `DataBatch` mang tên `"Đợt 1"` và gắn file v1 vào đợt này.

