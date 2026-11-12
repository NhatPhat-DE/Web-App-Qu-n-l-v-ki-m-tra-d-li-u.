# DataLens DQ — Bài toán nghiệp vụ và sáu câu hỏi

TÀI LIỆU TRÌNH BÀY VỚI GIẢNG VIÊN

**Tên đề tài:** “Xây dựng website quản lý danh mục dữ liệu và kiểm tra chất lượng dữ liệu sử dụng Python FastAPI, React và PostgreSQL”.

**Tên sản phẩm:** DataLens DQ.

**Ngày đối chiếu:** 19/10/2026. Tài liệu tập trung vào nghiệp vụ; công nghệ chỉ được tóm tắt ở mục 8.

**Bối cảnh giả định:** bộ phận tổng hợp/phân tích dữ liệu của một chuỗi bán lẻ nhận các file CSV từ chi nhánh hoặc bộ phận nguồn để kiểm tra trước khi lập báo cáo. Chưa có khảo sát doanh nghiệp thực tế; không đại diện cho một tổ chức đã triển khai sản phẩm.

**Cách đọc:** tình huống bán lẻ là minh họa nghiệp vụ. Số liệu chạy thử ở mục 7 lấy từ báo cáo demo đã lưu trong dự án, không phải số liệu kinh doanh. Nội dung đã triển khai, lợi ích kỳ vọng và phần chưa xác minh được phân biệt rõ.

## Mục lục

[MỤC LỤC TỰ ĐỘNG]

<!-- PAGE -->

# 1. TÊN ĐỀ TÀI VÀ GIỚI THIỆU NGẮN

**Tên đề tài:** “Xây dựng website quản lý danh mục dữ liệu và kiểm tra chất lượng dữ liệu sử dụng Python FastAPI, React và PostgreSQL”.

**DataLens DQ** là website giúp người phụ trách dữ liệu biết một bộ dữ liệu có nội dung gì, đến từ đâu, ai phụ trách và đã được kiểm tra theo tiêu chuẩn nào. Người dùng nhập CSV, bổ sung mô tả, đặt quy tắc và đọc kết quả gắn với từng phiên bản dữ liệu.

**Data Catalog** ở đây là danh mục metadata: thông tin mô tả bộ dữ liệu và các cột. Đây không phải danh mục hàng hóa, website bán hàng hoặc phần mềm thực hiện giao dịch bán lẻ. Dữ liệu bán lẻ chỉ là bối cảnh để giải thích nhu cầu quản lý và kiểm tra thông tin.

Giá trị cốt lõi của hệ thống là làm rõ tiêu chuẩn kiểm tra và cung cấp bằng chứng để đối chiếu nguồn. Hệ thống không thay người phụ trách quyết định dữ liệu nào đúng về nghiệp vụ và không tự sửa dữ liệu.

# 2. LÝ DO CHỌN ĐỀ TÀI

**Thứ nhất, cần hiểu dữ liệu trước khi sử dụng.** Người tổng hợp nhận được một file nhưng có thể chưa biết cột mã là mã gì, chỉ tiêu số dùng đơn vị nào, file được xuất từ đâu và phải hỏi ai khi có thắc mắc. Metadata giúp ghi lại các thông tin này thay vì để chúng chỉ tồn tại trong trao đổi cá nhân.

**Thứ hai, kiểm tra thủ công khó lặp lại nhất quán.** Mỗi lần nhận file mới, người kiểm tra có thể phải lọc ô trống, tìm bản ghi trùng và so giá trị với khoảng cho phép. Nếu tiêu chuẩn không được lưu rõ, hai lần kiểm tra hoặc hai người kiểm tra có thể áp dụng các điều kiện khác nhau.

**Thứ ba, cần truy vết tiêu chuẩn và kết quả.** Một file có thể được gửi lại sau khi đối chiếu nguồn. Người dùng cần phân biệt phiên bản trước và sau, xem lỗi cụ thể và biết điều kiện đã áp dụng tại thời điểm kiểm tra, kể cả khi quy tắc hiện tại đã đổi.

**Thứ tư, đề tài phù hợp chuyên ngành Hệ thống thông tin.** Bài toán kết nối người tham gia, luồng chuyển giao dữ liệu, trách nhiệm giải thích thông tin, tiêu chuẩn kiểm tra và công cụ hỗ trợ. Công nghệ phục vụ việc tổ chức quy trình và quản lý bằng chứng, không phải mục đích tự thân.

**Thứ năm, phạm vi đủ hẹp để kiểm chứng.** CSV, metadata, quy tắc xác định và kết quả lưu theo phiên bản cho phép xây dựng demo có đầu vào, đáp án và báo cáo đối chiếu. Không cần giả định đã tích hợp hệ thống bán hàng của một doanh nghiệp hoặc tự động hóa toàn bộ việc sửa lỗi. AI là phần hỗ trợ tùy chọn, không phải lý do nghiệp vụ chính để chọn đề tài.



