# DATAGUARD SME — HM-01D: MIGRATION & DATA BACKFILL REPORT

## 1. Phương án Sao lưu Dự phòng (Database Backup)

Trước khi thực hiện bất kỳ thay đổi nào trên cấu trúc cơ sở dữ liệu `data_catalog`, một bản sao lưu vật lý độc lập (physical clone template database) đã được khởi tạo:

```sql
CREATE DATABASE data_catalog_backup_hm01d WITH TEMPLATE data_catalog;
```

### Thống kê kiểm tra tính toàn vẹn trước Migration:
- **Datasets**: 23 bản ghi
- **Dataset Versions**: 28 bản ghi
- **Dataset Rows**: 335 bản ghi
- **Dataset Columns**: 68 bản ghi
- **Quality Rules**: 41 bản ghi
- **Quality Runs**: 54 bản ghi
- **Violations**: 230 bản ghi

---

## 2. Chi tiết Migration 0009 (`0009_data_batches.py`)

Migration script `0009_data_batches.py` được thiết kế theo nguyên tắc Zero Data Loss và đảm bảo tính tuần tự nguyên tử:

### Bước 1: Khởi tạo bảng `data_batches`
```sql
CREATE TABLE data_batches (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description VARCHAR(2000),
    period_label VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_data_batches_name_nonblank CHECK (trim(name) != ''),
    CONSTRAINT ck_data_batches_updated_after_created CHECK (updated_at >= created_at)
);
CREATE INDEX ix_data_batches_dataset_created ON data_batches (dataset_id, created_at DESC);
```

### Bước 2: Thêm cột `batch_id` tạm thời nullable vào `dataset_versions`
```sql
ALTER TABLE dataset_versions ADD COLUMN batch_id BIGINT REFERENCES data_batches(id) ON DELETE RESTRICT;
```

### Bước 3: Backfill an toàn cho các Dataset & Version hiện có
Hệ thống duyệt qua tất cả Dataset đã có phiên bản:
- Tự động tạo một `DataBatch` mặc định với tên: `"Đợt khởi tạo (Kế thừa)"`, `period_label = 'Kế thừa'`, và thời gian `created_at` tương ứng với phiên bản sớm nhất.
- Cập nhật toàn bộ `batch_id` trong `dataset_versions` tương ứng với ID của `DataBatch` vừa tạo.

```sql
INSERT INTO data_batches (dataset_id, name, description, period_label, created_at, updated_at)
SELECT d.id, 'Đợt khởi tạo (Kế thừa)', 'Đợt dữ liệu được khởi tạo tự động khi nâng cấp mô hình quản lý 3 cấp', 'Kế thừa',
       COALESCE(MIN(v.imported_at), CURRENT_TIMESTAMP), COALESCE(MIN(v.imported_at), CURRENT_TIMESTAMP)
FROM datasets d
JOIN dataset_versions v ON v.dataset_id = d.id
GROUP BY d.id;

UPDATE dataset_versions v
SET batch_id = b.id
FROM data_batches b
WHERE b.dataset_id = v.dataset_id AND b.name = 'Đợt khởi tạo (Kế thừa)';
```

### Bước 4: Khóa chặt ràng buộc và cập nhật Unique Index
```sql
ALTER TABLE dataset_versions ALTER COLUMN batch_id SET NOT NULL;
ALTER TABLE dataset_versions DROP CONSTRAINT IF EXISTS uq_dataset_versions_number;
ALTER TABLE dataset_versions ADD CONSTRAINT uq_dataset_versions_batch_number UNIQUE (batch_id, version_number);
CREATE INDEX ix_dataset_versions_batch_id ON dataset_versions (batch_id);
```

---

## 3. Kết quả xác minh sau Migration

1. **Trạng thái Alembic**: `0009 (head)` — Áp dụng thành công, không gặp lỗi.
2. **Số lượng Batch được tạo tự động**: 22 đợt mặc định cho 22 Dataset có phiên bản dữ liệu. (1 Dataset rỗng không có version nên không tạo batch thừa).
3. **Số phiên bản chưa gán batch (`batch_id IS NULL`)**: **0 bản ghi** (100% được map chính xác).
4. **Toàn vẹn dữ liệu**:
   - Tất cả 28 `dataset_versions` giữ nguyên `version_number`, `row_count`, `file_size_bytes`, `inferred_types`.
   - Tất cả 54 `quality_runs` và 230 `violations` liên kết nguyên vẹn qua `version_id`.
   - Tất cả 41 `quality_rules` hoạt động ổn định.

