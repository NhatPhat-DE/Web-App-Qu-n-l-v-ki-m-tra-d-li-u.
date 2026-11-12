# KIẾN TRÚC THÔNG TIN (INFORMATION ARCHITECTURE SPECIFICATION)
## HỆ THỐNG DATAGUARD SME

**Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)  
**Hạng mục:** HM-02B: Information Architecture & Navigation Design  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior UX Architect, Product Designer & SaaS Product Manager  

---

## 1. Mục tiêu & Mô hình nhận thức (Cognitive Model)

### 1.1. Mục tiêu kiến trúc
1. **Chuyển dịch từ "Công cụ kỹ thuật" sang "Bàn làm việc nghiệp vụ":**  
   Thay thế tư duy phân cấp dữ liệu kỹ thuật (`Dataset` $\rightarrow$ `DatasetVersion` $\rightarrow$ `QualityRun` $\rightarrow$ `RuleSnapshot`) bằng tư duy nhiệm vụ (`Hồ sơ nghiệp vụ` $\rightarrow$ `File kỳ này` $\rightarrow$ `Kết quả & Dòng cần sửa`).
2. **Quy hoạch tập trung (Unified Workspace):**  
   Xóa bỏ sự phân tán qua 7 tab rời rạc tại trang chi tiết Dataset cũ, hợp nhất thành 3 khu vực chức năng trực quan: **Kiểm tra dữ liệu**, **Lịch sử & Cải thiện**, **Cấu trúc & Thông tin**.
3. **Bảo toàn khả năng truy vết (Auditability):**  
   Mọi lần nạp file, mọi quy tắc tại thời điểm chạy và kết quả đối soát đều được bảo toàn 100% về mặt dữ liệu, nhưng được thể hiện bằng ngôn ngữ kinh doanh thân thiện.

### 1.2. Đối tượng người dùng mục tiêu
- **Nhân viên kế toán, kinh doanh, tổng hợp dữ liệu:** Quen thuộc với Microsoft Excel và các thao tác bảng tính, không có nền tảng về Data Engineering, SQL hay Regex.
- **Quản trị viên hệ thống (Admin):** Cấp phát tài khoản, phân quyền, giám sát kết nối và quản trị danh mục dùng chung.

---

## 2. Cấu trúc điều hướng chính (Main Navigation)

Hệ thống điều hướng sử dụng bố cục **Collapsible Sidebar (Thanh điều hướng bên trái có thể thu gọn)** kết hợp **Top Header Bar (Thanh tiêu đề trên cùng)**.

```
┌───────────────────────────────────────────────────────────────────────────┐
│ SIDEBAR (Menu chính)             │ TOPBAR (Breadcrumb + Tài khoản)        │
│                                  │ Trang chủ / Khách hàng / Kiểm tra      │
│ [🛡️ DataGuard SME]               ├────────────────────────────────────────┤
│                                  │ MAIN CONTENT AREA                      │
│ KHÔNG GIAN LÀM VIỆC              │                                        │
│ 🏠 1. Trang chủ                  │ (Nội dung màn hình theo route)         │
│ 📁 2. Bộ dữ liệu                 │                                        │
│ 📊 3. Lịch sử & Báo cáo          │                                        │
│ 📖 4. Trợ giúp & Mẫu file        │                                        │
│                                  │                                        │
│ QUẢN TRỊ HỆ THỐNG (Chỉ Admin)    │                                        │
│ 👥 5. Quản trị tài khoản         │                                        │
│                                  ├────────────────────────────────────────┤
│ 🔌 Trạng thái kết nối            │ FOOTER                                 │
└──────────────────────────────────┴────────────────────────────────────────┘
```

### 2.1. Danh mục Menu chính (Sidebar Items)

| STT | Tên menu tiếng Việt | Icon đề xuất | Route hash | Đối tượng | Mục đích nghiệp vụ |
|:---:|---|---|---|---|---|
| 1 | **Trang chủ** | `LayoutDashboard` | `#/dashboard` | Tất cả | Xem nhanh việc cần xử lý trong ngày, các bộ dữ liệu có lỗi gần nhất và lối tắt bắt đầu công việc mới. |
| 2 | **Bộ dữ liệu** | `FolderClosed` | `#/datasets` | Tất cả | Quản lý danh mục các hồ sơ dữ liệu nghiệp vụ, tạo mới hồ sơ, nạp file CSV kỳ mới. |
| 3 | **Lịch sử & Báo cáo** | `FileCheck2` / `History` | `#/history` | Tất cả | Tra cứu tập trung toàn bộ các lần kiểm tra, tải báo cáo lỗi Excel/CSV và theo dõi tiến độ tổng thể. |
| 4 | **Trợ giúp & Mẫu file** | `BookOpen` | `#/guide` | Tất cả | Hướng dẫn 4 bước chuẩn bị dữ liệu đúng cách, tải các file mẫu Excel/CSV thực hành. |
| 5 | **Quản trị tài khoản** | `Users` | `#/accounts` | Chỉ `admin` | Quản lý danh sách tài khoản, cấp quyền người phụ trách hoặc quản trị viên, vô hiệu hóa tài khoản. |

