# HỆ THỐNG THIẾT KẾ GIAO DIỆN (DESIGN SYSTEM SPECIFICATION)
## HỆ THỐNG DATAGUARD SME

**Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)  
**Hạng mục:** HM-02B: SaaS Design System & Visual Tokens  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior Product Designer & UI Architect  

---

## 1. Triết lý thiết kế (Design Philosophy)

1. **Nhẹ nhàng, Hiện đại & Chuyên nghiệp (Light & Trustworthy):**
   - Sử dụng nền trắng sáng kết hợp sắc xám lam nhẹ (`slate`), giảm thiểu tối đa các đường viền đậm hoặc màu nền gắt gây mỏi mắt khi làm việc với bảng tính lâu dài.
   - Tránh trang trí rườm rà; mọi thành phần thị giác đều phục vụ trực tiếp cho việc đọc hiểu và phát hiện lỗi dữ liệu.
2. **Khả năng tiếp cận cao (WCAG AA Compliance):**
   - Độ tương phản chữ viết và nền luôn đạt tối thiểu **4.5:1** cho văn bản thường và **3:1** cho tiêu đề lớn/icon.
   - Mọi trạng thái (Thành công, Cảnh báo, Lỗi) bắt buộc phải có **kết hợp cả Biểu tượng (Icon) và Chữ viết (Text)**, không dựa hoàn toàn vào màu sắc để truyền tải thông tin.
3. **Thân thiện với thao tác bàn phím (Keyboard Accessible):**
   - Đường viền chỉ báo tiêu điểm (`focus-visible`) rõ ràng với màu tím lam đậm (`#4f46e5`), độ dày 2px có khoảng cách đệm (offset).

---

## 2. Bảng màu chuẩn mực (Design Tokens & Color Palette)

### 2.1. Màu thương hiệu & Màu chính (Brand & Primary)
- **Primary Main:** `#4f46e5` (Indigo-600) — Dùng cho nút hành động chính, tab đang chọn, liên kết chính.
- **Primary Hover:** `#4338ca` (Indigo-700) — Trạng thái rê chuột.
- **Primary Active:** `#3730a3` (Indigo-800) — Trạng thái bấm giữ.
- **Primary Light / Surface:** `#eef2ff` (Indigo-50) — Nền các khối nổi bật, huy hiệu thông tin.

### 2.2. Màu trung tính & Nền (Neutral & Surface)
- **Text Main (Văn bản chính):** `#0f172a` (Slate-900) — Tiêu đề, chữ số quan trọng (Độ tương phản 16.5:1 trên nền trắng).
- **Text Secondary (Văn bản phụ):** `#334155` (Slate-700) — Nội dung bảng, nhãn trường nhập liệu (Độ tương phản 9.5:1).
- **Text Muted (Chú thích, gợi ý):** `#64748b` (Slate-500) — Chữ gợi ý, ngày giờ (Độ tương phản 4.6:1, đạt chuẩn WCAG AA).
- **Border Default:** `#e2e8f0` (Slate-200) — Đường viền bảng, thẻ, ô nhập liệu.
- **Background App:** `#f8fafc` (Slate-50) — Nền toàn bộ ứng dụng.
- **Background Card / Surface:** `#ffffff` (White) — Nền các khối bảng, modal, thẻ nổi.

### 2.3. Màu trạng thái nghiệp vụ (Semantic Colors)

| Trạng thái | Mã màu chính | Màu nền đệm | Màu chữ | Ứng dụng nghiệp vụ |
|---|---|---|---|---|
| **Thành công (Success)** | `#16a34a` (Green-600) | `#f0fdf4` (Green-50) | `#15803d` (Green-700) | Dữ liệu đạt chuẩn 100%, lưu thành công, kết nối máy chủ tốt. |
| **Cảnh báo (Warning)** | `#d97706` (Amber-600) | `#fffbeb` (Amber-50) | `#b45309` (Amber-700) | Phát hiện dòng vi phạm quy tắc, cần tải file sửa lại. |
| **Lỗi nghiêm trọng (Danger/Error)** | `#dc2626` (Red-600) | `#fef2f2` (Red-50) | `#b91c1c` (Red-700) | Cấu trúc file không khớp, lỗi kết nối, validation thất bại. |
| **Đang xử lý (Info / Progress)** | `#2563eb` (Blue-600) | `#eff6ff` (Blue-50) | `#1d4ed8` (Blue-700) | Đang kiểm tra dữ liệu, gợi ý mẹo làm việc. |

---

## 3. Hệ thống Kiểu chữ (Typography)

Sử dụng bộ font hệ thống không chân hiện đại, tối ưu hóa hiển thị tiếng Việt có dấu:
`font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;`

