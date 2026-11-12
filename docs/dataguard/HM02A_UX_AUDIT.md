# ĐÁNH GIÁ TOÀN DIỆN TRẢI NGHIỆM NGƯỜI DÙNG (UX AUDIT)
## HỆ THỐNG DATAGUARD SME (PHÁT TRIỂN TỪ DATALENS DQ / DATACHECK)

**Hạng mục:** HM-02A — Phân tích trải nghiệm người dùng & Đánh giá giao diện  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior UX Researcher, Product Designer, Business Analyst & SaaS Product Manager  
**Đối tượng mục tiêu (Target Persona):** Nhân viên kế toán, kinh doanh, nhân sự, tổng hợp dữ liệu tại các doanh nghiệp vừa và nhỏ (SME). Họ quen thuộc với Microsoft Excel/Google Sheets, không có kiến thức kỹ thuật về Data Engineering hay SQL/Regex.  

---

## 1. Tổng quan kiến trúc Frontend hiện tại

Hệ thống frontend hiện tại được xây dựng bằng **React 19**, **TypeScript** và **Vite**, sử dụng mô hình SPA (Single Page Application) điều hướng thông qua Hash-based Routing (`location.hash`).

### 1.1. Bản đồ điều hướng & Tuyến đường (Routes)

| Hash Route | Component chính | Mục đích nghiệp vụ |
|---|---|---|
| `#/dashboard` | `Dashboard.tsx` | Trang tổng quan: metrics thống kê, luồng nhanh 3 bước, bảng lần kiểm tra gần đây, phân bố vi phạm, danh sách bộ dữ liệu cần chú ý. |
| `#/datasets` | `CatalogPages.tsx` (`CatalogPage`) | Danh mục dữ liệu: danh sách bộ dữ liệu, bộ lọc (tìm kiếm, nguồn, người phụ trách, trạng thái), nút tạo bộ dữ liệu. |
| `#/datasets/{id}/{tab}` | `CatalogPages.tsx` (`DatasetPage`) | Chi tiết bộ dữ liệu gồm 7 tab: `overview` (Tổng quan), `fields` (Mô tả trường), `versions` (Phiên bản), `rules` (Quy tắc), `history` (Lịch sử), `compare` (Đối chiếu), `trend` (Xu hướng). |
| `#/datasets/{id}/runs/{runId}` | `Results.tsx` | Chi tiết kết quả kiểm tra chất lượng: metrics tổng quan, tab danh sách vi phạm (`Violations.tsx`), snapshot quy tắc, phân tích chiều dữ liệu (`Breakdown`). |
| `#/rules` | `RuleList.tsx` | Quản lý quy tắc toàn hệ thống hoặc theo từng dataset; mở modal tạo quy tắc thủ công (`RuleDialog`) hoặc gợi ý AI (`AISuggestions`). |
| `#/history` | `HistoryBrowser.tsx` | Lịch sử chạy kiểm tra tập trung của toàn hệ thống, hỗ trợ lọc đa chiều (ngày, dataset, version, status, quality). |
| `#/guide` | `Guide.tsx` | Hướng dẫn sử dụng 6 bước, tải file CSV mẫu thực hành (`customers`, `fixed`, `products`, `orders`). |
| `#/accounts` | `Accounts.tsx` | Quản trị tài khoản người dùng (chỉ hiển thị với vai trò `admin`). |

---

## 2. Kiểm kê trạng thái giao diện (UI States Inventory)

