# BẢN ĐỐI CHIẾU BẢO TOÀN TÍNH NĂNG & KHOẢNG TRỐNG BACKEND
## HỆ THỐNG DATAGUARD SME

**Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)  
**Hạng mục:** HM-02B: Feature Preservation & Backend Gap Analysis  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior Business Analyst & QA Architect  

---

## 1. Bảng đối chiếu Tính năng cũ $\rightarrow$ Vị trí Giao diện mới

| Mã tính năng | Tên tính năng trong DataCheck cũ | Vị trí màn hình cũ | Vị trí giao diện mới (HM-02B) | API Backend tương ứng | Trạng thái bảo toàn |
|---|---|---|---|---|---|
| **FP-01** | Tạo bộ dữ liệu độc lập | `UploadDialog` (sau HM-01C: `CreateDatasetDialog`) | Nút "Tạo bộ dữ liệu mới" trên Dashboard & Catalog $\rightarrow$ `CreateDatasetDialog` | `POST /api/datasets` | **Bảo toàn 100%** |
| **FP-02** | Xem danh sách hồ sơ dữ liệu | `CatalogPages.tsx` | Menu `Bộ dữ liệu` (`#/datasets`) | `GET /api/datasets` | **Bảo toàn 100%** |
| **FP-03** | Chỉnh sửa tên, người phụ trách, nguồn | `EditDialogs.tsx` (`MetadataDialog`) | Tab `Cấu trúc & Thông tin` $\rightarrow$ Nút "Chỉnh sửa thông tin" | `PATCH /api/datasets/{id}` | **Bảo toàn 100%** |
| **FP-04** | Chỉnh sửa mô tả cột | `EditDialogs.tsx` (`MetadataDialog` column) | Tab `Cấu trúc & Thông tin` $\rightarrow$ Bảng danh sách cột $\rightarrow$ Nút bút chì | `PATCH /api/datasets/{id}/columns/{colId}` | **Bảo toàn 100%** |
| **FP-05** | Nạp CSV tạo phiên bản đầu tiên ($v1$) | `UploadDialog.tsx` | Tab `Kiểm tra dữ liệu` $\rightarrow$ Empty State banner $\rightarrow$ Kéo thả CSV | `POST /api/datasets/{id}/versions/import` | **Bảo toàn 100%** |
| **FP-06** | Nạp CSV các phiên bản tiếp theo ($v2+$) | `UploadDialog.tsx` | Tab `Kiểm tra dữ liệu` $\rightarrow$ Nút "Tải lên bản đã sửa" | `POST /api/datasets/{id}/versions/import` | **Bảo toàn 100%** |
| **FP-07** | Xem trước dữ liệu dòng | `CatalogPages.tsx` (`PreviewDialog`) | Tab `Kiểm tra dữ liệu` $\rightarrow$ Nút "Xem trước dữ liệu gốc" | `GET /api/datasets/{id}/versions/{vId}/rows` | **Bảo toàn 100%** |
| **FP-08** | Hiển thị suy luận kiểu dữ liệu | `InferenceDetails.tsx` | Tab `Cấu trúc & Thông tin` $\rightarrow$ Cột "Kiểu dữ liệu đề xuất" | Thuộc tính `inferred_types` trong `DatasetVersion` | **Bảo toàn 100%** |
| **FP-09** | 7 loại quy tắc kiểm tra cốt lõi | `EditDialogs.tsx` (`RuleDialog`) | Tab `Kiểm tra dữ liệu` $\rightarrow$ Quick Rule Matrix & Modal quy tắc nâng cao | `POST /api/datasets/{id}/rules` | **Bảo toàn 100%** |
| **FP-10** | Bật / tắt quy tắc kiểm tra | `RuleList.tsx` | Tab `Kiểm tra dữ liệu` $\rightarrow$ Cột checkbox bật/tắt trong ma trận | `PATCH /api/datasets/{id}/rules/{rId}` | **Bảo toàn 100%** |
| **FP-11** | Gợi ý quy tắc bằng AI | `AISuggestions.tsx` | Tab `Kiểm tra dữ liệu` $\rightarrow$ Nút "Gợi ý bằng AI" (Thẻ tiếng Việt, ẩn JSON thô) | `POST /api/ai/preview`, `POST /api/ai/suggest` | **Bảo toàn 100%** |
| **FP-12** | Thực thi Quality Engine v5 | `RunDialog.tsx` | Tab `Kiểm tra dữ liệu` $\rightarrow$ Nút "Bắt đầu kiểm tra ngay" | `POST /api/datasets/{id}/versions/{vId}/runs` | **Bảo toàn 100%** |
| **FP-13** | Xem kết quả kiểm tra & Snapshot quy tắc | `Results.tsx` | Tab `Kiểm tra dữ liệu` (Khu vực kết quả) hoặc route `#/datasets/{id}/runs/{runId}` | `GET /api/datasets/{id}/runs/{runId}` | **Bảo toàn 100%** |
| **FP-14** | Danh sách dòng vi phạm | `Violations.tsx` | Tab `Kiểm tra dữ liệu` $\rightarrow$ Bảng vi phạm (có thêm cột số dòng Excel) | `GET /api/datasets/{id}/runs/{runId}/violations` | **Bảo toàn 100%** |
| **FP-15** | Xem toàn bộ giá trị 1 dòng vi phạm | `Violations.tsx` (`RecordDialog`) | Nút [👁️ Xem dòng] tại bảng lỗi $\rightarrow$ Modal xem bản ghi | `GET /api/datasets/{id}/versions/{vId}/rows?page={row}&page_size=1` | **Bảo toàn 100%** |
| **FP-16** | Phân tích vi phạm 4 chiều chất lượng | `Results.tsx` (`Breakdown`) | Tab `Kiểm tra dữ liệu` $\rightarrow$ Mục "Phân tích vi phạm chuyên sâu" (thu gọn) | `GET /api/datasets/{id}/runs/{runId}/quality-summary` | **Bảo toàn 100%** |
| **FP-17** | Xuất file CSV lỗi | `Violations.tsx` | Nút "Xuất file CSV lỗi" | Tạo file CSV UTF-8 BOM phía client | **Bảo toàn 100%** |
| **FP-18** | Tải báo cáo Excel (.xlsx) | Dropdown chọn định dạng trong `Violations.tsx` | **Nút bấm chính màu xanh lá:** "Tải báo cáo Excel (.xlsx)" | `GET /api/datasets/{id}/runs/{runId}/report.xlsx` | **Bảo toàn 100% (Nâng cấp vị trí)** |
| **FP-19** | Tải báo cáo JSON | Dropdown chọn định dạng trong `Violations.tsx` | Nút tùy chọn tải JSON trong mục kỹ thuật | `GET /api/datasets/{id}/runs/{runId}/report` | **Bảo toàn 100%** |
| **FP-20** | Lịch sử kiểm tra tập trung | `HistoryBrowser.tsx` | Menu chính `Lịch sử & Báo cáo` (`#/history`) | `GET /api/datasets/{id}/runs` | **Bảo toàn 100%** |
| **FP-21** | Đối chiếu 2 lần kiểm tra (Compare) | `QualityInsights.tsx` (`Comparison`) | Tab `Lịch sử & Cải thiện` $\rightarrow$ Thẻ đối chiếu tự động 1-click & Trang đối chiếu | `GET /api/datasets/{id}/run-comparison` | **Bảo toàn 100% (Tối ưu hóa)** |
| **FP-22** | Biểu đồ xu hướng chất lượng | `QualityInsights.tsx` (`QualityTrend`) | Tab `Lịch sử & Cải thiện` $\rightarrow$ Đồ thị xu hướng (loại bỏ hiển thị mã băm) | `GET /api/datasets/{id}/quality-trend` | **Bảo toàn 100%** |
| **FP-23** | Quản lý tài khoản người dùng | `Accounts.tsx` | Menu `Quản trị tài khoản` (`#/accounts` - chỉ Admin) | `GET / POST / PATCH /api/admin/users` | **Bảo toàn 100%** |
| **FP-24** | Kiểm tra kết nối dịch vụ | `SystemStatus.tsx` | Nút "Trạng thái hệ thống" dưới chân Sidebar | `GET /api/health`, `GET /api/health/db` | **Bảo toàn 100%** |
| **FP-25** | Hướng dẫn sử dụng & CSV mẫu | `Guide.tsx` | Menu `Trợ giúp & Mẫu file` (`#/guide`) | Client-side Blobs (`khach-hang-co-loi.csv`, v.v.) | **Bảo toàn 100%** |

