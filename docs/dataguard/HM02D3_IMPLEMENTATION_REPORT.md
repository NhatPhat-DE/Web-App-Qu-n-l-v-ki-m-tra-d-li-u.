# DATAGUARD SME — HM-02D.3: IMPLEMENTATION REPORT

## 1. Thông tin tổng quan

- **Mã hạng mục:** HM-02D.3
- **Tên hạng mục:** Data Catalog & Contextual Empty State Rebuild
- **Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)
- **Ngày hoàn thành:** 04/11/2026
- **Trạng thái:** Hoàn thành toàn diện, 35/35 unit tests đạt chuẩn, build Vite thành công.

---

## 2. Chi tiết các công việc triển khai

### DG-231: Tái cấu trúc giao diện Danh mục dữ liệu (Catalog Table)
- Thiết kế lại layout của `CatalogPage` trong `frontend/src/workspace/CatalogPages.tsx`.
- Bổ sung cấu trúc bảng 6 cột chuẩn mực:
  1. `Bộ dữ liệu`: Dataset mark, tên nổi bật kèm link điều hướng, mô tả nghiệp vụ (tối đa 2 dòng, ellipsize).
  2. `Nguồn & Phụ trách`: Phân tách rành mạch dòng phòng ban và người chịu trách nhiệm.
  3. `Phiên bản CSV`: Hiển thị rõ số hiệu phiên bản (`v1`, `v2`, ...) và số lượng bản ghi hoặc huy hiệu `Chưa có dữ liệu`.
  4. `Trạng thái kiểm tra`: Huy hiệu màu tương ứng theo 6 trạng thái nghiệp vụ cùng số thứ tự lần chạy và ngày kiểm tra.
  5. `Cập nhật`: Ngày cập nhật gần nhất định dạng Việt Nam.
  6. `Thao tác tiếp theo`: Căn phải với nút hành động chính ngữ cảnh và nút chỉnh sửa thông tin metadata.

### DG-232: Tìm kiếm & Lọc nâng cao kết hợp (Server & Client Hybrid)
- Tìm kiếm từ khóa: `search` được debounce 300ms qua hook `useDebounced`, truyền trực tiếp vào tham số `q` của backend (`GET /api/datasets?q=...`).
- Bộ lọc kết hợp: Cho phép lọc đồng thời theo `Nguồn / bộ phận`, `Người phụ trách`, và `Trạng thái kiểm tra`.
- Đảm bảo tính minh bạch: Hiển thị ghi chú giải thích rõ cơ chế xử lý (tìm kiếm trên máy chủ; lọc thuộc tính áp dụng trên danh sách tải về).
- Bổ sung thanh tóm tắt bộ lọc (`catalog-filter-summary`) và nút "Đặt lại bộ lọc" (`RotateCcw`).

### DG-233: Phân loại 6 trạng thái & Cô lập phiên bản
- Xây dựng hàm nghiệp vụ `getCatalogStatus(item: CatalogEntry): CatalogStatusInfo` phân loại chuẩn xác:
  1. `NO_FILE` (Chưa có file CSV)
  2. `NEEDS_RUN` (Chưa kiểm tra phiên bản mới)
  3. `RUNNING` (Đang kiểm tra)
  4. `TECHNICAL_FAILED` (Lỗi kỹ thuật)
  5. `HAS_ERRORS` (Có lỗi dữ liệu)
  6. `PASSED` (Đạt chuẩn)
- Đảm bảo tính độc lập giữa các phiên bản: Luôn đối chiếu `latestRun(item, latest.id)`. Một bộ dữ liệu có v1 đạt chuẩn nhưng mới upload v2 sẽ hiển thị ngay trạng thái `NEEDS_RUN` chứ không nhận nhầm trạng thái của v1.

### DG-234: Tạo Dataset độc lập bằng metadata
- Bảo toàn component `CreateDatasetDialog` kết nối endpoint `POST /api/datasets`.
- Cho phép tạo dataset hoàn chỉnh mà không cần tải lên file CSV ngay lập tức.
- Giữ nguyên các quy tắc kiểm tra hợp lệ: Tên không để trống/khoảng trắng (tối đa 200 ký tự), mô tả (tối đa 2000 ký tự), nguồn (tối đa 200 ký tự), phụ trách (tối đa 200 ký tự).

### DG-235: Hệ thống 4 Empty States ngữ cảnh
- **Global Empty State**: Khi toàn bộ hệ thống chưa có dataset nào, hiển thị thông điệp chào đón và nút tạo dataset.
- **Search Empty State**: Khi tìm kiếm hoặc lọc không có kết quả, hiển thị hướng dẫn và nút đặt lại bộ lọc.
- **Dataset Row Empty State**: Khi một dataset trong bảng chưa có file CSV, hiển thị rõ huy hiệu "Chưa có dữ liệu" và nút "Tải file CSV".
- **API Error State**: Xử lý lỗi kết nối qua `LoadState` với thông điệp tiếng Việt và nút "Thử lại".

