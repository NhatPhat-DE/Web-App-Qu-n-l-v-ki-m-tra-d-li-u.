# TIÊU CHÍ NGHIỆM THU GIAO DIỆN & TRẢI NGHIỆM (UI/UX ACCEPTANCE CRITERIA)
## HỆ THỐNG DATAGUARD SME

**Dự án:** DataGuard SME (phát triển từ DataLens DQ / DataCheck)  
**Hạng mục:** HM-02B: UI/UX Acceptance Criteria & Testable Specifications  
**Thời gian lập:** 03/11/2026  
**Vai trò:** Senior QA Architect & SaaS Product Manager  

---

## 1. Tiêu chí nghiệm thu Bố cục & Điều hướng chung (Navigation & Shell)

- **AC-NAV-01 (Cấu trúc Menu):** Sidebar hiển thị đúng 5 mục: *Trang chủ*, *Bộ dữ liệu*, *Lịch sử & Báo cáo*, *Trợ giúp & Mẫu file*, và *Quản trị tài khoản* (chỉ hiển thị khi `user.role === 'admin'`).
- **AC-NAV-02 (Phân quyền Admin):** Khi đăng nhập bằng tài khoản `data_steward`, menu *Quản trị tài khoản* hoàn toàn ẩn. Nếu cố tình truy cập hash `#/accounts`, hệ thống hiển thị thông báo lỗi 403 thân thiện và có nút "Về trang chủ".
- **AC-NAV-03 (Breadcrumb):** Breadcrumb luôn hiển thị đường dẫn phân cấp chính xác. Bấm vào từng cấp trên Breadcrumb điều hướng về đúng trang cấp cha tương ứng mà không làm mới trang.
- **AC-NAV-04 (Deep Link Tương thích ngược):** Các đường dẫn cũ (`#/datasets/{id}/overview`, `#/datasets/{id}/fields`, `#/datasets/{id}/versions`, `#/datasets/{id}/trend`) tự động chuyển hướng hiển thị tương ứng vào 3 khu vực mới trong Workspace mà không bị lỗi trang trắng 404.

---

## 2. Tiêu chí nghiệm thu Màn hình Trang chủ & Danh mục (UX-202)

- **AC-HOM-01 (Chỉ số hoạt động thực tế):** 4 thẻ số liệu trên Dashboard phản ánh đúng số liệu từ API backend (`total_datasets`, `populated_datasets`, `total_completed_runs`, `datasets_with_errors`). Tuyệt đối không hiển thị chỉ số giả lập (mock KPI).
- **AC-HOM-02 (Danh sách bộ dữ liệu có lỗi):** Khối "Bộ dữ liệu có lỗi cần xử lý" chỉ hiển thị các bộ dữ liệu mà đợt kiểm tra gần nhất có `error_row_count > 0`. Mỗi mục có đầy đủ nút xem dòng lỗi và nút tải báo cáo Excel.
- **AC-CAT-01 (Trạng thái bộ dữ liệu rỗng):** Trong danh mục, bộ dữ liệu chưa nạp file hiển thị nhãn trạng thái xám *"Chưa có dữ liệu"*, cột đợt kiểm tra hiển thị *"Chưa kiểm tra"*. Không được tự động gán mặc định `v1`.
- **AC-CAT-02 (Tìm kiếm & Bộ lọc):** Ô tìm kiếm lọc được theo tên bộ dữ liệu, mô tả, người phụ trách và nguồn dữ liệu (debounce 250ms). Khi không tìm thấy kết quả, hiển thị Empty State kèm nút "Đặt lại bộ lọc".

---

## 3. Tiêu chí nghiệm thu Dataset Workspace (UX-203)

- **AC-WRK-01 (Tạo bộ dữ liệu độc lập):** Form tạo hồ sơ chỉ yêu cầu Tên bộ dữ liệu (bắt buộc, $\le$ 200 ký tự); các trường Người phụ trách, Nguồn, Mô tả là tùy chọn. Sau khi bấm tạo, tự động chuyển đến tab *Kiểm tra dữ liệu* của hồ sơ đó.
- **AC-WRK-02 (Empty State khi chưa có file):** Tại tab *Kiểm tra dữ liệu*, hồ sơ rỗng hiển thị thông điệp *"Bộ dữ liệu chưa có file nào"* cùng nút CTA duy nhất *"Tải file CSV đầu tiên"*. Không hiển thị bảng vi phạm hoặc biểu đồ trống.
- **AC-WRK-03 (Chuyển bước liền mạch):** Sau khi nạp file $v1$ thành công, giao diện tự động cập nhật hiển thị bảng quy tắc và kích hoạt nút kiểm tra mà không yêu cầu người dùng phải refresh trang (F5) hay tạo lại hồ sơ.
- **AC-WRK-04 (Tab Cấu trúc & Thông tin):** Hiển thị danh sách các cột trích xuất từ file. Cho phép người dùng bấm sửa mô tả cột và lưu thành công qua API `PATCH /api/datasets/{id}/columns/{colId}`.

---

