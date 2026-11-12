# DATAGUARD SME — HM-02D.3: DATA CATALOG & EMPTY STATE DESIGN SPECIFICATION

## 1. Tổng quan & Mục tiêu

Hạng mục **HM-02D.3** tái cấu trúc giao diện **Danh mục dữ liệu (Data Catalog)** và hệ thống **Trạng thái rỗng (Empty States)** của DataGuard SME nhằm phục vụ đối tượng người dùng doanh nghiệp vừa và nhỏ (kế toán, kinh doanh, vận hành).

### Mục tiêu chính:
1. **Minh bạch hóa thông tin**: Hiển thị rõ tên bộ dữ liệu, mô tả nghiệp vụ, nguồn/bộ phận, người phụ trách, phiên bản CSV hiện hành, trạng thái kiểm soát chất lượng và hành động tiếp theo.
2. **Tìm kiếm & Lọc kết hợp**: Hỗ trợ tìm kiếm từ khóa phía máy chủ (`q`) cùng bộ lọc kết hợp (Nguồn, Người phụ trách, Trạng thái) với thông báo giải thích rõ ràng về cơ chế áp dụng.
3. **Phân loại chính xác 6 trạng thái**: Phân biệt rành mạch giữa dataset chưa có file, dataset có file nhưng chưa kiểm tra, đang kiểm tra, kiểm tra lỗi kỹ thuật, kiểm tra có vi phạm quy tắc, và kiểm tra đạt chuẩn.
4. **Cô lập phiên bản nghiêm ngặt**: Phiên bản mới nhất v2 chưa kiểm tra không bao giờ được phép kế thừa trạng thái "Đạt quy tắc" từ phiên bản v1 cũ.
5. **Hệ thống 4 Empty States ngữ cảnh**: Tránh để màn hình trắng hoặc thông báo kỹ thuật chung chung; hướng dẫn người dùng hành động rõ ràng tương ứng từng tình huống.
6. **Hành động ngữ cảnh tức thì (Next Action)**: Tải file CSV đầu tiên, Chạy kiểm tra, Xem lỗi, Xem kết quả, Chỉnh sửa thông tin.

---

## 2. Kiến trúc giao diện Danh mục dữ liệu (DG-231)

### 2.1 Cấu trúc màn hình
Giao diện `CatalogPage` bao gồm 3 khối thành phần chính:
```
+--------------------------------------------------------------------------------------------------+
| PageTitle: KHÔNG GIAN DỮ LIỆU / Danh mục dữ liệu                                [Tạo bộ dữ liệu] |
+--------------------------------------------------------------------------------------------------+
| Panel (Bảng điều khiển danh mục):                                                                |
|  [Tất cả bộ dữ liệu (N)]                                           [Dữ liệu lưu trên hệ thống]   |
|  ----------------------------------------------------------------------------------------------  |
|  Bộ lọc: [Tìm kiếm (q)...] | [Nguồn/bộ phận: Tất cả v] | [Phụ trách: Tất cả v] | [Trạng thái v]  |
|  [Đang hiển thị X/Y bộ dữ liệu] [Từ khóa: ...] [Đặt lại bộ lọc]                                 |
|  [Thông báo cơ chế lọc: Tìm kiếm máy chủ, lọc kết hợp trên tập dữ liệu tải về]                  |
|  ----------------------------------------------------------------------------------------------  |
|  Bảng danh mục (Catalog Table):                                                                  |
|  +-------------------+------------------+---------------+--------------------+-----------+-----+ |
|  | Bộ dữ liệu        | Nguồn & Phụ trách| Phiên bản CSV | Trạng thái kiểm tra| Cập nhật  |     | |
|  +-------------------+------------------+---------------+--------------------+-----------+-----+ |
|  | [Icon] Tên dataset| Nguồn: Kế toán   | [v2] 120 dòng | [Đạt chuẩn]        | 04/11/2026| ... | |
|  |        Mô tả ngắn | Phụ trách: NamNV |               | Lần #12 · 04/11    |           |     | |
|  +-------------------+------------------+---------------+--------------------+-----------+-----+ |
|  Phân trang: [1-10 trong N kết quả]  < Trang 1 / K >                                            |
+--------------------------------------------------------------------------------------------------+
```

