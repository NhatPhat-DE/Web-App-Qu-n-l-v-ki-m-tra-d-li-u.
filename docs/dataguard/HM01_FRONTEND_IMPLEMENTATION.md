# BÁO CÁO TRIỂN KHAI HM-01C: FRONTEND IMPLEMENTATION

**Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)  
**Hạng mục:** HM-01C: Frontend Implementation — Tách tạo Dataset khỏi upload CSV  
**Thời gian hoàn thành:** 03/11/2026  
**Vai trò thực hiện:** Senior React Developer, UX Designer & QA Engineer  

---

## 1. Danh sách file đã sửa & tạo mới

| STT | File | Thao tác | Mô tả thay đổi |
|---|---|---|---|
| 1 | `frontend/src/api/datasets.ts` | Chỉnh sửa | Bổ sung interface `CreateDatasetInput`, `CreatedDataset` và hàm `createDataset(input, signal)` gọi `POST /api/datasets` với payload JSON, xử lý chuẩn hóa khoảng trắng và ánh xạ lỗi tiếng Việt. |
| 2 | `frontend/src/workspace/ui.tsx` | Chỉnh sửa | Mở rộng component `Field` hỗ trợ prop `error?: string`, hiển thị lỗi xác thực ngay dưới input (`.field-validation` màu đỏ) thân thiện với người dùng. |
| 3 | `frontend/src/workspace/CreateDatasetDialog.tsx` | Tạo mới | Component modal chuyên biệt tạo Dataset độc lập chỉ bằng metadata: Tên bộ dữ liệu (bắt buộc, $\le$ 200 ký tự), Người phụ trách (tùy chọn), Nguồn/Bộ phận (tùy chọn), Mô tả (tùy chọn). Chống submit lặp qua state `saving` và `useRef(lock)`. |
| 4 | `frontend/src/workspace/UploadDialog.tsx` | Chỉnh sửa | Nâng cấp kiểm soát schema: Khi Dataset chưa có phiên bản (`dataset.versions.length === 0`), `hasExistingSchema = false` giúp không bị báo lỗi `mismatch` giả khi tải file đầu tiên ($v1$). Đổi tiêu đề phù hợp thành "Tải file CSV đầu tiên". Giữ nguyên tính tương thích ngược cho luồng tải file cũ. |
| 5 | `frontend/src/workspace/CatalogPages.tsx` | Chỉnh sửa | - Nâng cấp `DatasetActions` thêm phương thức `create: () => void`.<br>- Catalog hiển thị trạng thái "Chưa có dữ liệu" khi `version_count = 0` (không dùng mặc định v1).<br>- Trang chi tiết Dataset hiển thị Empty State chuyên biệt ở tab Tổng quan khi chưa có file nào: tiêu đề "Bộ dữ liệu chưa có file nào", nút "Tải file CSV đầu tiên".<br>- Tab Mô tả trường và Phiên bản hiển thị Empty State tương ứng, không sinh bảng rỗng.<br>- Nút tải phiên bản đổi nhãn thông minh: "Tải file CSV đầu tiên" khi rỗng và "Tải phiên bản mới" khi đã có dữ liệu. |
| 6 | `frontend/src/workspace/RuleList.tsx` | Chỉnh sửa | Xử lý an toàn khi Dataset chưa có cột (`dataset.columns.length === 0`): disable nút thêm quy tắc / AI gợi ý quy tắc và hiển thị cảnh báo hướng dẫn người dùng tải file CSV đầu tiên trước khi thiết lập quy tắc. |
| 7 | `frontend/src/workspace/Dashboard.tsx` | Chỉnh sửa | Điều chỉnh các nút hành động "Tạo bộ dữ liệu" và bước 01 quy trình nhanh gọi `actions.create()` mở trực tiếp modal tạo Dataset độc lập. |
| 8 | `frontend/src/workspace/DataCheckApp.tsx` | Chỉnh sửa | Quản lý state modal `kind: 'create'`, kết nối điều hướng tự động: sau khi tạo Dataset thành công, tự động reload Catalog và chuyển hướng URL hash tới `#/datasets/{id}/overview`. |
| 9 | `frontend/package.json` | Chỉnh sửa | Bổ sung script `"test": "node --test tests/*.test.mjs"`. |
| 10 | `frontend/tests/hm01c_frontend.test.mjs` | Tạo mới | Bộ 8 unit/integration test cases kiểm tra validation, schema mismatch, empty state, navigation và xử lý lỗi tiếng Việt. |

