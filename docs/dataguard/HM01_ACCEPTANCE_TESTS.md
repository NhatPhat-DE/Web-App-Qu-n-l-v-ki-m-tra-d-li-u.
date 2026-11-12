# HM-01: Tiêu chí và Kịch bản Kiểm thử Nghiệm thu (Acceptance Tests)

**Dự án:** DataGuard SME  
**Hạng mục:** HM-01 — Tách biệt Tạo Dataset khỏi Upload CSV  
**Tài liệu tham chiếu:** `HM01_DATA_CATALOG_DESIGN.md`, `HM01_CHANGE_IMPACT.md`  
**Ngày lập:** Tháng 11/2026  

---

## 1. Mục tiêu và Nguyên tắc Kiểm thử

1. **Bảo toàn dữ liệu cũ:** Tuyệt đối không làm thay đổi các bảng dữ liệu cũ (21 datasets, 57 runs hiện tại).
2. **Kiểm thử độc lập:** Sử dụng cơ chế database kiểm thử riêng biệt (disposable test database) tương tự kịch bản trong `verify-redesign.py` hoặc rollback transaction sau khi test.
3. **Độ phủ toàn diện:** Kiểm tra từ API độc lập, tính an toàn khi rỗng, luồng nạp $v1, v2, v3$, tính tương thích ngược, cho đến giao diện người dùng.

---

## 2. Danh mục Kịch bản Kiểm thử Chi tiết (Acceptance Test Cases)

### Nhóm 1: API Tạo Dataset Độc lập (`POST /api/datasets`)

#### TC-HM01-01: Tạo Dataset thành công với metadata hợp lệ
* **Đầu vào:**
  ```json
  {
    "name": "Báo cáo Doanh thu Miền Bắc",
    "description": "Dữ liệu đối chiếu từ các chi nhánh miền Bắc",
    "source": "Phòng Kế toán",
    "owner": "Trần Thị B"
  }
  ```
  Kèm cookie phiên hợp lệ, Origin `http://127.0.0.1:5173` và `X-CSRF-Token`.
* **Kỳ vọng:**
  * Mã trạng thái: `201 Created`.
  * Response body chứa: `id` (nguyên dương), `name`, `description`, `source`, `owner`, `created_at`, `updated_at`.
  * Trong DB: Bảng `datasets` có đúng 1 dòng mới, bảng `dataset_columns` và `dataset_versions` không có dòng nào thuộc dataset này.

#### TC-HM01-02: Từ chối tạo Dataset khi metadata không hợp lệ
* **Các trường hợp thử nghiệm:**
  1. `name` rỗng: `""` hoặc chỉ có khoảng trắng `"   "`.
  2. `name` chứa ký tự NUL: `"Dataset\x00Name"`.
  3. `owner` hoặc `description` chứa ký tự NUL.
  4. Body chứa trường lạ không cho phép: `{"name": "Test", "extra_field": 123}`.
* **Kỳ vọng:**
  * Mã trạng thái: `422 Unprocessable Entity`.
  * Mã lỗi: `INVALID_NAME` hoặc `INVALID_METADATA` hoặc Pydantic validation error.
  * Không có dữ liệu rác nào được ghi vào cơ sở dữ liệu.

#### TC-HM01-03: Kiểm tra Xác thực và Bảo mật phiên
* **Các trường hợp:**
  1. Gửi request không có cookie `datalens_session` $\rightarrow$ Mã `401 UNAUTHENTICATED`.
  2. Gửi request thiếu header `X-CSRF-Token` $\rightarrow$ Mã `403 CSRF_FAILED`.
  3. Gửi request với Origin không thuộc allowlist (ví dụ: `http://malicious-site.com`) $\rightarrow$ Mã `403` hoặc bị chặn.

---

### Nhóm 2: Trạng thái và Hành vi của Dataset Rỗng (Empty State Lifecycle)

#### TC-HM01-04: Danh sách `GET /api/datasets` với Dataset rỗng
* **Thao tác:** Gọi `GET /api/datasets` sau khi tạo dataset ở TC-01.
* **Kỳ vọng:**
  * Dataset mới xuất hiện trong danh sách.
  * Trường `version_count` có giá trị chính xác là `0`.

#### TC-HM01-05: Chi tiết `GET /api/datasets/{dataset_id}` với Dataset rỗng
* **Thao tác:** Gọi `GET /api/datasets/{id}` của dataset rỗng.
* **Kỳ vọng:**
  * Mã `200 OK`.
  * `columns`: Mảng rỗng `[]`.
  * `versions`: Mảng rỗng `[]`.
  * Thông tin `name`, `description`, `source`, `owner` đầy đủ.

#### TC-HM01-06: Hành vi an toàn của các Endpoint phụ trợ khi Dataset chưa có dữ liệu
* **Các kịch bản:**
  1. `GET /api/datasets/{id}/rules` $\rightarrow$ Trả `200 OK` với `{"items": [], "total": 0, "page": 1, "page_size": 20}`.
  2. `POST /api/datasets/{id}/rules` $\rightarrow$ Bị từ chối với `422 INVALID_HEADER` (do chưa có cột nào để áp dụng quy tắc).
  3. `GET /api/datasets/{id}/runs` $\rightarrow$ Trả `200 OK` với `{"items": [], "total": 0, "page": 1, "page_size": 20}`.
  4. `GET /api/datasets/{id}/quality-trend` $\rightarrow$ Trả `200 OK` với `points: []`, `total_completed: 0`.
  5. `POST /api/datasets/{id}/ai-rule-suggestions/preview` $\rightarrow$ Trả `404 DATASET_VERSION_NOT_FOUND`.

