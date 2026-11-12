# MA TRẬN TÍNH NĂNG FRONTEND & DANH SÁCH BẢO TOÀN
## HỆ THỐNG DATAGUARD SME

**Hạng mục:** HM-02A — Frontend Feature Matrix & Preservation Checklist  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior Product Designer & Business Analyst  

---

## 1. Ma trận tính năng Frontend hiện tại

| Nhóm chức năng | Tên tính năng | Màn hình / Component | API Backend kết nối | Trạng thái tích hợp | Vai trò hỗ trợ |
|---|---|---|---|---|---|
| **Xác thực & Phiên** | Đăng nhập tài khoản | `SessionApp.tsx` (`LoginForm`) | `POST /api/auth/login` | Đầy đủ | Tất cả |
| | Đăng xuất | `DataCheckApp.tsx` | `POST /api/auth/logout` | Đầy đủ | Tất cả |
| | Kiểm tra phiên & CSRF | `SessionApp.tsx` | `GET /api/auth/me` | Đầy đủ (tự động refresh token) | Tất cả |
| **Quản trị người dùng** | Danh sách tài khoản | `Accounts.tsx` (`AccountList`) | `GET /api/admin/users` | Đầy đủ | Quản trị viên (`admin`) |
| | Tạo tài khoản mới | `Accounts.tsx` (`AccountDialog`) | `POST /api/admin/users` | Đầy đủ | `admin` |
| | Đổi vai trò / Khóa tài khoản | `Accounts.tsx` (`AccountDialog`) | `PATCH /api/admin/users/{id}` | Đầy đủ (thu hồi phiên tức thì) | `admin` |
| **Danh mục dữ liệu** | Tạo Dataset độc lập | `CreateDatasetDialog.tsx` | `POST /api/datasets` | Đầy đủ (HM-01B/C) | Tất cả |
| | Xem danh sách Dataset | `CatalogPages.tsx` (`CatalogPage`) | `GET /api/datasets` | Đầy đủ (hỗ trợ phân trang, tìm kiếm) | Tất cả |
| | Sửa thông tin Dataset | `EditDialogs.tsx` (`MetadataDialog`) | `PATCH /api/datasets/{id}` | Đầy đủ | Tất cả |
| | Sửa mô tả cột | `EditDialogs.tsx` (`MetadataDialog`) | `PATCH /api/datasets/{id}/columns/{colId}` | Đầy đủ | Tất cả |
| | Xem chi tiết Dataset | `CatalogPages.tsx` (`DatasetPage`) | `GET /api/datasets/{id}` | Đầy đủ | Tất cả |
| **Quản lý phiên bản** | Upload CSV tạo v1 | `UploadDialog.tsx` | `POST /api/datasets/{id}/versions/import` | Đầy đủ (HM-01B/C) | Tất cả |
| | Upload CSV tạo v2, v3 | `UploadDialog.tsx` | `POST /api/datasets/{id}/versions/import` | Đầy đủ (bắt buộc khớp schema) | Tất cả |
| | Xem trước dữ liệu dòng | `CatalogPages.tsx` (`PreviewDialog`) | `GET /api/datasets/{id}/versions/{vId}/rows` | Đầy đủ (phân trang 20 dòng) | Tất cả |
| | Suy luận kiểu dữ liệu | `InferenceDetails.tsx` | Thuộc tính `inferred_types` trong version | Đầy đủ (đọc từ backend inference) | Tất cả |
| **Quy tắc kiểm tra** | Danh sách quy tắc | `RuleList.tsx` | `GET /api/datasets/{id}/rules` | Đầy đủ (phân trang server) | Tất cả |
| | Tạo quy tắc thủ công | `EditDialogs.tsx` (`RuleDialog`) | `POST /api/datasets/{id}/rules` | Đầy đủ (hỗ trợ 7 loại quy tắc cốt lõi) | Tất cả |
| | Chỉnh sửa quy tắc | `EditDialogs.tsx` (`RuleDialog`) | `PATCH /api/datasets/{id}/rules/{rId}` | Đầy đủ | Tất cả |
| | Bật / tắt quy tắc | `EditDialogs.tsx` (`RuleDialog`) | `PATCH /api/datasets/{id}/rules/{rId}` | Đầy đủ | Tất cả |
| | AI Gợi ý quy tắc | `AISuggestions.tsx` | `POST /api/ai/preview`, `POST /api/ai/suggest` | Đầy đủ (preview payload + xác nhận) | Tất cả |
| **Thực thi kiểm tra** | Khởi chạy kiểm tra | `RunDialog.tsx` | `POST /api/datasets/{id}/versions/{vId}/runs` | Đầy đủ (chạy qua Quality Engine v5) | Tất cả |
| | Xem chi tiết kết quả | `Results.tsx` | `GET /api/datasets/{id}/runs/{runId}` | Đầy đủ (tự động polling khi đang chạy) | Tất cả |
| | Danh sách vi phạm | `Violations.tsx` | `GET /api/datasets/{id}/runs/{runId}/violations` | Đầy đủ (lọc theo cột, rule, dòng) | Tất cả |
| | Xem dữ liệu dòng vi phạm | `Violations.tsx` (`RecordDialog`) | `GET /api/datasets/{id}/versions/{vId}/rows` | Đầy đủ (xem 1 dòng chi tiết) | Tất cả |
| | Phân tích vi phạm | `Results.tsx` (`Breakdown`) | `GET /api/datasets/{id}/runs/{runId}/summary` | Đầy đủ (theo 4 chiều chất lượng) | Tất cả |
| **Báo cáo & Xuất file** | Xuất CSV danh sách lỗi | `Violations.tsx` (`exportReport`) | Tạo blob CSV phía client | Đầy đủ (UTF-8 có BOM cho Excel) | Tất cả |
| | Tải Báo cáo Excel | `Violations.tsx` (`fetchReport`) | `GET /api/datasets/{id}/runs/{runId}/report/xlsx` | Đầy đủ (file Excel format sẵn) | Tất cả |
| | Tải Báo cáo JSON | `Violations.tsx` (`fetchReport`) | `GET /api/datasets/{id}/runs/{runId}/report/json` | Đầy đủ | Tất cả |
| **Theo dõi chất lượng** | Lịch sử kiểm tra tập trung | `HistoryBrowser.tsx` | `GET /api/datasets/{id}/runs` | Đầy đủ (lọc ngày, status, quality) | Tất cả |
| | Đối chiếu 2 lần kiểm tra | `QualityInsights.tsx` (`Comparison`) | `GET /api/datasets/{id}/runs/compare?a={a}&b={b}` | Đầy đủ (so sánh chênh lệch chỉ số) | Tất cả |
| | Biểu đồ xu hướng | `QualityInsights.tsx` (`QualityTrend`) | `GET /api/datasets/{id}/quality-trend` | Đầy đủ (vẽ đồ thị SVG theo nhóm điều kiện) | Tất cả |
| **Hệ thống & Trợ giúp** | Kiểm tra kết nối dịch vụ | `SystemStatus.tsx` | `GET /api/health`, `GET /api/health/db` | Đầy đủ | Tất cả |
| | Hướng dẫn & Tải CSV mẫu | `Guide.tsx` | Sinh Blob từ file mẫu có sẵn trong code | Đầy đủ (4 file thực hành) | Tất cả |