---

## 2. So sánh luồng người dùng: Trước và Sau

### Luồng cũ (Trước HM-01C):
1. Người dùng bấm "Tạo bộ dữ liệu".
2. Hệ thống mở cửa sổ `UploadDialog` 4 bước:
   - Bước 1: Nhập thông tin metadata.
   - Bước 2: **Bắt buộc kéo thả file CSV ngay lúc này**.
   - Bước 3: Xem trước dữ liệu CSV.
   - Bước 4: Bấm xác nhận, hệ thống gửi đồng thời cả metadata và file CSV qua `POST /api/datasets/import`.
3. **Bất cập đối với doanh nghiệp SME:**
   - Người quản lý danh mục không thể khai báo trước cấu trúc dữ liệu nếu chưa có sẵn file dữ liệu từ phòng ban.
   - Không có khái niệm rõ ràng về việc quản lý Dataset độc lập với các file phiên bản.

### Luồng mới chuẩn hóa DataGuard SME (Sau HM-01C):
1. **Bước 1 — Khởi tạo Dataset:**
   - Người dùng bấm nút "Tạo bộ dữ liệu" tại Dashboard hoặc Catalog.
   - Xuất hiện form `CreateDatasetDialog` gọn gàng: chỉ yêu cầu Tên bộ dữ liệu (bắt buộc) và các thông tin mô tả, người phụ trách, nguồn dữ liệu (tùy chọn).
   - Bấm "Tạo bộ dữ liệu" $\rightarrow$ gọi `POST /api/datasets` tạo bản ghi Dataset rỗng.
2. **Bước 2 — Điều hướng tự động:**
   - Hệ thống tự động chuyển người dùng đến trang chi tiết Dataset vừa tạo: `#/datasets/{id}/overview`.
   - Hiển thị thông báo thành công: *"Đã tạo bộ dữ liệu mới. Bạn có thể tải file CSV đầu tiên."*
3. **Bước 3 — Trạng thái Dataset rỗng (Empty State):**
   - Banner hướng dẫn nổi bật: **"Bộ dữ liệu chưa có file nào"** — *"Tải file CSV đầu tiên để bắt đầu quản lý và kiểm tra dữ liệu."*
   - Nút hành động chính: **"Tải file CSV đầu tiên"**.
   - Không hiển thị biểu đồ hay trạng thái kiểm tra giả.
   - Danh mục hiển thị trạng thái *"Chưa có dữ liệu"* (không mặc định hiển thị v1).
4. **Bước 4 — Nạp file phiên bản đầu tiên ($v1$):**
   - Bấm "Tải file CSV đầu tiên" $\rightarrow$ mở `UploadDialog` ở bước chọn CSV cho Dataset hiện tại.
   - Chọn file CSV và xem trước $\rightarrow$ Không bị kiểm tra mismatch sai lệch vì chưa có schema cũ.
   - Xác nhận lưu $\rightarrow$ gọi `POST /api/datasets/{id}/versions/import`.
   - Hệ thống tạo $v1$, tự động trích xuất các cột dữ liệu vào `DatasetColumn`.
   - Dataset chuyển sang trạng thái sẵn sàng để thiết lập quy tắc hoặc chạy kiểm tra chất lượng.
5. **Bước 5 — Tải tiếp các phiên bản sau ($v2, v3, \dots$):**
   - Từ trang chi tiết bấm "Tải phiên bản mới".
   - Hệ thống đối chiếu nghiêm ngặt với schema của $v1$: nếu trùng khớp tạo tiếp $v2, v3$; nếu sai cấu trúc báo lỗi rõ ràng.

---

## 3. Các API được gọi

