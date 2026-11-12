# DATAGUARD SME — HM-02C: SEMANTIC COLOR TOKENS & PALETTE SPECIFICATION

## 1. Triết lý Thiết kế Design Tokens

Kiến trúc Design Tokens của DataGuard SME được cấu trúc theo 3 tầng (3-tier Token Architecture):
1. **Global/Reference Tokens**: Các giá trị màu gốc (vd: Indigo 50–950, Slate 50–900, Amber, Emerald, Red, Stone).
2. **Semantic Tokens**: Các biến CSS mang ý nghĩa nghiệp vụ (vd: `--bg-app`, `--bg-surface`, `--text-primary`, `--border-default`, `--primary`, `--success`, `--danger`).
3. **Component Tokens**: Tái sử dụng trực tiếp các Semantic Tokens trong các thành phần (vd: Button, Input, Card, Table, Badge, Dialog).

Tất cả các thành phần UI trong DataGuard SME đều liên kết qua Semantic Tokens. Việc chuyển đổi Theme chỉ đơn thuần là gán lại giá trị của các Semantic Tokens tương ứng trong từng khối `[data-theme="..."]`.

---

## 2. Bảng Tra cứu Toàn diện Semantic Tokens (Token Reference Matrix)

| Tên biến CSS Token | Mục đích sử dụng | Light Theme | Dark Theme | Soft Theme (Dịu mắt) | Ghi chú & Tương phản |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`--bg-app`** | Nền chính toàn màn hình ứng dụng | `#f8fafc` (Slate 50) | `#0b0f19` (Deep Obsidian) | `#f7f5f0` (Warm Ivory) | Nền trung lập bao quanh các thẻ |
| **`--bg-surface`** | Nền thẻ, bảng, panel, dialog, sidebar, topbar | `#ffffff` (White) | `#111827` (Gray 900) | `#ffffff` (Pure Warm White) | Bề mặt tương tác chính |
| **`--bg-surface-elevated`** | Nền popover, menu thả xuống, floating card | `#ffffff` | `#1f2937` (Gray 800) | `#fcfbf8` (Warm Shell) | Tầng nổi |
| **`--bg-surface-muted`** | Nền header bảng (`<th>`), ô nhập phụ, preview code | `#f1f5f9` (Slate 100) | `#1e293b` (Slate 800) | `#ede8df` (Ivory Neutral) | Phân tách khu vực |
| **`--bg-surface-hover`** | Trạng thái rê chuột trên dòng bảng biểu, menu | `#f8fafc` | `#283548` (Slate Hover) | `#f2eee5` (Muted Warm) | Phản hồi tương tác |
| **`--bg-input`** | Nền ô nhập liệu (`<input>`, `<select>`, `<textarea>`) | `#ffffff` | `#0f172a` (Slate 950) | `#ffffff` | Tương phản tốt với chữ |
| **`--text-primary`** | Tiêu đề chính, nhãn quan trọng, dữ liệu bảng chính | `#0f172a` (17.5:1) | `#f8fafc` (16.7:1) | `#292524` (11.2:1) | Vượt xa chuẩn WCAG AA 4.5:1 |
| **`--text-secondary`** | Văn bản giải thích, mô tả, nội dung thẻ | `#475569` (5.9:1) | `#cbd5e1` (10.1:1) | `#44403c` (8.2:1) | Đạt chuẩn WCAG AA ($\ge 4.5:1$) |
| **`--text-muted`** | Chú thích nhỏ, breadcrumb, placeholder, thời gian | `#64748b` (4.6:1) | `#94a3b8` (5.8:1) | `#57534e` (5.4:1) | Đạt chuẩn WCAG AA ($\ge 4.5:1$) |
| **`--text-inverse`** | Văn bản hiển thị trên nền tối/ngược | `#ffffff` | `#0f172a` | `#ffffff` | Dùng cho nút chính |
| **`--border-default`** | Đường kẻ bảng, viền thẻ card, viền ngăn cách | `#cbd5e1` | `#334155` | `#d8d1c5` | Đường nét phân chia rõ ràng |
| **`--border-subtle`** | Đường kẻ mờ giữa các hàng bảng biểu | `#e2e8f0` | `#1e293b` | `#e8e3d9` | Nhẹ nhàng, không rối mắt |
| **`--border-input`** | Viền mặc định của ô nhập liệu | `#94a3b8` | `#475569` | `#b8aea0` | Phân định trường nhập |
| **`--border-focus`** | Viền khi focus và vòng chọn bàn phím | `#4338ca` (7.8:1) | `#818cf8` (8.5:1) | `#246b62` (5.7:1) | Đạt chuẩn Non-text Contrast $\ge 3:1$ |
| **`--primary`** | Màu chủ đạo (Nút hành động chính, tab đang chọn) | `#4338ca` (Indigo 700) | `#6366f1` (Indigo 500) | `#246b62` (Deep Pine Teal) | Nhận diện thương hiệu vững chắc |
| **`--primary-hover`** | Trạng thái hover của nút bấm chính | `#3730a3` | `#818cf8` | `#1b524b` | Phản hồi xúc giác thị giác |
| **`--primary-subtle`** | Nền badge chủ đạo, banner chào mừng, step hiện tại | `#eef2ff` | `#1e1b4b` | `#e6f2f0` | Nhẹ nhàng, êm dịu |
| **`--primary-subtle-border`**| Viền badge chủ đạo, viền hộp thông báo chính | `#c7d2fe` | `#3730a3` | `#b6dad5` | Tạo khối mềm mại |
| **`--primary-contrast`**| Màu chữ hiển thị bên trong nút chủ đạo | `#ffffff` | `#ffffff` | `#ffffff` | Tương phản $\ge 4.5:1$ |
| **`--success`** | Báo trạng thái Đạt (Passed), Thành công, Hoàn tất | `#15803d` (4.9:1) | `#22c55e` (9.5:1) | `#2e7448` (5.3:1) | Đạt chuẩn WCAG AA |
| **`--success-subtle`** | Nền thông báo thành công, badge đạt quy tắc | `#f0fdf4` | `#052e16` | `#eaf4ed` | Êm mắt, dễ phân biệt |
| **`--success-border`** | Viền badge thành công | `#bbf7d0` | `#166534` | `#b8dec4` | Rõ nét |
| **`--warning`** | Cảnh báo bản ghi lỗi dữ liệu, lưu ý, cần rà soát | `#b45309` (4.6:1) | `#f59e0b` (8.8:1) | `#97621c` (4.8:1) | Đạt chuẩn WCAG AA |
| **`--warning-subtle`** | Nền thẻ cảnh báo lỗi, badge cảnh báo | `#fffbeb` | `#451a03` | `#fcf3e6` | Phân biệt tức thì |
| **`--warning-border`** | Viền thẻ cảnh báo | `#fde68a` | `#92400e` | `#ecd3ad` | Rõ nét |
| **`--danger`** | Lỗi nghiêm trọng, thực thi thất bại, xóa bỏ | `#b91c1c` (6.2:1) | `#ef4444` (7.6:1) | `#b03737` (5.8:1) | Đạt chuẩn WCAG AA |
| **`--danger-subtle`** | Nền thông báo lỗi, nút nguy hiểm | `#fef2f2` | `#450a0a` | `#fdf0f0` | Báo động rõ ràng |
| **`--danger-border`** | Viền thông báo lỗi | `#fecaca` | `#991b1b` | `#f5c2c2` | Rõ nét |
| **`--info`** | Hướng dẫn, thông tin hệ thống, ghi chú | `#0369a1` (5.7:1) | `#38bdf8` (9.8:1) | `#1f6f8b` (5.1:1) | Đạt chuẩn WCAG AA |
| **`--info-subtle`** | Nền hướng dẫn, chú thích | `#f0f9ff` | `#082f49` | `#e6f4f8` | Thư thái |
| **`--info-border`** | Viền hướng dẫn | `#bae6fd` | `#0369a1` | `#b3dfe8` | Rõ nét |
| **`--focus-outline`** | Đường bao focus bàn phím | `2px solid #4338ca` | `2px solid #818cf8` | `2px solid #246b62` | Chuẩn WCAG 2.4.11 |

