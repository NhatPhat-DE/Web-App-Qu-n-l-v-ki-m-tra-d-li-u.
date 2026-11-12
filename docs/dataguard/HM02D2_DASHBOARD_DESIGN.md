# DATAGUARD SME — HM-02D.2: TASK-ORIENTED DASHBOARD & DATA WORKBENCH DESIGN SPECIFICATION

## 1. Mục tiêu và Triết lý Thiết kế

Trong phiên bản DataCheck trước đây, Dashboard tập trung hiển thị các biểu đồ kỹ thuật (conic-gradient donut phân bố vi phạm, danh sách lỗi rời rạc) mà không trả lời được các câu hỏi then chốt của người dùng SME (kế toán, kinh doanh, chuyên viên phân tích dữ liệu):
- *Tôi đang có bao nhiêu bộ dữ liệu?*
- *Bộ dữ liệu nào đang thiếu file CSV hoặc chưa kiểm tra?*
- *Dữ liệu nào đang có lỗi cần sửa gấp?*
- *Hôm nay tôi cần làm gì tiếp theo?*

Hạng mục **HM-02D.2** tái thiết kế toàn diện trang Dashboard thành **Bàn làm việc dữ liệu (Data Workbench)** theo các nguyên tắc:
1. **Task-oriented UX**: Giao diện tập trung vào hành động thực tế cần làm thay vì chỉ hiển thị số liệu tĩnh.
2. **Ngôn ngữ SME đơn giản**: Loại bỏ các thuật ngữ gây bối rối (fingerprint, engine version, schema hash, payload JSON).
3. **Phân loại trạng thái dữ liệu chính xác tuyệt đối**:
   - Chưa có file $\neq$ Đã kiểm tra.
   - Chưa kiểm tra $\neq$ Đạt.
   - Lỗi kỹ thuật máy chủ (`failed`) $\neq$ Dữ liệu sai (`completed` with errors).
4. **Không có CTA giả (Zero Dead Buttons)**: Mọi nút bấm đều liên kết tới hành động tương ứng trong chu trình xử lý dữ liệu.

---

## 2. Giải đáp 5 Câu hỏi Cốt lõi của Người dùng SME

| Câu hỏi của người dùng | Vị trí phản hồi trên Dashboard | Cơ chế & Dữ liệu hiển thị |
| :--- | :--- | :--- |
| **1. Tôi đang quản lý bao nhiêu bộ dữ liệu?** | KPI Card 1: **Tổng bộ dữ liệu** & Nút **Xem danh mục** | Số lượng tổng quát từ `datasets.length`, kèm chú thích số lượng bộ dữ liệu đã nạp file CSV. |
| **2. Bộ dữ liệu nào chưa có file hoặc chưa kiểm tra?** | KPI Card 2 & Bộ lọc **Chưa có file**, **Chờ kiểm tra** | Thẻ cảnh báo số lượng và danh sách chi tiết các bộ dữ liệu chưa có file CSV hoặc phiên bản mới chưa chạy kiểm tra. |
| **3. Bộ dữ liệu nào đang có lỗi?** | KPI Card 3 & Thẻ **Dữ liệu cần chú ý** (Tab: **Có dòng lỗi**) | Hiển thị chính xác tên bộ dữ liệu, số dòng có lỗi, và nút **Xem lỗi** mở thẳng màn hình kết quả lần chạy. |
| **4. Tôi cần làm gì tiếp theo?** | Thanh **Thao tác nhanh (Quick Actions Bar)** | Nút gợi ý thông minh: Nếu có bộ dữ liệu lỗi $\rightarrow$ Gợi ý "Sửa lỗi [Tên]", nếu có file chưa kiểm tra $\rightarrow$ Gợi ý "Kiểm tra [Tên]", nếu chưa có file $\rightarrow$ Gợi ý "Tải file [Tên]". |
| **5. Tôi có thể tiếp tục công việc ở đâu?** | Bảng **Lượt kiểm tra gần đây (Recent Runs)** | Hiển thị 5 lần chạy mới nhất kèm trạng thái, thời gian và nút **Xem kết quả**. |

---

## 3. Cấu trúc Khối Bàn làm việc (Workbench Layout Architecture)