| Endpoint | Method | Trigger từ Frontend | Mục đích |
|---|---|---|---|
| `/api/datasets` | `POST` | `CreateDatasetDialog.tsx` $\rightarrow$ `createDataset()` | Tạo Dataset độc lập chỉ bằng metadata (DG-201, DG-202). |
| `/api/datasets/{id}/versions/import` | `POST` | `UploadDialog.tsx` $\rightarrow$ `importVersion()` | Tải file CSV đầu tiên ($v1$) hoặc các phiên bản tiếp theo ($v2+$) vào Dataset đã tồn tại (DG-205). |
| `/api/datasets` | `GET` | `CatalogPages.tsx` $\rightarrow$ `catalogSelection()` | Tải danh sách bộ dữ liệu hiển thị trên Catalog (DG-206). |
| `/api/datasets/{id}` | `GET` | `CatalogPages.tsx` $\rightarrow$ `fetchDatasetDetail()` | Đọc chi tiết Dataset để render các tab Tổng quan, Trường, Phiên bản, Quy tắc (DG-204). |
| `/api/datasets/import` | `POST` | `UploadDialog.tsx` (luồng tương thích ngược) | Luồng cũ tải kèm CSV vẫn được bảo lưu 100% trong code (DG-207). |

---

## 4. Kết quả kiểm thử

### 4.1. Frontend Unit / Integration Tests (`npm test`)
Thực thi bằng test runner Node.js (`frontend/tests/hm01c_frontend.test.mjs`):
- `DG-202: Validation rejects blank or whitespace-only names`: **PASSED** (1.9ms)
- `DG-202: Validation rejects field lengths exceeding limits`: **PASSED** (0.3ms)
- `DG-204 & DG-205: Empty dataset has no schema mismatch on first upload`: **PASSED** (0.4ms)
- `DG-206: Catalog displays "Chưa có dữ liệu" for empty dataset and does not default to v1`: **PASSED** (0.3ms)
- `DG-204: Empty state titles and buttons conform to requirements`: **PASSED** (0.2ms)
- `DG-201: createDataset payload trims strings and excludes empty optionals`: **PASSED** (0.2ms)
- `DG-203: Standalone creation flow navigates to dataset overview and reuses dataset for CSV upload`: **PASSED** (0.3ms)
- `DG-205: CSV_SCHEMA_MISMATCH produces clear Vietnamese error message`: **PASSED** (0.2ms)

👉 **Kết quả:** **8/8 test cases ĐẠT 100%** trong 126ms.

### 4.2. TypeScript Typecheck & Production Build
- `npm run typecheck` (`tsc --noEmit`): **PASSED** (0 lỗi type).
- `npm run build` (`vite build`): **PASSED** (Bundle thành công 1950 modules trong 1.30s, không có cảnh báo nghiêm trọng).

### 4.3. Backend Integration Tests Regression (`pytest`)
- Chạy toàn bộ 12 test integration HM-01B (`tests/test_dataguard_hm01.py`): **12/12 PASSED** trong 12.94s.
- Cơ sở dữ liệu và API backend hoàn toàn tương thích và không bị ảnh hưởng.

---

## 5. Mô tả các màn hình thay đổi

### 5.1. Modal Tạo Bộ Dữ Liệu Mới (`CreateDatasetDialog`)
- **Tiêu đề:** "Tạo bộ dữ liệu mới".
- **Mô tả:** "Khởi tạo danh mục dữ liệu chỉ bằng thông tin metadata. Bạn có thể tải file CSV sau tại trang chi tiết."
- **Các trường:**
  - *Tên bộ dữ liệu*\* (input text, autofocus, maxLength 200). Hiển thị lỗi đỏ bên dưới nếu để trống hoặc chỉ có khoảng trắng.
  - *Người phụ trách* (input text, tùy chọn, maxLength 200).
  - *Nguồn / bộ phận* (input text, tùy chọn, maxLength 200).
  - *Mô tả* (textarea, tùy chọn, maxLength 2000).
- **Hành động:** Nút "Hủy" và nút "Tạo bộ dữ liệu" (disable khi đang gửi, hiển thị biểu tượng xoay `LoaderCircle`).

