# DATAGUARD SME — HM-02D.2: DASHBOARD REBUILD IMPLEMENTATION REPORT

## 1. Thông tin Triển khai

- **Hạng mục**: HM-02D.2 — Task-Oriented Dashboard Rebuild.
- **Dự án**: DataGuard SME.
- **Phạm vi hoàn thành**: Xây dựng lại toàn bộ giao diện Bàn làm việc (Dashboard), chuẩn hóa các khối Quick Actions, 4 thẻ KPI, danh sách Dữ liệu cần chú ý có phân loại và Lượt kiểm tra gần đây theo hướng Task-oriented UX cho doanh nghiệp SME.

---

## 2. Danh mục Tệp đã Tạo và Chỉnh sửa

### A. Tệp tạo mới:
1. `frontend/tests/hm02d2_dashboard.test.mjs`:
   - 8 ca kiểm thử đơn vị chuyên biệt cho Dashboard:
     - Phân loại bộ dữ liệu rỗng (`NO_FILE` $\rightarrow$ Hành động: "Tải file CSV").
     - Phân loại bộ dữ liệu có file nhưng chưa kiểm tra (`NEEDS_RUN` $\rightarrow$ Hành động: "Chạy kiểm tra").
     - Phân loại bộ dữ liệu gặp lỗi kỹ thuật máy chủ (`TECHNICAL_FAILED` $\rightarrow$ Hành động: "Thử lại", phân biệt với lỗi dữ liệu).
     - Phân loại bộ dữ liệu phát hiện lỗi nghiệp vụ (`HAS_ERRORS` $\rightarrow$ Hành động: "Xem lỗi", link kết quả).
     - Phân loại bộ dữ liệu đạt chuẩn (`PASSED` $\rightarrow$ Hành động: "Xem kết quả").
     - Tính toán KPI chính xác từ dữ liệu thực, không suy diễn số liệu ảo.
     - Kiểm tra sự hiện diện của các khối giao diện ARIA trong component.
     - Kiểm tra token CSS và class giao diện trong `design.css`.
2. Tài liệu bàn giao tại `docs/dataguard/`:
   - `HM02D2_DASHBOARD_DESIGN.md`: Bản đặc tả kiến trúc Bàn làm việc dữ liệu cho SME.
   - `HM02D2_IMPLEMENTATION_REPORT.md`: Báo cáo kỹ thuật chi tiết các thay đổi.
   - `HM02D2_TEST_RESULTS.md`: Báo cáo kết quả kiểm thử và nghiệm thu.

### B. Tệp chỉnh sửa:
1. `frontend/src/workspace/Dashboard.tsx`:
   - Tái cấu trúc thành Bàn làm việc dữ liệu chuyên nghiệp cho SME.
   - Xây dựng hàm phân loại `classifyDataset()` phân biệt rõ 5 trạng thái thực tế.
   - Bổ sung thanh thao tác nhanh `quick-actions-bar` (Tạo bộ dữ liệu mới, Xem danh mục, Tiếp tục xử lý, Bật/tắt hướng dẫn).
   - Tối ưu 4 thẻ KPI tổng quan với số liệu xác thực từ API.
   - Xây dựng danh sách **Dữ liệu cần chú ý** kèm 5 tab lọc trạng thái (`Tất cả`, `Có lỗi`, `Chờ kiểm tra`, `Chưa có file`, `Đạt quy tắc`).
   - Xây dựng bảng **Lượt kiểm tra gần đây** kèm số dòng lỗi và liên kết trực tiếp tới màn hình kết quả.
   - Bổ sung khối Onboarding 3 bước và Mẹo làm việc hữu ích ("Sửa file nguồn, giữ nguyên lịch sử").
   - Hỗ trợ Loading skeleton, Empty state và Error state có nút Thử lại.
   - Loại bỏ biểu đồ donut phức tạp cũ để tránh request thừa và tối ưu hóa hiệu năng render.
2. `frontend/src/workspace/DataCheckApp.tsx`:
   - Truyền đầy đủ các trạng thái `loading={catalog.loading}`, `error={catalog.error}` và `onRetry={catalog.reload}` vào `<Dashboard />`.