## 4. Tiêu chí nghiệm thu Bảng chọn nhanh quy tắc (Quick Rule Matrix - UX-204)

- **AC-RUL-01 (Ma trận quy tắc theo cột):** Mỗi cột hiển thị các checkbox nhanh: *Bắt buộc điền*, *Không trùng lặp*, dropdown *Kiểu dữ liệu* (Văn bản, Số nguyên, Số tiền, Ngày tháng, Email). Tích chọn và bấm lưu cập nhật thành công vào danh sách quy tắc của dataset.
- **AC-RUL-02 (Gợi ý AI tiếng Việt):** Modal gợi ý quy tắc bằng AI hiển thị các thẻ đề xuất bằng tiếng Việt rõ nghĩa kèm lý do đề xuất. **Tuyệt đối không hiển thị chuỗi JSON thô (`<pre>` payload)**.
- **AC-RUL-03 (Chấp nhận gợi ý có chọn lọc):** Người dùng có thể bỏ chọn từng gợi ý trước khi bấm "Áp dụng vào hồ sơ". Sau khi áp dụng, các quy tắc này xuất hiện ngay trong bảng quy tắc của dataset.
- **AC-RUL-04 (Tắt quy tắc):** Khi bỏ chọn một quy tắc, hệ thống cập nhật `is_active = false` qua API `PATCH`, không gọi lệnh DELETE (tránh lỗi 405 của backend).

---

## 5. Tiêu chí nghiệm thu Kết quả kiểm tra & Báo cáo Excel (UX-205)

- **AC-RES-01 (Phân định dòng lỗi vs lượt vi phạm):** Giao diện thể hiện rõ hai chỉ số riêng biệt: *Dòng có lỗi* (số dòng cần sửa) và *Lượt vi phạm* (tổng số vi phạm tiêu chuẩn). Có dòng chú thích giải thích sự khác biệt này.
- **AC-RES-02 (Khớp số dòng Excel):** Bảng chi tiết vi phạm hiển thị cột *Dòng Excel* tương ứng chính xác với số dòng thực tế trong Microsoft Excel (`row_number + 1`), giúp kế toán đối chiếu nhanh.
- **AC-RES-03 (Nút tải Excel trực tiếp):** Nút **"Tải báo cáo Excel (.xlsx)"** màu xanh lá hiển thị trực tiếp tại màn hình kết quả, không bị ẩn trong menu dropdown. Bấm nút tải về đúng file `.xlsx` format chuẩn.
- **AC-RES-04 (Lọc danh sách vi phạm):** Hỗ trợ lọc vi phạm theo Cột, theo Loại lỗi, theo Số dòng hoặc Tìm kiếm nội dung. Bấm "Xem chi tiết" mở popup xem toàn bộ giá trị các ô trong dòng đó.

---

## 6. Tiêu chí nghiệm thu Lịch sử & Đối chiếu (UX-206)

- **AC-HIS-01 (Thẻ đối chiếu 1 chạm):** Khi vừa kiểm tra xong phiên bản đã sửa ($v2$), hệ thống tự động hiển thị Thẻ đối chiếu tiến độ so sánh với $v1$, ghi nhận số dòng lỗi giảm và tỷ lệ cải thiện.
- **AC-HIS-02 (Biểu đồ xu hướng thân thiện):** Đồ thị xu hướng chất lượng hiển thị tỷ lệ % dữ liệu sạch qua các đợt kiểm tra. **Ẩn hoàn toàn chuỗi mã băm kỹ thuật `rule_set_fingerprint`**.
- **AC-HIS-03 (Bảo toàn lịch sử bất biến):** Xem lại bất kỳ đợt kiểm tra cũ nào trong lịch sử đều hiển thị đúng danh sách quy tắc đã áp dụng tại thời điểm đó (`rule_snapshot`), không bị ảnh hưởng bởi việc bật/tắt quy tắc ở hiện tại.

---

## 7. Tiêu chí nghiệm thu Khả năng tiếp cận & Phản hồi ngoại lệ (A11y & Edge Cases)

- **AC-A11Y-01 (Độ tương phản WCAG AA):** Tất cả các văn bản chữ thường trên giao diện đạt tỷ lệ tương phản tối thiểu **4.5:1** so với màu nền.
- **AC-A11Y-02 (Điều hướng bàn phím):** Tất cả các nút bấm, ô nhập, menu và modal đều có thể thao tác hoàn toàn bằng phím `Tab`, `Enter`, `Space`, `Escape`. Có viền focus rõ ràng.
- **AC-ERR-01 (Cấu trúc file không khớp - Schema Mismatch):** Khi tải file $v2$ bị lệch cột, hệ thống hiển thị thông báo lỗi rõ ràng kèm danh sách cột thiếu / cột thừa bằng tiếng Việt, hướng dẫn người dùng chỉnh lại file Excel.
- **AC-ERR-02 (Hết hạn phiên - Session Expiry):** Khi phiên đăng nhập hết hạn, hệ thống hiển thị thông báo yêu cầu đăng nhập lại, lưu giữ an toàn các thông tin chưa submit nếu có thể.