### DG-236: Gắn kết nút hành động ngữ cảnh (Next Actions)
- `NO_FILE` $\rightarrow$ Nút Primary `Tải file CSV` mở dialog upload.
- `NEEDS_RUN` $\rightarrow$ Nút Primary `Chạy kiểm tra` mở dialog cấu hình kiểm tra.
- `RUNNING` $\rightarrow$ Nút Ghost `Đang kiểm tra` (vô hiệu hóa kèm spinner).
- `TECHNICAL_FAILED` $\rightarrow$ Nút Secondary `Thử lại` chạy lại kiểm tra.
- `HAS_ERRORS` $\rightarrow$ Nút Primary link `Xem lỗi` điều hướng thẳng đến trang kết quả chạy (`#/datasets/{id}/runs/{run_id}`).
- `PASSED` $\rightarrow$ Nút Secondary link `Xem kết quả` điều hướng đến trang kết quả.
- Nút Pencil mở `MetadataDialog` để chỉnh sửa tên, mô tả, nguồn, người phụ trách.

### DG-237: Multi-theme Design Tokens & Khả năng tiếp cận
- Cập nhật `frontend/src/workspace/design.css` bổ sung các class:
  `.catalog-filter-bar`, `.search-clear-btn`, `.catalog-filter-summary`, `.catalog-filter-pill`, `.catalog-filter-disclaimer`, `.catalog-cell-main`, `.catalog-cell-meta`, `.catalog-cell-version`, `.catalog-cell-quality`, `.catalog-cell-date`, `.catalog-cell-action`, `.catalog-action-group`, `.badge-muted`.
- 100% sử dụng semantic CSS tokens từ HM-02C (`--bg-surface`, `--bg-surface-raised`, `--border-default`, `--text-primary`, `--text-secondary`, `--text-muted`, `--primary`, `--warning`, `--success`, `--danger`).
- Hoàn toàn tương thích và hiển thị sắc nét trên cả 4 theme (`system`, `light`, `dark`, `soft`).

---

## 3. Danh sách tệp thay đổi

1. `frontend/src/workspace/CatalogPages.tsx`:
   - Viết lại `CatalogPage` theo chuẩn mới.
   - Thêm `getCatalogStatus`, `CatalogStatus`, `CatalogStatusInfo`.
   - Bổ sung bộ lọc 6 trạng thái, thanh tóm tắt, nút đặt lại bộ lọc, nút xóa từ khóa.
   - Bổ sung bảng dữ liệu 6 cột và các nút hành động ngữ cảnh.
   - Bảo toàn nguyên vẹn `DatasetPage` (3 nhóm tab của HM-02D.1), `PreviewDialog` và `RulesPage`.
2. `frontend/src/workspace/design.css`:
   - Bổ sung định dạng cho hệ thống catalog, filter, clear button, summary pills, action groups, table cells và badge styles.
3. `frontend/tests/hm02d3_catalog.test.mjs`:
   - Tạo mới bộ kiểm thử 6 ca test độc lập cho toàn bộ nghiệp vụ HM-02D.3.
4. `docs/dataguard/HM02D3_CATALOG_DESIGN.md`: Tài liệu thiết kế đặc tả chi tiết.
5. `docs/dataguard/HM02D3_IMPLEMENTATION_REPORT.md`: Báo cáo triển khai kỹ thuật.
6. `docs/dataguard/HM02D3_TEST_RESULTS.md`: Kết quả nghiệm thu kiểm thử.

---

## 4. Xác minh không phá vỡ tính năng (Feature Preservation)

- **Không đụng chạm Backend/Database:** Không chỉnh sửa bất kỳ tệp nào trong `backend/` hoặc các migration Alembic.
- **Bảo toàn Quality Engine v5 & Rule Engine:** Không thay đổi logic chạy kiểm tra chất lượng hay schema snapshot.
- **Bảo toàn Dashboard (HM-02D.2):** Giữ nguyên vẹn bàn làm việc Dashboard, các thẻ KPI và danh sách cần xử lý.
- **Bảo toàn Cấu trúc Điều hướng (HM-02D.1):** Sidebar, Topbar Breadcrumb, 3 nhóm tab và các route alias vẫn hoạt động chính xác 100%.
- **Bảo toàn Hệ thống Giao diện (HM-02C):** Cả 4 theme tiếp tục hoạt động mượt mà, chuyển đổi tức thì không giật FOUT.

