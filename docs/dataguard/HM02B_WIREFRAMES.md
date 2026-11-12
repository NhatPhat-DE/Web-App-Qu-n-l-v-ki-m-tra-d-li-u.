# BẢN ĐẶC TẢ WIREFRAMES & THIẾT KẾ GIAO DIỆN CHI TIẾT
## HỆ THỐNG DATAGUARD SME

**Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)  
**Hạng mục:** HM-02B: Wireframes & Detailed Component Layouts  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior Product Designer & UX Architect  

---

## 1. Màn hình UX-202: Trang chủ (Task-oriented Dashboard) & Danh mục dữ liệu

### 1.1. Bố cục Wireframe Trang chủ (`#/dashboard`)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [TOPBAR] Không gian dữ liệu / Trang chủ                             [🔔] [👤 Mai Nguyễn]│
├────────────────────────────────────────────────────────────────────────────────────────┤
│ BANNER CHÀO MỪNG & LỐI TẮT NHANH                                                       │
│ Xin chào Mai Nguyễn! Cùng hoàn thiện chất lượng dữ liệu hôm nay.                       │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ 🚀 BẮT ĐẦU CÔNG VIỆC NHANH:                                                        │ │
│ │ [➕ Tạo bộ dữ liệu mới]   [📥 Nạp file CSV kiểm tra ngay]   [📖 Xem hướng dẫn mẫu]  │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                        │
│ 4 CHỈ SỐ HOẠT ĐỘNG THỰC TẾ (Không dùng KPI giả)                                        │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────┐ │
│ │ 📁 Tổng bộ hồ sơ │ │ 📄 Đã có dữ liệu │ │ 🔍 Đợt kiểm tra  │ │ ⚠️ File cần sửa lỗi │ │
│ │      12 hồ sơ    │ │   10 có file     │ │   48 lượt xong   │ │   3 hồ sơ có lỗi    │ │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘ └─────────────────────┘ │
│                                                                                        │
│ KHU VỰC TRỌNG TÂM: DANH SÁCH BỘ DỮ LIỆU CẦN XỬ LÝ (Attention List)                     │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ ⚠️ BỘ DỮ LIỆU CÓ LỖI Ở LẦN KIỂM TRA MỚI NHẤT (3 bộ dữ liệu)                        │ │
│ │                                                                                    │ │
│ │ 1. Danh sách khách hàng SME (v2) · 15 dòng lỗi · Kiểm tra lúc 14:30 03/11           │ │
│ │    [Xem 15 dòng lỗi]   [📥 Tải báo cáo Excel sửa lỗi]   [Tải lên bản đã sửa]       │ │
│ │ ────────────────────────────────────────────────────────────────────────────────── │ │
│ │ 2. Báo cáo doanh số tháng 10 (v1) · 8 dòng lỗi · Kiểm tra lúc 09:15 02/11          │ │
│ │    [Xem 8 dòng lỗi]    [📥 Tải báo cáo Excel sửa lỗi]   [Tải lên bản đã sửa]       │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                        │
│ CÁC LƯỢT KIỂM TRA GẦN ĐÂY (Recent Activity)                                            │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Bộ dữ liệu            │ Phiên bản │ Thời điểm        │ Kết quả           │ Thao tác│ │
│ │ ───────────────────── │ ───────── │ ──────────────── │ ───────────────── │ ─────── │ │
│ │ Danh sách khách hàng  │ v2 (mới)  │ 03/11 14:30      │ ⚠️ Có 15 dòng lỗi │ [Mở xem]│ │
│ │ Đơn đặt hàng Q4       │ v1        │ 03/11 11:20      │ ✅ Đạt chuẩn 100% │ [Mở xem]│ │
│ │ Kho hàng tổng         │ v3        │ 02/11 16:45      │ ⚠️ Có 2 dòng lỗi  │ [Mở xem]│ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2. Màn hình Danh mục Dữ liệu (`#/datasets`)

- **Bộ lọc nghiệp vụ:**
  - Ô tìm kiếm: `Tìm theo tên, mô tả, người phụ trách, nguồn dữ liệu...`
  - Lọc theo phòng ban/nguồn: Tất cả / Kinh doanh / Kế toán / Kho vận.
  - Lọc theo trạng thái: Tất cả / Chưa có dữ liệu / Đạt chuẩn / Có lỗi cần sửa.