---

## 3. Kiến trúc chi tiết một Bộ dữ liệu (Dataset Workspace)

Khi người dùng chọn một Bộ dữ liệu từ danh mục hoặc từ Trang chủ, họ bước vào **Dataset Workspace** (`#/datasets/{id}`).  
Thay vì hiển thị 7 tab kỹ thuật rời rạc (`overview`, `fields`, `versions`, `rules`, `history`, `compare`, `trend`), không gian làm việc được quy hoạch thành **3 khu vực chuyên trách**:

```
BỘ DỮ LIỆU: Danh sách khách hàng SME [v2 · Đã kiểm tra]
[Tab 1: 🔍 Kiểm tra dữ liệu]  [Tab 2: 📈 Lịch sử & Cải thiện]  [Tab 3: 📋 Cấu trúc & Thông tin]
```

### 3.1. Khu vực 1: Kiểm tra dữ liệu (`#/datasets/{id}/check`)
- **Mục tiêu:** Nơi người dùng thực hiện 90% thời lượng công việc hàng ngày.
- **Thành phần tích hợp:**
  1. *Thanh trạng thái tóm tắt file hiện tại:* Tên file nạp gần nhất, số dòng, thời điểm nạp.
  2. *Bảng chọn nhanh quy tắc (Quick Rule Matrix):* Bật/tắt nhanh các tiêu chuẩn dữ liệu cốt lõi (Bắt buộc điền, Không trùng lặp, Định dạng ngày, Định dạng số/tiền).
  3. *Nút hành động chính (Primary CTA):* **"Chạy kiểm tra ngay"** (hoặc tự động cập nhật khi đã có kết quả).
  4. *Khu vực kết quả kiểm tra tức thì:* Thẻ tổng hợp lỗi, số dòng có lỗi, tỷ lệ đạt chuẩn.
  5. *Bảng chi tiết các dòng vi phạm:* Có số thứ tự dòng tương ứng trong file Excel, nút xem chi tiết ô lỗi.
  6. *Hành động khắc phục:* Nút **"Tải báo cáo lỗi Excel (.xlsx)"** và nút **"Tải lên bản đã sửa"** ngay trên màn hình.

### 3.2. Khu vực 2: Lịch sử & Cải thiện (`#/datasets/{id}/history`)
- **Mục tiêu:** Theo dõi tiến độ làm sạch dữ liệu qua các đợt nạp file.
- **Thành phần tích hợp:**
  1. *Thẻ đối chiếu nhanh (1-Click Compare):* Tự động so sánh phiên bản vừa nạp ($v2$) với phiên bản trước đó ($v1$) để ghi nhận số lỗi đã khắc phục.
  2. *Biểu đồ xu hướng chất lượng (Quality Trend):* Trực quan hóa tỷ lệ dữ liệu sạch qua các kỳ (theo tuần/tháng), ẩn các chuỗi mã băm kỹ thuật.
  3. *Bảng lưu trữ các đợt kiểm tra:* Liệt kê từng lần chạy, ngày chạy, số dòng lỗi, trạng thái và nút xem lại chi tiết kết quả bất biến (Rule Snapshot).

### 3.3. Khu vực 3: Cấu trúc & Thông tin (`#/datasets/{id}/schema`)
- **Mục tiêu:** Cung cấp tài liệu và giải thích ý nghĩa các cột dữ liệu.
- **Thành phần tích hợp:**
  1. *Thông tin chung:* Người phụ trách, phòng ban/nguồn dữ liệu, mô tả mục đích sử dụng.
  2. *Danh mục các cột:* Tên cột, kiểu dữ liệu gợi ý (Số tiền, Ngày tháng, Văn bản), mô tả nghiệp vụ và ví dụ minh họa.
  3. *Công cụ chỉnh sửa metadata:* Cập nhật thông tin mô tả cột và thông tin liên hệ.

---

## 4. Bản đồ Tuyến đường (Sitemap & Route Map)

Nhằm đảm bảo **tính tương thích ngược hoàn hảo (Backward Compatibility)** và không làm hỏng các liên kết đã lưu (Deep Links / Bookmarks), hệ thống định tuyến được ánh xạ song song:

| Tuyến đường mới (Đề xuất HM-02B) | Tuyến đường cũ tương thích | Component phụ trách | Mục đích nghiệp vụ |
|---|---|---|---|
| `#/dashboard` | `#/dashboard` | `Dashboard.tsx` | Trang tổng quan định hướng công việc. |
| `#/datasets` | `#/datasets` | `CatalogPages.tsx` | Danh mục toàn bộ hồ sơ dữ liệu. |
| `#/datasets/{id}` | `#/datasets/{id}/overview` | `DatasetWorkspace.tsx` | Mặc định chuyển tiếp vào khu vực Kiểm tra dữ liệu. |
| `#/datasets/{id}/check` | `#/datasets/{id}/overview` | `DatasetWorkspace.tsx` | Khu vực 1: Bàn kiểm tra dữ liệu tập trung. |
| `#/datasets/{id}/history` | `#/datasets/{id}/history`, `#/datasets/{id}/versions` | `DatasetHistory.tsx` | Khu vực 2: Lịch sử, phiên bản & xu hướng. |
| `#/datasets/{id}/compare` | `#/datasets/{id}/compare` | `DatasetComparison.tsx` | Chế độ đối chiếu chuyên sâu hai lần chạy bất kỳ. |
| `#/datasets/{id}/schema` | `#/datasets/{id}/fields` | `DatasetSchema.tsx` | Khu vực 3: Cấu trúc cột & Metadata. |
| `#/datasets/{id}/rules` | `#/datasets/{id}/rules` | `RuleList.tsx` (Embedded) | Chế độ nâng cao: Cấu hình quy tắc chi tiết. |
| `#/datasets/{id}/runs/{runId}` | `#/datasets/{id}/runs/{runId}` | `Results.tsx` | Chi tiết kết quả của một đợt kiểm tra cụ thể. |
| `#/history` | `#/history` | `HistoryBrowser.tsx` | Tra cứu lịch sử kiểm tra toàn hệ thống. |
| `#/guide` | `#/guide` | `Guide.tsx` | Hướng dẫn sử dụng & file mẫu. |
| `#/accounts` | `#/accounts` | `Accounts.tsx` | Quản trị tài khoản (chỉ Admin). |

### 4.1. Quy tắc xử lý Deep Links & Chuyển hướng (Redirect Rules)
1. Khi truy cập URL cũ `#/datasets/{id}/overview` $\rightarrow$ Tự động chuyển hướng hiển thị giao diện `#/datasets/{id}/check`.
2. Khi truy cập `#/datasets/{id}/versions` $\rightarrow$ Chuyển hướng hiển thị danh sách phiên bản trong tab `#/datasets/{id}/history`.
3. Khi truy cập `#/datasets/{id}/fields` $\rightarrow$ Chuyển hướng hiển thị tab `#/datasets/{id}/schema`.
4. Khi truy cập `#/datasets/{id}/trend` $\rightarrow$ Mở khu vực biểu đồ xu hướng trong `#/datasets/{id}/history`.
5. Khi truy cập trực tiếp `#/datasets/{id}/runs/{runId}` $\rightarrow$ Mở trang kết quả chi tiết kèm thanh breadcrumb cho phép quay lại `#/datasets/{id}/check` chỉ bằng 1 click.

---

## 5. Hệ thống Điều hướng phân cấp (Breadcrumbs) & Tiêu đề trang

Thanh Breadcrumb luôn hiển thị ở đầu trang chính (`topbar`), phản ánh chính xác vị trí phân cấp của người dùng:

- **Cấp 1 (Gốc):** `Không gian dữ liệu` (hoặc tên tổ chức SME).
- **Cấp 2 (Màn hình chính):** `Trang chủ` / `Bộ dữ liệu` / `Lịch sử & Báo cáo` / `Hướng dẫn`.
- **Cấp 3 (Bộ dữ liệu cụ thể):** `Bộ dữ liệu` $\rightarrow$ `Danh sách khách hàng SME`.
- **Cấp 4 (Trang con / Lần kiểm tra):** `Bộ dữ liệu` $\rightarrow$ `Danh sách khách hàng SME` $\rightarrow$ `Đợt kiểm tra #48`.

---

## 6. Phân quyền và Bảo mật (Role-Based Navigation)

| Thành phần giao diện | Vai trò Người quản lý dữ liệu (`data_steward`) | Vai trò Quản trị viên (`admin`) |
|---|---|---|
| **Menu Quản trị tài khoản** | **Ẩn hoàn toàn** (nếu cố tình gõ URL `#/accounts` sẽ hiển thị thông báo từ chối truy cập 403 thân thiện). | **Hiển thị đầy đủ** (Tạo tài khoản, đổi vai trò, khóa tài khoản). |
| **Tạo / Sửa / Upload Bộ dữ liệu** | Cho phép toàn quyền thao tác. | Cho phép toàn quyền thao tác. |
| **Thiết lập quy tắc & Chạy kiểm tra** | Cho phép toàn quyền thao tác. | Cho phép toàn quyền thao tác. |
| **Xuất báo cáo Excel / CSV / JSON** | Cho phép toàn quyền tải về máy. | Cho phép toàn quyền tải về máy. |
| **Xem trạng thái hệ thống** | Cho phép xem tình trạng kết nối. | Cho phép xem tình trạng kết nối. |