### 2.2 Các cột dữ liệu chi tiết
1. **Bộ dữ liệu (`catalog-cell-main`)**:
   - `DatasetMark`: Icon màu đại diện dựa trên hash tên dataset.
   - Link điều hướng: `#/datasets/{id}/overview`.
   - Tiêu đề đậm: `item.name`.
   - Mô tả nghiệp vụ: `item.description` (cắt tối đa 2 dòng, fallback: "Chưa có mô tả").
2. **Nguồn & Phụ trách (`catalog-cell-meta`)**:
   - Dòng 1: `item.source` (nguồn/phòng ban, fallback: "—").
   - Dòng 2: `item.owner` (người chịu trách nhiệm, fallback: "Chưa ghi nhận").
3. **Phiên bản CSV (`catalog-cell-version`)**:
   - Có phiên bản: Tag `v{latest.version_number}` cùng số lượng `{row_count} dòng`.
   - Chưa có phiên bản: Tag xám nhẹ `Chưa có dữ liệu` cùng ghi chú `Chưa tải CSV`.
4. **Trạng thái kiểm tra (`catalog-cell-quality`)**:
   - Huy hiệu màu theo 6 trạng thái nghiệp vụ.
   - Dòng phụ: Số lần chạy `#id`, thời gian thực hiện hoặc ghi chú cảnh báo.
5. **Cập nhật (`catalog-cell-date`)**:
   - Ngày cập nhật định dạng thân thiện tiếng Việt (`DD/MM/YYYY`).
6. **Thao tác tiếp theo (`catalog-cell-action text-right`)**:
   - Nút hành động chính ngữ cảnh (Primary/Secondary).
   - Nút icon Chỉnh sửa metadata (`Pencil`) mở `MetadataDialog`.

---

## 3. Cơ chế Tìm kiếm & Lọc kết hợp (DG-232)

### 3.1 Tìm kiếm từ khóa (`search` -> `q`)
- Người dùng gõ từ khóa vào ô tìm kiếm (tìm đồng thời trên tên bộ dữ liệu, mô tả, nguồn, người phụ trách).
- Sử dụng hook `useDebounced` (trễ 300ms) để không bắn request dồn dập lên backend.
- Request backend: `GET /api/datasets?q={q}&page=1&page_size=10`.

### 3.2 Bộ lọc kết hợp (`source`, `owner`, `status`)
- Backend SME hiện tại chỉ nhận tham số `q`, chưa hỗ trợ lọc nhiều chiều (multi-facet filtering).
- Khi có bất kỳ bộ lọc local nào được chọn (`localFilters = !!source || !!owner || !!status`):
  - Hàm `catalogSelection` tự động tải toàn bộ danh sách phù hợp với `q` (`allPages('/api/datasets?q=...')`).
  - Frontend áp dụng hàm lọc đa điều kiện trên tập dữ liệu này:
    - `matchesSource`: Khớp chính xác `source`.
    - `matchesOwner`: Khớp chính xác `owner`.
    - `matchesStatus`: Khớp theo 6 trạng thái phân loại.
  - Phân trang client-side 10 bản ghi/trang (`filtered.slice((page-1)*10, page*10)`).
- **Thông báo minh bạch**: Hiển thị ghi chú giải thích rõ cơ chế xử lý giúp người dùng hiểu rõ phạm vi kết quả.
- **Nút "Đặt lại bộ lọc"**: Hiển thị ngay trên thanh công cụ và trong thanh tóm tắt khi có bất kỳ điều kiện lọc nào đang hoạt động.

---

## 4. Phân loại 6 trạng thái dữ liệu (DG-233)

Hệ thống phân tách chính xác 6 trạng thái dựa trên phiên bản mới nhất:

| Trạng thái | Mã định danh | Điều kiện xác định | Huy hiệu hiển thị | Hành động chính |
|---|---|---|---|---|
| **Chưa có file CSV** | `NO_FILE` | `item.versions.length === 0` | `Chưa có file` (Neutral) | **Tải file CSV** (`primary`) |
| **Chưa kiểm tra** | `NEEDS_RUN` | `item.versions.length > 0` && không có run nào cho phiên bản mới nhất này | `Chưa kiểm tra` (Warning) | **Chạy kiểm tra** (`primary`) |
| **Đang kiểm tra** | `RUNNING` | Run mới nhất có `status === 'running'` | `Đang kiểm tra` (Primary / Spin) | *Vô hiệu hóa tạm thời* |
| **Lỗi kỹ thuật** | `TECHNICAL_FAILED` | Run mới nhất có `status === 'failed'` | `Lỗi kỹ thuật` (Danger) | **Thử lại** (`secondary`) |
| **Có lỗi dữ liệu** | `HAS_ERRORS` | Run mới nhất có `status === 'completed'` && `error_row_count > 0` | `Có lỗi (N dòng)` (Warning) | **Xem lỗi** (`primary`) |
| **Đạt chuẩn** | `PASSED` | Run mới nhất có `status === 'completed'` && `error_row_count === 0` | `Đạt chuẩn` (Success) | **Xem kết quả** (`secondary`) |

### Nguyên tắc bất biến về cô lập phiên bản:
> **TUYỆT ĐỐI KHÔNG** dùng kết quả kiểm tra của phiên bản cũ (v1) để gán trạng thái cho phiên bản mới (v2). Mỗi phiên bản là một thực thể dữ liệu độc lập. Khi upload v2, trạng thái lập tức chuyển sang `NEEDS_RUN` ("Chưa kiểm tra") cho đến khi có lượt kiểm tra mới được kích hoạt trên v2.

---

## 5. Hệ thống 4 Empty States ngữ cảnh (DG-235)

1. **Global Empty State (Hệ thống chưa có bộ dữ liệu nào)**:
   - Điều kiện: `datasets.length === 0`.
   - Tiêu đề: *Chưa có bộ dữ liệu nào*.
   - Mô tả: *Tạo bộ dữ liệu mới và bắt đầu quản lý thông tin tập trung cho doanh nghiệp.*
   - Nút hành động: `[+ Tạo bộ dữ liệu]` mở `CreateDatasetDialog`.
2. **Search / Filter Empty State (Không tìm thấy kết quả phù hợp)**:
   - Điều kiện: `datasets.length > 0 && filtered.length === 0`.
   - Tiêu đề: *Không tìm thấy bộ dữ liệu phù hợp*.
   - Mô tả: *Không có bộ dữ liệu nào khớp với điều kiện tìm kiếm hoặc bộ lọc hiện tại. Thử đổi từ khóa hoặc đặt lại bộ lọc.*
   - Nút hành động: `[Đặt lại bộ lọc]` xóa toàn bộ từ khóa và bộ lọc, đưa trang về 1.
3. **Empty Dataset Row Cell State (Bộ dữ liệu trong bảng chưa có file)**:
   - Hiển thị tại cột Phiên bản: `<span className="badge badge-muted">Chưa có dữ liệu</span>` cùng dòng phụ `Chưa tải CSV`.
   - Hiển thị tại cột Trạng thái: `<Badge tone="neutral">Chưa có file</Badge>` cùng dòng phụ `Chưa tải file dữ liệu`.
   - Nút hành động trực tiếp: `[Tải file CSV]` mở `UploadDialog`.
4. **API Load Error State (Lỗi kết nối / Máy chủ)**:
   - Điều kiện: `list.error !== ''`.
   - Hiển thị qua component `LoadState` với thông báo lỗi chi tiết bằng tiếng Việt và nút `[Thử lại]`.

---

## 6. Khả năng truy cập & Multi-theme (DG-237)

- **Semantic Tokens**: Sử dụng toàn bộ hệ biến CSS từ HM-02C (`--bg-surface`, `--bg-surface-raised`, `--border-default`, `--text-primary`, `--text-secondary`, `--text-muted`, `--primary`, `--warning`, `--success`, `--danger`).
- **Độ tương phản WCAG 2.2 AA**: Kiểm tra đạt tỷ lệ tương phản tối thiểu 4.5:1 trên cả 4 giao diện (`system`, `light`, `dark`, `soft`).
- **Khả năng tiếp cận bàn phím (Keyboard & A11y)**:
  - Bảng dữ liệu có thuộc tính `scope="col"` đầy đủ trên thẻ `th`.
  - Các nút icon có `aria-label` và `title` rõ nghĩa.
  - Phím Tab điều hướng tuần tự qua tất cả các bộ lọc, link dòng và nút thao tác.