---

### Nhóm 3: Luồng Nạp Phiên bản Dữ liệu ($v1, v2, v3$)

#### TC-HM01-07: Nạp phiên bản đầu tiên ($v1$) vào Dataset rỗng
* **Thao tác:** Gửi `POST /api/datasets/{id}/versions/import` với file `customers_v1.csv` (có 4 cột: `id, customer_name, email, age` và 10 dòng dữ liệu).
* **Kỳ vọng:**
  * Mã trạng thái: `201 Created`.
  * Response: `version_number: 1`, `column_count: 4`, `row_count: 10`.
  * Trong DB:
    * Bảng `dataset_columns` được sinh tự động 4 bản ghi tương ứng với 4 tên cột theo đúng thứ tự (`position` từ 1 đến 4).
    * Bảng `dataset_versions` có 1 bản ghi với `version_number = 1`, `row_count = 10`, `inferred_types` chứa mảng suy luận kiểu cho 4 cột.
    * Bảng `dataset_rows` có đúng 10 bản ghi cho phiên bản này.

#### TC-HM01-08: Nạp phiên bản thứ hai ($v2$) cùng cấu trúc vào Dataset
* **Thao tác:** Gửi `POST /api/datasets/{id}/versions/import` với file `customers_v2.csv` (cùng 4 cột: `id, customer_name, email, age`, 15 dòng dữ liệu).
* **Kỳ vọng:**
  * Mã trạng thái: `201 Created`.
  * Response: `version_number: 2`, `column_count: 4`, `row_count: 15`.
  * Bảng `dataset_columns` **không bị duplicate**, vẫn giữ nguyên 4 cột ban đầu.
  * Bảng `dataset_versions` có thêm bản ghi $v2$.

#### TC-HM01-09: Chặn nạp phiên bản ($v3$) có cấu trúc sai lệch (Schema Mismatch)
* **Thao tác:** Gửi `POST /api/datasets/{id}/versions/import` với file `customers_v3_invalid.csv` (đổi tên cột `age` thành `customer_age` hoặc đổi vị trí cột).
* **Kỳ vọng:**
  * Mã trạng thái: `422 Unprocessable Entity`.
  * Mã lỗi: `CSV_SCHEMA_MISMATCH`.
  * Thông báo: *"Tên và thứ tự cột phải khớp bộ dữ liệu. Hãy tạo bộ dữ liệu khác nếu cấu trúc thay đổi."*
  * Không tạo ra version rác trong cơ sở dữ liệu.

---

### Nhóm 4: Tính Tương thích Ngược (Backward Compatibility)

#### TC-HM01-10: Nạp file qua endpoint cũ `POST /api/datasets/import`
* **Thao tác:** Gửi request multipart gồm file CSV và form metadata đến `POST /api/datasets/import`.
* **Kỳ vọng:**
  * Mã `201 Created`.
  * Tạo đồng thời Dataset và version 1 như thiết kế ban đầu.
  * Đảm bảo mọi script kiểm thử cũ không bị gãy.

---

### Nhóm 5: Kiểm thử Giao diện Người dùng (Frontend E2E / UI Tests)

#### TC-HM01-11: Trải nghiệm người dùng tạo Dataset độc lập
1. **Bước 1:** Tại trang Danh mục dữ liệu (`#/datasets`), bấm nút **"Tạo bộ dữ liệu"**.
2. **Bước 2:** Màn hình hiển thị dialog tạo mới: Chỉ yêu cầu nhập Tên bộ dữ liệu, Nguồn/bộ phận, Người phụ trách và Mô tả. Không yêu cầu đính kèm file CSV.
3. **Bước 3:** Bấm nút **"Lưu bộ dữ liệu"** $\rightarrow$ Hệ thống gọi `POST /api/datasets` $\rightarrow$ Thông báo thành công và chuyển hướng người dùng đến trang chi tiết của bộ dữ liệu mới tạo (`#/datasets/{id}/overview`).
4. **Bước 4:** Tại trang chi tiết:
   * Header hiển thị: *"Chưa tải file"*.
   * Khối hành động hiển thị: *"Tải phiên bản CSV đầu tiên"*, đi kèm nút hành động **"Tải CSV"**.
   * Tab *Mô tả trường* và *Quy tắc* hiển thị trạng thái hướng dẫn người dùng tải phiên bản đầu tiên trước khi cấu hình.
5. **Bước 5:** Bấm **"Tải CSV"** $\rightarrow$ Chọn file $\rightarrow$ Xem trước dữ liệu $\rightarrow$ Bấm lưu $\rightarrow$ Sinh phiên bản $v1$ và mở khóa toàn bộ các tính năng đặt quy tắc và chạy kiểm tra.

---

## 3. Tiêu chí Hoàn thành Hạng mục (Definition of Done - DoD)

* [ ] Tất cả 12 test cases trên đạt trạng thái **PASS**.
* [ ] Kiểm tra checksum 7 bảng nghiệp vụ cũ trước và sau khi chạy test không phát hiện bất kỳ sự biến đổi bất thường nào đối với dữ liệu lịch sử.
* [ ] Lệnh `npm run build` ở thư mục frontend đạt **0 lỗi TypeScript**.
* [ ] Kiểm tra `git status` / diff chỉ chạm đúng các file được liệt kê trong tài liệu `HM01_CHANGE_IMPACT.md`.