# 3. VẤN ĐỀ NGHIỆP VỤ

Trong tình huống giả định, bộ phận tổng hợp/phân tích dữ liệu cần số liệu từ các chi nhánh để lập báo cáo quản trị bán lẻ. Nhân sự tại nguồn xuất file CSV từ công cụ đang sử dụng rồi gửi cho người tổng hợp qua kênh trao đổi sẵn có. Website hiện tại không tự tạo hoặc tự nhận file từ các kênh đó.

Người tiếp nhận phải hiểu ý nghĩa từng cột trước khi tổng hợp. Ví dụ, một file có hai cột code và amount chưa cho biết code tham chiếu đối tượng nào, amount dùng đơn vị gì và giới hạn hợp lệ đã được người phụ trách xác nhận hay chưa. Nếu thiếu mô tả, việc chỉ nhìn tên cột có thể dẫn đến diễn giải sai.

Trước khi dùng file, người tổng hợp kiểm tra dữ liệu thiếu, trùng hoặc không đáp ứng điều kiện đã thống nhất. Mã tham chiếu bị thiếu có thể làm một dòng khó đối chiếu; dòng trùng có thể khiến tổng hợp lặp; một ngày không tồn tại hoặc số ngoài khoảng có thể làm sai bước phân nhóm hay tính chỉ tiêu. Đây là các rủi ro cần kiểm soát, không phải kết luận rằng mọi file nhận từ chi nhánh đều có lỗi.

Khi phát hiện vấn đề, người kiểm tra cần chỉ rõ bản ghi nào, cột nào, giá trị nguyên bản và điều kiện không đạt. Người phụ trách nguồn đối chiếu lại hồ sơ hoặc hệ thống nguồn rồi sửa ở bên ngoài DataLens DQ. Bản CSV gửi lại được nhập thành phiên bản mới và kiểm tra lại; bản cũ và kết quả cũ vẫn được giữ để đối chiếu.

Nếu file và tiêu chuẩn chỉ được trao đổi rời rạc, người tổng hợp có thể chọn nhầm bản cũ hoặc không biết kết quả trước đây dùng quy tắc nào. Vì vậy, việc lưu phiên bản dữ liệu cùng snapshot quy tắc có ý nghĩa ngay cả khi công cụ không tự sửa dữ liệu.

**Điều có thể kiểm chứng bằng sản phẩm:** nhập file cùng cấu trúc thành phiên bản mới; lưu mô tả; đặt quy tắc; chỉ ra vi phạm; lưu lịch sử và xuất báo cáo. Các khả năng này được đối chiếu từ mã và báo cáo demo đã có.

**Điều còn là giả định cần khảo sát:** cách chi nhánh xuất/gửi file, tần suất gửi, người chịu trách nhiệm, số lỗi thường gặp, thời gian kiểm tra thủ công và tác động tới quyết định quản trị. Chưa có phỏng vấn hoặc phép đo tại doanh nghiệp để xác nhận các giả định này.

# 4. TRẢ LỜI ĐÚNG SÁU CÂU HỎI

## 4.1. Đơn vị hoặc tổ chức nào đang gặp vấn đề?

Đối tượng minh họa là **bộ phận tổng hợp/phân tích dữ liệu của một chuỗi bán lẻ** nhận CSV từ các chi nhánh hoặc bộ phận nguồn. Bộ phận này cần hiểu dữ liệu, kiểm tra trước khi báo cáo và có bằng chứng khi yêu cầu đối chiếu lại nguồn.

Đây là **bối cảnh giả định phục vụ đồ án**, chưa xác định tên doanh nghiệp và chưa khảo sát thực tế. Không khẳng định tổ chức cụ thể đang gặp sự cố hoặc đang dùng DataLens DQ. Chi nhánh là bên tham gia luồng dữ liệu, không mặc định có vai trò hay tài khoản riêng trong phần mềm.



## 4.2. Quy trình hiện tại đang được thực hiện như thế nào?

Quy trình trước khi có DataLens DQ được giả định như sau; cần xác minh lại bằng khảo sát:

**Xuất file → gửi file → tiếp nhận → kiểm tra thủ công → trao đổi lỗi → sửa nguồn → gửi lại → tổng hợp.**

1. Người phụ trách tại chi nhánh hoặc bộ phận nguồn xuất CSV phục vụ kỳ báo cáo.
2. Người này gửi file cho bộ phận tổng hợp bằng kênh trao đổi đang có, kèm mô tả nếu cần.
3. Người tiếp nhận lưu file, đọc cấu trúc cột và tìm hiểu nguồn gốc, đơn vị tính, người phụ trách.
4. Người kiểm tra dùng bảng tính hoặc thao tác thủ công để tìm dữ liệu thiếu, trùng và giá trị không phù hợp với tiêu chuẩn đã biết.
5. Nếu có vấn đề, người kiểm tra trao đổi lại các dòng hoặc cột cần đối chiếu. Việc trao đổi không đồng nghĩa đã có quy trình giao việc hay phê duyệt chính thức.
6. Người phụ trách nguồn đối chiếu, sửa trong công cụ nguồn hoặc file ở bên ngoài rồi xuất/gửi lại CSV.
7. Người tổng hợp kiểm tra lại, chọn bản phù hợp và đưa vào công việc tổng hợp, đồng thời tự quản lý các bản nhận được.