| Trạng thái | Đánh giá hiện trạng | Bằng chứng mã nguồn |
|---|---|---|
| **Loading State** | Sử dụng component dùng chung `<LoadState loading={...} />` với biểu tượng `LoaderCircle` xoay tròn (`.spin`). Thời gian chờ mượt mà nhưng thiếu skeleton loading cho bảng dữ liệu lớn. | [`ui.tsx#L51-L55`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/ui.tsx#L51-L55) |
| **Empty State** | Đã được chuẩn hóa qua component `<Empty />`. Sau HM-01C, dataset rỗng hiển thị thông điệp rõ ràng "Bộ dữ liệu chưa có file nào" kèm CTA "Tải file CSV đầu tiên". Tuy nhiên, một số màn hình như `QualityTrend` và `Comparison` khi thiếu dữ liệu chỉ hiển thị text đơn giản, chưa hướng dẫn người dùng cần làm gì tiếp theo để tạo ra dữ liệu. | [`ui.tsx#L56-L58`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/ui.tsx#L56-L58), [`CatalogPages.tsx#L55`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/CatalogPages.tsx#L55) |
| **Error Handling** | Các thông báo lỗi API nghiệp vụ (như `CSV_SCHEMA_MISMATCH`, `DATASET_NAME_EMPTY`) đã được Việt hóa rõ nghĩa qua component `<Notice kind="error" />`. | [`datasets.ts#L36-L42`](file:///d:/UserFile/DNCN/Webb/frontend/src/api/datasets.ts#L36-L42) |
| **Success Feedback** | Sử dụng thanh thông báo `<Notice kind="success">` ở đầu trang nội dung chính (`main`). Tồn tại vấn đề: thông báo biến mất khi chuyển trang (hashchange) khiến người dùng dễ mất dấu trạng thái. | [`DataCheckApp.tsx#L33-L47`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/DataCheckApp.tsx#L33-L47) |
| **Validation** | Form tạo Dataset (HM-01C) đã có inline validation hiển thị sát input. Các form còn lại (`MetadataDialog`, `RuleDialog`, `AccountDialog`) vẫn phụ thuộc nhiều vào HTML5 validation bubble mặc định của trình duyệt (`onInvalid`), thông điệp tiếng Việt đôi khi còn máy móc. | [`ui.tsx#L96-L108`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/ui.tsx#L96-L108), [`EditDialogs.tsx#L71-L82`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/EditDialogs.tsx#L71-L82) |

---

## 3. Đánh giá Khả năng tiếp cận (Accessibility) & Responsive

### 3.1. Accessibility (A11y)
- **Điểm cộng:**
  - Có liên kết bỏ qua đầu trang (`<a className="skip-link" href="#main">`) hỗ trợ người dùng bàn phím ([`DataCheckApp.tsx#L45`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/DataCheckApp.tsx#L45)).
  - Dialog có trap focus bằng phím `Tab` và `Shift+Tab`, tự động restore focus khi đóng ([`ui.tsx#L80-L94`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/ui.tsx#L80-L94)).
  - Hỗ trợ `prefers-reduced-motion` trong CSS ([`design.css#L19`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/design.css#L19)).
- **Hạn chế:**
  - Một số bảng dữ liệu cuộn ngang lớn (`.table-scroll`) thiếu chỉ báo trực quan cho người dùng dùng chuột rằng bảng có thể cuộn sang phải.
  - Tỷ lệ tương phản chữ phụ (`color: #7c899f`, `color: #847d9b`) trên nền trắng xám đôi khi xấp xỉ ngưỡng WCAG AA (dưới 4.5:1 với font chữ 12px).

### 3.2. Tính thích ứng trên thiết bị di động (Responsive)
- Hệ thống breakpoint CSS phân chia rõ ràng: Desktop lớn (>1550px), Laptop (1190px), Tablet (960px), Mobile (720px).
- Trên mobile (<720px): Sidebar tự động ẩn và chuyển thành menu trượt có overlay; các khối lưới (`.metric-grid`, `.form-grid`, `.detail-grid`) tự động chuyển thành cột đơn (`1fr`).
- **Điểm cần cải thiện:** Bảng dữ liệu lớn (như danh sách vi phạm `Violations` hay bảng xem trước dữ liệu CSV `RowsPage`) trên mobile bị tràn ngang nhiều, người dùng phải vuốt ngang liên tục để thấy nút hành động xem chi tiết bản ghi.

---

## 4. Bảng phân loại vấn đề UX chi tiết (P0 / P1 / P2)

> **Ghi chú phân loại bằng chứng:**
> - **[VERIFIED] - Đã xác minh:** Vấn đề có bằng chứng cụ thể hiển thị trực tiếp trong mã nguồn frontend/CSS hoặc lỗi giao diện rõ ràng.
> - **[HYPOTHESIS] - Giả thuyết UX:** Suy luận dựa trên tâm lý và thói quen của người dùng SME (dân văn phòng quen Excel), cần được kiểm chứng thêm qua usability test với người dùng thực tế.

| Mức độ | Mã ID | Tên vấn đề | Loại bằng chứng | Bằng chứng mã nguồn / Vị trí | Mô tả chi tiết & Tác động |
|---|---|---|---|---|---|
| **P0** | **UX-01** | Bắt buộc đối chiếu 100% cột ngăn cản sửa file CSV | **[VERIFIED]** | [`UploadDialog.tsx#L25-L28`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/UploadDialog.tsx#L25-L28), [`datasets.ts#L37`](file:///d:/UserFile/DNCN/Webb/frontend/src/api/datasets.ts#L37) | Khi người dùng tải phiên bản đã sửa $v2$, nếu Excel vô tình lưu thừa khoảng trắng ở tên cột, đổi thứ tự cột hoặc thêm cột tính toán phụ, hệ thống lập tức khóa chặn với lỗi `CSV_SCHEMA_MISMATCH`. Người dùng SME không hiểu tại sao file bị từ chối và bị tắc nghẽn luồng làm việc. |
| **P0** | **UX-02** | Thuật ngữ bản ghi CSV lệch 1 dòng so với số dòng Excel | **[VERIFIED]** | [`Violations.tsx#L63`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/Violations.tsx#L63), [`Results.tsx#L22`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/Results.tsx#L22) | Dòng thông báo ghi: *"Bản ghi 1 là bản ghi dữ liệu đầu tiên sau dòng tiêu đề, không phải số dòng vật lý của file."* Khi kế toán mở file trong Excel, dòng tiêu đề là dòng 1, bản ghi dữ liệu 1 nằm ở dòng số 2. Việc lệch index ($N$ vs $N+1$) khiến người dùng phải tự cộng trừ thủ công trong đầu khi tìm dòng lỗi trong file Excel hàng nghìn dòng. |
| **P0** | **UX-03** | Khái niệm "Chạy kiểm tra" (Run) tách biệt và gián đoạn với "Quy tắc" (Rules) | **[HYPOTHESIS]** | [`CatalogPages.tsx#L55`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/CatalogPages.tsx#L55), [`RunDialog.tsx#L33-L40`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/RunDialog.tsx#L33-L40) | Người dùng Excel quen tư duy: "Tôi đặt điều kiện $\rightarrow$ tôi thấy kết quả sai ngay". Tại hệ thống hiện tại, sau khi tải CSV và tạo quy tắc, người dùng phải tự tìm nút "Chạy kiểm tra", mở một hộp thoại mới (`RunDialog`), chọn lại phiên bản, rồi mới có kết quả. Nhiều thao tác phân mảnh không cần thiết. |
| **P1** | **UX-04** | Hiển thị mã JSON thô trong tính năng AI Gợi ý quy tắc | **[VERIFIED]** | [`AISuggestions.tsx#L56`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/AISuggestions.tsx#L56) | Thẻ `<pre className="payload-preview">{JSON.stringify(preview.payload, null, 2)}</pre>` hiển thị trực tiếp cấu trúc JSON kỹ thuật chứa mảng đối tượng, kiểu dữ liệu backend cho nhân viên văn phòng. Điều này gây sợ hãi công nghệ (technophobia) và không mang lại giá trị nghiệp vụ. |
| **P1** | **UX-05** | Form thiết lập quy tắc chứa tùy chọn Regex kỹ thuật (`pattern`) | **[VERIFIED]** | [`EditDialogs.tsx#L34-L35`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/EditDialogs.tsx#L34-L35), [`EditDialogs.tsx#L78`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/EditDialogs.tsx#L78) | Danh sách loại kiểm tra đưa tùy chọn "Mẫu tùy chỉnh (nâng cao)" với gợi ý cú pháp RE2. Người dùng SME không biết viết biểu thức chính quy (Regex). Thiếu các mẫu thông dụng sẵn có như: Số điện thoại Việt Nam, Mã số thuế, Căn cước công dân. |
| **P1** | **UX-06** | Trang chi tiết Dataset có quá nhiều tab phụ (7 tabs) | **[HYPOTHESIS]** | [`CatalogPages.tsx#L43`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/CatalogPages.tsx#L43) | Thanh điều hướng tab gồm: Tổng quan, Mô tả trường, Phiên bản, Quy tắc, Lịch sử kiểm tra, Đối chiếu, Xu hướng. Đối với người dùng SME, việc phân tán thông tin qua 7 tab khiến họ không biết "bước tiếp theo cần làm gì" (thiếu tính Task-oriented). |
| **P1** | **UX-07** | Luồng đối chiếu hai lần kiểm tra (Compare) khó tiếp cận | **[VERIFIED]** | [`QualityInsights.tsx#L10-L24`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/QualityInsights.tsx#L10-L24) | Màn hình `Comparison` yêu cầu người dùng phải tự bấm chọn lần A, chọn lần B trong bảng lịch sử rồi mới bấm nút "Đối chiếu". Không có phím tắt tự động so sánh lần chạy mới nhất với lần chạy liền trước đó của cùng một phiên bản/file. |
| **P1** | **UX-08** | Thông báo thành công biến mất khi người dùng chuyển trang | **[VERIFIED]** | [`DataCheckApp.tsx#L33`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/DataCheckApp.tsx#L33) | Khi tạo dataset mới thành công, hệ thống gán `success = 'Đã tạo...'`, nhưng ngay lập tức `location.hash` đổi sang trang chi tiết, sự kiện `hashchange` kích hoạt và xóa sạch thông báo (`setSuccess('')`), làm mất phản hồi tích cực tới người dùng. |
| **P2** | **UX-09** | Xuất báo cáo lỗi (Export) bị ẩn trong menu dropdown | **[VERIFIED]** | [`Violations.tsx#L63`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/Violations.tsx#L63) | Nút "Xuất CSV lỗi" nằm cạnh một thẻ `<select>` tiêu đề "Báo cáo đầy đủ… (Tải Excel / Tải JSON)". Người dùng kế toán muốn tải trực tiếp file Excel tổng hợp có màu định dạng để chuyển cho phòng ban sửa thì lại dễ bấm nhầm vào CSV hoặc bỏ qua menu này. |
| **P2** | **UX-10** | Trạng thái hiển thị thuật ngữ kỹ thuật bộ máy kiểm tra (Engine Fingerprint) | **[VERIFIED]** | [`Results.tsx#L41`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/Results.tsx#L41), [`QualityInsights.tsx#L28`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/QualityInsights.tsx#L28) | Hiển thị chuỗi băm kỹ thuật như `rule_set_fingerprint` dạng mã hex hoặc `engine_version: "v5"` gây bối rối cho người dùng phổ thông khi đọc báo cáo. |

