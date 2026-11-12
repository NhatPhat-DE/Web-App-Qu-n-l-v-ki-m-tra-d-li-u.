# DATAGUARD SME — HM-02C: THEME ARCHITECTURE & MULTI-THEME DESIGN SPECIFICATION

## 1. Tổng quan Kiến trúc Giao diện (Theme Architecture)

Để đáp ứng nhu cầu làm việc lâu dài của người dùng doanh nghiệp vừa và nhỏ (SME)—bao gồm kế toán, nhân viên kinh doanh, chuyên viên phân tích và người tổng hợp báo cáo dữ liệu—DataGuard SME chuẩn hóa kiến trúc giao diện theo mô hình Semantic Design Tokens và Multi-Theme linh hoạt.

Hệ thống hỗ trợ 4 chế độ hiển thị:
1. **System (Mặc định)**: Tự động phát hiện và đồng bộ theo cài đặt giao diện (Light/Dark) của hệ điều hành hoặc trình duyệt của người dùng.
2. **Light (Sáng rõ)**: Tối ưu cho môi trường văn phòng đủ sáng, độ tương phản sắc nét, phông chữ đậm nét và phân định rõ ràng giữa các phân vùng bảng biểu và báo cáo.
3. **Dark (Nền tối)**: Tối ưu cho làm việc trong điều kiện ánh sáng yếu hoặc người dùng kỹ thuật, giảm phát xạ ánh sáng xanh, nền sâu `#0b0f19` với thẻ bề mặt `#111827`, chữ tương phản cao không gây lóa mắt.
4. **Soft (Dịu mắt - Ngà ấm)**: Thiết kế đặc thù cho người dùng SME làm việc với số liệu, bảng biểu CSV nhiều giờ liên tục. Sử dụng tông màu nền ngà ấm tự nhiên (`#f7f5f0`), bề mặt trung tính ấm (`#ede8df`), văn bản màu đá tự nhiên (`#292524`), và điểm nhấn màu ngọc lục bảo thông sẫm (`#246b62`).

---

## 2. Chiến lược Chống Chớp Giao diện (Zero FOUT / Flash Prevention)

Hiện tượng nhấp nháy giao diện (Flash of Unstyled Theme - FOUT) xảy ra khi trình duyệt hiển thị mặc định giao diện Light trước khi bundle JavaScript của React kịp tải và khởi tạo `ThemeProvider`.

Để triệt tiêu hoàn toàn FOUT, DataGuard SME triển khai kỹ thuật **Head Execution Bootstrapper** trong file `frontend/index.html`:

```html
<script>
  (function() {
    try {
      var pref = localStorage.getItem('dataguard-theme') || 'system';
      var resolved = pref;
      if (pref === 'system') {
        resolved = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      document.documentElement.setAttribute('data-theme', resolved);
      document.documentElement.setAttribute('data-theme-preference', pref);
      document.documentElement.style.colorScheme = resolved === 'dark' ? 'dark' : 'light';
    } catch (e) {}
  })();
</script>
```

### Ưu điểm kỹ thuật:
- Chạy đồng bộ (blocking) ngay trong thẻ `<head>` trước khi thẻ `<body>` và `#root` được render lần đầu.
- Gán ngay lập tức thuộc tính `data-theme="light|dark|soft"` và `color-scheme` lên thẻ `<html>`.
- Trình duyệt áp dụng các biến CSS `--bg-app`, `--text-primary` ngay từ khung hình đầu tiên, ngăn chặn hoàn toàn hiện tượng chớp sáng/tối.

---

## 3. Kiến trúc Quản lý Trạng thái (`ThemeContext` & `ThemeProvider`)

Hệ thống quản lý trạng thái Theme được đóng gói tại `frontend/src/theme/ThemeContext.tsx` với các thành phần chính:

### Types:
- `ThemePreference`: `'system' | 'light' | 'dark' | 'soft'` — Lựa chọn của người dùng được lưu trữ trong `localStorage`.
- `ResolvedTheme`: `'light' | 'dark' | 'soft'` — Giao diện thực tế đang được áp dụng lên DOM.