DataLens DQ không được dùng để mô tả ngược quy trình này như thể trước đây đã có website. File gửi, trao đổi lỗi và sửa nguồn đều là hoạt động giả định của con người, không phải chức năng đã tự động hóa.

## 4.3. Bất cập nằm ở bước nào?

| Bước | Bất cập cụ thể trong tình huống giả định | Hệ quả cần kiểm soát |
| --- | --- | --- |
| Xuất/gửi file | Không kèm đủ mô tả cột, đơn vị hoặc người phụ trách. | Người nhận phải hỏi lại, có thể hiểu sai nội dung. |
| Tiếp nhận | Tên file không đủ để xác định bản mới và mối liên hệ với bản trước. | Có thể dùng nhầm phiên bản để tổng hợp. |
| Kiểm tra thủ công | Điều kiện kiểm tra không được ghi thành bộ quy tắc thống nhất. | Hai người hoặc hai lần kiểm tra có thể bỏ sót khác nhau. |
| Trao đổi lỗi | Chỉ nói “file sai” mà thiếu dòng, cột, giá trị và điều kiện mong đợi. | Người nguồn khó tìm lại nội dung cần đối chiếu. |
| Nhận bản gửi lại | Khó biết lỗi nào đã được kiểm tra lại và theo tiêu chuẩn nào. | Dễ nhầm kết quả của file trước với file sau. |
| Tổng hợp/tra cứu | Không còn bằng chứng về bộ quy tắc ở thời điểm kiểm tra cũ. | Khó giải thích vì sao một bản từng đạt hoặc không đạt. |

Các bất cập trên là giả thuyết nghiệp vụ có thể khảo sát, không phải số liệu đã đo. Vấn đề không chỉ là “tốn thời gian” mà còn là thiếu khả năng giải thích và tái hiện kết quả.



## 4.4. Những ai tham gia quy trình?

- **Người tạo/phụ trách dữ liệu ở nguồn:** hiểu cách phát sinh dữ liệu, xuất CSV, giải thích cột và đối chiếu lại nguồn khi có phản hồi. Việc sửa nguồn diễn ra ngoài website.
- **Người tiếp nhận/tổng hợp/kiểm tra:** nhập CSV, bổ sung metadata đã xác nhận, cấu hình quy tắc, chạy kiểm tra, xem lỗi và dùng báo cáo để trao đổi.
- **Người sử dụng báo cáo để ra quyết định:** đọc thông tin đã tổng hợp và các giới hạn chất lượng; có thể nhận báo cáo qua kênh bên ngoài, không nhất thiết đăng nhập website.
- **Quản trị viên hệ thống:** quản lý tài khoản và quyền; có quyền nghiệp vụ trong ứng dụng hiện tại. Một người có thể kiêm nhiều trách nhiệm trên.

**Vai trò nghiệp vụ khác vai trò phần mềm.** Ứng dụng hiện có hai vai trò admin và data_steward. Cả hai được thao tác nghiệp vụ; chỉ admin quản lý tài khoản. Metadata “người phụ trách” là văn bản, không tự cấp tài khoản/quyền, không phân quyền theo chi nhánh hay chủ sở hữu. Không có vai trò phần mềm riêng cho người sửa lỗi hoặc người phê duyệt lỗi.

## 4.5. Những dữ liệu, chứng từ, biểu mẫu nào được tạo ra?

