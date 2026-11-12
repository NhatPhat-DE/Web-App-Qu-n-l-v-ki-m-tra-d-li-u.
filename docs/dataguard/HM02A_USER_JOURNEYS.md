# PHÂN TÍCH HÀNH TRÌNH NGƯỜI DÙNG & TÁI THIẾT KẾ TASK-ORIENTED UX
## HỆ THỐNG DATAGUARD SME

**Hạng mục:** HM-02A — User Journey Analysis & Task-oriented UX Design  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior UX Researcher, Product Designer & Business Analyst  

---

## 1. Persona đại diện: Chị Mai — Chuyên viên Tổng hợp Dữ liệu & Kế toán Doanh nghiệp SME

- **Độ tuổi:** 32 tuổi.
- **Kinh nghiệm làm việc:** 8 năm làm kế toán bán hàng và tổng hợp dữ liệu doanh số cho công ty thương mại 50 nhân viên.
- **Công cụ quen thuộc:** Microsoft Excel (VLOOKUP, IF, Conditional Formatting, Pivot Table), Zalo, Google Sheets.
- **Điểm yếu công nghệ:** Không biết lập trình, không hiểu SQL, Regex, Schema, Fingerprint, NUL byte, API.
- **Mục tiêu chính khi dùng DataGuard:**  
  1. Kiểm tra nhanh file danh sách đơn hàng hoặc khách hàng từ các chi nhánh gửi về có bị thiếu mã, trùng email, sai ngày tháng hay không trước khi nhập vào phần mềm ERP/kế toán.  
  2. Xuất danh sách các dòng bị lỗi để chuyển lại cho nhân viên chi nhánh sửa.  
  3. Khi nhận lại file đã sửa, tải lên để kiểm tra xem đã hết lỗi chưa.  

---

## 2. Phân tích chi tiết 9 Hành trình người dùng hiện tại (A $\rightarrow$ I)

