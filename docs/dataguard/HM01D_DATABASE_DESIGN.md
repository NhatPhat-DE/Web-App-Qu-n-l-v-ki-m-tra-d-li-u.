# DATAGUARD SME — HM-01D: DATABASE DESIGN SPECIFICATION

## 1. Tổng quan kiến trúc mô hình ba cấp

Để giải quyết triệt để bất cập trong việc quản lý dữ liệu định kỳ (ví dụ: dữ liệu tháng 10, bản sửa tháng 10, dữ liệu tháng 11 bị đánh số phiên bản liên tục gây nhầm lẫn), DataGuard SME nâng cấp cấu trúc dữ liệu từ 2 cấp sang **3 cấp**:

$$\mathbf{Dataset} \longrightarrow \mathbf{DataBatch} \longrightarrow \mathbf{DatasetVersion}$$

```
Dataset (Bộ dữ liệu: e.g. Khách hàng doanh nghiệp)
  ├── DataBatch 1 (Kỳ tiếp nhận: Khách hàng T10/2026)
  │     ├── DatasetVersion v1 (File gốc - 1,200 bản ghi, phát hiện 18 lỗi)
  │     └── DatasetVersion v2 (File đã sửa - 1,200 bản ghi, 0 lỗi - Closed-loop Remediation)
  └── DataBatch 2 (Kỳ tiếp nhận: Khách hàng T11/2026)
        └── DatasetVersion v1 (File gốc mới - 1,450 bản ghi)
```

---

## 2. Chi tiết cấu trúc Bảng & Ràng buộc (Schema & Constraints)

### 2.1. Bảng mới: `data_batches`

| Cột | Kiểu dữ liệu | Ràng buộc | Mục đích & Nghiệp vụ |
| :--- | :--- | :--- | :--- |
| `id` | `BIGINT` | `PRIMARY KEY GENERATED ALWAYS AS IDENTITY` | Định danh duy nhất của đợt dữ liệu |
| `dataset_id` | `BIGINT` | `NOT NULL, REFERENCES datasets(id) ON DELETE CASCADE` | Thuộc về Dataset nào |
| `name` | `VARCHAR(200)` | `NOT NULL, CHECK (trim(name) != '')` | Tên đợt dữ liệu (e.g. Khách hàng tháng 10/2026) |
| `description` | `VARCHAR(2000)`| `NULLABLE` | Ghi chú, mô tả nghiệp vụ |
| `period_label`| `VARCHAR(100)` | `NULLABLE` | Nhãn kỳ dữ liệu (e.g. 10/2026, Q4/2026) |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Thời điểm tạo đợt |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Thời điểm cập nhật |

#### Ràng buộc & Chỉ mục (Indices & Checks):
- `ck_data_batches_name_nonblank`: `CHECK (trim(name) != '')`
- `ck_data_batches_updated_after_created`: `CHECK (updated_at >= created_at)`
- `ix_data_batches_dataset_created`: `CREATE INDEX ix_data_batches_dataset_created ON data_batches (dataset_id, created_at DESC)`

---

### 2.2. Nâng cấp bảng `dataset_versions`

- Thêm cột `batch_id`:
  - Kiểu dữ liệu: `BIGINT NOT NULL REFERENCES data_batches(id) ON DELETE RESTRICT`
  - Chỉ mục: `ix_dataset_versions_batch_id` ON `dataset_versions(batch_id)`
- Thay đổi ràng buộc duy nhất (Unique Constraint):
  - **Hủy bỏ constraint cũ**: `uq_dataset_versions_number` trên `(dataset_id, version_number)`
  - **Thiết lập constraint mới**: `uq_dataset_versions_batch_number` trên `(batch_id, version_number)`
- **Giữ nguyên cột `dataset_id`**: Bảo đảm tương thích ngược tuyệt đối (backward compatibility) cho tất cả các truy vấn JOIN, Quality Rules, Quality Runs và View hiện có.

---

## 3. Tính độc lập của Version Numbering per Batch

Mỗi `DataBatch` quản lý chu kỳ phiên bản độc lập:
1. Khi tạo Batch mới và tải file CSV đầu tiên vào Batch, hệ thống cấp phát `version_number = 1`.
2. Khi tải bản sửa cho Batch đó, hệ thống tự động tăng `version_number = 2, 3, ...` thông qua cơ chế khóa dòng nguyên tử `SELECT ... FOR UPDATE` trên `data_batches`.
3. Batch mới tiếp theo (ví dụ tháng 11) bắt đầu lại từ `version_number = 1`, hoàn toàn tách biệt với Batch tháng 10.

---

## 4. Bảo toàn Quality Engine v5 & Run Comparison

- `quality_runs` liên kết với `dataset_versions(id)` thông qua `version_id`.
- Do `dataset_versions(id)` là khóa chính không thay đổi, Quality Engine v5, Rule Snapshot v5, Violation Details và Lịch sử kiểm tra hoạt động bình thường 100%.
- Bổ sung khả năng lọc theo `batch_id` tại endpoint `/api/datasets/{id}/runs?batch_id={batch_id}`.
- So sánh lần chạy (Run Comparison) hỗ trợ đối chiếu trực tiếp giữa phiên bản gốc (v1) và phiên bản sửa (v2) trong cùng một Batch để tính toán chỉ số cải thiện chất lượng (Remediation Delta).

