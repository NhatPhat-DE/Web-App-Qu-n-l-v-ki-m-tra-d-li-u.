# BÁO CÁO TRIỂN KHAI HM-01B: BACKEND IMPLEMENTATION

**Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)  
**Hạng mục:** HM-01B: Backend Implementation — Tách Dataset khỏi CSV upload  
**Thời gian hoàn thành:** 03/11/2026  
**Vai trò thực hiện:** Senior Backend Engineer, Database Architect & QA Engineer  

---

## 1. Danh sách file đã sửa đổi & bổ sung

| STT | Đường dẫn file | Thao tác | Mô tả thay đổi |
|---|---|---|---|
| 1 | `backend/app/services/dataset_metadata.py` | Chỉnh sửa | Bổ sung hàm `create_dataset(metadata: dict) -> dict` thực hiện insert bản ghi `Dataset` độc lập, trả về metadata đầy đủ. |
| 2 | `backend/app/routers/datasets.py` | Chỉnh sửa | Khai báo schema Pydantic `DatasetCreate`, validator `validate_dataset_create`, và endpoint `POST /api/datasets` (HTTP 201) với đầy đủ CSRF/Auth validation. |
| 3 | `backend/app/services/dataset_import.py` | Chỉnh sửa | Nâng cấp hàm `import_version(dataset_id, parsed, filename)`. Nhận diện Dataset chưa có phiên bản (`version_count == 0`), tự động tạo `DatasetColumn` từ header hợp lệ, khởi tạo `DatasetVersion` với `version_number = 1`, batch insert `DatasetRow`, khóa giao dịch bằng `with_for_update()`. Bảo toàn schema matching đối với $v2+$. |
| 4 | `backend/tests/conftest.py` | Chỉnh sửa | Đăng ký suite `test_dataguard_hm01` vào danh mục `BUSINESS_TESTS` để tự động chạy và dọn dẹp dữ liệu test độc lập. |
| 5 | `backend/tests/test_dataguard_hm01.py` | Tạo mới | Bộ 12 Integration Test Cases chuyên biệt cho HM-01B theo ma trận kiểm thử tại `HM01_ACCEPTANCE_TESTS.md`. |

---

## 2. API mới được bổ sung

### `POST /api/datasets` (DG-101)

- **Mục đích:** Khởi tạo Dataset độc lập chỉ từ thông tin metadata nghiệp vụ, không cần tải lên file dữ liệu hoặc khai báo cột trước.
- **Quyền hạn & Bảo mật:**
  - Yêu cầu Authentication (Session-based).
  - Yêu cầu CSRF token (`X-CSRF-Token` header và cookie đối chiếu).
- **Trạng thái HTTP thành công:** `201 Created`

#### Request Body Schema:
```json
{
  "name": "string (bắt buộc, không chỉ chứa khoảng trắng, tối đa 200 ký tự, không chứa null-byte)",
  "description": "string (tùy chọn, tối đa 2000 ký tự)",
  "source": "string (tùy chọn, tối đa 200 ký tự)",
  "owner": "string (tùy chọn, tối đa 200 ký tự)"
}
```

#### Response Body mẫu:
```json
{
  "id": "c1f73ad8-f3d2-4e4b-97e3-0599a0f0275a",
  "name": "Danh sách khách hàng SME",
  "description": "Dữ liệu khách hàng từ phòng kinh doanh",
  "source": "Phòng kinh doanh",
  "owner": "Nguyễn Văn A",
  "created_at": "2026-11-03T00:46:12.345678Z",
  "updated_at": "2026-11-03T00:46:12.345678Z"
}
```

#### Mã lỗi nghiệp vụ:
- `400 Bad Request`: Tên rỗng (`DATASET_NAME_EMPTY`), tên quá 200 ký tự (`DATASET_NAME_TOO_LONG`), mô tả quá dài, hoặc chứa null byte.
- `401 Unauthorized`: Chưa đăng nhập.
- `403 Forbidden`: Thiếu CSRF token hoặc CSRF token không khớp.

---

## 3. Những thay đổi trong Import Service (`dataset_import.py`)

### 3.1. Nhận diện Dataset rỗng vs Dataset đã có dữ liệu
- Cơ chế nhận diện: Truy vấn trực tiếp số lượng phiên bản của Dataset trong giao dịch:
  ```python
  version_count = connection.execute(
      select(func.count()).where(DatasetVersion.dataset_id == dataset_id)
  ).scalar_one()
  ```
- **Không suy đoán chỉ dựa trên việc thiếu header**: Khắc phục triệt để nguy cơ sai lệch khi có dataset đã cấu hình trước nhưng chưa có file.

### 3.2. Luồng tạo phiên bản đầu tiên ($v1$) — DG-103
1. Khóa bản ghi Dataset bằng `select(Dataset).where(Dataset.id == dataset_id).with_for_update()`.
2. Kiểm tra `version_count == 0`:
   - Nếu chưa có `DatasetColumn`: Parser trích xuất và chuẩn hóa header từ CSV, tạo các bản ghi `DatasetColumn` tương ứng.
   - Nếu đã có cột (trường hợp hiếm): Kiểm tra khớp schema với các cột hiện có.
