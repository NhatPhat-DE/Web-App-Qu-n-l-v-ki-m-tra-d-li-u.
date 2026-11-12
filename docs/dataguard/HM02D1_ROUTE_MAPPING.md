# DATAGUARD SME — HM-02D.1: ROUTE & NAVIGATION MAPPING SPECIFICATION

## 1. Mục tiêu và Nguyên tắc Ánh xạ Route

Giai đoạn **HM-02D.1: Core Layout & Navigation** chuẩn hóa kiến trúc điều hướng của DataGuard SME theo định hướng **Task-oriented UX**, giúp người dùng doanh nghiệp (kế toán, kinh doanh, chuyên viên phân tích) định vị công việc nhanh chóng mà không làm gián đoạn bất kỳ đường dẫn (deep link) hay chức năng nào sẵn có từ phiên bản trước.

### Các nguyên tắc cốt lõi:
1. **Không phá vỡ Deep Link (Zero Broken Links)**: Mọi URL hash cũ (`#/dashboard`, `#/datasets`, `#/history`, `#/rules`, `#/guide`, `#/accounts`, `#/datasets/:id/*`, `#/datasets/:id/runs/:runId`) tiếp tục hoạt động chính xác 100%.
2. **Hỗ trợ Alias linh hoạt**: Tự động chuyển đổi các alias phổ biến (`#/home` $\rightarrow$ `#/dashboard`, `#/reports` $\rightarrow$ `#/history`, `#/admin` $\rightarrow$ `#/accounts`, `#/help` $\rightarrow$ `#/guide`).
3. **Mặc định an toàn cho Dataset**: Truy cập `#/datasets/:id` tự động dẫn vào `#/datasets/:id/overview`.
4. **Phân quyền truy cập (Role-based Guard)**: Trang `#/accounts` chỉ hiển thị và cho phép truy cập đối với vai trò `admin`. Người dùng `data_steward` truy cập sẽ nhận thông báo phân quyền thân thiện thay vì lỗi crash.
5. **Bảo toàn trạng thái khi Refresh**: Lưu giữ chính xác route trên hash và vị trí tab đang chọn, không tự nhảy về trang chủ khi tải lại trình duyệt.

---

## 2. Bảng Ma trận Ánh xạ Tuyến đường (Route Mapping Matrix)

| Tuyến đường (Route / Hash) | Tên chức năng hiển thị | Nhóm điều hướng | Thành phần hiển thị (Component) | Quyền truy cập | Trạng thái bảo toàn |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`#/dashboard`** | Trang chủ | Menu chính (Topbar: Trang chủ) | `<Dashboard />` | Tất cả | Bảo toàn 100% |
| **`#/home`** *(Alias)* | Trang chủ | Tự động chuyển hướng | `<Dashboard />` | Tất cả | Ánh xạ mượt sang `#/dashboard` |
| **`#/datasets`** | Bộ dữ liệu | Menu chính | `<CatalogPage />` | Tất cả | Kèm badge đếm tổng bộ dữ liệu |
| **`#/datasets/:id`** | Chi tiết bộ dữ liệu | Không gian làm việc | `<DatasetPage tab="overview" />` | Tất cả | Tự động mở tab Tổng quan |
| **`#/datasets/:id/overview`** | Tổng quan bộ dữ liệu | Nhóm: **Kiểm tra dữ liệu** | `<DatasetPage tab="overview" />` | Tất cả | Nút chạy kiểm tra, v1/v mới |
| **`#/datasets/:id/rules`** | Quy tắc kiểm tra | Nhóm: **Kiểm tra dữ liệu** | `<RulesPage embedded />` | Tất cả | Quy tắc riêng của bộ dữ liệu |
| **`#/datasets/:id/runs/:runId`** | Kết quả lần kiểm tra | Chi tiết lần chạy | `<Results />` & `<Violations />` | Tất cả | Danh sách lỗi & phân tích |
| **`#/datasets/:id/history`** | Lịch sử kiểm tra | Nhóm: **Lịch sử & Cải thiện** | `<HistoryPage embedded />` | Tất cả | Lịch sử các lần chạy của dataset |
| **`#/datasets/:id/compare`** | Đối chiếu lần chạy | Nhóm: **Lịch sử & Cải thiện** | `<Comparison />` | Tất cả | So sánh kết quả 2 lần kiểm tra |
| **`#/datasets/:id/trend`** | Xu hướng chất lượng | Nhóm: **Lịch sử & Cải thiện** | `<QualityTrend />` | Tất cả | Biểu đồ diễn tiến tỷ lệ lỗi |
| **`#/datasets/:id/fields`** | Cột & Kiểu dữ liệu | Nhóm: **Cấu trúc & Thông tin**| `<DatasetPage tab="fields" />` | Tất cả | Bảng trường & Type Inference |
| **`#/datasets/:id/versions`** | Phiên bản dữ liệu | Nhóm: **Cấu trúc & Thông tin**| `<DatasetPage tab="versions" />` | Tất cả | Danh sách CSV đã nạp kèm v-tags |
| **`#/history`** | Lịch sử & Báo cáo | Menu chính | `<HistoryPage />` | Tất cả | Lịch sử kiểm tra toàn hệ thống |
| **`#/reports`** *(Alias)*| Lịch sử & Báo cáo | Tự động chuyển hướng | `<HistoryPage />` | Tất cả | Ánh xạ sang `#/history` |
| **`#/rules`** *(Legacy)*| Quy tắc kiểm tra chung | Tuyến tương thích ngược | `<RulesPage />` | Tất cả | Giữ nguyên cho deep link cũ |
| **`#/accounts`** | Quản trị | Menu chính (Hệ thống) | `<Accounts />` | `admin` | Phân quyền bảo vệ an toàn |
| **`#/admin`** *(Alias)* | Quản trị | Tự động chuyển hướng | `<Accounts />` | `admin` | Ánh xạ sang `#/accounts` |
| **`#/guide`** | Trợ giúp | Menu chính (Hỗ trợ) | `<Guide />` | Tất cả | Hướng dẫn sử dụng & file mẫu |
| **`#/help`** *(Alias)* | Trợ giúp | Tự động chuyển hướng | `<Guide />` | Tất cả | Ánh xạ sang `#/guide` |

