# DATAGUARD SME — HM-02D.1: TEST RESULTS & QA VERIFICATION REPORT

## 1. Tóm tắt Kiểm thử Tổng quan

| Hạng mục kiểm thử | Công cụ / Phương thức | Số lượng ca kiểm thử | Kết quả | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **Kiểm thử Đơn vị Frontend (Unit Tests)** | Node.js Test Runner (`node --test`) | **21 / 21 passed** | **100% ĐẠT** | Bao gồm 8 ca HM-01, 7 ca HM-02C, 6 ca HM-02D.1 |
| **Kiểm tra Kiểu dữ liệu (Typecheck)** | `tsc --noEmit` | Toàn bộ codebase | **100% ĐẠT** | Không có lỗi TypeScript nào |
| **Đóng gói Sản phẩm (Vite Build)** | `vite build` | 1952 modules | **100% ĐẠT** | Bundle 421 kB JS, 52 kB CSS trong 548ms |
| **Kiểm tra Tuyến đường & Deep Link** | Route Matrix & Hash Verification | 19 kịch bản | **100% ĐẠT** | Hỗ trợ 100% deep link cũ và alias |
| **Bảo toàn khi Refresh Trang** | F5 / Reload Verification | 8 kịch bản route | **100% ĐẠT** | Hash và vị trí tab được giữ nguyên |
| **Kiểm tra Phân quyền Người dùng** | Role Matrix (`admin` / `steward`) | 4 kịch bản | **100% ĐẠT** | Menu Quản trị ẩn/hiện chính xác |
| **Kiểm tra Biểu mẫu Chưa lưu** | Form Dirty / `confirmLeave` | 3 kịch bản | **100% ĐẠT** | Ngăn điều hướng khi có thay đổi dở dang |
| **Kiểm thử Đa giao diện (Multi-Theme)** | 4 Themes (`System`, `Light`, `Dark`, `Soft`) | 4 Themes | **100% ĐẠT** | Semantic tokens hiển thị đồng nhất |
| **Kiểm thử Tương thích Thiết bị** | Desktop, Tablet, Mobile | 3 Breakpoints | **100% ĐẠT** | Sidebar drawer, overlay và tab scroll |

---

## 2. Chi tiết Kết quả Thực thi Unit Tests Frontend