3. Tạo `DatasetVersion` với `version_number = 1`.
4. Batch insert toàn bộ dữ liệu vào `DatasetRow`.
5. Quản lý giao dịch: Giao dịch được commit nguyên khối (`Atomic Transaction`). Nếu xảy ra bất kỳ lỗi nào (định dạng, I/O, database constraint), toàn bộ thay đổi đối với cột, version và dòng đều tự động Rollback, trả trạng thái cơ sở dữ liệu về nguyên trạng.

### 3.3. Bảo toàn luồng các phiên bản tiếp theo ($v2, v3, \dots$) — DG-104
- Nếu `version_count > 0`:
  - Lấy danh sách tên cột hiện tại từ `DatasetColumn`.
  - So sánh đối chiếu nghiêm ngặt với header của file CSV mới.
  - Nếu không trùng khớp hoàn toàn thứ tự và tên cột: Báo lỗi `422 Unprocessable Entity` với mã lỗi `CSV_SCHEMA_MISMATCH`.
  - Nếu khớp: Tìm `max(version_number)` và gán `version_number = max + 1`, thực hiện batch insert `DatasetRow`.
- Giữ nguyên hợp đồng API không sửa đổi `Dataset.updated_at` trong quá trình import version để bảo đảm tính tương thích với các bài test hiện hành (`test_version_import.py`).

### 3.4. Kiểm soát đồng thời (Concurrency Control)
- Sử dụng Row-level Locking (`FOR UPDATE`) trên bảng `datasets` tại thời điểm bắt đầu phiên import version:
  - Ngăn chặn hoàn toàn hiện tượng race-condition khi 2 luồng cùng lúc upload CSV tạo $v1$.
  - Luồng thứ hai buộc phải đợi luồng thứ nhất hoàn tất và sẽ nhìn thấy phiên bản $v1$ đã tồn tại, sau đó kiểm tra schema hợp lệ để tạo tiếp $v2$.

### 3.5. Tương thích ngược (Backward Compatibility) — DG-105
- Endpoint `POST /api/datasets/import` được giữ nguyên vẹn 100%. Luồng người dùng upload CSV trực tiếp tạo cả Dataset và Version 1 tại endpoint này vẫn hoạt động bình thường mà không bị ảnh hưởng.

---

## 4. Kết quả kiểm thử

Toàn bộ kiểm thử được thực thi trên môi trường test cô lập (`TEST_DATABASE_URL` kết nối PostgreSQL test instance `datalens_test`). Database chính `datalens` hoàn toàn nguyên vẹn.

### 4.1. Bộ kiểm thử HM-01B (`test_dataguard_hm01.py`) — 12/12 ĐẠT (100%)

| Test Case | Mô tả kiểm thử | Kết quả | Thời gian |
|---|---|---|---|
| `test_dg101_create_dataset_metadata_only` | Tạo Dataset chỉ bằng metadata, trả về HTTP 201 | **PASSED** | 0.81s |
| `test_dg101_reject_blank_or_whitespace_name` | Từ chối tên rỗng / toàn khoảng trắng (400 DATASET_NAME_EMPTY) | **PASSED** | 0.05s |
| `test_dg101_reject_name_over_200_chars` | Từ chối tên vượt quá 200 ký tự (400 DATASET_NAME_TOO_LONG) | **PASSED** | 0.05s |
| `test_dg101_enforces_auth_and_csrf` | Kiểm tra bắt buộc xác thực và đối soát CSRF token | **PASSED** | 0.05s |
| `test_dg102_empty_dataset_read_apis_safe` | Đọc Dataset rỗng: catalog, detail, rules, runs, trend không lỗi 500 | **PASSED** | 0.16s |
| `test_dg103_import_csv_first_version_creates_v1` | Upload CSV lần đầu vào Dataset rỗng tạo thành công $v1$ và các cột | **PASSED** | 0.44s |
| `test_dg104_import_csv_subsequent_version_creates_v2` | Upload CSV tiếp theo tạo thành công $v2$ khi schema khớp | **PASSED** | 0.44s |
| `test_dg104_import_csv_schema_mismatch_rejected` | Upload CSV sai schema ở phiên bản tiếp theo bị từ chối 422 | **PASSED** | 0.44s |
| `test_dg103_rollback_on_failed_row_insertion` | Rollback giao dịch hoàn toàn nếu batch insert dòng thất bại | **PASSED** | 0.44s |
| `test_dg103_concurrent_first_version_import` | 2 yêu cầu import đồng thời được tuần tự hóa, an toàn dữ liệu | **PASSED** | 0.87s |
| `test_dg105_backward_compatibility_old_import_flow` | API import cũ `POST /api/datasets/import` vẫn hoạt động nguyên vẹn | **PASSED** | 0.46s |
| `test_dg105_quality_engine_and_history_unaffected` | Thực thi Quality Engine v5 và Snapshot trên dataset mới không lỗi | **PASSED** | 0.65s |