---

## 2. Xác định các khoảng trống Backend (Backend Gaps & Constraints)

Nhằm đảm bảo thiết kế UI không bị "ảo tưởng tính năng" (Vaporware), các ràng buộc kỹ thuật thực tế của backend được ghi nhận rõ ràng:

### 2.1. Xóa cứng quy tắc kiểm tra (Hard Delete Rule)
- **Hiện trạng Backend:** Router [`backend/app/routers/rules.py`](file:///d:/UserFile/DNCN/Webb/backend/app/routers/rules.py) **hoàn toàn không có endpoint `DELETE /api/datasets/{id}/rules/{rule_id}`**.
- **Giải pháp UX:** Không thiết kế nút "Xóa vĩnh viễn" gọi lệnh DELETE (sẽ gây lỗi 405 Method Not Allowed). Thay vào đó, thiết kế nút gạt **"Bật / Tắt điều kiện"** hoặc thao tác **"Tắt áp dụng"** bằng cách gọi `PATCH /api/datasets/{id}/rules/{rule_id}` với `{"is_active": false}`.

### 2.2. Tiến hóa cấu trúc cột khi nạp phiên bản mới (Schema Evolution & Mapping)
- **Hiện trạng Backend:** Service [`dataset_import.py`](file:///d:/UserFile/DNCN/Webb/backend/app/services/dataset_import.py) kiểm tra nghiêm ngặt danh sách cột của phiên bản sau so với phiên bản trước. Nếu tên hoặc thứ tự cột thay đổi, backend trả mã lỗi `422 CSV_SCHEMA_MISMATCH`. Backend chưa hỗ trợ tính năng chọn ghép cột (Column Mapping) hoặc thêm cột mới tự động.
- **Giải pháp UX:** 
  - Giao diện nạp phiên bản $v2+$ giữ nguyên kiểm tra schema.
  - Khi có lỗi `CSV_SCHEMA_MISMATCH`, hiển thị bảng đối chiếu rõ ràng: *Cột thiếu là gì? Cột thừa là gì?* Hướng dẫn người dùng sửa lại file Excel cho đúng cấu trúc ban đầu, tránh gây hiểu nhầm rằng hệ thống tự động merge cột được.

### 2.3. Hỗ trợ đọc trực tiếp file Excel (.xlsx) phía máy chủ
- **Hiện trạng Backend:** Endpoint upload [`datasets.py#L148`](file:///d:/UserFile/DNCN/Webb/backend/app/routers/datasets.py#L148) kiểm tra đuôi mở rộng bắt buộc kết thúc bằng `.csv` và đọc luồng byte UTF-8. Backend chưa có thư viện nạp file `.xlsx` trực tiếp qua API upload.
- **Giải pháp UX:**
  - Hướng dẫn rõ ràng tại vùng kéo thả: *"Hệ thống hỗ trợ file .csv (UTF-8). Nếu bạn đang dùng Excel (.xlsx), hãy vào File $\rightarrow$ Save As $\rightarrow$ chọn định dạng CSV UTF-8."*
  - Bổ sung nút bấm tải file hướng dẫn chuyển đổi nhanh 1 phút.

### 2.4. Đối chiếu chính xác số dòng lỗi đã sửa giữa v1 và v2
- **Hiện trạng Backend:** API `/run-comparison` chỉ so sánh tổng số bản ghi và tổng số bản ghi lỗi giữa hai lần chạy (ví dụ: $v1$ có 20 lỗi, $v2$ có 5 lỗi $\rightarrow$ chênh lệch giảm 15 dòng lỗi). Backend không theo dõi định danh từng dòng (Row tracking ID) để khẳng định dòng X cụ thể đã được sửa.
- **Giải pháp UX:** Không viết câu khẳng định: *"Dòng số 5 đã được sửa"*. Thay vào đó, viết câu thống kê chính xác: *"Số dòng có lỗi đã giảm từ 20 dòng xuống còn 5 dòng (-75% dòng lỗi)"*.

