# DATAGUARD SME — HM-02D.2: TEST RESULTS & QA VERIFICATION REPORT

## 1. Tóm tắt Kết quả Kiểm thử Tổng thể

| Nội dung kiểm thử | Phương thức kiểm tra | Số lượng ca kiểm thử | Kết quả | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| **Kiểm thử Đơn vị Frontend (Unit Tests)** | Node.js Test Runner (`node --test`) | **29 / 29 passed** | **100% ĐẠT** | 8 ca HM-01, 7 ca HM-02C, 6 ca HM-02D.1, 8 ca HM-02D.2 |
| **Kiểm tra Kiểu dữ liệu (Typecheck)** | `tsc --noEmit` | Toàn bộ dự án | **100% ĐẠT** | Không có lỗi TypeScript |
| **Đóng gói Sản phẩm (Vite Build)** | `vite build` | 1952 modules | **100% ĐẠT** | Bundle 428 kB JS, 55 kB CSS trong 627ms |
| **Phân loại Trạng thái Dữ liệu (DG-224)**| Test Runner & Mock Cases | 5 kịch bản phân loại | **100% ĐẠT** | Phân biệt chính xác lỗi dữ liệu vs lỗi kỹ thuật |
| **Tính toán Chỉ số KPI (DG-223)** | Data Calculation Matrix | 4 chỉ số thực tế | **100% ĐẠT** | Không suy diễn số liệu ảo |
| **Thao tác Nhanh (DG-222)** | Interaction Verification | 4 nút hành động | **100% ĐẠT** | Mọi CTA đều hoạt động chính xác |
| **Trạng thái Giao diện (DG-226)** | UI States Test | 4 trạng thái | **100% ĐẠT** | Loading skeleton, Empty, Error retry, Normal |
| **Đa giao diện (Multi-Theme - DG-227)** | 4 Themes (`System`, `Light`, `Dark`, `Soft`) | 4 chế độ giao diện | **100% ĐẠT** | Semantic tokens hiển thị hài hòa, tương phản chuẩn |
| **Đa thiết bị (Responsive - DG-227)** | Desktop, Tablet, Mobile | 3 Breakpoints | **100% ĐẠT** | Không tràn viền, cuộn tab mượt mà |

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
# Subtest: HM-02D.2 / DG-224: Classification of empty dataset without files
ok 22 - HM-02D.2 / DG-224: Classification of empty dataset without files
# Subtest: HM-02D.2 / DG-224: Classification of dataset with file but uninspected
ok 23 - HM-02D.2 / DG-224: Classification of dataset with file but uninspected
# Subtest: HM-02D.2 / DG-224: Classification of dataset with technical execution failure
ok 24 - HM-02D.2 / DG-224: Classification of dataset with technical execution failure
# Subtest: HM-02D.2 / DG-224: Classification of dataset with detected errors in latest run
ok 25 - HM-02D.2 / DG-224: Classification of dataset with detected errors in latest run
# Subtest: HM-02D.2 / DG-224: Classification of dataset meeting all quality rules (Passed)
ok 26 - HM-02D.2 / DG-224: Classification of dataset meeting all quality rules (Passed)
# Subtest: HM-02D.2 / DG-223: Accurate KPI calculations without synthetic metrics
ok 27 - HM-02D.2 / DG-223: Accurate KPI calculations without synthetic metrics
# Subtest: HM-02D.2 / DG-221 & DG-222: Dashboard component markup and action elements
ok 28 - HM-02D.2 / DG-221 & DG-222: Dashboard component markup and action elements
# Subtest: HM-02D.2 / DG-227: CSS tokens and workbench classes in design.css
ok 29 - HM-02D.2 / DG-227: CSS tokens and workbench classes in design.css
1..29
# tests 29, suites 0, pass 29, fail 0
```

---

## 3. Ma trận Kiểm thử Phân loại Trạng thái Dữ liệu (DG-224)

| Mã trạng thái | Tình trạng thực tế | Nhãn hiển thị | Màu sắc | Hành động tương ứng | Kiểm thử xác minh |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`NO_FILE`** | `versions.length === 0` | `Chưa có file dữ liệu` | `neutral` | Nút "Tải file CSV" $\rightarrow$ mở dialog tải file | **ĐẠT** |
| **`NEEDS_RUN`** | Có version nhưng chưa có run | `Chưa kiểm tra` | `neutral` | Nút "Chạy kiểm tra" $\rightarrow$ gọi dialog chạy kiểm tra | **ĐẠT** |
| **`TECHNICAL_FAILED`**| Run gần nhất có `status: "failed"` | `Thực thi thất bại` | `danger` | Nút "Thử lại" $\rightarrow$ thử lại lần chạy mới | **ĐẠT** |
| **`HAS_ERRORS`** | Run gần nhất có `error_row_count > 0` | `${n} dòng lỗi` | `warning` | Nút "Xem lỗi" $\rightarrow$ mở link `#/datasets/:id/runs/:runId` | **ĐẠT** |
| **`PASSED`** | Run gần nhất có `error_row_count === 0` | `Đạt quy tắc` | `success` | Nút "Xem kết quả" $\rightarrow$ mở link kết quả | **ĐẠT** |

---

## 4. Ma trận Kiểm thử Trạng thái Giao diện (DG-226)

1. **Trạng thái Đang tải (Loading Skeleton)**:
   - Khi `loading === true` và chưa có dữ liệu: Hiển thị 4 thẻ KPI skeleton và khối nội dung hiệu ứng pulse mờ ảo. Không làm giật khung hình.
2. **Trạng thái Lỗi (Error State)**:
   - Khi API gặp sự cố (`error` có giá trị): Hiển thị thông báo lỗi rõ ràng kèm nút "Thử lại" (`onRetry`), không làm trắng toàn bộ trang web.
3. **Trạng thái Trống (Empty State)**:
   - Khi `datasets.length === 0` (hệ thống mới tinh): Hiển thị màn hình chào mừng thân thiện, thẻ hướng dẫn 3 bước cho SME và nút kêu gọi hành động lớn "Tạo bộ dữ liệu đầu tiên".
4. **Trạng thái Bình thường (Full Workbench)**:
   - Hiển thị đầy đủ thanh Quick Actions, 4 thẻ KPI, phân loại Dữ liệu cần chú ý và Lượt kiểm tra gần đây.