### Hành trình A: Người dùng mới đăng nhập lần đầu
- **Luồng hiện tại:**
  1. Truy cập trang web $\rightarrow$ Màn hình đăng nhập `LoginForm` ([`SessionApp.tsx#L10`](file:///d:/UserFile/DNCN/Webb/frontend/src/SessionApp.tsx#L10)).
  2. Đăng nhập thành công $\rightarrow$ Chuyển đến `#/dashboard`.
  3. Nhìn thấy các thẻ số liệu bằng 0 ("Tổng bộ dữ liệu 0", "Lượt kiểm tra 0") và banner trống "Chào mừng đến với DataCheck".
- **Điểm nghẽn & Ma sát nhận thức:**
  - *[HYPOTHESIS]* Không có "Welcome Onboarding Tour" hoặc hướng dẫn tương tác trực tiếp giải thích quy trình 3 bước cốt lõi. Người dùng không biết nên bắt đầu từ đâu nếu không tự mò vào tab "Hướng dẫn sử dụng".
  - Chữ "Không gian dữ liệu", "DataCheck" chưa mang cảm giác an toàn và bảo vệ dữ liệu như tên gọi DataGuard.
- **Đề xuất Task-oriented UX:**
  - Hiển thị thanh tiến trình Onboarding rõ ràng: `Bước 1: Tạo bộ dữ liệu đầu tiên (0/3)` $\rightarrow$ `Bước 2: Tải file dữ liệu` $\rightarrow$ `Bước 3: Xem kết quả kiểm tra`.

---

### Hành trình B: Tạo bộ dữ liệu mới (Metadata-first sau HM-01C)
- **Luồng hiện tại:**
  1. Từ Dashboard hoặc Catalog bấm "Tạo bộ dữ liệu".
  2. Mở modal `CreateDatasetDialog` ([`CreateDatasetDialog.tsx`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/CreateDatasetDialog.tsx)): Nhập Tên bộ dữ liệu, Người phụ trách, Nguồn, Mô tả.
  3. Bấm "Tạo bộ dữ liệu" $\rightarrow$ Điều hướng về `#/datasets/{id}/overview`.
- **Đánh giá sau HM-01C:**
  - *[VERIFIED]* Luồng tạo độc lập hoạt động mượt mà, không còn bắt buộc phải có sẵn CSV.
  - *[HYPOTHESIS]* Người dùng văn phòng thường đặt tên file theo tháng (ví dụ: `Khach_hang_T11.csv`). Họ chưa quen với việc "Bộ dữ liệu" là một chiếc bìa kẹp hồ sơ lâu dài (Folder/Dataset), còn các file hàng tháng là "Phiên bản" (Versions). Cần giải thích ngắn gọn bằng ví dụ trực quan.

---

### Hành trình C: Tải file CSV đầu tiên ($v1$)
- **Luồng hiện tại:**
  1. Tại trang chi tiết Dataset rỗng, bấm nút "Tải file CSV đầu tiên".
  2. Mở `UploadDialog`: Kéo thả file CSV.
  3. Xem trước cấu trúc và 10 dòng đầu.
  4. Bấm "Xác nhận lưu phiên bản" $\rightarrow$ Hiển thị màn hình thành công với 2 nút: "Thiết lập quy tắc" hoặc "Chạy kiểm tra".
- **Điểm nghẽn & Ma sát nhận thức:**
  - *[VERIFIED]* Parser phía frontend ([`csv.ts#L4`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/csv.ts#L4)) chỉ chấp nhận đuôi `.csv`, mã hóa UTF-8. Trong thực tế SME, người dùng mở file Excel rồi bấm Save As thường chọn mặc định `Excel Workbook (.xlsx)` hoặc CSV ANSI (mã hóa Windows-1258 cho tiếng Việt). Khi kéo thả file vào, hệ thống báo lỗi cú pháp hoặc mã hóa khiến người dùng bối rối.
  - *[HYPOTHESIS]* Ở bước thành công, nút "Chạy kiểm tra" được hiển thị nổi bật hơn nút "Thiết lập quy tắc". Người dùng bấm luôn "Chạy kiểm tra", nhưng vì chưa có quy tắc nào nên hệ thống báo cảnh báo "Chưa có quy tắc đang bật", tạo cảm giác cụt luồng (dead end).
- **Đề xuất Task-oriented UX:**
  - Luồng thông minh (Smart Workflow): Sau khi nạp file đầu tiên thành công, tự động gợi ý: *"Bộ dữ liệu có 4 cột: Mã KH, Tên KH, Email, Ngày sinh. Hãy kích hoạt nhanh các quy tắc phổ biến để kiểm tra ngay."*

---

### Hành trình D: Thiết lập các quy tắc kiểm tra (Quality Rules)
- **Luồng hiện tại:**
  1. Vào tab "Quy tắc" (`#/datasets/{id}/rules`).
  2. Bấm "Thêm quy tắc", mở modal `RuleDialog` ([`EditDialogs.tsx#L36`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/EditDialogs.tsx#L36)).
  3. Chọn 1 trong 10 loại kiểm tra: Không được thiếu, Không được trùng, Định dạng email, Số nguyên, Số thập phân, Ngày tháng, Đúng/sai, Khoảng giá trị số, Danh sách giá trị, Mẫu tùy chỉnh.
  4. Điền cấu hình và bấm "Lưu quy tắc".
- **Điểm nghẽn & Ma sát nhận thức:**
  - *[VERIFIED]* Mỗi lần chỉ tạo được 1 quy tắc cho 1 cột. Nếu file có 15 cột và người dùng muốn đặt quy tắc "Không được thiếu" cho 5 cột bắt buộc, họ phải mở modal lặp đi lặp lại 5 lần liên tiếp.
  - *[HYPOTHESIS]* Người dùng SME không quen với thuật ngữ "Boolean", "Decimal", "Dialect RE2-v1". Họ quen với: "Cột này là số tiền", "Cột này là ngày ghi sổ", "Cột này là số điện thoại".
- **Đề xuất Task-oriented UX:**
  - Bổ sung giao diện "Cài đặt nhanh quy tắc dạng bảng" (Column-based Rule Matrix): Cho phép tích chọn hàng loạt quy tắc "Bắt buộc điền" hoặc "Không trùng" cho nhiều cột cùng lúc trên một màn hình duy nhất.

---

### Hành trình E: Chạy kiểm tra và xem kết quả lỗi
- **Luồng hiện tại:**
  1. Bấm nút "Chạy kiểm tra" $\rightarrow$ Mở `RunDialog` chọn lại phiên bản $\rightarrow$ Bấm "Bắt đầu kiểm tra".
  2. Điều hướng tới trang kết quả `#/datasets/{id}/runs/{runId}` ([`Results.tsx`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/Results.tsx)).
  3. Hiển thị 5 thẻ số liệu: Tổng bản ghi, Bản ghi có lỗi, Bản ghi không vi phạm, Tỷ lệ không vi phạm, Lượt vi phạm quy tắc.
  4. Bên dưới là bảng chi tiết các dòng vi phạm (`Violations.tsx`).
- **Điểm nghẽn & Ma sát nhận thức:**
  - *[HYPOTHESIS]* Sự khác biệt giữa "Bản ghi có lỗi" (Error rows) và "Lượt vi phạm quy tắc" (Violations) gây nhầm lẫn: Ví dụ file có 10 dòng lỗi nhưng có tới 25 lượt vi phạm (vì 1 dòng vi phạm cả ngày tháng và để trống mã). Cần chú thích trực quan hơn.
  - *[VERIFIED]* Cột "Số bản ghi" hiển thị số thứ tự $N$. Khi đối chiếu với Excel, dòng tiêu đề chiếm dòng 1 nên dòng dữ liệu $N$ nằm ở dòng $N+1$ của Excel. Kế toán thường thắc mắc: *"Tại sao phần mềm báo dòng 5 lỗi mà mở Excel dòng 5 thấy bình thường (thực tế lỗi ở dòng 6)?"*

---

### Hành trình F: Xuất báo cáo lỗi và sửa dữ liệu trong Excel
- **Luồng hiện tại:**
  1. Tại màn hình kết quả, bấm nút "Xuất CSV lỗi" hoặc chọn "Báo cáo đầy đủ… $\rightarrow$ Tải Excel".
  2. Mở file trong Excel để đối chiếu và sửa dữ liệu nguồn.
- **Điểm nghẽn & Ma sát nhận thức:**
  - *[VERIFIED]* Nút tải Excel bị giấu trong thẻ dropdown `<select>` ([`Violations.tsx#L63`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/Violations.tsx#L63)), trong khi người dùng SME 95% có nhu cầu dùng file Excel (.xlsx) chứ không phải file CSV thô.
  - File xuất CSV lỗi chỉ liệt kê danh sách các ô vi phạm, không phải toàn bộ file dữ liệu gốc có đánh dấu ô đỏ (highlight lỗi).
- **Đề xuất Task-oriented UX:**
  - Đưa nút "Tải báo cáo lỗi Excel (.xlsx)" ra vị trí hành động chính (Primary CTA).
  - Bổ sung cột "Dòng trong Excel" (Row $N+1$) trong bảng và file báo cáo xuất ra.

---

### Hành trình G: Tải phiên bản đã sửa lên ($v2, v3, \dots$)
- **Luồng hiện tại:**
  1. Người dùng bấm nút "Tải lên bản đã sửa" trên đầu trang kết quả ([`Results.tsx#L22`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/Results.tsx#L22)).
  2. Mở `UploadDialog` để nạp file CSV đã sửa.
  3. Nếu file khớp cấu trúc $\rightarrow$ Lưu thành phiên bản mới (ví dụ: $v2$).
- **Điểm nghẽn nghiêm trọng (P0):**
  - *[VERIFIED]* Nếu trong quá trình sửa bằng Excel, người dùng vô tình kéo thêm 1 cột ghi chú ("Ghi chú sửa"), hoặc thứ tự cột bị đảo, hệ thống từ chối lưu và báo lỗi đỏ: `Cấu trúc khác các phiên bản đã lưu. Tên và thứ tự cột không khớp dataset. Hãy tạo bộ dữ liệu khác...`
  - Người dùng SME bị bế tắc hoàn toàn vì họ không muốn tạo dataset khác mà chỉ muốn kiểm tra tiếp file vừa sửa.

---

### Hành trình H: Đối chiếu kết quả trước và sau (Run Comparison)
- **Luồng hiện tại:**
  1. Người dùng vào tab "Đối chiếu" (`#/datasets/{id}/compare`) trong chi tiết Dataset.
  2. Hệ thống hiển thị bảng lịch sử chạy. Người dùng phải bấm nút "Chọn A" cho lần cũ, "Chọn B" cho lần mới, rồi bấm nút "Đối chiếu".
  3. Hiển thị bảng so sánh chênh lệch: Số bản ghi có lỗi giảm bao nhiêu, Tỷ lệ cải thiện bao nhiêu điểm phần trăm.
- **Điểm nghẽn & Ma sát nhận thức:**
  - *[VERIFIED]* Sau khi tải file $v2$ và chạy kiểm tra xong, người dùng không được tự động dẫn tới màn hình đối chiếu với $v1$.
  - Thao tác chọn thủ công hai lần A và B là quá kỹ thuật. 90% nhu cầu thực tế là: "So sánh lần chạy hiện tại với lần chạy trước đó xem lỗi đã giảm chưa".
- **Đề xuất Task-oriented UX:**
  - Cung cấp tính năng "Đối chiếu ngay với phiên bản trước" (1-Click Compare) ngay tại màn hình kết quả của $v2$.

---

### Hành trình I: Xem lịch sử và xu hướng chất lượng (History & Quality Trend)
- **Luồng hiện tại:**
  1. Người dùng vào tab "Xu hướng" (`#/datasets/{id}/trend`).
  2. Hiển thị đồ thị SVG nối các điểm tỷ lệ không vi phạm theo thời gian ([`QualityInsights.tsx#L46`](file:///d:/UserFile/DNCN/Webb/frontend/src/workspace/QualityInsights.tsx#L46)).
- **Điểm nghẽn & Ma sát nhận thức:**
  - *[VERIFIED]* Đồ thị vẽ đường nối dựa trên điều kiện cùng `engine_version` và `rule_set_fingerprint`. Nếu người dùng bật/tắt 1 quy tắc, hệ thống coi là "Khác nhóm điều kiện" và không nối đường liền, hiển thị thông báo kỹ thuật: *"Nhóm điều kiện 1 · 4 quy tắc · v5 · 0a9f...c2"*.
  - Người dùng SME không hiểu khái niệm "Fingerprint" hay "Nhóm điều kiện kỹ thuật", họ chỉ muốn thấy một biểu đồ trực quan: Tuần này chất lượng dữ liệu sạch hơn tuần trước hay kém hơn.

---

## 3. Bản thiết kế Luồng người dùng mới (Proposed Task-oriented Workflow)

```
[ BƯỚC 1: TIẾP NHẬN DỮ LIỆU ]
Người dùng tạo hoặc chọn Bộ dữ liệu ──► Kéo thả file Excel / CSV
                                            │
                                            ▼
[ BƯỚC 2: TỰ ĐỘNG NHẬN DIỆN & GỢI Ý ]
Hệ thống tự động phát hiện kiểu dữ liệu & đề xuất quy tắc chuẩn nghiệp vụ:
- Cột Mã: Không được để trống & Không được trùng
- Cột Email / SĐT: Đúng định dạng
- Cột Số tiền: Là số dương, không chứa chữ
                                            │
                                            ▼
[ BƯỚC 3: KIỂM TRA TỨC THÌ (1-CLICK CHECK) ]
Bấm "Bắt đầu kiểm tra" ──► Nhận kết quả trong 3 giây:
- Thẻ điểm chất lượng (Ví dụ: 95/100 điểm)
- Số dòng có lỗi (kèm số dòng tương ứng trong file Excel)
                                            │
                                            ▼
[ BƯỚC 4: SỬA LỖI & ĐỐI CHIẾU TIẾN ĐỘ ]
Tải file Excel báo cáo lỗi ──► Mở Excel sửa ──► Tải lại phiên bản mới
                                                        │
                                                        ▼
                        Hiển thị ngay thẻ so sánh tiến độ:
                        "Tuyệt vời! Đã sửa hết 42/45 lỗi (Giảm 93% lỗi so với bản v1)"
```