3. `frontend/src/workspace/design.css`:
   - Bổ sung định dạng CSS cho `.dashboard-workbench`, `.quick-actions-bar`, `.quick-actions-info`, `.quick-actions-buttons`.
   - Bổ sung styles cho `.attention-tabs`, `.attention-tab-btn`, `.attention-item-list`, `.attention-item`, `.attention-item-main`, `.attention-item-info`, `.attention-item-title`, `.attention-dataset-title`, `.attention-item-desc`, `.attention-item-action`.
   - Bổ sung styles cho `.skeleton-grid`, `.skeleton`, `@keyframes skeleton-pulse` và `.button-sm`.
   - Bổ sung các quy tắc responsive dưới `@media (max-width: 960px)` và `@media (max-width: 720px)`.
   - Sử dụng 100% Semantic Tokens từ HM-02C.

---

## 3. Các API Đã Sử Dụng & Công Thức Tính Toán KPI

Dashboard sử dụng dữ liệu được tổng hợp từ client qua các endpoint backend hiện hữu:
- `GET /api/datasets`: Danh sách bộ dữ liệu (tên, mô tả, nguồn, người phụ trách).
- `GET /api/datasets/{id}`: Chi tiết các phiên bản (`versions`) và các cột (`columns`).
- `GET /api/datasets/{id}/runs`: Danh sách các lần kiểm tra chất lượng của từng bộ dữ liệu.

### Công thức tính toán từng KPI (100% từ dữ liệu thực tế, không suy diễn ảo):
1. **Tổng bộ dữ liệu**:
   $$\text{Total Datasets} = \text{datasets.length}$$
2. **Bộ dữ liệu chưa có file**:
   $$\text{Empty Datasets} = \sum [\text{dataset.versions.length} == 0]$$
3. **Bộ dữ liệu cần xem xét**:
   $$\text{Needing Review} = \sum [\text{status} \neq \text{'PASSED'}]$$
   Bao gồm các bộ dữ liệu có dòng lỗi ở lần kiểm tra gần nhất, lỗi kỹ thuật cần chạy lại, hoặc có file nhưng chưa chạy kiểm tra. Phân biệt rõ số dòng có lỗi (`error_row_count`) với số lượt vi phạm quy tắc (`violation_count`).
4. **Lượt kiểm tra hoàn tất**:
   $$\text{Completed Runs} = \sum [\text{run.status} == \text{'completed'}]$$

---

## 4. Những Chức năng Nghiệp vụ được Bảo toàn Tuyệt đối

- [x] Tạo bộ dữ liệu độc lập từ metadata (HM-01).
- [x] Nạp file CSV tạo phiên bản v1, v2, v3 (HM-01B / HM-01C).
- [x] Động cơ kiểm tra chất lượng Quality Engine v5 và Rule Snapshot.
- [x] Đối chiếu kết quả các lần chạy (Run Comparison) và Xu hướng chất lượng (Quality Trend).
- [x] Hệ thống Multi-Theme (System, Light, Dark, Soft) không bị vỡ giao diện.
- [x] Phân quyền người dùng (RBAC) và tuyến đường điều hướng (HM-02D.1).
- [x] Bảo vệ dữ liệu biểu mẫu chưa lưu (`confirmLeave`).
- [x] Không làm gián đoạn bất kỳ endpoint backend nào.

---

## 5. Rủi ro còn lại và Đề xuất

- **Backend Gap**: Hiện tại backend chưa có endpoint riêng dạng `GET /api/dashboard/stats` để trả về thống kê tóm tắt 1 lần; frontend hiện tại phải tổng hợp thông qua `loadCatalog` (duyệt qua danh sách datasets và runs). Với các doanh nghiệp có hàng nghìn bộ dữ liệu, trong tương lai nên đề xuất bổ sung endpoint `GET /api/dashboard/summary` ở phía backend để tối ưu truy vấn SQL phía server.
- **Dừng lại theo quy định**: Hạng mục HM-02D.2 đã hoàn tất toàn diện. Dừng lại tại đây, không tự ý triển khai HM-02D.3.