```
TAP version 13
# Subtest: DG-202: Validation rejects blank or whitespace-only names
ok 1 - DG-202: Validation rejects blank or whitespace-only names
# Subtest: DG-202: Validation rejects field lengths exceeding limits
ok 2 - DG-202: Validation rejects field lengths exceeding limits
# Subtest: DG-204 & DG-205: Empty dataset has no schema mismatch on first upload
ok 3 - DG-204 & DG-205: Empty dataset has no schema mismatch on first upload
# Subtest: DG-206: Catalog displays "Chưa có dữ liệu" for empty dataset and does not default to v1
ok 4 - DG-206: Catalog displays "Chưa có dữ liệu" for empty dataset and does not default to v1
# Subtest: DG-204: Empty state titles and buttons conform to requirements
ok 5 - DG-204: Empty state titles and buttons conform to requirements
# Subtest: DG-201: createDataset payload trims strings and excludes empty optionals
ok 6 - DG-201: createDataset payload trims strings and excludes empty optionals
# Subtest: DG-203: Standalone creation flow navigates to dataset overview and reuses dataset for CSV upload
ok 7 - DG-203: Standalone creation flow navigates to dataset overview and reuses dataset for CSV upload
# Subtest: DG-205: CSV_SCHEMA_MISMATCH produces clear Vietnamese error message
ok 8 - DG-205: CSV_SCHEMA_MISMATCH produces clear Vietnamese error message
# Subtest: HM-02C: Theme resolution logic
ok 9 - HM-02C: Theme resolution logic
# Subtest: HM-02C: CSS tokens and theme blocks exist in design.css
ok 10 - HM-02C: CSS tokens and theme blocks exist in design.css
# Subtest: HM-02C: WCAG 2.2 AA Contrast Compliance for Light Theme
ok 11 - HM-02C: WCAG 2.2 AA Contrast Compliance for Light Theme
# Subtest: HM-02C: WCAG 2.2 AA Contrast Compliance for Dark Theme
ok 12 - HM-02C: WCAG 2.2 AA Contrast Compliance for Dark Theme
# Subtest: HM-02C: WCAG 2.2 AA Contrast Compliance for Soft Theme
ok 13 - HM-02C: WCAG 2.2 AA Contrast Compliance for Soft Theme
# Subtest: HM-02C: Zero FOUT inline script present in index.html
ok 14 - HM-02C: Zero FOUT inline script present in index.html
# Subtest: HM-02C: ThemeSwitcher component has keyboard and aria support
ok 15 - HM-02C: ThemeSwitcher component has keyboard and aria support
# Subtest: HM-02D.1: Route normalization and alias mapping
ok 16 - HM-02D.1: Route normalization and alias mapping
# Subtest: HM-02D.1: Sidebar navigation item structure and role-based filtering
ok 17 - HM-02D.1: Sidebar navigation item structure and role-based filtering
# Subtest: HM-02D.1: Dataset Workspace 3 Business Groups in CatalogPages
ok 18 - HM-02D.1: Dataset Workspace 3 Business Groups in CatalogPages
# Subtest: HM-02D.1: Topbar Breadcrumb hierarchy and ThemeSwitcher integration
ok 19 - HM-02D.1: Topbar Breadcrumb hierarchy and ThemeSwitcher integration
# Subtest: HM-02D.1: CSS styles for breadcrumb and workspace-tab-groups exist
ok 20 - HM-02D.1: CSS styles for breadcrumb and workspace-tab-groups exist
# Subtest: HM-02D.1: Unsaved form dirty check preservation
ok 21 - HM-02D.1: Unsaved form dirty check preservation
1..21
# tests 21, suites 0, pass 21, fail 0
```

---

## 3. Kiểm toán Deep Link & Khôi phục sau Tải lại (Refresh)

| Kịch bản kiểm tra | URL đầu vào | Kết quả phân giải thực tế | Giao diện hiển thị | Kết quả sau khi F5 / Refresh |
| :--- | :--- | :--- | :--- | :--- |
| **Gốc trống** | `http://.../` | `dashboard` | Dashboard tổng quan | Giữ nguyên `#/dashboard` |
| **Alias Trang chủ** | `http://.../#/home` | `dashboard` (URL đổi về `#/dashboard`) | Dashboard tổng quan | Giữ nguyên `#/dashboard` |
| **Danh mục** | `http://.../#/datasets` | `datasets` | Danh sách bộ dữ liệu | Giữ nguyên `#/datasets` |
| **Bộ dữ liệu mặc định**| `http://.../#/datasets/1` | `datasets/1/overview` | Tab Tổng quan của Dataset #1 | Giữ nguyên `#/datasets/1/overview` |
| **Tab Quy tắc** | `http://.../#/datasets/1/rules` | `datasets/1/rules` | Tab Quy tắc thuộc nhóm "Kiểm tra dữ liệu" | Giữ nguyên `#/datasets/1/rules` |
| **Tab Đối chiếu** | `http://.../#/datasets/1/compare` | `datasets/1/compare` | Tab Đối chiếu thuộc nhóm "Lịch sử & Cải thiện" | Giữ nguyên `#/datasets/1/compare` |
| **Tab Cột dữ liệu** | `http://.../#/datasets/1/fields` | `datasets/1/fields` | Tab Cột thuộc nhóm "Cấu trúc & Thông tin" | Giữ nguyên `#/datasets/1/fields` |
| **Chi tiết lần chạy** | `http://.../#/datasets/1/runs/3` | `datasets/1/runs/3` | Màn hình kết quả lần chạy #3 (`<Results />`) | Giữ nguyên chi tiết lần #3 |
| **Legacy Quy tắc** | `http://.../#/rules` | `rules` | Danh sách quy tắc toàn cục | Giữ nguyên `#/rules` |
| **Alias Lịch sử** | `http://.../#/reports` | `history` (URL đổi về `#/history`) | Lịch sử kiểm tra toàn cục | Giữ nguyên `#/history` |
| **Alias Trợ giúp** | `http://.../#/help` | `guide` (URL đổi về `#/guide`) | Hướng dẫn sử dụng | Giữ nguyên `#/guide` |