| Tên | Nội dung | Ai tạo | Dùng ở bước nào | Trong hay ngoài hệ thống |
| --- | --- | --- | --- | --- |
| CSV đầu vào | Dữ liệu xuất để kiểm tra. | Người nguồn. | Xuất, gửi, nhập. | Tạo/gửi ngoài; nhập vào website. |
| CSV đã sửa ở nguồn | Bản được đối chiếu và điều chỉnh bên ngoài. | Người nguồn. | Sửa, gửi lại. | Ngoài; sau đó nhập bản mới. |
| Metadata bộ dữ liệu/cột | Tên, mô tả, nguồn, người phụ trách; ý nghĩa cột. | Người quản lý dữ liệu. | Tìm hiểu, bổ sung mô tả. | Trong; nội dung cần xác nhận với nguồn. |
| Cấu hình quy tắc | Loại, cột, điều kiện, trạng thái bật/tắt. | Người kiểm tra. | Đặt tiêu chuẩn. | Trong. |
| Phiên bản nhập | Bản dữ liệu, tên file, thời điểm và số bản ghi. | Hệ thống khi người dùng nhập. | Nhận lần đầu/gửi lại. | Trong. |
| Snapshot quy tắc | Bộ quy tắc đang bật của một lần chạy. | Hệ thống. | Bắt đầu kiểm tra. | Trong; giữ theo lịch sử. |
| Lần chạy | Trạng thái, thời gian và thống kê kết quả. | Hệ thống theo lệnh người dùng. | Kiểm tra, tra cứu. | Trong. |
| Chi tiết vi phạm | Bản ghi, cột, giá trị gốc, mã lỗi, giải thích. | Engine kiểm tra. | Xem lỗi, đối chiếu. | Trong; có trong báo cáo xuất. |
| Báo cáo Excel/JSON | Tổng quan, quy tắc snapshot và toàn bộ vi phạm. | Hệ thống theo yêu cầu xuất. | Đối chiếu, chia sẻ. | Xuất từ website; chuyển file ngoài. |

Không phát sinh hóa đơn, phiếu duyệt hay phiếu giao việc trong quy trình này. Báo cáo chất lượng là bằng chứng kiểm tra, không phải chứng từ xác nhận dữ liệu đã được làm sạch.



## 4.6. Hệ thống mới giúp giảm sai sót, tiết kiệm thời gian hoặc cải thiện quyết định như thế nào?

| Bất cập | Chức năng cụ thể đã có | Tác dụng có thể kỳ vọng |
| --- | --- | --- |
| Khó hiểu dữ liệu | Metadata bộ dữ liệu/cột, nguồn và người phụ trách. | Giảm việc hỏi lại; tăng khả năng diễn giải đúng. |
| Kiểm tra thiếu nhất quán | Cấu hình quy tắc và engine xác định. | Lặp lại cùng điều kiện, giảm thao tác lọc thủ công. |
| Khó chỉ rõ lỗi | Chi tiết bản ghi/cột/giá trị, điều kiện và mã lỗi. | Giúp người nguồn định vị nội dung cần đối chiếu. |
| Nhầm bản dữ liệu | Phiên bản nhập và lần chạy gắn với từng bản. | Phân biệt bản nhận trước/sau khi gửi lại. |
| Không biết tiêu chuẩn cũ | Snapshot quy tắc và kết quả đã lưu. | Giải thích kết quả lịch sử khi quy tắc hiện tại thay đổi. |
| Khó chia sẻ bằng chứng | Excel ba sheet và JSON của đúng lần chạy. | Chuyển đủ kết quả để trao đổi ngoài hệ thống. |

**Khả năng đã kiểm chứng trong chạy thử:** báo cáo demo ở mục 7 lưu 4 bản ghi, 2 bản ghi lỗi và 3 vi phạm của phiên bản đầu; phiên bản sau có 0 vi phạm theo hai quy tắc tương ứng. Mã hiện tại và tài liệu kiểm thử cũng xác nhận luồng metadata, cấu hình bảy loại quy tắc, lưu snapshot/lịch sử và xuất báo cáo. Đây là bằng chứng kỹ thuật/demo, không phải chứng cứ về hiệu quả vận hành trong một chuỗi bán lẻ.

Luồng AI gợi ý đã có và từng được người dùng xác nhận nhận đề xuất thật, xem xét giả định rồi lưu quy tắc mặc định tắt. Bằng chứng này không chứng minh mọi đề xuất AI đúng hoặc hệ thống tự xác định tiêu chuẩn nghiệp vụ.

**Lợi ích chưa đo tại doanh nghiệp:** tiết kiệm bao nhiêu thời gian, giảm bao nhiêu lỗi và thay đổi chất lượng quyết định ra sao. Không đưa ra phần trăm cải thiện khi chưa có phép đo hoặc nhóm đối chứng.

**Đề xuất đánh giá:** chọn cùng một bộ CSV có đáp án do người am hiểu nghiệp vụ xác nhận. Đo thời gian kiểm tra thủ công và bằng hệ thống, bao gồm đặt quy tắc và đọc kết quả; đối chiếu lỗi phát hiện đúng, lỗi báo sai và lỗi bỏ sót. Với một bản dữ liệu và cùng tiêu chuẩn, kiểm tra khả năng tái hiện; đo thời gian tìm lại phiên bản, điều kiện và lỗi cũ. Ghi điều kiện thử, người thực hiện và phạm vi quy tắc để không so sánh thiếu công bằng.

Thông tin chất lượng giúp người dùng cân nhắc trước khi tổng hợp. Hệ thống không tự quyết định bản nào được phép đưa vào báo cáo và không bảo đảm số liệu đúng hoàn toàn về nghiệp vụ.



# 5. MỤC TIÊU VÀ PHẠM VI BÀI TOÁN

