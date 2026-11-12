# BỘ YÊU CẦU THIẾT KẾ LẠI FRONTEND (TASK-ORIENTED UX REQUIREMENTS)
## HỆ THỐNG DATAGUARD SME

**Hạng mục:** HM-02A — UX Redesign Requirements & Information Architecture  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior UX Researcher, Product Designer, Business Analyst & SaaS Product Manager  

---

## 1. Nguyên tắc thiết kế cho đối tượng SME (SME Design Principles)

1. **Excel-Friendly Mindset (Tư duy thân thuộc với Excel):**
   - Người dùng SME xem file bảng tính là vật thể trung tâm. Mọi khái niệm cần được quy chiếu về trải nghiệm Excel: cột tiêu đề, dòng dữ liệu, ô bị bôi đỏ, định dạng số/ngày.
   - Luôn hiển thị vị trí lỗi khớp với số dòng thực tế trong Microsoft Excel (Dòng $N+1$).

2. **Plain Business Language (Ngôn ngữ nghiệp vụ giản dị):**
   - Loại bỏ hoàn toàn biệt ngữ kỹ thuật (Jargon) như Regex, Schema, Fingerprint, Null-byte, Backend engine.
   - Sử dụng tiếng Việt chuẩn mực, rõ ràng, tập trung vào mục tiêu công việc: *"Kiểm tra dữ liệu"*, *"Dòng có lỗi"*, *"Tải báo cáo Excel"*.

3. **Guided & Task-oriented Workflows (Luồng công việc có hướng dẫn):**
   - Không đặt người dùng vào trạng thái bối rối "Bây giờ làm gì tiếp theo?". Mỗi màn hình luôn có một hành động chính rõ ràng (Single Primary Call-To-Action).
   - Tự động dẫn dắt người dùng qua các chặng: `Tạo bộ dữ liệu` $\rightarrow$ `Nạp file` $\rightarrow$ `Chọn quy tắc nhanh` $\rightarrow$ `Xem & Tải lỗi` $\rightarrow$ `Đối chiếu file sau khi sửa`.

4. **Error Prevention over Error Correction (Ngăn ngừa lỗi hơn là bắt lỗi):**
   - Cho phép người dùng xem trước và xác nhận kiểu dữ liệu trước khi lưu.
   - Khi file CSV có khoảng trắng thừa ở tên cột hoặc khác thứ tự cột, hệ thống nên hỗ trợ tự động cắt khoảng trắng (auto-trim) hoặc hỗ trợ mapping trực quan thay vì lập tức quăng lỗi kỹ thuật.

5. **Instant Feedback & Progress Celebration (Phản hồi tức thì & Khích lệ tiến độ):**
   - Khi người dùng sửa được lỗi và tải lên phiên bản mới, hiển thị rõ thành tích cải thiện chất lượng (ví dụ: *"Tuyệt vời! Bạn đã xử lý hết 38/40 dòng lỗi, chất lượng tăng từ 72% lên 98%"*).

---

## 2. Từ điển chuyển đổi thuật ngữ (Terminology Mapping Dictionary)

