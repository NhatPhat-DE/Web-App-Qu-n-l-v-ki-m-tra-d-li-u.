# DATAGUARD SME — HM-01D: FRONTEND IMPLEMENTATION REPORT

## 1. Tổng quan giao diện quản lý 3 cấp (DG-305)

Giao diện người dùng được tổ chức rõ ràng theo phân cấp 3 tầng dữ liệu, tối ưu hóa cho người dùng doanh nghiệp SME:

```
[Level 1: Danh mục Bộ dữ liệu]
  ├── Hiển thị số đợt dữ liệu (e.g. 2 đợt) và phiên bản mới nhất
  └── Nhấp vào Bộ dữ liệu -> Chuyển đến Level 2

[Level 2: Chi tiết Bộ dữ liệu - Tab "Đợt dữ liệu"]
  ├── Nút "+ Tạo đợt mới"
  ├── Bảng danh sách các Đợt dữ liệu: Tên đợt, Kỳ dữ liệu, Số phiên bản, Ngày tạo
  └── Nhấp vào Đợt dữ liệu -> Chuyển đến Level 3

[Level 3: Chi tiết Đợt dữ liệu (Batch Detail Page)]
  ├── Thông tin đợt: Tên, Kỳ dữ liệu, Ngày tạo, Nút "Sửa thông tin"
  ├── Thao tác nhanh: "Tải file đầu tiên (v1)" (nếu đợt trống) hoặc "Tải bản đã sửa (v2...)"
  ├── Thẻ đối chiếu chu trình khắc phục lỗi (Closed-loop Remediation Card)
  └── Danh sách các phiên bản trong đợt kèm kết quả kiểm tra chất lượng
```

---

## 2. Chi tiết các Component đã triển khai

### 2.1. Dialog tạo đợt mới: `CreateBatchDialog.tsx`
- Form nhập thông tin:
  - Tên đợt dữ liệu (bắt buộc, tối đa 200 ký tự, kiểm tra không được để trống hoặc chỉ có khoảng trắng).
  - Kỳ dữ liệu (tùy chọn, tối đa 100 ký tự, ví dụ: "10/2026", "Quý 4/2026").
  - Mô tả nghiệp vụ (tùy chọn, tối đa 2000 ký tự).
- Tính năng: Kiểm tra trạng thái dirty để chống mất dữ liệu khi đóng, hiển thị thông báo lỗi chi tiết, tự động chuyển hướng đến trang chi tiết đợt dữ liệu ngay sau khi tạo thành công.

### 2.2. Trang chi tiết đợt dữ liệu: `BatchDetailPage.tsx`
- Đường dẫn route: `#/datasets/{id}/batches/{batch_id}`
- Breadcrumb đồng bộ: `Bộ dữ liệu > [Tên Dataset] > Đợt dữ liệu > Đợt #[ID]`
- Hỗ trợ các hành động:
  - Xem trước dữ liệu thô từng phiên bản (`PreviewDialog`).
  - Chạy kiểm tra chất lượng trực tiếp cho phiên bản trong đợt.
  - Xem báo cáo lỗi chất lượng hoặc kết quả kiểm tra.
  - Tải bản sửa CSV (`UploadDialog` kế thừa thông tin `batch`).

### 2.3. Closed-loop Remediation Card (DG-306)
Khi đợt dữ liệu có từ 2 phiên bản trở lên (ví dụ: v1 file gốc, v2 file sửa):
- Tự động so sánh phiên bản đầu tiên ($v_1$) và phiên bản mới nhất ($v_N$).
- Tính toán độ lệch số bản ghi lỗi: $\Delta_{\text{errors}} = \text{Errors}_{v_1} - \text{Errors}_{v_N}$.
- Tính tỷ lệ cải thiện chất lượng: $\% = (\Delta_{\text{errors}} / \text{Errors}_{v_1}) \times 100$.
- Phân loại trực quan:
  - **Khắc phục hoàn toàn** (Đã giải quyết 100% lỗi): Banner màu xanh thành công (`resolved`).
  - **Đã cải thiện** (Số lỗi giảm): Banner màu xanh dương thông tin (`improved`).
  - **Chất lượng suy giảm** (Số lỗi tăng thêm): Banner màu đỏ cảnh báo (`regressed`).
  - **Chưa có thay đổi**: Banner màu vàng (`unchanged`).
- Nút bấm trực tiếp "So sánh chi tiết lần chạy" điều hướng đến công cụ Run Comparison.

### 2.4. Tab "Đợt dữ liệu" trong `CatalogPages.tsx`
- Đưa tab `{ id: 'batches', label: 'Đợt dữ liệu' }` vào nhóm `Kiểm tra dữ liệu` ngay sau tab `Tổng quan`.
- Hiển thị badge số lượng đợt trên tiêu đề tab khi `batch_count > 0`.
- Tích hợp ô tìm kiếm đợt dữ liệu theo tên, kỳ dữ liệu và phân trang bảng.

### 2.5. Tuân thủ Design System & Đa giao diện (Multi-theme)
- 100% màu sắc và card sử dụng biến ngữ nghĩa (Semantic Tokens):
  - `--bg-surface`, `--bg-surface-muted`, `--border-default`
  - `--primary`, `--success`, `--warning`, `--danger`, `--info`
  - `--success-subtle`, `--danger-subtle`, `--warning-subtle`, `--info-subtle`
- Không sử dụng bất kỳ mã màu hardcode nào (#hex, rgb), tương thích hoàn toàn 4 theme (Light, Dark, Soft, High Contrast).

