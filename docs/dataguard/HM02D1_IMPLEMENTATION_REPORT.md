# DATAGUARD SME — HM-02D.1: CORE LAYOUT & NAVIGATION IMPLEMENTATION REPORT

## 1. Thông tin Triển khai

- **Hạng mục**: HM-02D.1 — Core Layout & Navigation.
- **Dự án**: DataGuard SME.
- **Mục tiêu đạt được**: Chuẩn hóa toàn bộ khung điều hướng (Sidebar, Topbar, Workspace Tab Groups, Breadcrumb, Routing Aliases) theo định hướng Task-oriented UX cho đối tượng SME, bảo toàn 100% chức năng và tương thích ngược hoàn toàn.

---

## 2. Danh mục Tệp đã Tạo và Chỉnh sửa

### A. Tệp tạo mới:
1. `frontend/tests/hm02d1_navigation.test.mjs`:
   - 6 ca kiểm thử chuyên sâu về điều hướng:
     - Logic chuẩn hóa route và chuyển đổi alias (`home`, `reports`, `admin`, `help`, `datasets/:id`).
     - Cấu trúc menu Sidebar và phân quyền `adminOnly`.
     - Phân nhóm 3 tầng nghiệp vụ trong Workspace Dataset.
     - Cấu trúc Breadcrumb phân cấp và tích hợp `ThemeSwitcher`.
     - Sự tồn tại của CSS Tokens và class cho layout mới trong `design.css`.
     - Kiểm tra bảo vệ thay đổi chưa lưu (`confirmLeave`).
2. Tài liệu đặc tả và kiểm thử tại `docs/dataguard/`:
   - `HM02D1_ROUTE_MAPPING.md`: Bảng ma trận ánh xạ toàn diện 19 route và alias.
   - `HM02D1_IMPLEMENTATION_REPORT.md`: Báo cáo chi tiết kỹ thuật triển khai.
   - `HM02D1_TEST_RESULTS.md`: Kết quả kiểm thử hồi quy và kiểm thử giao diện.

### B. Tệp chỉnh sửa:
1. `frontend/src/workspace/DataCheckApp.tsx`:
   - Chuẩn hóa hàm phân giải route `normalizeRoute(hash)` với hỗ trợ alias thông minh.
   - Chuẩn hóa danh sách menu điều hướng chính `MAIN_NAVIGATION`:
     * Trang chủ (`#/dashboard`)
     * Bộ dữ liệu (`#/datasets`)
     * Lịch sử & Báo cáo (`#/history`)
     * Quản trị (`#/accounts`) — Tự động ẩn với vai trò `data_steward`, chỉ hiển thị cho `admin`.
     * Trợ giúp (`#/guide`)
   - Nâng cấp nhận diện thương hiệu DataGuard SME trong Sidebar (`DataGuard SME · Quản lý dữ liệu doanh nghiệp`, avatar `DG`).
   - Xây dựng thành phần Breadcrumb phân cấp đa tầng (Root $\rightarrow$ Parent $\rightarrow$ Leaf Tab / Run), có thể nhấp chuột để chuyển nhanh cấp độ.
   - Tích hợp bảo vệ phiên làm việc và cảnh báo form chưa lưu trên cả điều hướng hash và nút Đăng xuất.
   - Bổ sung bảo vệ màn hình quản trị: nếu người dùng phi quản trị cố tình vào `#/accounts`, hệ thống hiển thị thông báo quyền hạn rõ ràng thay vì lỗi.
2. `frontend/src/workspace/CatalogPages.tsx`:
   - Tái cấu trúc thanh điều hướng tab bên trong `DatasetPage` thành 3 nhóm nghiệp vụ:
     * **Kiểm tra dữ liệu**: `Tổng quan`, `Quy tắc kiểm tra`
     * **Lịch sử & Cải thiện**: `Lịch sử kiểm tra`, `Đối chiếu lần chạy`, `Xu hướng chất lượng`
     * **Cấu trúc & Thông tin**: `Cột & Kiểu dữ liệu`, `Phiên bản dữ liệu`
   - Cung cấp giao diện trực quan với thẻ phân nhóm `workspace-tab-group` và nút tab `workspace-tab-btn`.
   - Giữ nguyên 100% hash URL cũ cho từng tab để bảo toàn mọi bookmark/deep link.
   - Cập nhật nút quay lại kèm icon `<ArrowLeft size={15} />` và liên kết trực tiếp về danh mục.
3. `frontend/src/workspace/design.css`:
   - Bổ sung định dạng CSS cho `.breadcrumb a`, `.breadcrumb-root`, `.breadcrumb-link`, `.breadcrumb-separator`.
   - Bổ sung hệ thống class `.workspace-tab-groups`, `.workspace-tab-group`, `.workspace-tab-group-label`, `.workspace-tab-items`, `.workspace-tab-btn`, `.tab-badge`.
   - Bổ sung responsive rules cho màn hình nhỏ (`@media (max-width: 720px)` và `@media (max-width: 960px)`).
   - Sử dụng 100% Semantic Tokens từ HM-02C (`--bg-surface`, `--bg-surface-muted`, `--border-default`, `--primary`, `--text-primary`, `--shadow-sm`). Không hardcode thêm bất kỳ mã màu tĩnh nào.

---

## 3. Các Tính năng Nghiệp vụ được Bảo toàn Tuyệt đối

1. **Toàn vẹn Dữ liệu & Công cụ Kiểm tra (Quality Engine v5)**:
   - Toàn bộ cơ chế Rule Snapshot, Run Comparison, Trend Chart, Type Inference, và AI Rule Suggestions tiếp tục hoạt động nguyên vẹn.
2. **Quy trình Tạo Dataset Độc lập & Nạp CSV (HM-01)**:
   - Luồng tạo Dataset từ metadata, nạp CSV v1 đầu tiên, và nạp các phiên bản tiếp theo v2, v3 không bị tác động.
3. **Phân quyền vai trò người dùng (RBAC)**:
   - Phân biệt rõ ràng giữa `admin` (toàn quyền, xem được Quản trị tài khoản) và `data_steward` (quản lý bộ dữ liệu, không truy cập cấu hình hệ thống/tài khoản).
4. **Hệ thống Multi-Theme (HM-02C)**:
   - Các thành phần mới tương thích ngay lập tức và hiển thị hoàn hảo trên cả 4 chế độ: `System`, `Light`, `Dark`, và `Soft`.
5. **Cơ chế chống mất dữ liệu biểu mẫu (`confirmLeave`)**:
   - Khi có dữ liệu chưa lưu (`useDirty`), cố gắng chuyển tab hoặc chuyển trang sẽ kích hoạt xác nhận an toàn.

---

## 4. Xác nhận Giới hạn Phạm vi

- [x] Không can thiệp backend, cơ sở dữ liệu hoặc API routers.
- [x] Không viết lại nội dung các màn hình (Dashboard, Catalog, Results, Rules) — các màn hình này được dành riêng cho các giai đoạn tiếp theo (HM-02D.2, HM-02D.3, v.v.).
- [x] Không xóa bỏ bất kỳ route cũ hay tham số URL nào.
- [x] 100% kiểm thử hồi quy và kiểm thử điều hướng mới vượt qua.
- [x] Đã hoàn thành trọn vẹn và dừng lại ở HM-02D.1.