**Người sử dụng chính:** người tiếp nhận/tổng hợp/kiểm tra dữ liệu; quản trị viên quản lý tài khoản. Người nguồn và người nhận báo cáo có thể tham gia bên ngoài mà không có tài khoản riêng.

**Đầu vào:** CSV do người dùng chủ động chọn, metadata bộ dữ liệu/cột và cấu hình quy tắc đã được người phụ trách xem xét. Suy luận kiểu chỉ gợi ý cách hiểu cột, không tự tạo quy tắc, chuyển kiểu hay sửa giá trị gốc.

**Xử lý:** xác thực cấu trúc file, lưu phiên bản và metadata, kiểm tra theo quy tắc bật, thống kê, lưu snapshot/lần chạy/vi phạm, tra cứu lịch sử và xuất báo cáo. AI chỉ hỗ trợ gợi ý để người dùng duyệt; engine xác định quyết định kết quả kiểm tra.

**Đầu ra:** dữ liệu xem trước, metadata, kết quả theo phiên bản, chi tiết vi phạm, lịch sử và Excel/JSON. Tỷ lệ lỗi là số bản ghi có ít nhất một vi phạm chia tổng bản ghi, không phải tổng vi phạm chia tổng bản ghi.

| Loại quy tắc đã có | Điều kiện kiểm tra chính |
| --- | --- |
| required | Bắt giá trị thiếu: null, rỗng hoặc chỉ khoảng trắng. |
| unique | Một cột hoặc tổ hợp cột không trùng nguyên bản; bỏ qua tổ hợp thiếu. |
| numeric_range | Số hữu hạn trong khoảng đóng đã cấu hình. |
| data_type | Cú pháp integer, decimal hữu hạn hoặc true/false viết thường. |
| date_format | Đúng một trong ba format hỗ trợ và ngày Gregorian tồn tại. |
| allowed_values | Thuộc tập chuỗi cho phép, phân biệt hoa/thường và khoảng trắng. |
| pattern | Khớp toàn bộ mẫu re2-v1; không trim, không tự đoán cú pháp. |

Ngoài required, các loại trên bỏ qua giá trị thiếu; cần kết hợp required nếu phải bắt thiếu. integer nhận số 0 đầu không chứng minh mã định danh là số nghiệp vụ. pattern khớp hình thức ngày không chứng minh ngày đó tồn tại.

**Giới hạn CSV:** UTF-8/UTF-8 BOM, phân cách phẩy, có header và 1–10.000 bản ghi; tối đa 5 MiB. Header phải hợp lệ, không trùng; số trường mỗi bản ghi phải đúng. Không tự trim hoặc đổi chuỗi NULL thành null. Phiên bản mới phải cùng tên và thứ tự cột; khác cấu trúc thì tạo bộ dữ liệu khác. Các quy tắc mới và Excel còn có giới hạn riêng; vượt giới hạn được báo lỗi, không âm thầm cắt dữ liệu. Pattern có budget số quy tắc, độ dài giá trị và tổng byte; không là công cụ kiểm tra dữ liệu vô hạn.

**Trong phạm vi:** đăng nhập/quản lý tài khoản; AI có xem trước/xác nhận và người duyệt, hiện chỉ gợi ý required, unique, numeric_range. Excel có ba sheet; JSON giữ dữ liệu kỹ thuật. Có API xu hướng kết quả đã lưu; không mô tả một dashboard biểu đồ xu hướng chưa triển khai như chức năng đã có.

**Ngoài phạm vi:** sửa dữ liệu trực tiếp/tự làm sạch; tự gửi báo cáo lỗi về chi nhánh; giao việc/phê duyệt; kết nối database nguồn; tìm file toàn máy; so sánh liên bảng, công thức và phát hiện bất thường. PostgreSQL là nơi lưu ứng dụng, không đồng nghĩa website đã kết nối database nguồn của chi nhánh.



# 6. QUY TRÌNH KHI CÓ HỆ THỐNG

Trước khi vào website, người phụ trách nguồn vẫn phải xuất và gửi CSV bằng kênh bên ngoài. DataLens DQ hỗ trợ phần tiếp nhận, mô tả, kiểm tra và lưu bằng chứng; không tự nhận file từ chi nhánh hoặc thay thế việc trao đổi nghiệp vụ.