### Lắng nghe và Đồng bộ Hệ thống:
- Khi người dùng chọn `system`, một listener `prefers-color-scheme: dark` được tự động đăng ký:
  ```ts
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  const handleChange = () => {
    const nextResolved = mediaQuery.matches ? 'dark' : 'light'
    setResolvedTheme(nextResolved)
    document.documentElement.setAttribute('data-theme', nextResolved)
    document.documentElement.style.colorScheme = nextResolved === 'dark' ? 'dark' : 'light'
  }
  mediaQuery.addEventListener('change', handleChange)
  ```
- Khi thiết bị người dùng chuyển từ chế độ Ngày sang Đêm (hoặc ngược lại), ứng dụng phản hồi ngay lập tức mà không cần tải lại trang.

---

## 4. Thành phần Chuyển đổi Giao diện (`ThemeSwitcher`)

Component `frontend/src/workspace/ThemeSwitcher.tsx` được thiết kế theo tiêu chuẩn Accessibility (ARIA) cao nhất:

1. **Cấu trúc ARIA**:
   - Container mang thuộc tính `role="radiogroup"` và `aria-label="Chọn giao diện hiển thị"`.
   - Mỗi nút tùy chọn mang `role="radio"`, `aria-checked={isSelected}`, `tabIndex={isSelected ? 0 : -1}`.
2. **Điều hướng bàn phím (Keyboard Navigation)**:
   - Hỗ trợ phím mũi tên `ArrowLeft` / `ArrowUp` và `ArrowRight` / `ArrowDown` để luân chuyển giữa các giao diện theo chuẩn WAI-ARIA Radio Group pattern.
   - Tự động chuyển `focus()` sang nút được chọn kế tiếp.
3. **Hiển thị trực quan**:
   - Biểu tượng `Monitor` (Hệ thống), `Sun` (Sáng), `Moon` (Tối), `Coffee` (Dịu mắt).
   - Trên desktop: hiển thị kèm nhãn ngắn gọn ("Hệ thống", "Sáng", "Tối", "Dịu mắt").
   - Trên thiết bị di động / màn hình hẹp (`<= 960px`): ẩn chữ, chỉ hiển thị biểu tượng nhưng vẫn bảo toàn đầy đủ `title` và `aria-label` cho Screen Reader.

---

## 5. Điểm gắn kết trong Ứng dụng

`ThemeSwitcher` được bố trí tại hai vị trí trọng yếu:
1. **Topbar Header (`DataCheckApp.tsx`)**: Đặt ngay trong thanh điều hướng cạnh thông tin người dùng và nút đăng xuất, giúp người dùng dễ dàng chuyển đổi bất cứ lúc nào trong phiên làm việc.
2. **Màn hình Đăng nhập (`SessionApp.tsx`)**: Đặt ở góc trên bên phải trang xác thực, cho phép người dùng lựa chọn chế độ dễ chịu nhất ngay từ trước khi nhập tài khoản.

---

## 6. Hướng dẫn cho Giai đoạn Xây dựng Frontend Mới (HM-02D)

Khi triển khai các màn hình mới ở HM-02D (Dashboard, Catalog, Dataset Workspace, Run Results, Rules Manager):
1. **Tuyệt đối không hardcode màu sắc**: Không viết mã màu trực tiếp như `#ffffff`, `#182230`, `rgb(240, 242, 245)` trong mã nguồn JSX/TSX hay trong các file CSS mới.
2. **Luôn sử dụng Semantic Tokens**:
   - Nền: `var(--bg-app)`, `var(--bg-surface)`, `var(--bg-surface-muted)`, `var(--bg-surface-hover)`.
   - Chữ: `var(--text-primary)`, `var(--text-secondary)`, `var(--text-muted)`.
   - Viền: `var(--border-default)`, `var(--border-subtle)`, `var(--border-input)`.
   - Hành động / Thương hiệu: `var(--primary)`, `var(--primary-hover)`, `var(--primary-subtle)`.
   - Trạng thái: `var(--success)`, `var(--warning)`, `var(--danger)`, `var(--info)`.
3. **Bảo toàn Focus State**: Luôn kiểm tra giao diện qua bàn phím (`Tab`, `Shift+Tab`) để đảm bảo outline `var(--focus-outline)` hiển thị sắc nét trên cả 4 giao diện.