- **Bảng danh mục trực quan:**
  - *Tên bộ dữ liệu & Mô tả:* Tên đậm, mô tả ngắn gọn bên dưới.
  - *Người phụ trách & Nguồn:* Ví dụ: *"Mai Nguyễn · Phòng Kế toán"*.
  - *Trạng thái dữ liệu:* Hiển thị rõ **"Chưa có dữ liệu"** (màu xám nhạt) hoặc **"v2 · 1.500 dòng"**.
  - *Đợt kiểm tra gần nhất:* Huy hiệu trạng thái: `✅ Đạt chuẩn` hoặc `⚠️ 15 dòng lỗi`.
  - *Hành động tiếp theo (Next Action CTA):* Nút bấm tương ứng theo ngữ cảnh:
    - Nếu chưa có file: Nút **"Nạp file đầu tiên"** (Primary).
    - Nếu có lỗi: Nút **"Sửa lỗi"** (Secondary).
    - Nếu đã đạt: Nút **"Xem kết quả"** (Ghost).

---

## 2. Màn hình UX-203: Dataset Workspace (Bàn làm việc 3 khu vực)

### 2.1. Thanh định danh hồ sơ dữ liệu (Workspace Header)
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [<- Quay lại danh mục]                                                                 │
│ 📁 Danh sách khách hàng SME                                                            │
│ Phụ trách: Mai Nguyễn  ·  Nguồn: Phòng Kinh doanh  ·  Cập nhật: 03/11/2026             │
│                                                                                        │
│ [ 🔍 1. Kiểm tra dữ liệu (Đang chọn) ]  [ 📈 2. Lịch sử & Cải thiện ]  [ 📋 3. Cấu trúc]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2. Chi tiết Khu vực 1: Bàn kiểm tra dữ liệu (`#/datasets/{id}/check`)