### 4.2. Bộ kiểm thử hồi quy toàn diện (Regression Tests) — 56/56 ĐẠT (100%)

Đã thực hiện chạy lại toàn bộ các test suites nghiệp vụ cốt lõi:
- `test_dataset_import.py`: 6 passed
- `test_version_import.py`: 7 passed
- `test_dataset_metadata.py`: 6 passed
- `test_dataset_catalog.py`: 8 passed
- `test_demo_flow.py`: 8 passed
- `test_quality_results.py`: 12 passed
- `test_quality_rules.py`: 9 passed

**Tổng cộng:** **68/68 test cases ĐẠT 100%** (12 HM-01B tests + 56 regression tests). Không có bất kỳ lỗi hồi quy nào.

---

## 5. Những test chưa chạy được và lý do

- **Số lượng:** 0.
- Tất cả 12 kịch bản yêu cầu trong tài liệu nghiệm thu và 56 kịch bản hồi quy đều đã được chạy trực tiếp và thành công 100%.

---

## 6. Trạng thái cơ sở dữ liệu hiện tại

Dữ liệu trên cơ sở dữ liệu PostgreSQL chính (`datalens`) đã được kiểm tra trước và sau khi hoàn thiện code, bảo đảm không có bất kỳ dòng nào bị mất hoặc bị biến đổi:
- **Datasets:** 21 bản ghi (bảo toàn 100%)
- **Dataset Columns:** 79 bản ghi (bảo toàn 100%)
- **Dataset Versions:** 25 bản ghi (bảo toàn 100%)
- **Dataset Rows:** 260 bản ghi (bảo toàn 100%)
- **Quality Rules:** 36 bản ghi (bảo toàn 100%)
- **Quality Runs:** 50 bản ghi (bảo toàn 100%)
- **Rule Violations:** 211 bản ghi (bảo toàn 100%)

---

## 7. Đánh giá rủi ro còn lại

1. **Schema Evolution / Column Mapping:** Hiện tại nếu $v2$ có cột mới, hệ thống sẽ trả lỗi `422 CSV_SCHEMA_MISMATCH`. Đây là hành vi đúng theo phạm vi của HM-01B (không tự ý hỗ trợ schema evolution khi chưa có thiết kế chuyên biệt ở các giai đoạn sau).
2. **Frontend UI:** Giao diện hiện tại chưa có form bấm tạo riêng Dataset độc lập (nút "Tạo Dataset"). Người dùng hiện có thể gọi qua API `POST /api/datasets`. Phần giao diện frontend sẽ được thực hiện tại HM-01C/HM-01 Frontend Phase.

---

## 8. Hướng dẫn kiểm tra API thủ công

### Bước 1: Lấy Session Cookie và CSRF Token
Mở PowerShell hoặc terminal, gửi request đăng nhập vào backend:
```powershell
$loginBody = @{
    email = "admin@example.com"
    password = "adminpassword"
} | ConvertTo-Json

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$res = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/login" `
    -Method Post `
    -Body $loginBody `
    -ContentType "application/json" `
    -WebSession $session

$csrfToken = $session.Cookies.GetCookies("http://127.0.0.1:8000")["csrf_token"].Value
```

### Bước 2: Tạo Dataset độc lập (không kèm file CSV)
```powershell
$createBody = @{
    name = "Dataset Khảo Sát Thị Trường Q4"
    description = "Số liệu thị trường phòng Marketing"
    source = "Phòng Marketing"
    owner = "Trần Thị B"
} | ConvertTo-Json

$dataset = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/datasets" `
    -Method Post `
    -Headers @{ "X-CSRF-Token" = $csrfToken } `
    -Body $createBody `
    -ContentType "application/json" `
    -WebSession $session

$datasetId = $dataset.id
Write-Host "Đã tạo Dataset ID: $datasetId"
```

### Bước 3: Kiểm tra Dataset rỗng trong Catalog và Detail
```powershell
# Xem chi tiết Dataset (phải trả về version_count = 0, columns = [])
$detail = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/datasets/$datasetId" `
    -Method Get `
    -WebSession $session

Write-Host "Số phiên bản hiện tại: " $detail.versions.Count
Write-Host "Số cột hiện tại: " $detail.columns.Count
```

### Bước 4: Upload file CSV để tạo phiên bản đầu tiên ($v1$)
Tạo một file CSV mẫu `test_v1.csv`:
```csv
id,name,age,email
1,Alice,28,alice@example.com
2,Bob,32,bob@example.com
```
Gửi yêu cầu upload qua `POST /api/datasets/{dataset_id}/versions`:
```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/datasets/$datasetId/versions" `
  -H "X-CSRF-Token: $csrfToken" `
  -b "session_id=...; csrf_token=$csrfToken" `
  -F "file=@test_v1.csv"
```
Kết quả trả về phiên bản mới `version_number: 1`, tự động sinh 4 cột `id`, `name`, `age`, `email`.