### 5.2. Màn hình Chi tiết Dataset Rỗng (Empty State)
- **Tiêu đề trang:** Tên bộ dữ liệu do người dùng vừa đặt.
- **Thanh metadata:** Hiển thị người phụ trách, nguồn dữ liệu và thời gian cập nhật.
- **Tab Tổng quan:**
  - Hero card trung tâm với biểu tượng tìm kiếm dữ liệu.
  - Tiêu đề: **"Bộ dữ liệu chưa có file nào"**.
  - Mô tả: *"Tải file CSV đầu tiên để bắt đầu quản lý và kiểm tra dữ liệu."*
  - Nút chính màu xanh tím: **"Tải file CSV đầu tiên"** (kèm icon `Upload`).
  - Không vẽ biểu đồ donut vi phạm, không hiển thị lần kiểm tra giả, không có chất lượng giả.
- **Tab Mô tả trường:**
  - Hiển thị Empty state: *"Chưa có thông tin trường dữ liệu. Bộ dữ liệu chưa có file nào. Hãy tải file CSV đầu tiên để hệ thống tự động nhận diện các cột."* cùng nút tải file.
- **Tab Phiên bản:**
  - Hiển thị Empty state: *"Chưa có phiên bản dữ liệu. Bộ dữ liệu này chưa có file nào. Hãy tải file CSV đầu tiên để tạo phiên bản v1."*
- **Tab Quy tắc kiểm tra:**
  - Các nút "Thêm quy tắc" và "AI gợi ý quy tắc" bị disable hợp lý kèm cảnh báo: *"Bộ dữ liệu chưa có file dữ liệu nào. Vui lòng tải file CSV đầu tiên để nhận diện các cột trước khi thiết lập quy tắc."*

### 5.3. Màn hình Danh mục Dữ liệu (Catalog)
- Dòng của Dataset rỗng hiển thị cột **Phiên bản mới nhất:** nhãn xám *"Chưa có dữ liệu"* (thay vì cố định `v1` như lỗi trước đây).
- Cột **Kiểm tra gần nhất:** nhãn *"Chưa kiểm tra"*.

### 5.4. Trải nghiệm Responsive trên Mobile & Tablet
- Sử dụng toàn bộ hệ thống breakpoint CSS có sẵn (`max-width: 960px` và `max-width: 720px`).
- Lưới nhập liệu 2 cột trong modal tự động co giãn về 1 cột trên điện thoại (`grid-template-columns: 1fr`).
- Nút bấm và kích thước chữ tự động tối ưu hóa cho màn hình cảm ứng.

---

## 6. Các chức năng được kiểm chứng không bị ảnh hưởng

1. **Dashboard & Tổng quan hệ thống:** Các số liệu đếm tổng bộ dữ liệu, số bộ dữ liệu đã có phiên bản, số lượt kiểm tra và biểu đồ vi phạm hoạt động chính xác.
2. **Quality Engine v5:** Logic kiểm tra, thực thi 7 loại rule (Required, Unique, Pattern, Data Type, Date Format, Numeric Range, Allowed Values) hoàn toàn nguyên vẹn.
3. **Rule Snapshot & Run Comparison:** Đối chiếu giữa 2 lần chạy hoàn tất không bị can thiệp.
4. **Quality Trend & Biểu đồ xu hướng:** Biểu đồ SVG xu hướng chất lượng qua các phiên bản giữ nguyên 100%.
5. **AI Rule Suggestions & Reporting:** Đề xuất quy tắc bằng AI và tính năng xuất báo cáo Excel/CSV/JSON giữ nguyên.
6. **Quản lý tài khoản & Admin:** Trang phân quyền và bảo mật tài khoản nguyên vẹn.
7. **Luồng import CSV cũ:** `POST /api/datasets/import` và logic import kết hợp vẫn được giữ lại hoàn toàn để dự phòng tương thích ngược.

---

## 7. Các vấn đề chưa giải quyết (Nằm ngoài phạm vi HM-01C)

- **Schema Evolution (HM-02):** Hiện tại các phiên bản sau ($v2+$) bắt buộc phải khớp 100% cột với $v1$. Việc cho phép thay đổi cấu trúc cột hoặc ánh xạ cột mới sẽ được giải quyết chuyên sâu tại HM-02 theo đúng lộ trình.
- **Tùy chỉnh định dạng CSV nâng cao:** Tách dấu chấm phẩy, tab hoặc encoding ngoài UTF-8 thuộc các giai đoạn nâng cấp sau.