---

## 2. Danh sách các chức năng cốt lõi BẮT BUỘC BẢO TOÀN khi Redesign

Trong quá trình tái thiết kế frontend tại HM-02, các chức năng và cấu trúc dữ liệu sau **tuyệt đối không được làm gián đoạn, thay đổi hợp đồng hoặc xóa bỏ**:

1. **Quality Engine v5 Execution:**
   - Cơ chế chạy kiểm tra độc lập lưu trữ bất biến (`POST /api/datasets/{id}/versions/{vId}/runs`).
   - Không được thay đổi tham số truyền vào hoặc giả lập kết quả phía client.

2. **Hệ thống 7 loại Quality Rules:**
   - `required`: Không được để trống (bắt buộc).
   - `unique`: Không được trùng lặp giá trị (hỗ trợ đơn cột hoặc tổ hợp nhiều cột).
   - `pattern`: Định dạng mẫu biểu thức chính quy (email hoặc regex).
   - `data_type`: Đúng kiểu dữ liệu cơ bản (`integer`, `decimal`, `boolean`).
   - `date_format`: Đúng định dạng ngày tháng (`YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`).
   - `numeric_range`: Khoảng giá trị số hữu hạn ($min \le x \le max$).
   - `allowed_values`: Danh sách các giá trị hợp lệ cho phép.