| Thuật ngữ kỹ thuật cũ | Thuật ngữ mới đề xuất cho SME | Ý nghĩa nghiệp vụ thực tế |
|---|---|---|
| `Dataset` / Bộ dữ liệu | **Hồ sơ dữ liệu** hoặc **Thư mục dữ liệu** | Nơi chứa các đợt nạp file của cùng một nghiệp vụ (ví dụ: Báo cáo doanh số hàng tháng). |
| `DatasetVersion` / Phiên bản | **File dữ liệu đợt này** / **Bản nạp ngày DD/MM** | Mỗi file Excel/CSV tải lên trong một kỳ báo cáo. |
| `DatasetRow` / Bản ghi $N$ | **Dòng $N+1$ trong file Excel** | Dòng dữ liệu cần đối chiếu trong bảng tính Excel của người dùng. |
| `QualityRule` / Quy tắc kiểm tra | **Tiêu chuẩn dữ liệu** / **Điều kiện kiểm tra** | Tiêu chí để xác định dòng dữ liệu có hợp lệ hay không. |
| `QualityRun` / Lần kiểm tra | **Đợt kiểm tra** | Kết quả đánh giá chất lượng tại một thời điểm. |
| `Violation` / Lượt vi phạm | **Lỗi vi phạm tiêu chuẩn** | Một ô hoặc một dòng không đáp ứng điều kiện đặt ra. |
| `CSV_SCHEMA_MISMATCH` | **Cột trong file không khớp với đợt trước** | Cảnh báo khi người dùng tải file bị thiếu cột, thừa cột hoặc đổi tên cột. |
| `Rule Set Fingerprint` / `Engine v5` | **Bộ tiêu chuẩn đã áp dụng** | Đơn giản hóa thành nhãn hiển thị: "Áp dụng 5 điều kiện kiểm tra". Ẩn chuỗi mã hóa kỹ thuật. |
| `Type: Decimal / Boolean` | **Số tiền / Số thập phân** · **Có / Không (Đúng / Sai)** | Diễn giải bằng từ ngữ quen thuộc của dân văn phòng. |
| `Pattern (RE2 dialect)` | **Định dạng đặc biệt** (SĐT, MST, CCCD...) | Chuyển thành các lựa chọn có sẵn (preset dropdown). |

---

## 3. Tái cấu trúc thông tin (Information Architecture) & Hệ thống Menu mới

### 3.1. Cấu trúc Menu bên trái (Sidebar Navigation) theo hướng Task-oriented

Menu hiện tại phân bổ theo đối tượng tĩnh (`Tổng quan`, `Danh mục dữ liệu`, `Quy tắc kiểm tra`, `Lịch sử kiểm tra`). Đề xuất chuyển đổi thành menu định hướng công việc:

```
[ KHÔNG GIAN LÀM VIỆC ]
├─ 1. Bàn làm việc (Dashboard) ────► Xem việc cần xử lý hôm nay & các file có lỗi gần nhất
├─ 2. Hồ sơ dữ liệu (Data Catalog) ─► Quản lý các thư mục dữ liệu & nạp file mới
│     └─ [Chi tiết hồ sơ: 3 tab gọn]
│         ├─ Tab 1: Kiểm tra & Kết quả (Tập trung toàn bộ luồng File + Rule + Result)
│         ├─ Tab 2: Lịch sử & Tiến độ (Các bản nạp trước và so sánh cải thiện)
│         └─ Tab 3: Cấu trúc cột (Ý nghĩa các trường)
├─ 3. Thư viện điều kiện (Rule Hub) ─► Danh sách các tiêu chuẩn kiểm tra mẫu
└─ 4. Hướng dẫn & Dữ liệu mẫu ──────► File thực hành & hướng dẫn sử dụng nhanh

[ QUẢN TRỊ ] (Chỉ Admin)
└─ Quản lý người dùng & phân quyền
```

### 3.2. Rút gọn 7 Tab chi tiết Dataset thành 3 Tab tập trung
Hiện tại trang chi tiết Dataset có tới 7 tab (`overview`, `fields`, `versions`, `rules`, `history`, `compare`, `trend`) gây loãng sự chú ý. Đề xuất quy hoạch lại thành 3 khu vực chức năng:
1. **Khu vực 1: Bàn kiểm tra dữ liệu (Kiểm tra & Kết quả):**
   - Kết hợp Tổng quan + Chọn file nạp + Kích hoạt quy tắc + Xem ngay bảng lỗi và nút tải Excel.
2. **Khu vực 2: Theo dõi tiến độ (Lịch sử & Đối chiếu):**
   - Kết hợp Danh sách phiên bản + Đồ thị xu hướng + Nút so sánh nhanh giữa các lần nạp (v2 vs v1).
3. **Khu vực 3: Cấu trúc & Ý nghĩa cột (Cấu trúc cột):**
   - Bảng danh sách cột, kiểu dữ liệu và mô tả trường.

---

## 4. Top 10 Vấn đề UX quan trọng nhất & Thay đổi bắt buộc