Giao diện được phân bổ thành 5 phân khu trực quan:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. TIÊU ĐỀ: Bàn làm việc                                               │
│    [+ Tạo bộ dữ liệu]  [▶ Chạy kiểm tra]                               │
├────────────────────────────────────────────────────────────────────────┤
│ 2. THANH THAO TÁC NHANH (QUICK ACTIONS BAR)                            │
│    [+ Tạo bộ dữ liệu mới]  [📁 Xem danh mục (n)]  [▶ Tiếp tục xử lý]    │
├────────────────────────────────────────────────────────────────────────┤
│ 3. HƯỚNG DẪN 3 BƯỚC CHO SME (Có thể ẩn/hiện hoặc hiển thị khi mới dùng) │
│    [01 Tạo bộ dữ liệu] ──▶ [02 Tải file CSV] ──▶ [03 Kiểm tra dữ liệu] │
├────────────────────────────────────────────────────────────────────────┤
│ 4. 4 THẺ CHỈ SỐ KPI TỔNG QUAN                                          │
│    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│    │ Tổng bộ d.liệu│ │ Chưa có file │ │ Cần xem xét  │ │ Đã hoàn tất  │  │
│    │     [ 12 ]   │ │     [ 2 ]    │ │    [ 3 ] ⚠   │ │    [ 28 ]    │  │
│    └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
├────────────────────────────────────────────────────────────────────────┤
│ 5. KHU VỰC CÔNG VIỆC CHÍNH (DASHBOARD GRID)                             │
│ ┌────────────────────────────────────────┐ ┌─────────────────────────┐  │
│ │ DỮ LIỆU CẦN CHÚ Ý (ATTENTION LIST)     │ │ LƯỢT KIỂM TRA GẦN ĐÂY   │  │
│ │ Tabs: [Tất cả] [Có lỗi] [Chờ kiểm tra] │ │ Bảng 5 lần chạy gần nhất│  │
│ │ ────────────────────────────────────── │ │ v1 · Đạt quy tắc        │  │
│ │ • KH miền Bắc: 15 dòng lỗi [Xem lỗi]   │ │ v2 · 8 dòng lỗi         │  │
│ │ • Tồn kho T10: Chưa kiểm tra [Kiểm tra]│ ├─────────────────────────┤  │
│ │ • Chi phí Q3: Chưa có file [Tải CSV]   │ │ MẸO LÀM VIỆC CHO SME    │  │
│ └────────────────────────────────────────┘ └─────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Đặc tả Chi tiết từng Thành phần

### A. Quick Actions Bar (Thao tác nhanh)
- Nằm ngay dưới tiêu đề bàn làm việc.
- Cung cấp 4 lối tắt:
  1. `Tạo bộ dữ liệu mới`: Kích hoạt `CreateDatasetDialog` độc lập (HM-01).
  2. `Xem danh mục`: Điều hướng sang `#/datasets`.
  3. `Tiếp tục công việc`: Nút thông minh tự động trỏ đến bộ dữ liệu cần hành động nhất.
  4. `Hướng dẫn 3 bước`: Nút bật/tắt sổ tay quy trình 3 bước (Tạo $\rightarrow$ Tải $\rightarrow$ Kiểm tra).

### B. KPI Cards (Chỉ số tổng quan)
1. **Tổng bộ dữ liệu**:
   - Giá trị: `datasets.length`
   - Chú thích: Số lượng bộ dữ liệu đã có file CSV.
2. **Chưa có file dữ liệu**:
   - Giá trị: `datasets.filter(d => d.versions.length === 0).length`
   - Chú thích: Cần tải file CSV đầu tiên để quản lý. Màu cảnh báo hổ phách nếu $> 0$.
3. **Bộ dữ liệu cần xem xét**:
   - Giá trị: Tổng số bộ dữ liệu chưa ở trạng thái Đạt (gồm có dòng lỗi, lỗi thực thi kỹ thuật, hoặc chờ kiểm tra).
   - Chú thích: Phân tách rõ ràng `${errorsCount} bộ có lỗi · ${uninspectedCount} bộ chờ kiểm tra`.
4. **Lượt kiểm tra hoàn tất**:
   - Giá trị: `runs.filter(r => r.status === 'completed').length`
   - Chú thích: Trên tổng số lượt chạy kiểm tra.

### C. Dữ liệu cần chú ý (Attention List & 5 Tabs)
Bao gồm thanh lọc tiện lợi:
- `Tất cả cần chú ý`: Hiển thị tất cả các bộ dữ liệu tồn đọng.
- `Có dòng lỗi`: Chỉ hiển thị các bộ dữ liệu có lỗi ở lần kiểm tra gần nhất.
- `Chờ kiểm tra`: Chỉ hiển thị các bộ dữ liệu đã có file nhưng chưa chạy kiểm tra.
- `Chưa có file`: Chỉ hiển thị các bộ dữ liệu rỗng.
- `Đạt quy tắc`: Xem nhanh các bộ dữ liệu đã vượt qua kiểm tra.

Mỗi dòng mang đầy đủ:
- Tên bộ dữ liệu (nhấp vào xem chi tiết).
- Huy hiệu trạng thái (vd: `15 dòng lỗi`, `Chưa kiểm tra`, `Chưa có file`, `Đạt quy tắc`).
- Người phụ trách dữ liệu nếu có.
- Nút hành động tương ứng: **[Xem lỗi]**, **[Chạy kiểm tra]**, **[Tải file CSV]**, **[Thử lại]**.

### D. Lượt kiểm tra gần đây (Recent Runs)
- Hiển thị 5 lần chạy mới nhất.
- Bảng hiển thị: Bộ dữ liệu $\rightarrow$ Phiên bản $\rightarrow$ Huy hiệu kết quả $\rightarrow$ Số dòng lỗi $\rightarrow$ Nút **Xem kết quả**.
- Liên kết trực tiếp tới màn hình kết quả kiểm tra `#/datasets/:id/runs/:runId`.

