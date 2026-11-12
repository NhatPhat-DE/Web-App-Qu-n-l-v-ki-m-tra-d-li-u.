# DATAGUARD SME — HM-02D.3: TEST RESULTS & VERIFICATION

## 1. Kết quả kiểm thử tổng hợp

Toàn bộ hệ thống kiểm thử frontend đã chạy thành công **35/35 tests** (100% pass, 0 fail, 0 skipped).
Quá trình biên dịch TypeScript và đóng gói Vite hoàn tất không có cảnh báo hoặc lỗi.

```bash
> data-catalog-frontend@0.1.0 test
> node --test tests/*.test.mjs

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
# Subtest: DG-233: 6 precise status classifications
ok 30 - DG-233: 6 precise status classifications
# Subtest: DG-233: Strict version isolation - uninspected v2 with passed v1 is classified as NEEDS_RUN
ok 31 - DG-233: Strict version isolation - uninspected v2 with passed v1 is classified as NEEDS_RUN
# Subtest: DG-232: Filter matching across source, owner, and status
ok 32 - DG-232: Filter matching across source, owner, and status
# Subtest: DG-235: Empty state copy and condition definitions
ok 33 - DG-235: Empty state copy and condition definitions
# Subtest: DG-236: Action buttons correctly mapped per status
ok 34 - DG-236: Action buttons correctly mapped per status
# Subtest: DG-231 & DG-237: Catalog CSS classes and semantic tokens in design.css
ok 35 - DG-231 & DG-237: Catalog CSS classes and semantic tokens in design.css
1..35
# tests 35
# suites 0
# pass 35
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

---

## 2. Chi tiết kết quả kiểm thử bộ test HM-02D.3

| STT | Mã kiểm thử | Mục đích kiểm thử | Kết quả | Ghi chú |
|---|---|---|---|---|
| 1 | **DG-233-A** | Phân loại chính xác 6 trạng thái nghiệp vụ | **PASS** | Kiểm tra toàn bộ 6 trạng thái (`NO_FILE`, `NEEDS_RUN`, `RUNNING`, `TECHNICAL_FAILED`, `HAS_ERRORS`, `PASSED`) |
| 2 | **DG-233-B** | Tính độc lập giữa các phiên bản (Version Isolation) | **PASS** | Dataset có v1 Đạt chuẩn nhưng vừa tải v2 chưa kiểm tra phải trả về `NEEDS_RUN`, không được trả về `PASSED` |
| 3 | **DG-232-A** | Logic lọc đa tiêu chí (Nguồn, Phụ trách, Trạng thái) | **PASS** | Khớp chính xác kết quả lọc đa điều kiện trên tập dữ liệu tải về |
| 4 | **DG-235-A** | Văn bản và điều kiện hiển thị 4 Empty States | **PASS** | Kiểm tra đầy đủ Global empty, Search empty, Empty cell tag "Chưa có dữ liệu", Disclaimer text |
| 5 | **DG-236-A** | Gán đúng nút hành động ngữ cảnh theo từng trạng thái | **PASS** | Kiểm tra nhãn nút, loại nút và đường dẫn link tương ứng cho từng trạng thái |
| 6 | **DG-231 & DG-237** | CSS classes và semantic tokens trong `design.css` | **PASS** | Xác minh không có màu hex hardcoded; tất cả sử dụng biến CSS token của hệ thống multi-theme |

---

## 3. Kết quả biên dịch (Build & Typecheck)

```bash
> data-catalog-frontend@0.1.0 build
> npm run typecheck && vite build

> data-catalog-frontend@0.1.0 typecheck
> tsc --noEmit

vite v8.3.4 building client environment for production...
transforming...
✓ 1952 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.27 kB │ gzip:   0.63 kB
dist/assets/index-CFuZHlCt.css   57.78 kB │ gzip:  10.75 kB
dist/assets/index-CdudjS4r.js   432.55 kB │ gzip: 126.01 kB
✓ built in 667ms
```

- **TypeScript Typecheck:** 0 lỗi, 0 cảnh báo.
- **Vite Production Bundle:** Đóng gói thành công toàn bộ bundle JavaScript và CSS.