3. **Tính bất biến của Rule Snapshot:**
   - Mỗi lần chạy lưu giữ snapshot toàn bộ các quy tắc tại thời điểm kiểm tra. Khi xem lại kết quả cũ, danh sách quy tắc hiển thị phải lấy từ `run.rule_snapshot`, không được lấy theo quy tắc hiện tại của dataset.

4. **Đối chiếu Run Comparison & Quality Trend:**
   - Logic so sánh 2 lần chạy (`fetchRunComparison`) và kiểm tra điều kiện tương thích so sánh (`comparable`, `non_comparable_reasons`).
   - Dữ liệu xu hướng chất lượng từ endpoint `/api/datasets/{id}/quality-trend`.

5. **Bộ xuất báo cáo Excel, JSON và CSV:**
   - Tải file Excel chuyên nghiệp từ `/report/xlsx`.
   - Xuất file CSV lỗi có tiền tố UTF-8 BOM (`\uFEFF`) để Excel tiếng Việt không bị lỗi font chữ.

6. **Phân quyền và bảo mật tài khoản (RBAC):**
   - Phân biệt vai trò `admin` và `data_steward`.
   - Cơ chế xác thực Session cookie và CSRF token validation tự động.

---

## 3. Danh sách các thành phần Frontend có thể TÁI SỬ DỤNG (Reusable Components)

| Tên component | Vị trí file | Khả năng tái sử dụng | Ghi chú điều chỉnh nếu có |
|---|---|---|---|
| `CreateDatasetDialog` | `CreateDatasetDialog.tsx` | **100% tái sử dụng** | Đã được chuẩn hóa validation tiếng Việt trong HM-01C, hoạt động ổn định. |
| `Button`, `Dialog`, `Empty`, `Notice` | `ui.tsx` | **100% tái sử dụng** | Các component nền tảng có khả năng tiếp cận tốt (focus trap, ARIA, keyboard support). |
| `QualityBadge`, `ExecutionBadge` | `ui.tsx` | **100% tái sử dụng** | Hiển thị trạng thái kiểm tra (Đạt quy tắc, Có lỗi dữ liệu, Đang kiểm tra, Thất bại) đồng nhất. |
| `Field` | `ui.tsx` | **100% tái sử dụng** | Đã tích hợp hiển thị inline error `.field-validation` màu đỏ. |
| `DatasetMark` | `ui.tsx` | **100% tái sử dụng** | Tạo biểu tượng nhận diện màu sắc ngẫu nhiên theo tên dataset. |
| `previewCSV`, `parseCSVText`, `samples` | `csv.ts` | **100% tái sử dụng** | Parser CSV client-side kết hợp PapaParse nhanh và bộ file mẫu thực hành tiếng Việt. |
| `RecordDialog` | `Violations.tsx` | **100% tái sử dụng** | Hộp thoại xem chi tiết từng dòng bản ghi dữ liệu. |
| `InferenceDetails` | `InferenceDetails.tsx` | **Tái sử dụng một phần** | Cần đơn giản hóa phần "Chi tiết suy luận" để phù hợp hơn với người dùng không chuyên. |