### Bảng Top 10 Vấn đề UX quan trọng nhất:
1. **Lệch số dòng giữa phần mềm và Excel ($N$ vs $N+1$):** Người dùng phải tự tính nhẩm để tìm dòng lỗi trong file Excel gốc.
2. **Khóa cứng cấu trúc cột (Strict Schema Check):** Khi nạp file sửa lỗi ($v2$), nếu vô tình có cột thừa hoặc khoảng trắng ở header thì bị chặn hoàn toàn mà không có công cụ hỗ trợ đối chiếu cột.
3. **Quá trình từ Nạp file $\rightarrow$ Quy tắc $\rightarrow$ Chạy kiểm tra bị chia nhỏ thành nhiều bước và nhiều popup:** Không có luồng kiểm tra tức thì (Instant Check).
4. **Nút tải báo cáo Excel (.xlsx) bị giấu trong menu chọn định dạng:** Kế toán phải mất 2-3 thao tác mới tải được file Excel.
5. **Hiển thị chuỗi JSON thô trong tính năng AI Gợi ý quy tắc:** Gây sợ hãi công nghệ cho người dùng văn phòng.
6. **Mẫu regex kỹ thuật trong tạo quy tắc:** Thiếu các preset thông dụng tại Việt Nam (Số điện thoại, Mã số thuế, CCCD).
7. **Tạo quy tắc thủ công đơn lẻ từng cột:** Mất nhiều thời gian khi muốn đặt điều kiện "Bắt buộc điền" cho 10 cột.
8. **7 tab phân mảnh trong trang chi tiết Dataset:** Thiếu tính tập trung theo nhiệm vụ.
9. **Chức năng Đối chiếu (Comparison) đòi hỏi chọn thủ công lần A, lần B:** Thiếu nút đối chiếu 1 chạm với phiên bản trước.
10. **Thông báo thành công bị biến mất khi chuyển trang:** Người dùng không nhận được feedback rõ ràng sau khi tạo mới hoặc tải file.

### Những thay đổi bắt buộc (Mandatory Changes):
- [x] **Hiển thị song song số dòng:** Bảng lỗi và file xuất ra phải ghi rõ: `Dòng Excel: X (Bản ghi: Y)`.
- [x] **Đưa nút "Tải báo cáo Excel (.xlsx)" thành CTA nổi bật** cạnh nút xuất CSV.
- [x] **Giao diện AI giản dị hóa:** Thay thế khung JSON thô bằng danh sách các cột và thông tin tóm tắt bằng tiếng Việt rõ ràng.
- [x] **Ẩn các thông số kỹ thuật nội bộ:** Ẩn chuỗi băm `rule_set_fingerprint` và nhãn `engine_version` khỏi tầm nhìn của người dùng văn phòng (chỉ giữ trong mục "Chi tiết kỹ thuật dành cho quản trị" thu gọn).
- [x] **Bảo toàn 100% logic Backend:** Quality Engine v5, Snapshot quy tắc, thuật toán so sánh và các endpoint API không được thay đổi.

---

## 5. Đề xuất đầu vào cho giai đoạn tiếp theo (HM-02B)

Giai đoạn **HM-02B: Thiết kế chi tiết & Wireframes** sẽ tập trung vào các hạng mục cụ thể:
1. **Wireframes giao diện Bàn kiểm tra dữ liệu tập trung (Unified Dataset Workspace):**
   - Tích hợp khu vực kéo thả file CSV/Excel, bảng checklist bật/tắt nhanh quy tắc, nút "Kiểm tra ngay", và bảng kết quả hiển thị dòng Excel $N+1$.
2. **Wireframes Bộ chọn quy tắc nhanh dạng lưới (Quick Rule Matrix):**
   - Thiết kế bảng phân loại cột với các checkbox: Bắt buộc điền, Không trùng, Định dạng chuẩn (Email/SĐT/Ngày).
3. **Wireframes Thẻ đối chiếu tiến độ trực quan (Progress Comparison Card):**
   - Thẻ so sánh trực quan giữa đợt sửa lỗi $v2$ và đợt nạp đầu $v1$ (số lỗi còn lại, tỷ lệ sạch).
4. **Design System & Style Guide điều chỉnh:**
   - Hoàn thiện bảng màu, font chữ, độ tương phản theo chuẩn WCAG AA và bộ icon nghiệp vụ dễ hiểu.