| Bước | Người thực hiện | Thao tác | Dữ liệu đầu vào | Kết quả |
| --- | --- | --- | --- | --- |
| 1 | Người tiếp nhận. | Đăng nhập, chọn và nhập CSV. | File được nguồn gửi ngoài website. | Bộ dữ liệu và phiên bản đầu; xem trước giá trị. |
| 2 | Người quản lý dữ liệu. | Bổ sung metadata, hỏi lại nguồn nếu chưa rõ. | Nội dung file và thông tin đã xác nhận. | Mô tả bộ dữ liệu/cột, nguồn, người phụ trách. |
| 3 | Người kiểm tra. | Chọn cột, loại và điều kiện; bật quy tắc. | Tiêu chuẩn nghiệp vụ đã thống nhất. | Bộ quy tắc; không tự chạy sau lưu. |
| 4 | Người kiểm tra. | Chủ động chạy trên phiên bản chọn. | Dữ liệu phiên bản và quy tắc bật. | Lần chạy, snapshot; kết quả hoặc trạng thái thất bại. |
| 5 | Người kiểm tra. | Xem lỗi/lọc, tra cứu và xuất báo cáo. | Lần chạy hoàn tất đã lưu. | Thống kê, lỗi cụ thể; Excel/JSON đầy đủ. |
| 6 | Người kiểm tra và người nguồn. | Chuyển báo cáo, trao đổi và đối chiếu ngoài website. | Báo cáo, file gốc và thông tin nguồn. | Nội dung cần xác minh, không phải phiếu giao việc. |
| 7 | Người phụ trách nguồn. | Sửa bên ngoài và xuất/gửi lại CSV. | Căn cứ đã được kiểm tra tại nguồn. | File mới; DataLens DQ không tự sửa. |
| 8 | Người tiếp nhận. | Nhập thành phiên bản mới cùng cấu trúc. | CSV gửi lại có cùng tên/thứ tự cột. | Phiên bản mới; bản cũ giữ nguyên. |
| 9 | Người kiểm tra. | Kiểm tra lại, đối chiếu hai lần và dùng kết quả. | Phiên bản mới và bộ quy tắc phù hợp. | Bằng chứng mới; lịch sử cũ không bị ghi đè. |

**Bước 6 và 7 diễn ra ngoài website.** Bổ sung metadata cũng có thể cần trao đổi ngoài hệ thống; không mặc định website xác minh được mọi mô tả do người dùng nhập.

Nếu quy tắc thay đổi, mỗi lần chạy lưu điều kiện riêng. Muốn đánh giá thay đổi chất lượng cần xét cả phiên bản dữ liệu, bộ quy tắc và phiên bản engine, không chỉ nhìn hai tỷ lệ cạnh nhau. Khi lần chạy thất bại, chưa có kết quả hoàn chỉnh; không hiểu là dữ liệu không có lỗi.

Báo cáo xuất lấy toàn bộ vi phạm của đúng lần chạy đã chọn, không phụ thuộc bộ lọc hoặc trang lỗi đang xem. Metadata hiện tại trong báo cáo được ghi rõ tại thời điểm xuất; điều kiện kiểm tra lịch sử lấy từ snapshot của lần chạy.



# 7. VÍ DỤ MINH HỌA XUYÊN SUỐT

**Một bộ dữ liệu duy nhất:** file tổng hợp từ nguồn có hai cột code và amount. Trong bối cảnh bán lẻ giả định, code là mã tham chiếu để tìm lại bản ghi tại nguồn; amount là một chỉ tiêu giá trị cần đối chiếu. Ý nghĩa, đơn vị và giới hạn phải được người nguồn xác nhận. Không mặc định code là mã hàng, cũng không coi 100 là trần doanh thu hợp lệ cho mọi chi nhánh.

Metadata minh họa cần ghi: bộ dữ liệu dùng cho việc gì, nguồn xuất, người phụ trách; code tham chiếu đối tượng nào; amount là chỉ tiêu nào và dùng đơn vị gì. Đây là cách giải thích metadata nên có, không khẳng định các mô tả giả định này đã được lưu vào demo.

**Bằng chứng demo có sẵn:** dataset 28, phiên bản 1 (ID 28), run 2. Hai quy tắc đã áp dụng là code bắt buộc và amount thuộc khoảng đóng 0–100. Khoảng này là điều kiện của demo, không phải chuẩn chung của ngành bán lẻ.

| Bản ghi | code nguyên bản | amount | Vi phạm trong run 2 |
| --- | --- | --- | --- |
| 1 | Chuỗi rỗng | 101 | Thiếu code; amount lớn hơn 100. |
| 2 | 001 | -1 | amount nhỏ hơn 0. |
| 3 | 日本語 | 0 | Không vi phạm hai quy tắc đã áp dụng. |
| 4 | “  dòng đầu↵dòng tiếp  ” | 100 | Không vi phạm hai quy tắc đã áp dụng. |

Ký hiệu ↵ ở bảng biểu diễn một newline trong trường CSV; hai khoảng trắng đầu/cuối được giữ ở dữ liệu gốc. Bản ghi logic có thể trải qua nhiều dòng vật lý. Chuỗi 001 không bị đổi thành số 1. Việc bản ghi 3 và 4 đạt required không chứng minh mã của chúng đúng về nghiệp vụ; demo chưa áp quy tắc định dạng mã hoặc đối chiếu danh mục nguồn.