#### Trường hợp A: Hồ sơ mới tạo (Chưa có file nào - Empty State)
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │                                  📁 [Icon File]                                    │ │
│ │                         BỘ DỮ LIỆU NÀY CHƯA CÓ FILE NÀO                            │ │
│ │          Hãy tải lên file CSV đầu tiên để bắt đầu quản lý và kiểm tra dữ liệu.      │ │
│ │                                                                                    │ │
│ │                       [ 📥 Tải file CSV đầu tiên ngay ]                            │ │
│ │                                                                                    │ │
│ │ 💡 Mẹo: Bạn có thể dùng file Excel sẵn có, chọn 'Save As' dạng CSV (UTF-8) để nạp. │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Trường hợp B: Đã nạp file (Sẵn sàng kiểm tra & xem kết quả)
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ THÔNG TIN FILE HIỆN TẠI                                                                │
│ 📄 File đang chọn: khach_hang_t11_v2.csv  ·  Số dòng: 200 dòng  ·  Nạp lúc: 14:30 03/11│
│ [Đổi file khác]                                            [ 📥 Tải lên bản đã sửa ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ BẢNG CHỌN NHANH TIÊU CHUẨN KIỂM TRA (Quick Rule Matrix - UX-204)                       │
│ Bật/tắt các điều kiện cần kiểm tra cho file này:                                       │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Tên cột      │ Bắt buộc điền │ Không trùng │ Định dạng dữ liệu     │ Cấu hình khác │ │
│ │ ──────────── │ ───────────── │ ─────────── │ ───────────────────── │ ───────────── │ │
│ │ ma_kh        │     [X]       │     [X]     │ Chữ & số (Văn bản)    │ [Sửa chi tiết]│ │
│ │ ten_kh       │     [X]       │     [ ]     │ Họ và tên (Văn bản)   │ [Sửa chi tiết]│ │
│ │ email        │     [X]       │     [X]     │ ✉️ Định dạng Email    │ [Sửa chi tiết]│ │
│ │ ngay_dang_ky │     [ ]       │     [ ]     │ 📅 Ngày (YYYY-MM-DD)  │ [Sửa chi tiết]│ │
│ │ so_tien      │     [X]       │     [ ]     │ 💰 Số tiền (> 0)      │ [0 - 100 tr]  │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│ [➕ Thêm điều kiện mới]   [✨ Gợi ý bằng AI]              [ 🚀 BẮT ĐẦU KIỂM TRA NGAY ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ KẾT QUẢ KIỂM TRA ĐỢT NÀY (Đợt #48 · UX-205)                                            │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌─────────────────────┐ │
│ │ 📊 Tỷ lệ sạch    │ │ ⚠️ Dòng có lỗi   │ │ 📋 Tổng số dòng  │ │ 💥 Lượt vi phạm     │ │
│ │     92.5%        │ │     15 dòng      │ │     200 dòng     │ │     22 lượt         │ │
│ └──────────────────┘ └──────────────────┘ └──────────────────┘ └─────────────────────┘ │
│                                                                                        │
│ HÀNH ĐỘNG XỬ LÝ LỖI:                                                                   │
│ [ 📥 TẢI BÁO CÁO EXCEL CÓ ĐÁNH DẤU LỖI (.xlsx) ]   [ Xuất file CSV lỗi ]              │
│                                                                                        │
│ BẢNG CHI TIẾT CÁC DÒNG CẦN SỬA LẠI:                                                    │
│ Lọc theo: [Tất cả lỗi 🔽]  [Tất cả cột 🔽]  [Tìm dòng hoặc nội dung lỗi...]            │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ Dòng Excel │ Cột bị lỗi │ Giá trị hiện tại │ Lỗi vi phạm                 │ Chi tiết│ │
│ │ ────────── │ ────────── │ ──────────────── │ ─────────────────────────── │ ─────── │ │
│ │ Dòng 5     │ ma_kh      │ (Ô bị trống)     │ Bắt buộc điền, không được bỏ│   [👁️] │ │
│ │ Dòng 18    │ email      │ nguyenvana       │ Thiếu ký tự @ (Sai email)   │   [👁️] │ │
│ │ Dòng 42    │ ngay_sinh  │ 30/02/2026       │ Ngày không tồn tại trong lịc│   [👁️] │ │
│ │ Dòng 89    │ ma_kh      │ KH001 (Bị trùng) │ Trùng mã với dòng số 2      │   [👁️] │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│ Hiển thị 1–10 trong tổng số 15 dòng lỗi. [Trang trước] [Trang 1/2] [Trang sau]        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Màn hình UX-204: Quick Rule Matrix & Thẻ đề xuất AI

### 3.1. Modal Tạo / Sửa Quy tắc nâng cao (Progressive Disclosure)
Khi người dùng bấm "Thêm điều kiện mới" hoặc "Sửa chi tiết", hộp thoại mở ra với thiết kế đơn giản:
- **Tên điều kiện:** Nhập tên dễ hiểu (Ví dụ: *"Mã số thuế phải đúng 10 số"*).
- **Cột áp dụng:** Chọn cột từ danh sách có sẵn của file.
- **Loại điều kiện:**
  1. *Ô bắt buộc (Không để trống)*.
  2. *Giá trị duy nhất (Không trùng lặp)*.
  3. *Kiểu dữ liệu:* Số nguyên, Số tiền/thập phân, Đúng/sai.
  4. *Định dạng ngày tháng:* YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY.
  5. *Khoảng số cho phép:* Từ [min] đến [max].
  6. *Thuộc danh sách cho phép:* Nhập các giá trị hợp lệ, phân cách bằng dấu phẩy.
  7. *Nâng cao (Regex):* Thu gọn trong mục `<details>Mẫu quy tắc tùy chỉnh dành cho chuyên gia</details>`.

### 3.2. Modal Gợi ý Quy tắc bằng AI (Đã loại bỏ mã JSON thô)
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ✨ AI ĐỀ XUẤT TIÊU CHUẨN KIỂM TRA CHO BỘ DỮ LIỆU                                  [X]  │
│ Dựa trên tên cột và phân tích mẫu dữ liệu, AI đề xuất 3 tiêu chuẩn phù hợp:            │
│ ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│ │ [X] 1. Cột 'ma_kh' không được để trống và không được trùng                        │ │
│ │     Lý do: Đây là mã định danh duy nhất của khách hàng (100% dòng có mã riêng biệt).│ │
│ │ ────────────────────────────────────────────────────────────────────────────────── │ │
│ │ [X] 2. Cột 'email' phải đúng định dạng thư điện tử                                │ │
│ │     Lý do: Phát hiện 98% giá trị chứa ký tự @ và tên miền hợp lệ.                  │ │
│ │ ────────────────────────────────────────────────────────────────────────────────── │ │
│ │ [X] 3. Cột 'ngay_dang_ky' theo định dạng YYYY-MM-DD                                │ │
│ │     Lý do: 100% các dòng đều ghi nhận ngày theo định dạng Năm-Tháng-Ngày.          │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│ ℹ️ An toàn dữ liệu: Quá trình gợi ý chỉ đọc cấu trúc và thống kê tổng hợp, tuyệt đối │
│ không gửi dữ liệu nhạy cảm hay thông tin cá nhân ra bên ngoài.                        │
│                                                                                        │
│ [Hủy bỏ]                                 [ ➕ Áp dụng 3 tiêu chuẩn đã chọn vào hồ sơ ] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Màn hình UX-205: Chi tiết Kết quả kiểm tra & Báo cáo Excel

- **Phân định rõ ràng giữa "Dòng lỗi" và "Lượt vi phạm":**
  - **Dòng có lỗi:** Đếm theo số dòng vật lý trong file Excel cần sửa (Ví dụ: `15 dòng`).
  - **Lượt vi phạm:** Tổng số lần phạm quy tắc (Ví dụ: `22 lượt` - giải thích rõ: Dòng 18 vừa sai email vừa để trống ngày sinh tính là 2 lượt vi phạm).
- **Tính toán số dòng Excel chính xác:**
  - Cột hiển thị: `Dòng Excel` = `row_number + 1` (do dòng 1 là dòng tiêu đề header).
  - Có nhãn giải thích: *"Dòng 5 tương ứng với dòng 5 trên Microsoft Excel"*.
- **Nút tải Excel chuyên biệt:**
  - Nhãn: **"Tải báo cáo Excel (.xlsx)"** với icon Excel màu xanh đặc trưng.
  - File tải về có 2 trang tính:
    1. *Trang 1: Tóm tắt kết quả kiểm tra & Danh sách quy tắc áp dụng*.
    2. *Trang 2: Toàn bộ các dòng lỗi được bôi đỏ tại các ô không đạt*.

---

## 5. Màn hình UX-206: Khu vực Lịch sử & Cải thiện (`#/datasets/{id}/history`)

### 5.1. Thẻ Đối chiếu nhanh giữa hai phiên bản (1-Click Comparison Card)
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 📈 ĐỐI CHIẾU TIẾN ĐỘ LÀM SẠCH DỮ LIỆU                                                  │
│ So sánh: Bản nạp v2 (Hôm nay 14:30) vs Bản nạp đầu v1 (Hôm qua 09:15)                  │
│                                                                                        │
│ ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────────────────┐ │
│ │ DÒNG CÓ LỖI          │  │ TỶ LỆ DỮ LIỆU SẠCH   │  │ ĐÁNH GIÁ TIẾN ĐỘ               │ │
│ │ 15 dòng (Giảm 12 dòng│  │ 92.5% (Tăng +6.0%)   │  │ 🎉 Bạn đã khắc phục được       │ │
│ │ so với 27 dòng ở v1) │  │ So với 86.5% ở v1    │  │ 80% số lỗi ban đầu!            │ │
│ └──────────────────────┘  └──────────────────────┘  └────────────────────────────────┘ │
│ [ 🔍 Xem chi tiết đối chiếu hai đợt kiểm tra ]       [ 📥 Tải báo cáo đối chiếu Excel ]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2. Biểu đồ Xu hướng Chất lượng (Quality Trend)
- Đồ thị đường thể hiện tỷ lệ % dữ liệu sạch qua các mốc thời gian (Đợt 1 $\rightarrow$ Đợt 2 $\rightarrow$ Đợt 3).
- **Loại bỏ hiển thị các chuỗi mã băm kỹ thuật** như `rule_set_fingerprint: "0a8b9f...c2"`.
- Thay thế bằng thông tin thân thiện: *"Áp dụng 5 tiêu chuẩn chất lượng"*.

---

## 6. Màn hình Quản trị Tài khoản (`#/accounts` - Dành cho Admin)

- **Bảng danh sách tài khoản:**
  - Cột: Tên đăng nhập, Vai trò (`Người phụ trách dữ liệu` / `Quản trị viên`), Trạng thái (`Đang hoạt động` / `Đã khóa`), Ngày tạo, Thao tác.
- **Hộp thoại Tạo / Sửa tài khoản:**
  - Tên đăng nhập (3–64 ký tự).
  - Mật khẩu & Xác nhận mật khẩu (Tối thiểu 12 ký tự, có nút bật/tắt mắt xem mật khẩu).
  - Lựa chọn vai trò dạng Radio button dễ hiểu kèm mô tả quyền hạn.
  - Cảnh báo bảo mật: *"Thay đổi trạng thái hoặc vai trò sẽ thu hồi phiên đăng nhập hiện tại của tài khoản đó."*