---

## 3. Hệ thống Đổ bóng (Elevation & Shadow Tokens)

Để duy trì chiều sâu không gian giữa các lớp giao diện (thẻ, popup, dialog):

- **`--shadow-sm`**:
  - Light: `0 1px 2px 0 rgb(0 0 0 / 0.05)`
  - Dark: `0 1px 2px 0 rgb(0 0 0 / 0.5)`
  - Soft: `0 1px 2px 0 rgb(41 37 36 / 0.05)`
- **`--shadow-md`**:
  - Light: `0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06)`
  - Dark: `0 4px 6px -1px rgb(0 0 0 / 0.4)`
  - Soft: `0 4px 6px -1px rgb(41 37 36 / 0.07)`
- **`--shadow-dialog`**:
  - Light: `0 20px 25px -5px rgb(0 0 0 / 0.15), 0 8px 10px -6px rgb(0 0 0 / 0.1)`
  - Dark: `0 25px 50px -12px rgb(0 0 0 / 0.7)`
  - Soft: `0 20px 25px -5px rgb(41 37 36 / 0.12)`

---

## 4. Tương thích Ngược (Legacy Compatibility Tokens)

Để không làm hỏng các component hiện hữu trước khi được chuẩn hóa ở HM-02D, các biến CSS cũ được ánh xạ sang hệ thống mới:

```css
--muted: var(--text-muted);
--border: var(--border-default);
--green: var(--success);
--amber: var(--warning);
--red: var(--danger);
```
Nhờ đó, 100% các đoạn CSS cũ và các biểu đồ sẵn có tiếp tục hiển thị chính xác mà không gặp lỗi hiển thị hay mất màu.