---

## 3. Cấu trúc 3 Nhóm Nghiệp vụ trong Không gian Bộ dữ liệu (Dataset Workspace)

Thay vì một hàng 7 tab ngang phẳng dễ gây quá tải thông tin, giao diện không gian làm việc của bộ dữ liệu được cấu trúc thành **3 nhóm nghiệp vụ chuẩn SME**:

```
[Bộ dữ liệu: Khách hàng miền Bắc]
├── 1. KIỂM TRA DỮ LIỆU
│   ├── [Tổng quan] (hash: #/datasets/:id/overview)
│   └── [Quy tắc kiểm tra] (hash: #/datasets/:id/rules)
│
├── 2. LỊCH SỬ & CẢI THIỆN
│   ├── [Lịch sử kiểm tra] (hash: #/datasets/:id/history)
│   ├── [Đối chiếu lần chạy] (hash: #/datasets/:id/compare)
│   └── [Xu hướng chất lượng] (hash: #/datasets/:id/trend)
│
└── 3. CẤU TRÚC & THÔNG TIN
    ├── [Cột & Kiểu dữ liệu] (hash: #/datasets/:id/fields)
    └── [Phiên bản dữ liệu] (kèm badge đếm) (hash: #/datasets/:id/versions)
```

### Đặc điểm kỹ thuật:
- Sử dụng thẻ ngữ nghĩa ARIA: `<div className="workspace-tab-groups" role="navigation" aria-label="Phân nhóm chức năng bộ dữ liệu">`.
- Mỗi nhóm mang nhãn mô tả rõ ràng, kèm vùng `<div role="tablist">` và các thẻ liên kết `<a role="tab" aria-selected={isActive}>`.
- Hỗ trợ cuộn ngang mượt mà trên thiết bị di động (`overflow-x: auto; overscroll-behavior-x: contain`).
- Kích hoạt nhóm tự động (`group-active`) theo tab đang được chọn trên URL hash.

---

## 4. Phân cấp Breadcrumb tại Thanh Điều hướng (Topbar)

Thanh Topbar thể hiện đường dẫn phân cấp (Breadcrumb) rõ ràng, giúp người dùng luôn biết mình đang ở đâu và dễ dàng quay ngược lên cấp cha:

1. **Tại Trang chủ**: `DataGuard SME` $\rightarrow$ **Trang chủ**
2. **Tại Danh mục**: `Trang chủ` $\rightarrow$ **Bộ dữ liệu**
3. **Tại Chi tiết Dataset**: `Bộ dữ liệu` $\rightarrow$ `[Tên bộ dữ liệu]` $\rightarrow$ **[Tên Tab hiện tại]**
4. **Tại Kết quả kiểm tra một Run**: `Bộ dữ liệu` $\rightarrow$ `[Tên bộ dữ liệu]` $\rightarrow$ **Lần kiểm tra #[runId]**
5. **Tại Lịch sử & Báo cáo**: `Trang chủ` $\rightarrow$ **Lịch sử & Báo cáo**
6. **Tại Quản trị**: `Trang chủ` $\rightarrow$ **Quản trị**
7. **Tại Trợ giúp**: `Trang chủ` $\rightarrow$ **Trợ giúp**

Tất cả các điểm nút cấp cha đều là đường dẫn nhấp được (`<a href="...">`), có hiệu ứng hover đổi màu theo `--primary` và ngắt dòng bảo vệ (`text-overflow: ellipsis`) trên màn hình nhỏ.

---

## 5. Cơ chế Bảo vệ Thay đổi Chưa lưu (`confirmLeave`)

Khi người dùng đang nhập dở biểu mẫu (tạo bộ dữ liệu, tải CSV, cấu hình quy tắc) và cố gắng:
- Bấm vào mục menu Sidebar khác;
- Bấm vào Breadcrumb hoặc nút Quay lại;
- Bấm nút Đăng xuất;

Hệ thống kích hoạt trình chặn `confirmLeave()`:
```ts
if (!confirmLeave()) {
  history.replaceState(null, '', current || '#/dashboard')
  return
}
```
Nếu người dùng bấm **Hủy (Cancel)** trong hộp thoại xác nhận, URL hash hiện tại được khôi phục ngay lập tức qua `history.replaceState`, giữ nguyên dữ liệu đang nhập dở của người dùng mà không bị mất.