| Cấp bậc | Kích thước | Độ đậm (Weight) | Chiều cao dòng (Line-height) | Ứng dụng |
|---|---|---|---|---|
| **Display Heading** | 24px (1.5rem) | 700 (Bold) | 32px | Tiêu đề chính màn hình (Dashboard, Tên bộ dữ liệu). |
| **Section Heading** | 18px (1.125rem) | 600 (Semi-bold) | 26px | Tiêu đề khối bảng, tiêu đề hộp thoại modal. |
| **Subheading** | 15px (0.9375rem) | 600 (Semi-bold) | 22px | Tiêu đề bảng nhỏ, thẻ card tóm tắt. |
| **Body Regular** | 13px (0.8125rem) | 400 (Regular) | 20px | Nội dung chữ thông thường, ô dữ liệu bảng. |
| **Body Medium** | 13px (0.8125rem) | 500 (Medium) | 20px | Nhãn trường nhập liệu, tên cột bảng, nút bấm. |
| **Caption / Helper**| 12px (0.75rem) | 400 (Regular) | 16px | Dòng chú thích dưới input, ngày giờ cập nhật. |
| **Code / Mono** | 12px (0.75rem) | 500 (Medium) | 18px | Tên cột kỹ thuật (`ma_kh`), giá trị ô dữ liệu. |

---

## 4. Đặc tả các thành phần giao diện (UI Components Specification)

### 4.1. Nút bấm (Button)
- **Primary Button:** Nền `#4f46e5`, chữ trắng, bo góc 8px, padding 8px 16px, chiều cao 38px. Dùng cho hành động quan trọng nhất trên màn hình (Ví dụ: *"Bắt đầu kiểm tra"*, *"Tải file CSV"*).
- **Success Button (Nút Excel):** Nền `#16a34a`, hover `#15803d`, chữ trắng. Dùng riêng cho hành động **"Tải báo cáo Excel (.xlsx)"**.
- **Secondary Button:** Nền trắng, viền `#e2e8f0`, chữ `#334155`. Dùng cho hành động phụ (Ví dụ: *"Hủy"*, *"Đổi file"*).
- **Ghost Button:** Nền trong suốt, chữ `#475569`, hover nền `#f1f5f9`. Dùng cho icon xem trước, sửa mô tả.
- **Trạng thái Loading:** Hiển thị icon vòng xoay `LoaderCircle` xoay tròn (`.spin`), tự động disable chuột và phím.

### 4.2. Khối thẻ cảnh báo (Alert / Notice)
- Thiết kế dạng dải viền trái (Left-accented card) hoặc khung nền mềm bo góc 8px.
- Cấu trúc: `[Icon trạng thái] + [Tiêu đề đậm] + [Nội dung hướng dẫn xử lý] + [Hành động phụ nếu có]`.

### 4.3. Bảng dữ liệu (Data Table)
- **Header:** Nền xám nhạt `#f8fafc`, chữ in hoa nhẹ hoặc xám đậm `#475569`, font size 12px, font-weight 600.
- **Row:** Chiều cao tối thiểu 44px (touch target chuẩn), ngăn cách bằng viền mỏng `#f1f5f9`. Hiệu ứng hover dòng nhẹ `#f8fafc`.
- **Cột số dòng Excel:** Hiển thị dạng badge nổi bật (Ví dụ: `Dòng 5`) giúp mắt người dùng quét nhanh.

### 4.4. Hộp thoại (Modal Dialog)
- Lớp phủ nền mờ (Backdrop overlay): Màu `#0f172a` độ trong suốt 45% (`rgba(15, 23, 42, 0.45)`).
- Hộp thoại: Nền trắng, bo góc 12px, đổ bóng mềm (`box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1)`).
- Phím tắt: Tự động khóa phím Tab bên trong modal và đóng khi bấm phím `Escape`.

---

## 5. Thích ứng đa thiết bị (Responsive Breakpoints)

| Thiết bị | Breakpoint | Hành vi điều hướng & Bố cục |
|---|---|---|
| **Desktop lớn** | $\ge$ 1200px | Sidebar mở cố định 240px; lưới hiển thị 2–4 cột đầy đủ. |
| **Tablet / Laptop nhỏ**| 768px – 1199px | Sidebar thu gọn dạng icon hoặc ẩn sau nút menu; bảng dữ liệu cho phép cuộn ngang có chỉ báo bóng mờ. |
| **Mobile** | $\le$ 767px | Sidebar chuyển thành menu trượt từ trái có lớp phủ; các khối lưới (`.form-grid`, `.metric-grid`) tự động chuyển thành 1 cột đơn (`1fr`). Các nút bấm mở rộng toàn chiều ngang (`width: 100%`). |