**Bản ghi lỗi khác tổng vi phạm:** bản ghi 1 có hai vi phạm, bản ghi 2 có một; do đó có 2 bản ghi lỗi nhưng 3 vi phạm. Tỷ lệ lỗi = 2/4 × 100% = 50.0000%, không phải 3/4. Báo cáo lỗi chỉ ra số bản ghi, cột, giá trị gốc, điều kiện và mã REQUIRED_MISSING hoặc NUMERIC_OUT_OF_RANGE để người nguồn đối chiếu.

**Bản gửi lại đã có trong demo:** phiên bản 2 (ID 30), run 5 của cùng dataset 28, dùng file quality_errors_fixed.csv. Code của bản ghi 1 thành FIX001; amount của bản ghi 1 và 2 lần lượt thành 100 và 0. Báo cáo lưu 4 bản ghi, 0 bản ghi lỗi, 0 vi phạm, 0.0000%. Đây là nội dung file sửa đã có, không phải giá trị thay thế do hệ thống tự suy ra; không có căn cứ để áp FIX001 cho mọi mã thiếu.

**Truy vết:** run 2 vẫn giữ snapshot code bắt buộc và amount 0–100 cùng ba vi phạm cũ; run 5 gắn với phiên bản mới và điều kiện của chính lần đó. Nếu sau này người dùng sửa quy tắc hiện tại, snapshot cũ vẫn giữ nguyên. Ví dụ không chứng minh demo này từng thay đổi quy tắc; khả năng bảo toàn snapshot khi sửa đã có kiểm thử riêng trong dự án.

**Đối chiếu báo cáo:** Excel có Tổng quan, Chi tiết lỗi và Quy tắc đã áp dụng; JSON chứa dữ liệu kỹ thuật của cùng run. File xuất là báo cáo kiểm tra, không phải CSV đã sửa. “0 vi phạm” chỉ là đạt theo các quy tắc đã áp dụng, không chứng minh toàn bộ dữ liệu chính xác.



# 8. TÓM TẮT GIẢI PHÁP VÀ CÔNG NGHỆ

Giải pháp là một nơi lưu mô tả, phiên bản, tiêu chuẩn và bằng chứng kiểm tra dữ liệu nhận từ nguồn. Người tổng hợp có thể trả lời: đang kiểm tra file nào, dữ liệu có nghĩa gì, đã dùng điều kiện nào, lỗi ở đâu và bản gửi lại có kết quả ra sao. Việc chuyển file, trao đổi và sửa nguồn vẫn do con người thực hiện bên ngoài.

| Thành phần | Vai trò ngắn gọn |
| --- | --- |
| React | Giao diện nhập file, metadata, modal quy tắc, xem lịch sử/lỗi và xuất báo cáo. |
| Python FastAPI | Cung cấp API và điều phối các thao tác nghiệp vụ, kiểm tra quyền và validation. |
| Engine xác định | Kiểm tra theo các quy tắc đã bật; lưu kết quả, không giao AI quyết định đạt/lỗi. |
| PostgreSQL | Lưu tài khoản, metadata, dữ liệu phiên bản, quy tắc, lần chạy và vi phạm của ứng dụng. |
| Gemini | Hỗ trợ gợi ý ba loại quy tắc ban đầu khi có cấu hình và xác nhận; người dùng xem xét trước khi lưu. |
| RE2 | Thực hiện pattern theo dialect giới hạn; worker có budget/deadline, không chạy regex người dùng trong trình duyệt. |

AI không tự áp dụng mọi đề xuất, không tự sửa dữ liệu và không tự chạy kiểm tra. Quy tắc lưu từ đề xuất mặc định tắt; người dùng xem lý do/giả định, chỉnh sửa và chủ động bật nếu phù hợp. Metadata “người phụ trách” và việc người dùng duyệt gợi ý AI không tạo ra quy trình giao việc/phê duyệt xử lý lỗi.

## Căn cứ đối chiếu và giới hạn bằng chứng

Tài liệu được đối chiếu ngày 19/10/2026 từ PROJECT_CONTEXT, MVP_SCOPE, PROGRESS, ACCESS_CONTROL, RULE_EXTENSION_PLAN, QUALITY_ENGINE, REPORT_SCHEMA; mã parser CSV/nhập phiên bản, validator/engine, AI, frontend form, tài khoản và xuất báo cáo. Các tài liệu MVP hoặc thiết kế cũ được đọc theo mốc lịch sử; hiện tại đã có bảy loại quy tắc thủ công.

Số liệu mục 7 lấy từ hai báo cáo đã lưu: backend/samples/bc01a/dataset-28-run-2-report.json và dataset-28-run-5-report.json, cùng hai CSV quality_errors_demo.csv và quality_errors_fixed.csv. Không tạo lại dữ liệu hoặc chạy engine để viết tài liệu. Mô tả chức năng hiện có không đồng nghĩa mọi tình huống giao diện đã được nghiệm thu: QT-04C pattern vẫn là checklist chưa xác nhận; các tình huống mạng, phiên và CSRF nâng cao chưa có bằng chứng riêng không được xem là đã đạt.