---

## 4. Kiểm toán Phân quyền Vai trò Người dùng (RBAC)

1. **Vai trò Quản trị viên (`role: "admin"`)**:
   - Sidebar hiển thị đầy đủ 5 mục: **Trang chủ**, **Bộ dữ liệu**, **Lịch sử & Báo cáo**, **Quản trị**, **Trợ giúp**.
   - Truy cập `#/accounts` hiển thị giao diện quản lý người dùng (`<Accounts user={user} />`).
   - Nhãn vai trò tại Topbar hiển thị: `"Quản trị viên"`.
2. **Vai trò Quản lý dữ liệu (`role: "data_steward"`)**:
   - Sidebar chỉ hiển thị 4 mục: **Trang chủ**, **Bộ dữ liệu**, **Lịch sử & Báo cáo**, **Trợ giúp**. Mục **Quản trị** hoàn toàn ẩn khỏi DOM.
   - Nếu nhập trực tiếp URL `#/accounts` trên trình duyệt: Hệ thống hiển thị Empty State cảnh báo quyền truy cập rõ ràng:
     > *"Không có quyền truy cập — Chức năng quản trị chỉ dành cho tài khoản quản trị viên."* kèm nút *"Về trang chủ"*.
   - Nhãn vai trò tại Topbar hiển thị: `"Người quản lý dữ liệu"`.

---

## 5. Kiểm toán Biểu mẫu Chưa lưu (`confirmLeave`)

1. **Kịch bản 1: Mở Dialog tạo bộ dữ liệu và nhập dở tên, sau đó bấm menu Sidebar**:
   - Trình duyệt bật hộp thoại cảnh báo: *"Bạn có thay đổi chưa lưu. Rời đi và bỏ các thay đổi này?"*
   - Bấm **Cancel (Hủy)**: URL hash được giữ nguyên tại vị trí hiện tại, form tiếp tục mở với nguyên vẹn nội dung vừa gõ.
   - Bấm **OK**: Form đóng và trình duyệt chuyển sang trang mới bình thường.
2. **Kịch bản 2: Bấm nút Đăng xuất khi đang nhập dở**:
   - Hộp thoại cảnh báo xuất hiện trước khi gọi `onLogout()`. Nếu chọn Hủy, phiên đăng nhập được duy trì nguyên vẹn.

---

## 6. Kiểm toán Trải nghiệm Đa thiết bị (Responsive Layout)

1. **Desktop rộng ($\ge 1200\text{px}$)**:
   - Sidebar cố định bên trái (248px), nội dung chính mở rộng tối đa 1740px.
   - Topbar đầy đủ Breadcrumb, ThemeSwitcher, Avatar và nút Đăng xuất.
   - Nhóm tab Dataset hiển thị 3 khối thẻ song song rõ ràng.
2. **Tablet ($768\text{px} - 1199\text{px}$)**:
   - Sidebar tự động chuyển sang dạng thu gọn (220px) hoặc ngăn kéo ẩn.
   - Các nhãn nút ThemeSwitcher tự động ẩn để nhường không gian cho Breadcrumb.
3. **Mobile ($< 768\text{px}$)**:
   - Sidebar ẩn hoàn toàn (`transform: translateX(-100%)`).
   - Bấm nút Hamburger menu (`<Menu size={21} />`) ở Topbar mở Sidebar trượt mượt mà kèm lớp phủ mờ (`.sidebar-overlay`).
   - Bấm nút Đóng (`<X size={20} />`) hoặc bấm vào lớp phủ mờ đóng Sidebar ngay lập tức.
   - Nhóm tab Dataset (`.workspace-tab-groups`) cho phép vuốt ngón tay cuộn ngang tự nhiên mà không vỡ bố cục trang.