Luồng AI có bằng chứng xác nhận người dùng tại mục 26H của PROGRESS; tài liệu này không gọi lại Gemini và không đánh giá độ chính xác chung của đề xuất. Lợi ích trong doanh nghiệp, tần suất lỗi và thời gian tiết kiệm vẫn cần khảo sát, đo lường như mục 4.6.

**Thông điệp kết luận:** DataLens DQ giúp minh bạch dữ liệu và tiêu chuẩn kiểm tra trước khi báo cáo. Hệ thống cung cấp bằng chứng để con người xử lý có căn cứ; không thay thế trách nhiệm xác nhận tại nguồn hoặc biến một báo cáo kiểm tra thành bảo chứng về tính chính xác tuyệt đối.

<!-- PAGE -->

# 9. BÀI NÓI TRÌNH BÀY 3–5 PHÚT

Kính thưa thầy cô, em chọn đề tài xây dựng website quản lý danh mục dữ liệu và kiểm tra chất lượng dữ liệu vì trước khi lập báo cáo, người sử dụng không chỉ cần có file mà còn cần hiểu file đó chứa gì, đến từ đâu và đã được kiểm tra như thế nào. Đề tài phù hợp với chuyên ngành Hệ thống thông tin vì kết nối quy trình làm việc, trách nhiệm quản lý dữ liệu và công cụ hỗ trợ.

Em sử dụng một tình huống giả định: bộ phận tổng hợp của một chuỗi bán lẻ nhận CSV từ các chi nhánh để lập báo cáo. Em chưa khảo sát doanh nghiệp thực tế nên không khẳng định một tổ chức cụ thể đang gặp vấn đề. Theo quy trình giả định, chi nhánh xuất và gửi file; người tổng hợp tiếp nhận, kiểm tra thủ công rồi trao đổi nếu có lỗi; phía nguồn đối chiếu, sửa và gửi lại trước khi tổng hợp.

Bất cập xuất hiện ở từng bước. Khi nhận file thiếu mô tả, người tổng hợp có thể chưa biết cột mã tham chiếu gì hoặc chỉ tiêu dùng đơn vị nào. Khi kiểm tra bằng thao tác riêng lẻ, tiêu chuẩn giữa các lần có thể khác nhau. Khi chỉ phản hồi rằng file sai mà không chỉ rõ dòng và cột, phía nguồn khó đối chiếu. Khi có nhiều bản gửi lại, người dùng còn dễ nhầm phiên bản hoặc không biết tiêu chuẩn của lần kiểm tra cũ.

Quy trình có người phụ trách dữ liệu tại nguồn, người tiếp nhận và kiểm tra, người dùng báo cáo để quyết định, cùng quản trị viên. Một người có thể kiêm nhiều trách nhiệm; không phải mỗi trách nhiệm đều là một vai trò riêng trong phần mềm. Dữ liệu cần quản lý gồm CSV, metadata, cấu hình quy tắc, phiên bản nhập, snapshot, kết quả chạy và báo cáo đối chiếu.

Giải pháp DataLens DQ cho phép nhập CSV, bổ sung metadata và đặt bảy loại quy tắc chất lượng. Người dùng chủ động kiểm tra, xem bản ghi nào vi phạm điều kiện nào rồi xuất Excel hoặc JSON. Nếu cần sửa, người phụ trách vẫn phải đối chiếu và sửa tại nguồn, sau đó nhập file gửi lại thành phiên bản mới. Website không tự chuyển file về chi nhánh, không tự làm sạch và không giao việc hay phê duyệt lỗi.

Trong demo đã lưu, cùng một bộ dữ liệu có bốn bản ghi. Phiên bản đầu có hai bản ghi lỗi nhưng ba vi phạm vì một bản ghi cùng lúc thiếu mã và có số ngoài khoảng. Phiên bản gửi lại có không vi phạm theo hai quy tắc đã áp dụng. Lịch sử và snapshot giúp xem lại tiêu chuẩn, kết quả của từng lần thay vì lấy quy tắc hiện tại để diễn giải lại quá khứ.

Lợi ích kỳ vọng là kiểm tra nhất quán, chỉ rõ nội dung cần đối chiếu và tìm lại bằng chứng nhanh hơn. Em chưa đo tại doanh nghiệp nên không khẳng định phần trăm tiết kiệm. Em đề xuất đánh giá bằng thời gian kiểm tra cùng dữ liệu, lỗi phát hiện đúng hoặc sai và khả năng tìm lại lịch sử. AI chỉ gợi ý để người dùng xem xét; engine xác định kết quả. Cuối cùng, không vi phạm chỉ có nghĩa dữ liệu đạt theo các quy tắc đã áp dụng, không chứng minh dữ liệu đúng hoàn toàn. Em xin cảm ơn thầy cô.
