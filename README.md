# Data Catalog và kiểm tra chất lượng dữ liệu

## CORE-ACK-QA — Mất phản hồi upload (12/11/2026)

Đã tái hiện commit v2 rồi mất HTTP201, bấm lại sinh v3; UI nay giữ trạng thái chưa xác nhận, có kiểm tra/xem/dùng phiên bản đã lưu và chặn retry ngay, kể cả reload. Engine FAILED không hiển thị Đạt nên giữ nguyên. Đạt84 test frontend,16 backend liên quan, typecheck/build và4 nhóm browser trên database tạm; QA hiện tại không đổi. [Bằng chứng và giới hạn](docs/CORE_ACK_QA_HANDOVER.md).

## SRC-01 — Nguồn cung cấp theo đợt (11/11/2026)

Danh mục Thương hiệu → Cửa hàng nằm trong Danh mục & Từ điển. Tạo đợt chọn loại dữ liệu/cửa hàng/kỳ; khóa đổi nguồn sau khi có file. Dashboard/Báo cáo lọc theo nguồn của đợt; CSV/JSON/Excel và kết quả giữ tên nguồn trong snapshot run. Migration0013 đã backup trước khi áp dụng, không gán nguồn hoặc sửa dữ liệu QA cũ. Đạt46 test backend liên quan,80 frontend, typecheck/build và6 nhóm browser. [Bàn giao, backup, URL và giới hạn](docs/SRC01_HANDOVER.md).

## UI theo demo HTML HTTT-36/M9 (11/11/2026)

Đã bám chuẩn bố cục/màu/font/khoảng cách của demo: sidebar navy232px, Inter, KPI4 cột, nhóm nguồn/stack, heatmap, biểu đồ và ưu tiên/đối soát. Các màn hình riêng Danh mục & Từ điển, Quy tắc, Nộp & Kiểm tra, Quản lý lỗi, Đối soát, Báo cáo, Quản trị; không lặp 6 bảng chỉ khác bộ lọc. Vào thẳng danh sách đợt, tạo từ danh mục/nguồn/kỳ có sẵn, giữ theme popover và URL/Back/reload. Không backend/schema/migration/dữ liệu giả. Đạt72 unit frontend, typecheck/build, 8 nhóm Chromium/31 ảnh tại1366/1024/768; QA39/83/84 không đổi. Xem [bàn giao và giới hạn](docs/DEMO_UI_HANDOVER.md), [ảnh so sánh demo–kết quả](docs/samples/demo-ui-comparison.html).

## UI-05 — Tổ chức giao diện theo công việc (10/11/2026)

Trang chủ thành điều hành theo đợt, có card/tiến trình/biểu đồ và bảng việc cần xử lý; 6 bảng công việc nối với Danh mục dữ liệu. Chi tiết đợt có 5 tab qua URL, giữ deep link/Back/bộ lọc; Giao diện chuyển thành popover có bàn phím/focus. Không đổi backend/API/nghiệp vụ, không migration hay dữ liệu QA. Đạt 69 unit frontend, typecheck/build và 8 nhóm Chromium/35 ảnh ở1366/1024/768; QA39 vẫn hoàn tất, run83=3/2/3, run84 sạch. Xem [bàn giao, ảnh trước/sau và URL QA](docs/UI05_HANDOVER.md).

## EXP-01 — CSV lỗi theo snapshot run (10/11/2026)

CSV lỗi giữ 6 cột cũ, thêm dataset/đợt/phiên bản/run và từng cột khóa từ snapshot, có JSON giá trị gốc và bảo vệ công thức Excel. Run mới lưu snapshot ngay khi bắt đầu; run cũ dùng bằng chứng lịch sử có nhãn, không ghi đè bằng cấu hình hiện tại. Migration hiện tại **0012**, không backfill. Đạt 28 test backend liên quan, 65 unit frontend, build và 2 nhóm Chromium tải CSV thật từ run83/58/39 chỉ đọc. Xem [bàn giao EXP-01](docs/EXP01_HANDOVER.md).

## UX-04 — Issue và đối soát trên Dashboard (09/11/2026)

Dashboard mỗi đợt có số issue chưa xử lý/chưa thể đối soát/ngoại lệ, lý do chặn hoàn tất và liên kết Xử lý lỗi. Summary theo lô qua endpoint hiện có; công thức chất lượng giữ nguyên. QA57/đợt34–38 xác nhận **15 bản ghi, 3 dòng lỗi, 4 vi phạm, 20%**. Đạt 18 test backend liên quan, 62 unit frontend, build và 3 nhóm Chromium local chỉ đọc. Xem [bàn giao UX-04](docs/UX04_HANDOVER.md).

## NV-02 — Xử lý lỗi, đối soát và hoàn tất đợt (09/11/2026)

Đã có khóa nhận diện tổ hợp theo revision, issue và lịch sử xử lý tách biệt violation, đối soát qua phiên bản có bằng chứng, ngoại lệ có ghi chú và hoàn tất/mở lại đợt có kiểm tra giao dịch. Migration head hiện tại **0011**; dữ liệu/snapshot QA52/55 được bảo toàn. Đạt **966 test backend**, **61 unit frontend**, TypeScript/build; Chromium thật đạt 5 nhóm ở database tạm và 3 nhóm chỉ đọc local. QA riêng: **dataset57, đợt34–37**. Xem [bàn giao và bước QA NV-02](docs/NV02_HANDOVER.md), [đáp án từng issue](qa_test_data/nv02/manifest.json). Nhấp đúp `start.cmd` để chạy lần sau. Các mốc bên dưới là lịch sử trước NV-02.

## Bổ sung BUG-04 — Đối chiếu và trạng thái sửa quy tắc (09/11/2026)

Loại trùng lý do sau ánh xạ thông báo; delta khác cấu hình vẫn Không áp dụng. Sửa quy tắc dùng mode/ID rõ ràng, đọc mới đúng scope và khóa lưu khi đang tải/lỗi, key theo ID chống state cũ. Đạt 60 unit frontend, build, 36 test backend; browser 4 nhóm/6 ảnh ở database tạm và 2 nhóm/3 ảnh chỉ đọc QA local. Chưa tái hiện nguyên nhân cụ thể của lần QA thấy form Thêm trống. Xem [bàn giao bổ sung BUG-04](docs/BUG04_FOLLOWUP_HANDOVER.md).


## BUG-04 — Form dataset và lỗi cấu hình quy tắc (09/11/2026)

Form tạo dataset gỡ đúng guard trước điều hướng thành công; các form CRUD dùng chung vòng đời lưu/đóng. Lỗi mẫu định dạng và cấu hình có thông báo tiếng Việt tại ô liên quan, chi tiết kỹ thuật thu gọn. Đạt 58 unit frontend, build, 124 test backend; browser 10 nhóm/12 ảnh ở database tạm và 3 nhóm/4 ảnh chỉ đọc trên QA 55/31/66–67. Xem [bàn giao BUG-04](docs/BUG04_HANDOVER.md).


## UX-03 — Điều hướng và giữ ngữ cảnh đợt (08/11/2026)

Breadcrumb kết quả có liên kết đợt; lịch sử/đối chiếu giữ scope qua URL, reload và Back. Tab dataset xuống hàng thay cho cuộn ngang; Back đóng preview đúng trang. Đạt 52 unit frontend, build, 4 test NV-01; browser thật: 6 nhóm/17 ảnh ở database tạm và 4 nhóm/10 ảnh chỉ đọc trên QA 52/27/59–61. Xem [bàn giao UX-03 điều hướng](docs/UX03_NAVIGATION_HANDOVER.md).


## BUG-03 — Guard tạo đợt và hiển thị khoảng trắng (08/11/2026)

Đã gỡ dirty guard đúng form trước điều hướng tạo đợt thành công; giữ bảo vệ form chưa lưu và nội dung khi API lỗi. Preview/kết quả phân biệt Trống với Chỉ có khoảng trắng theo engine; CSV giữ giá trị nguồn. Đạt 48 kiểm thử frontend, build, 79 kiểm thử backend và 8 nhóm browser thật. Fixture riêng: dataset 53/đợt 28, dataset 54/đợt 29; mọi dòng QA có sẵn không đổi. Xem [bàn giao BUG-03](docs/BUG03_HANDOVER.md).


## UX-02 — Thao tác theo Bộ dữ liệu → Đợt → Phiên bản (08/11/2026)

Đã làm rõ phạm vi upload/chạy kiểm tra, đưa phiên bản lên trước quy tắc thu gọn, thay bộ lọc Ctrl bằng checkbox/chip và sửa ngữ cảnh đối chiếu. Kiểm thử: 45 unit, build, 4 kiểm thử NV-01 và 10 nhóm browser thật đạt. Backend, migration và dữ liệu nghiệp vụ/lịch sử giữ nguyên. Xem [bàn giao UX-02](docs/UX02_HANDOVER.md) để biết danh sách file, bằng chứng và URL kiểm tra local.


## NV-01 — Quy tắc độc lập theo đợt (08/11/2026)

Mô hình hiện tại: Dataset → DataBatch → DatasetVersion → QualityRun. Rule dataset là mẫu; mỗi đợt có rule và revision riêng. Upload CSV đầy đủ tạo v1/v2/v3… trong đúng đợt, chuyển bản hiện hành atomically; run lưu snapshot rule/schema/revision. Dashboard lấy một lần hoàn tất gần nhất của current từng đợt, không thay bằng kết quả bản cũ. Khác đợt/revision/engine/cấu hình không có delta cải thiện; không nhận diện hoặc tự đóng lỗi xuyên file bằng số dòng.

Migration head: `0010`. Hướng dẫn, bảo toàn dữ liệu, kiểm thử và URL QA: [NV01_HANDOVER.md](docs/NV01_HANDOVER.md). Audit/kế hoạch: [NV01_PLAN.md](docs/NV01_PLAN.md). Nhấp đúp `start.cmd` để chạy. Các mốc dưới đây là lịch sử triển khai, không thay thế hợp đồng NV-01.

## Frontend DataCheck mới — 01/11/2026

Giao diện mới hoàn toàn bằng tiếng Việt, kết nối backend hiện có, theo luồng tạo bộ dữ liệu → CSV → quy tắc → kiểm tra → xem lỗi → tải bản đã sửa. Xem [bàn giao frontend mới](docs/FRONTEND_REBUILD.md) để biết màn hình, API, bản sao lưu, kiểm thử và cách chạy. Các phần bên dưới giữ lại lịch sử triển khai trước đó.

Các chức năng quản lý tài khoản, gợi ý AI, đối chiếu hai lần kiểm tra, xu hướng và kiểm tra kết nối đã có điểm truy cập trong giao diện mới. Xem [bảng đối chiếu chức năng và kết quả bổ sung](docs/FRONTEND_FUNCTION_AUDIT.md) để biết phạm vi hỗ trợ, API và bằng chứng nghiệm thu.

## OBS-01B — Dashboard breakdown của lần chạy đang mở

Trong tab **Kết quả kiểm tra**, mở một run completed từ lịch sử để xem **Phân tích vi phạm theo nhóm**: bốn chiều chất lượng, quy tắc snapshot và cột/nhóm cột. Mỗi nhóm có **số vi phạm** và **số bản ghi bị ảnh hưởng** đếm phân biệt; unique tổ hợp giữ nguyên nhóm cột. Không cộng số bản ghi giữa nhóm và không hiển thị tỷ lệ breakdown khi chưa có mẫu số. Tóm tắt phía trên giữ thống kê run đã lưu, tỷ lệ đạt và thời điểm của chính run đó.

Client dùng GET `quality-summary`, phân trang rule/cột độc lập (20 mục/trang), kiểm tra response đúng dataset/run/version/engine và số liệu đã lưu. Có trạng thái đang tải, lỗi và tải lại chủ động; chạy đang xử lý/thất bại không bị trình bày như không có lỗi. Đổi run/dataset hoặc hết phiên hủy/chặn phản hồi cũ. Snapshot, điều kiện đầy đủ và fingerprint xem được; không đọc rule hiện tại để thay lịch sử, không tải violations để tự tổng hợp. Dùng CSS hiện có, chưa làm trend UI.

Kiểm tra cuối: **build/TypeScript và 15 script đạt**; GET chỉ đọc demo28/run2 (**4/2/3; đạt50.0000%**) và run5 (**4/0/0; đạt100.0000%**) khớp toàn bộ đáp án API, bảy bảng nghiệp vụ không đổi. Chromium kiểm tra28 trạng thái ở1366×768 và390×844, không tràn ngang toàn trang. Đây là bằng chứng tự động; **chưa thay nghiệm thu trình duyệt của người dùng**, đặc biệt unique tổ hợp/phân trang nhiều trang trên dữ liệu thật và lỗi mạng/phiên. Xem [spec](docs/QUALITY_DASHBOARD_SPEC.md), [checklist](docs/UI_CHECKLIST.md), [GET](docs/samples/obs01b_quality_summary_readonly.json), [ảnh/DOM](docs/samples/obs01b-ui/ux03a-layout-verification.json).

## OBS-01A — API tổng hợp Dashboard theo run

`GET /api/datasets/{dataset_id}/runs/{run_id}/quality-summary?rule_page=1&column_page=1&page_size=20` chỉ đọc run completed theo quyền hiện có. Trả context engine/snapshot, thống kê run đã lưu, đủ bốn chiều và các trang rule/cột/nhóm cột. Đếm riêng số violation và dòng vi phạm DISTINCT; unique tổ hợp không phân bổ vào từng cột. **Chỉ có tỷ lệ overall; không trả tỷ lệ hoặc mẫu số đủ điều kiện theo nhóm**, kể cả required.

Aggregate thực hiện trong PostgreSQL bằng số truy vấn cố định, transaction REPEATABLE READ READ ONLY; không chạy engine/AI, đọc QualityRule hiện tại hoặc kéo toàn bộ violations lên frontend. Không migration/dependency/model/engine_version mới. Hợp đồng và lỗi tại [QUALITY_DASHBOARD_SPEC](docs/QUALITY_DASHBOARD_SPEC.md), kết quả kiểm thử cuối tại [PROGRESS](docs/PROGRESS.md). Frontend breakdown được bổ sung trong OBS-01B ở trên; chưa có trend UI hoặc thư viện biểu đồ mới.

Kiểm tra cuối: **124 test PostgreSQL/regression đạt**, pip check đạt; database ứng dụng vẫn **0008 head**, alembic check không phát hiện lệch schema. GET có xác thực demo28/run2 và run5 khớp số liệu, checksum bảy bảng nghiệp vụ không đổi; [bằng chứng](docs/samples/obs01a_quality_summary_readonly.json). Backend đã nạp endpoint mới; chưa nghiệm thu frontend hoặc tải lớn.

## UX-03A — Trang chi tiết theo quy trình kiểm tra

**Phương án 2 (21/10/2026):** tiếp tục bằng CSS thuần và component hiện có. Tab nhẹ hơn, đầu bảng/chữ dữ liệu rõ hơn, chia lại cột và gom bộ lọc lịch sử với nút tải lại. Không thêm thư viện/font, chỉ số sức khỏe, tag, tìm giá trị toàn bảng, mức độ lỗi hoặc PDF; không đổi API/nghiệp vụ/dữ liệu. Build/TypeScript và 14 script đạt; Chromium kiểm tra 24 trạng thái ở laptop/màn hẹp, không tràn ngang toàn trang. Xem [bằng chứng mới](docs/samples/ux03a-css/ux03a-layout-verification.json), [ảnh tab/quy tắc](docs/samples/ux03a-css/ux03a-laptop-rules.png), [checklist Phương án 2 chờ người dùng nghiệm thu](docs/UI_CHECKLIST.md). Các mô tả luồng dưới đây được giữ nguyên.

Header gọn giữ dataset, phiên bản và hai thao tác Nhập phiên bản mới/Chạy kiểm tra; nút chạy dùng đúng luồng hiện có. Bốn tab: **Tổng quan · Dữ liệu và cấu trúc · Quy tắc · Kết quả kiểm tra**. Tab kết quả ưu tiên tóm tắt run và **Xem lỗi**, tiếp đến lịch sử với **Mở kết quả**, rồi **Đối chiếu hai lần chạy**. Xem chi tiết từ đối chiếu rồi quay lại giữ A/B, trang chọn và kết quả đã tải. Tạo quy tắc/AI chung toolbar; cấu hình dài mở xem đầy đủ, tỷ lệ gắn run/thời điểm và snapshot.

Kiểm tra cuối lượt làm rõ luồng (20/10/2026): build/TypeScript và 14 script đạt. Chromium đo/chụp 24 trạng thái ở 1366×768 và 390×844, không tràn ngang toàn trang; xác nhận Xem lỗi không request mới, quay lại đối chiếu không GET lại và đổi A/B không gắn nhầm kết quả cũ. Xem [bằng chứng](docs/samples/ux03a-flow/ux03a-layout-verification.json), [ảnh kết quả](docs/samples/ux03a-flow/ux03a-laptop-runs-scrolled.png), [ảnh modal màn hình hẹp](docs/samples/ux03a-flow/ux03a-narrow-comparison-selected.png) và [checklist bốn luồng chờ người dùng nghiệm thu](docs/UI_CHECKLIST.md). Chỉ GET demo; không chạy engine hoặc sửa backend, dependency, .env hay dữ liệu demo. Frontend5173/backend8000 giữ chạy. Chi tiết tại [PROGRESS](docs/PROGRESS.md).

## MR-02C-FIX — Giữ ngữ cảnh đối chiếu

Chọn A/B bằng hai nút có dấu ✓ và aria-pressed; summary luôn thấy, cập nhật ngay. Xem chi tiết A/B rồi **Quay lại đối chiếu** giữ đúng cặp, trang/bộ lọc và result thành công, không tự GET lại. Run mở thông thường không có nút quay lại giả. Đổi cặp xóa kết quả cũ; close hủy request pending, dữ liệu chỉ ở bộ nhớ cùng dataset/phiên, reload/logout xóa. Build/TypeScript và12script đạt; **dấu chọn/quay lại sau sửa chờ nghiệm thu browser** theo [checklist](docs/UI_CHECKLIST.md). Không backend/demo hoặc tính năng mới.

## MR-02C — Đối chiếu hai lần chạy trên giao diện

Trong Kiểm tra & lịch sử, bấm **Đối chiếu hai lần chạy** để mở modal, chủ động chọn A/B từ lịch sử phân trang. A là mốc, chênh lệch B−A; chỉ completed cùng dataset, A=B được phép. Chỉ nhấn Đối chiếu mới GET, đổi cặp xóa kết quả cũ, Đóng hủy GET. Hai bên có metadata, số liệu, snapshot7loại và fingerprint mở xem đầy đủ; khác cơ sở ẩn delta/cảnh báo, không kết luận tốt/xấu. Mở chi tiết A/B đóng modal rồi mở đúng run, không chạy mới.

Build/TypeScript +12script PASS; productionclient GETdemo28 run2/run5, đảo/cùngrun khớp đáp án và checksum7bảng nghiệp vụ không đổi. [Bằng chứng](docs/samples/mr02c_comparison_verification.json), [spec](docs/RUN_COMPARISON_SPEC.md), [checklist MR-02D chưa nghiệm thu](docs/UI_CHECKLIST.md). Không sửa backend/dependency/schema/.env/demo; không trend/27B.

## MR-02B — API đối chiếu hai lần chạy

GET `/api/datasets/{dataset_id}/run-comparison?a_run_id=2&b_run_id=5` đọc hai completed cùng dataset, summary/version/file/time/engine/fingerprint và snapshot đầy đủ trong một REPEATABLE READ READ ONLY transaction. Cùng engine+hash mới có delta B−A; khác cơ sở delta=null. A=B hợp lệ, same_run=true/delta0. Rate/pass/delta dùng Decimal/chuỗi4sốlẻ; tỷ lệ chênh lệch là điểm phần trăm. Snapshot/kết quả hỏng trả500 INVALID_RUN_RESULT an toàn, không repair. Không engine/currentrules/violations/report hoặc ghi dữ liệu khi đối chiếu.

94test cuối và pipcheck đạt; GETdemo28 A2/B5 khớp4→4rows,2→0errorrows,3→0violations,50.0000→0.0000% lỗi; deltaerror−50.0000/pass+50.0000 điểm phần trăm. Đảo/cùngrun và checksum7bảng đã kiểm. Xem [spec](docs/RUN_COMPARISON_SPEC.md), [bằng chứng GET](docs/samples/mr02b_comparison_verification.json), [PROGRESS](docs/PROGRESS.md). **Chưa frontend MR-02C hoặc nghiệmthu browser MR-02D**, không đổi dependency/schema/demo.

## MR-01C — Tìm dataset theo metadata trên giao diện

Ô tìm chung theo tên/mô tả/nguồn/người phụ trách; nhấn Tìm hoặc Enter, không gửi mỗi phím. Xóa tìm kiếm bỏ lọc; total và phân trang theo q. Giữ q/page khi mở chi tiết rồi quay lại, reload reset; nhập CSV thành công bỏ lọc vềpage1. Giới hạn200 Unicode code point, NFC/trim theo [spec](docs/REGISTERED_DATASET_SEARCH_SPEC.md), lỗi giữ draft; hủy request cũ và chặn phản hồi sau đọc body/hết phiên. Không đổi backend hoặc dữ liệu.

Build/TypeScript + test tìm kiếm và10regression frontend PASS; **chưa nghiệm thu MR-01D bằng trình duyệt**. Xem [checklist](docs/UI_CHECKLIST.md) và [PROGRESS](docs/PROGRESS.md).

## MR-01B — Backend tìm dataset theo metadata

GET `/api/datasets?q=...` tìm nguyên cụm trên name/description/source/owner (OR), không phân biệt hoa/thường nhưng còn phân biệt dấu, NFC chỉ khi so sánh. q tối đa200 Unicode code point trước trim/NFC; %, _, nháy và backslash là literal. Không q/rỗng giữ API cũ; total sau lọc và items đọc cùng transaction REPEATABLE READ READ ONLY, sort cũ và quyền catalogue chung giữ nguyên. Không tìm raw/cột/filename, không filter source/owner riêng. Xem [hợp đồng và bàn giao](docs/REGISTERED_DATASET_SEARCH_SPEC.md).

Đã xác minh PostgreSQL17.11 UTF8 en_US.utf8 và HTTP chỉ GET ứng dụng (21dataset; match dataset49; không match sentinel), checksum7bảng nghiệp vụ không đổi. Chưa triển khai UI MR-01C hoặc nghiệm thu MR-01D; C sẽ giữ q/page khi đi–về chi tiết, reset khi reload, import thành công xóa q/page1 và báo danh sách đã bỏ lọc. Không migration/index/dependency hoặc thay demo. Kết quả test cuối tại [PROGRESS](docs/PROGRESS.md).

## QT-04B — frontend pattern RE2 đã triển khai

Quy tắc thủ công có “Đúng mẫu định dạng”, đúng một cột, textarea monospace giữ nguyên pattern và dialect re2-v1 chỉ đọc; config chỉ pattern/dialect. Không trim/sửaescape/thêmneo/chạy JavaScript RegExp. Client chỉ kiểm cấu trúc, UTF-8/Unicode code point và độ dài (512codepoint/2048byte/16KiBconfig); backend quyết định grammar. Trợ giúp đọc từ parser thực tế: ordinary groups/classes/escapes/count0..1000 và tập không hỗ trợ, không nút/endpoint chạy thử. Skipmissing/case/space và cảnh báo mẫu ngày cần date_format hiển thị rõ.

List/snapshot/chi tiết lỗi hiển thị pattern/dialect đầy đủ dạng text an toàn, nhãn PATTERN_MISMATCH tiếng Việt; điều kiện lấy snapshot, không đổi thống kê. Runclient giữ mã lỗi backend, body được đọc trong businessFetch để chặn response cũ; requestabort/identity/generation/ref khóa gửi bảo vệ khi đổi dataset/version/hếtphiên/unmount. Busy/budget không giả định córun; lỗi córunID cho mở lịch sử, failed không hiện như không có lỗi, không retry/autorun. AI vẫn ba loại ban đầu.

Kiểm tra cuối: build/TypeScript và10script frontend PASS (pattern/data_type/date_format/allowed_values/AI/modal/auth/business/export/report--mock-only); cảnh báo stripTypeScriptTypes hiện hữu. Client thật11GET demo48/version52/run41 khớp10/7/7/70.0000%, lỗi3,4,5,6,7,9,10, raw/snapshot/history/filter/JSON/XLSX; checksum7bảng nghiệp vụ không đổi. Session tạm thu hồi, không cookie/token trong artifact docs/samples/pattern_qt04b_readonly.json. Không ghi demo hoặc chạy engine.

**QT-04C đã đạt 8 bước luồng chính theo xác nhận người dùng tại MR-01A; Codex không tự nghiệm thu browser. Các ca busy/timeout/mạng/phiên/CSRF và nâng cao chưa thử vẫn mở. Tài liệu mẫu**: CSV/đáp án docs/samples/pattern_qt04c* và8bước UI_CHECKLIST đã chuẩn bị: mẫuSP[0-9]{4}7lỗi/70%; sửa[A-Z]{2}[0-9]{4}6lỗi/60%, AB0001đạtthêm; snapshotcũgiữ7lỗi/mẫucũ. Mock/HTTP/SSR không thay browser/Excel thật. Không sửa backend/migration/dependency/.env/AI hoặc tiếp tục27B.

## QT-04A — backend pattern đã triển khai

`pattern` đúng một cột/config `{pattern,dialect:"re2-v1"}` đã triển khai xuyên API/engine/snapshot/persistence/history/JSON/XLSX/fingerprint. Parser grammar dương + RE2 fullmatch nguyên bản/case-sensitive; bỏ qua thiếu, không trim/normalize/sửa raw hoặc suy luận kiểu. PATTERN_MISMATCH tối đa một lỗi/rule/row. AI vẫn đúng ba loại ban đầu, frontend pattern chưa triển khai.

Migration0008 mở CHECK quality_rules/quality_violations, downgrade chặn rule/violation/snapshot kể cả run đạt, không xóa dữ liệu. Run mới quality-v5; run cũ/snapshot/hash rules-v1/v2 giữ nguyên. Pattern dùng rules-v2 exact pattern/dialect và giữ rule trùng, không so sánh tương đương khác engine. Report JSON schema1 không đổi; Excel lấy pattern/dialect từ snapshot, bảo vệ text/formula/giới hạn giữ nguyên.

Pin google-re21.1.20251105 từ wheel QT-04A0, max_mem8MiB/mẫu (không trần RAM process). Worker spawn riêng mỗi run, một phase/backend process, busy409 trước tạo run; deadline5s gồm startup/compile/work/IPC. Preflight422 trước tạo run khi >10rule hoặc value>4096code point/16KiB hoặc matchbytes lặp theo rule>50MiB; config1..512code point/2048byte pattern và16KiB JSON. Worker lỗi/timeout/cancel không lưu stats/violation bán phần. IPC file tạm tránh deadlock pipe; endpoint chờ thread, cleanup child/IPC/lock trong finally. Xem [hợp đồng engine](docs/QUALITY_ENGINE.md) và [benchmark](docs/experiments/pattern_qt04a_benchmark.json) về grammar/escape, mã lỗi và giới hạn còn lại.

Demo mới QT-04A Pattern RE2 Demo: dataset48/version52/rule35/run41,10/7/7/70.0000%, lỗi3,4,5,6,7,9,10; rawrecord8rỗng bỏ qua. CSV/đáp án viết trước và reportJSON/XLSX/verification ở backend/samples/pattern_qt04a* và dataset-48-run-41-report.*. HTTP có xác thực và đọc workbook bằng thư viện đã đối chiếu; chưa nghiệm thu mẫu pattern bằng trình duyệt/Excel thật. Dữ liệu và hash cũ đã đối chiếu không đổi; phiên tạm thu hồi. BC-01C7bước ghi nhận đạt theo xác nhận người dùng; ca nâng cao chưa thử giữ mở. Không frontend/.env/Gemini/27B.

Các mục QT-04A0/QT-00 bên dưới giữ lịch sử tại thời điểm thiết kế, không phủ định trạng thái QT-04A hiện hành ở trên.

## Giao diện Xuất báo cáo — BC-01B

Trong kết quả run completed, bấm **Xuất báo cáo** để mở modal chung: **Excel(.xlsx) mặc định**, JSON(.json) là lựa chọn kỹ thuật. Modal ghi runID/phiên bản/versionID/dataset đang mở; xuất **toàn bộ vi phạm**, không phụ thuộc filter/page, và không phải dữ liệu đã sửa. Chỉ bấm **Tải báo cáo** mới gửi GET; Hủy đóng, không ghi dữ liệu.

Giữ cookie/phiên và cơ chế tải hiện có; khóa tải lặp, đang tải khóa modal, lỗi giữ lựa chọn để thử lại thủ công. Excel vượt giới hạn hiển thị thông báo backend và cho chọn JSON, không tự tải thay. Client kiểm tra lỗi/MIME/filename/an toàn/vỏZIPhoặcJSON trước lưublob; đổi run/dataset hoặc hết phiên hủy cả body, chặn callbackcũ. Filenamefallback đúng run/extension, objectURL được thu hồi. Không đổi modal/dirtyguard các form khác; lựa chọn định dạng là tạm.

Kiểm tra cuối **build/TypeScript và9script frontend PASS**. Client thật4GET có xác thực chỉ đọc dataset28/run2và5, cảExcel/JSON, đúng4/2/3/50.0000%và4/0/0/0.0000%;7bảng nghiệp vụ không đổi. [Bằng chứng](docs/samples/bc01b_report_readonly.json). **BC-01C chưa nghiệm thu trình duyệt/mở Excel/LibreOffice**, xem7bước [UI_CHECKLIST](docs/UI_CHECKLIST.md). Backend8000/frontend5173/PostgreSQL giữ chạy, không restartbackend. Không backend/dependency/.env/schema/demo/Gemini/CSV/pattern/27B changes. Chi tiết [REPORT_SCHEMA](docs/REPORT_SCHEMA.md), [PROGRESS](docs/PROGRESS.md). Hoàn thành BC-01B và dừng.


## Xuất báo cáo Excel và JSON dễ đọc — BC-01A

Backend có GET `/api/datasets/{dataset_id}/runs/{run_id}/report.xlsx` cho đúng run completed, attachment XLSX ba sheet **Tổng quan / Chi tiết lỗi / Quy tắc đã áp dụng**. Dùng snapshot và toàn bộ violations đã lưu, không chạy engine hoặc theo bộ lọc/phân trang UI. Metadata ghi rõ tại thời điểm xuất; hỗ trợ đủ6loại, unique tổ hợp vẫn một dòng/violation. Header/filter/freeze/wrap/độ rộng cột có sẵn; raw values/config là JSON có cấu trúc, ô text chống công thức, giữ số0 đầu/Unicode/whitespace/precision. Tỷ lệ từ số lưu và Decimal, timestamp giữ offset.

JSON URL `/report` giữ schema1/kiểu dữ liệu/attachment, chỉ đổi indent2/UTF-8 tiếng Việt dễ đọc. Quyền/lỗi401/403/404/409/503 giữ luồng hiện có. XLSX vượt giới hạn ô/ký tự/dòng hoặc budget sẽ trả mã lỗi có hướng dẫn JSON, không cắt dữ liệu; app chỉ thêm XlsxWriter==3.2.9. Xem [hợp đồng/budget](docs/REPORT_SCHEMA.md) và [PROGRESS](docs/PROGRESS.md).

Kiểm thử cuối: **145passed/0failed/0skipped**, PostgreSQL riêng; pipcheck đạt. Một cảnh báo Starlette/httpx cũ và một503setup không tái hiện ở lượt chạy riêng/bộ cuối được ghi rõ trong PROGRESS.

File HTTP mẫu: [có lỗi28/2](backend/samples/bc01a/dataset-28-run-2-report.xlsx), [không lỗi28/5](backend/samples/bc01a/dataset-28-run-5-report.xlsx); cả5demo28/2,28/5,42/28,44/33,46/38 đã đối chiếu MIME/attachment/data và JSON logical hashes cũ,7bảng nghiệp vụ không đổi. Đã mở lại bằng **openpyxl trong venv reader riêng**, **chưa mở Excel/LibreOffice thủ công hoặc nghiệm thu browser**. Backend8000 nạp endpoint mới, frontend5173/PostgreSQL giữ chạy; không sửa frontend/schemaDB/.env/dữ liệu demo, không gọi Gemini/CSV/pattern/27B. Hoàn thành BC-01A và dừng.


## Giao diện allowed_values — QT-03B

Modal Tạo/Sửa quy tắc thủ công có **Thuộc tập giá trị cho phép**, chọn đúng một cột. Mỗi giá trị một ô riêng, thêm/xóa và giữ thứ tự; nạp sửa giữ nguyên case/space/newline. Không split dấu phẩy/newline hoặc trim, Enter trong ô không gửi form. Payload đúng `{"values":["NEW","DONE","HOLD"]}`. Client kiểm tra1..100chuỗi không trùng/rỗng/chỉ whitespace, <=256Unicode code point/1024byte UTF-8 mỗi chuỗi và <=16KiB config; backend xác thực cuối. Bỏ qua thiếu, cần required bắt thiếu; NULL chuỗi vẫn kiểm tra, không đổi dữ liệu gốc.

Danh sách/snapshot/lỗi hiển thị đủ tập dạng JSON có giữ khoảng trắng, nhãn “Giá trị không thuộc tập cho phép”, raw values/message backend và điều kiện từ snapshot. AI vẫn chỉ ba loại đầu, config AI không mở mảng. Giữ modal/draft khi lỗi/khóa gửi lặp/cookie-CSRF/session, không retry ghi hoặc tự chạy.

Kiểm tra cuối build/TypeScript và8script client/form/modal/AI/auth/report đều PASS; handler/SSR/mock không thay nghiệm thu trình duyệt. Client thật chỉ7GET demo **46/50/38**, khớp **10/5/5/50.0000%**, lỗi4/5/6/9/10, thiếu7/8skip;7bảng nghiệp vụ không đổi. [Bằng chứng chỉ đọc](docs/samples/allowed_values_qt03b_readonly.json). Không tạo dataset/rule/run hoặc sửa demo, không backend/migration/.env/dependency/Gemini changes. Frontend5173/backend8000/PostgreSQL giữ chạy.

**QT-03C chưa nghiệm thu:** [CSV](docs/samples/allowed_values_qt03c.csv), [đáp án viết trước](docs/samples/allowed_values_qt03c_expected.json) và8bước [UI_CHECKLIST](docs/UI_CHECKLIST.md). Dùng dataset mới, một rule bật: NEW,DONE,HOLD cho10/5/5/50.0000%; thêm chính xác new cho10/4/4/40.0000%, lỗi còn5/6/9/10; snapshot run cũ vẫn50.0000%. Chưa xác minh thao tác browser/modal/keyboard/network/session/CSRF thực; chưa pattern/27B. Hoàn thành QT-03B và dừng.


## Backend allowed_values — QT-03A

Quy tắc thủ công `allowed_values` kiểm tra đúng một cột với config `{"values":["NEW","DONE","HOLD"]}`. Danh sách 1..100 chuỗi, không trùng nguyên bản/rỗng/chỉ whitespace; mỗi chuỗi <=256 Unicode code point và <=1024 byte UTF-8, config <=16 KiB JSON UTF-8 gọn. Không khóa thừa/null/coercion. So sánh exact, phân biệt case/space/NFC/NFD, giữ thứ tự config khi lưu; không trim, chuẩn hóa hoặc sửa dữ liệu/suy luận kiểu. Bỏ qua thiếu hiện có (rỗng/whitespace/NULL JSON), chuỗi `"NULL"` vẫn kiểm tra; dùng required riêng để bắt thiếu.

Mỗi rule/bản ghi tối đa một `ALLOWED_VALUE_NOT_IN_SET`; message nêu tập mong đợi và gợi ý đối chiếu nguồn. Run mới `quality-v4`; lịch sử/report đọc snapshot và kết quả đã lưu, report schema1. Migration0007 mở cả hai CHECK và chặn downgrade khi còn rule/violation/snapshot loại mới, kể cả run đạt. Fingerprint allowed_values dùng rules-v2, sort bản sao values theo Unicode code point; giữ nguyên hash rules-v1/v2 cũ và số rule trùng. Nhóm so sánh phải cùng fingerprint **và** engine_version. AI vẫn chỉ required/unique/numeric_range. Chưa frontend allowed_values, pattern hoặc27B.

Kiểm thử cuối: **653passed/0failed/0skipped**, PostgreSQL thử riêng, pip check và alembic check đạt. Demo HTTP giữ **dataset46 — QT-03A Allowed Values Demo / version50 / rule33 / run38**, **10/5/5/50.0000%**, lỗi4/5/6/9/10; bỏ qua7/8. [Report](backend/samples/dataset-46-run-38-allowed-values-report.json), [bằng chứng](backend/samples/allowed_values_qt03a_verification.json).37run cũ và dữ liệu cũ7bảng không đổi. Backend8000 đã nạp quality-v4, frontend5173/PostgreSQL giữ chạy.

QT-02C: người dùng xác nhận đạt8bước trình duyệt. Không suy rộng xác nhận này thành PASS các tình huống mạng/phiên/CSRF chưa thử. Bằng chứng kiểm thử, demo và trạng thái server QT-03A ghi trong [PROGRESS](docs/PROGRESS.md). CSV/đáp án trước chạy: [CSV](backend/samples/allowed_values_qt03a.csv), [đáp án](backend/samples/allowed_values_qt03a_expected.json).


## Giao diện quy tắc date_format — QT-02B

Trong tab Quy tắc chất lượng → Tạo/Sửa, modal chung có **Ngày đúng định dạng**, chọn đúng một cột và format **YYYY-MM-DD — ví dụ2026-12-31**, **DD/MM/YYYY — ví dụ31/12/2026**, **MM/DD/YYYY — ví dụ12/31/2026**. Edit nạp đúng format; đổi loại reset cột/cấu hình, chỉ gửi `{"format":"..."}` khi chọn date_format. Form giải thích kiểm tra cả hình thức và ngày thật, không đoán ngày/tháng hoặc bỏ whitespace, bỏ qua thiếu/required riêng, không sửa/chuyển dữ liệu gốc.

Danh sách/snapshot hiển thị format rõ ràng; lỗi có nhãn **Sai định dạng ngày** hoặc **Ngày không tồn tại**, giữ message backend và raw value/JSON. Điều kiện lịch sử lấy snapshot của run, không rule hiện tại; thống kê giữ nguyên. AI vẫn chỉ ba loại ban đầu: không có lựa chọn/date draft/save mới. Giữ modal/accessibility, dirty/draft khi lỗi/busy/duplicate lock/cookie-CSRF/phiên và không tự retry ghi hoặc chạy kiểm tra.

Kiểm tra cuối: `npm.cmd run build` (TypeScript+Vite) và `node verify-date-format.mjs`, `verify-data-type.mjs`, `verify-ai.mjs`, `verify-modal.mjs`, `verify-business.mjs`, `verify-auth.mjs`, `node verify-report.mjs --mock-only` đều PASS, còn warning stripTypeScriptTypes cũ. Client thật chỉ7GET demo **44/48/33**, đúng **8/5/5/62.5000%**, mã VALUE_INVALID ở2/3/6 và FORMAT_MISMATCH ở4/5; đối chiếu snapshot/report/history/filter/rawrows. Checksum7bảng nghiệp vụ không đổi, không ghi demo. Phiên cục bộ tạm đã thu hồi, không lưu token. Đây là test handler/SSR/API, **chưa nghiệm thu trình duyệt QT-02C**.

[CSV QT-02C](docs/samples/date_format_qt02c.csv) và [đáp án viết trước](docs/samples/date_format_qt02c_expected.json) đã lưu trên ổ đĩa, gồm12bản ghi cho cả ba format/ngày mơ hồ/năm nhuận/whitespace/thiếu. Dùng dataset UI thử riêng, chỉ một rule đang bật: ISO **12/9/9/75.0000%**, DD/MM **12/7/7/58.3333%**, MM/DD **12/8/8/66.6667%**. Xem8bước [QT-02C](docs/UI_CHECKLIST.md); QT-02C sau đó đã đạt8bước theo xác nhận người dùng; mạng/phiên/CSRF chưa thử giữ chưa xác minh. Không sửa backend/migration/.env/dependency hoặc demo44, không gọi Gemini/loại tiếp theo/27B. Vite5173/backend8000/PostgreSQL tiếp tục chạy, không restart backend cho QT-02B.

## Backend quy tắc date_format — QT-02A

Backend thủ công hỗ trợ `date_format` từ POST/PATCH/GET rules qua engine, snapshot, persistence, history, report và fingerprint. Đúng một cột tồn tại; config chỉ `{"format":"YYYY-MM-DD"}`, `{"format":"DD/MM/YYYY"}` hoặc `{"format":"MM/DD/YYYY"}`, không khóa thừa/null/coercion; tối đa16KiB JSON UTF-8 gọn chỉ cho config này. Full match nguyên bản ASCII, đúng4chữ số năm/2tháng/2ngày và dấu phân cách, sau đó kiểm tra ngày Gregorian thật/năm nhuận, năm0001..9999. Không trim/đoán format/nhận datetime hoặc timezone. Thiếu vẫn bỏ qua theo định nghĩa cũ, muốn bắt thiếu thêm required; không đổi raw value hoặc suy luận kiểu.

Mã `DATE_FORMAT_MISMATCH` cho hình thức sai; `DATE_VALUE_INVALID` cho đúng hình thức nhưng ngày không tồn tại, tối đa một vi phạm/rule/bản ghi. Message nêu format snapshot mong đợi. Migration mới **0006** mở hai CHECK rule/violation; downgrade bị chặn nếu còn date_format ở rule/violation/run snapshot, kể cả run đạt không lỗi. Run mới **quality-v3**, giữ nguyên lịch sửv1/v2; phải kiểm tra không run running trước restart. Report schema1; giữ nguyên hash rules-v1 của ba loại đầu và rules-v2 của data_type; date_format dùng rules-v2, giữ đúng format và số bản sao rule. So sánh cần cả engine_version+fingerprint.

Mẫu [date_format_qt02a.csv](backend/samples/date_format_qt02a.csv) và [đáp án viết trước](backend/samples/date_format_qt02a_expected.json): **8 bản ghi /5 bản ghi lỗi /5 vi phạm /62.5000%**. Parser xác nhận bản ghi7 được quote thành một trường rỗng `""`, không bị bỏ. Chi tiết kết quả demo/test nằm trong PROGRESS. QT-02A không làm frontend date_format, không mở AI (vẫn ba loại ban đầu), không gọi Gemini hoặc triển khai loại kế tiếp/27B. Các phần QT-01A/B bên dưới là mốc lịch sử; engine hiện hành sau QT-02A là quality-v3.

Đã xác minh HTTP thật qua5173: **dataset44 — QT-02A Date Format Demo**, **version48/rule31/run33**; đúng toàn bộ đáp án5lỗi và snapshot/history/report/trend. [Report](backend/samples/dataset-44-run-33-date-format-report.json), [bằng chứng](backend/samples/date_format_qt02a_verification.json). Đọc lại32run cũ, fingerprint cũ và checksum7bảng theo ID cũ không đổi. Kiểm thử cuối **611passed/0failed/0skipped**, pip check đạt, alembic check đạt, app **0006head**. Server backend đã restart sau hai lần kiểm tra không run running; frontend/backend/PostgreSQL tiếp tục chạy. Chưa nghiệm thu frontend ngày; QT-01C data_type đạt8bước theo xác nhận người dùng, ghi tại PROGRESS.

## Giao diện quy tắc data_type — QT-01B

Tại chi tiết dataset → **Quy tắc chất lượng** → **Tạo quy tắc/Sửa**, modal chung hỗ trợ **Đúng kiểu dữ liệu**, chọn một cột và kiểu yêu cầu **Số nguyên / Số thập phân / Boolean**. Khi sửa nạp đúng config; đổi loại reset cột và cấu hình, chỉ gửi `{type:...}`, `{min,max}` hoặc `{}` theo loại đang chọn. Giữ khóa gửi lặp, draft khi lỗi, dirty/busy, cookie/CSRF và xử lý phiên; không tự chạy kiểm tra hoặc retry POST/PATCH.

Giải thích ngay trong form: integer nhận dấu +/- và số0đầu nhưng không nhận1.0; decimal hữu hạn nhận ký pháp khoa học, không kiểm tra số chữ số thập phân; boolean chỉ true/false viết thường. Bỏ qua thiếu (dùng required để bắt thiếu), kiểm tra nguyên bản không bỏ whitespace ngoài. Đây là điều kiện kiểm tra, không đổi dữ liệu gốc hay kiểu suy luận. Danh sách rule và snapshot hiện nhãn tiếng Việt; từng lỗi hiển thị điều kiện từ snapshot của run, giá trị nguyên bản/JSON, thông điệp và mã. Thống kê/tỷ lệ giữ nguyên.

AI có AIRuleType/AIRuleInput riêng chỉ ba loại cũ; form draft không có data_type, phản hồi trộn loại ngoài phạm vi bị từ chối toàn bộ trước hiển thị, tạo draft/lưu cũng có guard. Không đổi backend/provider hoặc gọi Gemini. Kiểm thử cuối: `npm.cmd run build` (gồm TypeScript), `node verify-data-type.mjs`, `verify-ai.mjs`, `verify-modal.mjs`, `verify-business.mjs`, `verify-auth.mjs`, `node verify-report.mjs --mock-only` đều đạt; còn warning stripTypeScriptTypes đã có.

API client thật chỉ GET dataset42/version46/run28 đã khớp **10 bản ghi /4 bản ghi lỗi /11 vi phạm /40.0000%**, snapshot/report và nguyên bản10rows. Checksum bảy bảng nghiệp vụ không đổi; không tạo rule/run hoặc sửa demo. Phiên xác thực cục bộ tạm đã thu hồi, token chỉ ở bộ nhớ. Test form dùng handler/hook harness và SSR, **chưa nghiệm thu thao tác trình duyệt**; checklist [QT-01C](docs/UI_CHECKLIST.md) dùng dataset thử riêng cho mọi bước ghi. Frontend5173 và backend8000 tiếp tục chạy, không restart backend cho QT-01B.

## Backend quy tắc data_type — QT-01A

Backend hỗ trợ quy tắc thủ công `data_type` xuyên suốt API → engine → lưu kết quả → lịch sử → báo cáo → fingerprint. Chạy `alembic upgrade head` từ backend trước khi dùng; kiểm tra không còn run `running` trước nâng mã/restart, không tự sửa trạng thái hoặc hoàn tất run bằng engine khác. Run tại mốc QT-01A dùng `quality-v2`, sau QT-02A dùng `quality-v3`; lịch sử và snapshot cũ giữ nguyên. Sau QT-01B, form frontend đã mở loại này như phần trên; AI vẫn chỉ đề xuất `required`, `unique`, `numeric_range`, draft mặc định tắt và cần người dùng duyệt.

Qua API đã xác thực, tạo rule bằng POST `/api/datasets/{dataset_id}/rules` (cookie phiên, Origin hợp lệ và `X-CSRF-Token`):

```json
{"name":"Kiểm tra integer","rule_type":"data_type","columns":["integer_value"],"config":{"type":"integer"},"is_active":true}
```

Đúng một cột tồn tại; config chỉ nhận `{"type":"integer"}`, `{"type":"decimal"}` hoặc `{"type":"boolean"}`, không khóa thừa/null/chuyển kiểu. Config mới tối đa 16 KiB JSON UTF-8 dạng gọn; sai config trả 422/`INVALID_CONFIG`, không áp budget này lên loại cũ. Giá trị được full match nguyên bản, không trim/cast; thiếu được bỏ qua, muốn bắt thiếu cần `required`. Integer nhận `0012`, `+12`, `-0` theo ASCII; decimal hữu hạn nhận `.5`, `1.`, `1e3`, không kiểm tra precision/scale; boolean chỉ chuỗi `true`/`false`. Lỗi biểu diễn Decimal thành vi phạm có kiểm soát. Các mã lỗi: `DATA_TYPE_INTEGER_INVALID`, `DATA_TYPE_DECIMAL_INVALID`, `DATA_TYPE_BOOLEAN_INVALID`.

Kiểm tra kiểu theo rule khác suy luận kiểu metadata: không tự tạo rule từ inferred types; integer nhận số 0 đầu không chứng minh cột là số nghiệp vụ. Ngữ nghĩa `numeric_range` và dữ liệu gốc giữ nguyên. Chi tiết tại [QUALITY_ENGINE.md](docs/QUALITY_ENGINE.md).

Mẫu nghiệm thu riêng: [data_type_qt01a.csv](backend/samples/data_type_qt01a.csv), ba cột `integer_value`, `decimal_value`, `boolean_value`; [đáp án viết trước khi chạy](backend/samples/data_type_qt01a_expected.json). **HTTP thật qua proxy 5173 đã xác minh** dataset **42 — QT-01A Data Type Demo**, version **46**, run **28**, rules **25/26/27**: **10 bản ghi, 4 bản ghi lỗi, 11 vi phạm, 40.0000%**, quality-v2. Toàn bộ lỗi/giá trị nguyên bản/snapshot/report và fingerprint rules-v2 khớp đáp án. Giữ demo; [report đã xuất](backend/samples/dataset-42-run-28-data-type-report.json), [bằng chứng đối chiếu](backend/samples/data_type_qt01a_verification.json). Phiên admin cục bộ tạm chỉ giữ token trong bộ nhớ và đã thu hồi; không lưu mật khẩu/token. Đọc lại 27 run cũ và checksum bảy bảng nghiệp vụ xác nhận dữ liệu có sẵn không đổi. Đây là nghiệm thu API backend, chưa nghiệm thu UI data_type.

Kiểm thử cuối QT-01A: **449 passed, 0 failed, 0 skipped**, một cảnh báo TestClient/httpx đã có; `pip check` đạt, `alembic check` không có thay đổi schema chưa ghi migration; database ở **0005 (head)**. Chi tiết phạm vi/lệnh tại [PROGRESS.md](docs/PROGRESS.md). Backend đã restart sau kiểm tra không có run running; frontend 5173/backend 8000/PostgreSQL giữ chạy. Không gọi Gemini hoặc triển khai loại kế tiếp/27B.

## API xu hướng chất lượng — 27A

GET `/api/datasets/{dataset_id}/quality-trend?limit=30&version_id=...` dành admin/data_steward. limit1..100 (mặc định30),version_id tùy chọn phải thuộc dataset. Chỉ lấy completed mới nhất started_at/id giảm dần,sau đó trả points theo thời gian/id tăng dần. Có total_completed/truncated;không lịch sử thì points rỗng,không giả100%.

Điểm trả thống kê/tỷ lệ4 chữ số dạng chuỗi,pass_rate tính Decimal từ100-error_row_rate,rule_count vàfingerprint snapshot. QT-01A giữ nguyên hash `rules-v1` cho snapshot chỉ chứa ba loại cũ; snapshot có `data_type` dùng `rules-v2`, giữ subtype và số bản sao rule trùng. Nhận diện cùng cấu hình phải dùng cả engine_version vàfingerprint;không đánh dấu tương đương nếu engine khác,không suy ra ý nghĩa nghiệp vụ hoặc dữ liệu khác phiên bản tương đương. Chi tiết tại docs/QUALITY_TREND.md. Endpoint xu hướng không chạy engine/Gemini;frontend biểu đồ chưa triển khai.

## Giao diện duyệt AI — 26G

Mở dataset → chọn phiên bản → tab Quy tắc → **AI gợi ý quy tắc**. Chọn1..30 cột,bật/tắt gửi mô tả/thống kê rồi Xem trước payload. Giao diện hiển thị đầy đủ JSON vàprovider/model từ API,không hardcode model hoặc hiển thị key. Không gửi dữ liệu từng dòng/giá trị mẫu;metadata cũng có thể nhạy cảm. Phải xác nhận payload trước khi gửi Gemini;đổi lựa chọn làm mất preview cũ. Hết hạn/thay snapshot/model409 yêu cầu xem vàxác nhận lại,không gọi lại tự động.

Không gọi AI khi mở tab. Khi chờ chỉ hiện loading,khóa gửi lặp;quota/timeout/chưa cấu hình hiển thị lỗi thật.0 đề xuất nghĩa là chưa có đề xuất đủ căn cứ,không phải dữ liệu đã đạt;form tạo quy tắc thủ công vẫn có. Đổi dataset/version/logout hủy request vàbỏ draft AI;response cũ không cập nhật phiên mới.

Mỗi draft hiển thị loại/cột/config,lý do/giả định vàdùng cùng RuleForm với tạo thủ công. Phải tick từng giả định trước lưu;is_active mặc địnhfalse,người dùng chủ động bật nếu muốn. Lưu riêng qua POST rules,min/max giữ chuỗi;thành công ghi rule_id vàkhóa lưu lại draft. Lỗi lưu giữ trạng thái chưa xác nhận,có Tải lại danh sách để đối chiếu rồi mới cho phép thử thủ công. Không tự chạy kiểm tra hoặc sửa dữ liệu.

Kiểm tra26G: npm.cmd run build (gồm TypeScript),node verify-ai.mjs,verify-business.mjs,verify-auth.mjs. Mock chỉ trong test,không fallback runtime. **Provider thật mới xác minh nhánh0 đề xuất ở26F;nhánh có đề xuất mới kiểm tra bằng mock,chưa nghiệm thu Gemini thật.** Chưa có trình duyệt để xác minh UI;checklist26G trong docs/UI_CHECKLIST.md,các mục nâng cao25A/25D còn mở giữ nguyên.

## Adapter Gemini — 26E (test không mạng đã có, chưa smoke thật)

Gemini là provider duy nhất,SDK chính thức google-genai==2.31.0 (Python>=3.10,dự án3.11.9),requirements khóa cả dependency gián tiếp. Cài bằng backend/.venv và `python -m pip install -r requirements.txt` từ backend.

Cấu hình trực tiếp trên máy trong backend/.env: GEMINI_API_KEY là key riêng của bạn;GEMINI_MODEL là ID model cụ thể. Lượt26E không đọc/in key vào báo cáo và không ghi đè.env. Model đề xuất từ tài liệu chính thức: `gemini-3.5-flash-lite` (https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite). Không có mặc định;thiếu key/model hoặc alias latest trả503 AI_NOT_CONFIGURED,không tự đổi model/fallback. Giữ AI_PREVIEW_SECRET riêng cho consent. Restart backend sau đổi cấu hình/mã để nạp môi trường mới.

Preview hiển thị provider/model đã cấu hình và token bind target;đổi model/cấu hình sau preview yêu cầu xem lại409,token cũ thiếu target cũng cần preview mới. Endpoint điều phối chỉ gửi payload đã xác nhận,không raw rows/owner/filename/session/token;fixed system instructions,structured JSON,không tools/search/code/URL context/streaming/retry. Output qua validator26B,không tự lưu rule/chạy kiểm tra. Deadline20s/connect5s,HTTPX async cancellation/close thật,response envelope<=64KiB/generated JSON<=16KiB/output token2000. Quota demo26D không phải trần chi phí cứng.

Chưa chạy nhà cung cấp thật. Sau khi chốt ngân sách và quyền model,có thể chủ động chạy từ backend: `.\.venv\Scripts\python.exe scripts/gemini_smoke.py --allow-provider-call`. Script chỉ gửi metadata tổng hợp vô hại cố định,không đọc DB;đây là một call có thể tính phí và không đi qua quota runtime. Không chạy trong pytest. Không gửi key vào chat/log;script chỉ in model/số đề xuất hoặc mã lỗi. Chính sách metadata/model access/chi phí/độ trễ thật chưa xác minh. Chức năng tạo rule thủ công vẫn chạy khi AI lỗi/chưa cấu hình.

## API điều phối đề xuất AI — 26D (chưa bật nhà cung cấp)

POST `/api/datasets/{dataset_id}/ai-rule-suggestions` nhận `{version_id,preview_token,confirmed:true}` sau preview26C. Hai role nghiệp vụ dùng phiên hợp lệ/Origin/CSRF;token phải đúng user/phiên/dataset/version/hạn/hash payload. Input/token hoặc xác nhận sai không gọi adapter. Response có request_id,no-store;kết quả qua validator26B,kiểm tra lại phiên trước trả. Không tự lưu rule/chạy kiểm tra hoặc sửa dữ liệu.

Runtime26D chưa có provider adapter:request hợp lệ trả **503 AI_NOT_CONFIGURED** thật. Không fake fallback,không cần/cài SDK,không gọi mạng;không dùng API key để tự bật. Chức năng rule thủ công giữ nguyên. Không thay backend/.env.

Giới hạn demo một process:1 active call/user,5 lượt/user/10 phút,20 lượt/toàn ứng dụng/ngày UTC;reserve atomic,tính cả lỗi và timeout,429/Retry-After. Có cleanup/cap bộ nhớ;restart mất quota,không phải trần chi phí cứng. Deadline20s,connect budget5s/output token2000 giao qua Limits;raw output<=16KiB/5 đề xuất do validator kiểm tra. Adapter tương lai phải tự giới hạn đọc mạng/connect/token. Timeout không auto retry;slot giữ đến khi task thực sự dừng. Thiết kế và giới hạn tại docs/AI_DESIGN.md.

## AI preview — 26C (chưa gọi AI)

POST `/api/datasets/{dataset_id}/ai-rule-suggestions/preview` nhận `{version_id,columns,include_descriptions,include_statistics}`. Admin/data_steward dùng cookie phiên,Origin allowlist và X-CSRF-Token phiên. Trả payload chính xác để xem trước,preview_token và expires_at sau5 phút;Cache-Control:no-store. Chưa có frontend/provider adapter;endpoint điều phối26D chưa bật nhà cung cấp;provider/model trả null với provider_status=not_configured.

Bổ sung cấu hình mẫu `AI_PREVIEW_SECRET` trong backend/.env.example. Người vận hành tự provision secret hex riêng ổn định32–128byte ở backend,khác AUTH_CSRF_SECRET;không gửi secret vào chat/log hoặc commit. Lượt26C không sửa backend/.env;thiếu/sai cấu hình preview503 AI_PREVIEW_NOT_CONFIGURED,API thủ công vẫn hoạt động. Không sinh secret mỗi request/import. Token không chứa metadata/token phiên gốc,không log token/payload.

Preview giới hạn body8KiB,payload32KiB và10 lượt/user/phút;429 kèm Retry-After. Limiter bộ nhớ có cleanup/cap10000 user,phù hợp một process,mất khi restart;chưa có quota provider. Helper confirm_preview kiểm tra chữ ký/ngữ cảnh/phiên/hạn và hash snapshot dựng lại;409 yêu cầu xem lại khi nội dung gửi thay đổi. Không tự gửi lại,không ghi rule/run. Chi tiết và giới hạn tại docs/AI_DESIGN.md.

## Giao diện quản lý tài khoản — 25C

Đăng nhập admin, chọn **Quản lý tài khoản** hoặc mở `http://127.0.0.1:5173/#admin/users`. Trang độc lập với dataset. data_steward không có liên kết; mở URL trực tiếp hiện không đủ quyền và không tải API admin. Backend vẫn quyết định quyền.

Danh sách phân trang20 tài khoản theo API, nhãn vai trò tiếng Việt, trạng thái/ngày tạo/thao tác; có tải/trống/lỗi/thử lại. Tạo tài khoản trong modal: username, mật khẩu/xác nhận và vai trò mặc định Người phụ trách dữ liệu. Mật khẩu giữ nguyên khoảng trắng, hiện/ẩn theo lựa chọn; đóng/thành công bỏ state mật khẩu, không web storage/log. Gửi/đóng khóa trong lúc tạo, không tự POST retry; khi mất kết nối phải kiểm tra danh sách trước tạo lại.

Sửa chỉ role/is_active; đổi role hoặc vô hiệu hóa yêu cầu xác nhận thu hồi mọi phiên. Tài khoản hiện tại có giải thích không được tự khóa/hạ quyền. Backend quyết định bảo vệ admin cuối cùng, giao diện không suy đoán từ trang danh sách. Không PATCH khi không đổi; chỉ cập nhật sau response thành công, không retry/replay ghi. Danh sách/form tách theo tài khoản/role, unmount hủy request; helper chung chặn phản hồi của phiên cũ. CSRF403/503 không giả logout.

Kiểm tra: `npm.cmd run build` (gồm TypeScript), `node verify-admin.mjs`, `node verify-business.mjs`, `node verify-auth.mjs`. Test admin dùng mock response, không tạo tài khoản thật. Chưa kiểm thử UI trình duyệt; xem checklist25C và giữ các mụcUI25A còn mở.

## API quản lý tài khoản — 25B

Chỉ admin có phiên hợp lệ dùng được GET/POST `/api/admin/users` và PATCH `/api/admin/users/{user_id}`. Chưa đăng nhập401; data_steward403. POST/PATCH gửi cookie phiên, Origin allowlist và X-CSRF-Token phiên; không dùng CSRF pre-auth. Giao diện quản lý tài khoản đã có ở25C; chưa đăng ký công khai.

POST nhận username/password/role(admin hoặc data_steward), tự active=true;201 hoặc409 nếu username trùng sau strip/lowercase. Dùng cùng quy tắc username/mật khẩu và Argon2id của CLI. Không ghi mật khẩu vào tài liệu/log hoặc gửi vào chat. GET phân trang page=1/page_size=20 (tối đa100), id tăng dần, trả items/total/page/page_size. User trả về chỉ id,username,role,is_active,created_at,updated_at; không hash/token/session.

PATCH chỉ role/is_active; từ chối trường dư, null và body rỗng422; không có user404. Tự hạ quyền/vô hiệu hóa hoặc loại bỏ admin active cuối cùng409. Các thay đổi dùng cùng transaction/advisory lock với bootstrap, kiểm tra lại quyền sau khi chờ khóa. Đổi role/khóa user thu hồi mọi phiên nguyên tử; bật lại không phục hồi phiên cũ; PATCH không đổi giá trị giữ nguyên phiên. DB lỗi503 chung. Không migration mới, không tài khoản mặc định. UI25A còn mở trong docs/UI_CHECKLIST.md.

## Kiểm soát truy cập — 25A (trạng thái hiện tại)

Tất cả API dataset/rows/import/metadata/rules/runs/history/violations/report đã yêu cầu phiên hợp lệ; admin và data_steward có cùng quyền nghiệp vụ theo [ACCESS_CONTROL.md](docs/ACCESS_CONTROL.md). API ghi yêu cầu Origin allowlist và X-CSRF-Token phiên; pre-auth CSRF bị từ chối. Health vẫn công khai. Các câu “API nghiệp vụ chưa bảo vệ” trong mô tả24 bên dưới là trạng thái lịch sử, đã được thay thế bởi25A.

Website tự gửi cookie/CSRF trong bộ nhớ;401 về login,403 CSRF có Kiểm tra lại phiên rồi thử thủ công,503 không giả logout. Không tự phát lại upload/PATCH/run sau login. Các lệnh PowerShell GET nghiệp vụ cũ cần cookie jar đăng nhập trước, không còn truy cập ẩn danh. Khi cập nhật mã25A, restart backend đang không reload để nạp bảo vệ; không tạo admin mặc định. API quản lý tài khoản25B đã có, không owner/tenant.

## Đăng nhập trên website — 24E

Tự tạo admin bằng terminal tương tác, không gửi mật khẩu vào chat:

```powershell
cd D:\UserFile\DNCN\Webb\backend
.\.venv\Scripts\python.exe -m app.cli.create_admin
```

CLI chỉ tạo admin đầu tiên, không phục hồi admin có sẵn. Chạy PostgreSQL/backend/frontend theo các phần dưới; mở http://127.0.0.1:5173/, nhập thông tin bạn vừa tạo. Reload khôi phục phiên bằng /auth/me; navbar hiển thị username/vai trò/Đăng xuất. CSRF chỉ trong bộ nhớ, password giữ nguyên khi gửi, không token/password trong localStorage/sessionStorage. Phiên tới hạn được kiểm tra lại; không tự gửi lại login/logout hoặc thao tác nghiệp vụ. Lỗi mạng/503: kiểm tra lại phiên trước khi thao tác lại. CSRF403 lấy challenge mới để gửi thủ công,429 nêu số giây chờ.

Logout thành công tháo state nghiệp vụ, giữ hash dataset nội bộ để mở lại sau login. Chưa có redirect ngoài hệ thống. **Đây chỉ là chặn giao diện; API nghiệp vụ chưa được bảo vệ ở24.** Chưa gắn CSRF vào client nghiệp vụ (hạng mục25). UI24E chưa được kiểm thử trình duyệt; không có tài khoản demo mặc định.

## API auth độc lập — 24D

Đã có GET `/api/auth/me`, POST `/api/auth/login`, POST `/api/auth/logout`; mọi response auth no-store. Khởi động lại backend sau cập nhật mã. Local.env được bổ sung các khóa auth còn thiếu, không thay giá trị cấu hình có sẵn; giữ secret riêng, không commit/in ra log. Muốn tạo admin thật, tự dùng CLI bên dưới trong terminal; chưa có frontend đăng nhập.

Qua Vite proxy: GET `/api/auth/me` chưa đăng nhập trả401, csrf_token và cookie challenge (tái dùng15 phút). POST login JSON username/password cùng Origin `http://127.0.0.1:5173` và X-CSRF-Token; browser cookie được gửi same-origin. Thành công nhận user/expires_at/csrf_token và cookie phiên HttpOnly/Lax/host-only/Path=/api, expiry8 giờ. GET me không kéo dài hạn; logout gửi Origin/header token hiện tại, thu hồi server và xóa cookie,204. Không có phiên chỉ logout204 với pre-auth challenge hợp lệ. Không lưu session token trong web storage hoặc gửi nó qua JSON.

Limiter local một process:20 attempts/IP và5/cặpIP-username trong10 phút, tính thành công/lỗi,429 Retry-After trước verify Argon2. Không tin X-Forwarded-For. Giới hạn mất khi restart/không chia sẻ nhiều worker, peer IP qua proxy có thể chung127.0.0.1; chưa phù hợp hosting công khai. HTTP auth qua proxy đã kiểm thử bằng cookie jar trên database riêng, không phải trình duyệt. **API nghiệp vụ vẫn chưa được bảo vệ**, chưa quyền/CSRF cho dataset/rules/runs/report (hạng mục25).

## Bootstrap admin cục bộ — 24B

Mở Docker Desktop/PostgreSQL, chạy trong PowerShell tương tác:

```powershell
cd D:\UserFile\DNCN\Webb\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli.create_admin
```

CLI hỏi username, mật khẩu và xác nhận bằng nhập ẩn; không truyền password qua tham số hoặc gửi vào cuộc trò chuyện. Username ASCII3–64 ký tự, strip/lowercase; mật khẩu12–128 ký tự giữ nguyên khoảng trắng. Dùng terminal hỗ trợ getpass; nếu không thể nhập ẩn, lệnh từ chối. Không có tài khoản/mật khẩu mặc định.

Chỉ tạo admin đầu tiên: PostgreSQL transaction advisory lock tuần tự hóa các tiến trình, kiểm tra cả admin đã vô hiệu hóa; đây không phải lệnh phục hồi. Argon2id t3/m65536KiB/p4. Schema auth revision0004; không tạo admin thử trong database ứng dụng. **Chưa có login/logout/me và API nghiệp vụ vẫn chưa được bảo vệ**, chưa frontend auth/CSRF/rate limit.

## Xuất báo cáo JSON — 23A

### Tải từ giao diện — 23B

Mở dataset → Kiểm tra & lịch sử → mở một lần chạy completed → **Tải báo cáo JSON** cạnh tiêu đề kết quả. Nút tải đúng dataset/run đang xem (kể cả lịch sử phiên bản cũ), chỉ xuất JSON. Request lỗi hiển thị gần nút, có thể bấm lại thủ công; không tải response lỗi thành file. Đổi run/dataset trước khi phản hồi về sẽ hủy tải cũ. Frontend gọi qua `/api` Vite proxy, không thêm dependency. Thao tác tải file trên trình duyệt còn chờ xác minh; client/HTTP/build đã kiểm tra.

Sau khi khởi động lại backend để nạp mã mới, tải báo cáo completed qua Swagger hoặc PowerShell:

```powershell
Invoke-WebRequest 'http://127.0.0.1:8000/api/datasets/28/runs/2/report' -OutFile '.\dataset-28-run-2-report.json'
Invoke-WebRequest 'http://127.0.0.1:8000/api/datasets/28/runs/5/report' -OutFile '.\dataset-28-run-5-report.json'
```

Schema1 gồm metadata dataset hiện tại khi xuất (không phải snapshot lúc chạy), version/run, snapshot quy tắc và toàn bộ lỗi. Tỷ lệ lỗi là chuỗi4 chữ số; tên rule lấy từ snapshot. Run chưa completed trả409; sai quan hệ404, DB unavailable503. Báo cáo không chạy lại engine hoặc sửa dữ liệu. Chi tiết: [REPORT_SCHEMA.md](docs/REPORT_SCHEMA.md). Chưa có nút frontend; HTTP đã xác minh riêng cổng8001, server kiểm tra đã dừng. Backend8000 đang chạy cần restart nếu không reload.

## Suy luận kiểu theo phiên bản — 22B

Cả tạo dataset và nhập phiên bản mới đều suy luận tất cả bản ghi sau parse, trước transaction/khóa cấp số phiên bản. `inferred_types` lưu riêng phiên bản, GET chi tiết đọc kết quả đã lưu; không đổi chuỗi CSV hoặc tự tạo quy tắc. Tab Tổng quan hiển thị kiểu tiếng Việt theo phiên bản đang chọn và chi tiết số giá trị thiếu/không thiếu. Đây chỉ là gợi ý. Phiên bản cũ `[]` vẫn Chưa suy luận; unknown là Chưa xác định, không tự backfill.

Dataset thử giữ lại: **38 — Type Inference Demo 22B**; phiên bản1 ID40 có code=text, amount=integer, empty=unknown; phiên bản2 ID41 có amount=decimal. Demo28 không bị sửa. Đổi phiên bản trong Tổng quan để đối chiếu. UI22B chưa được kiểm thử trình duyệt; AC-04 còn chờ xác nhận UI.

Sau cập nhật mã, khởi động lại backend của bạn nếu process hiện tại chạy không có `--reload`, bằng Ctrl+C rồi lệnh Uvicorn ở dưới. HTTP22B đã xác minh trên server riêng cổng8001 và đã dừng server đó; không dừng backend đang có ở8000.

Backend FastAPI cung cấp `GET /api/health`: HTTP 200 với `{"status":"ok"}`, kể cả khi database không hoạt động. `GET /api/health/db` chạy `SELECT 1`: thành công trả HTTP 200 với `{"status":"ok","database":"ok"}`; không kết nối được trả HTTP 503 với `{"status":"error","database":"unavailable"}`, không gửi thông tin kết nối hoặc exception cho client.

## Chuẩn bị PostgreSQL cục bộ

Docker Desktop và Compose đã hoạt động. `compose.yaml` chạy PostgreSQL **17.11-bookworm**, bind `127.0.0.1`, có healthcheck và volume `webb_postgres_data` lưu dữ liệu. Kết nối thật đã được xác minh qua backend và HTTP.

Nếu dùng PostgreSQL có sẵn, lấy thông tin database/tài khoản từ cấu hình của bạn, không thay đổi dịch vụ dùng chung. Nếu dùng Docker, hãy mở Docker Desktop và chờ engine hoạt động, rồi kiểm tra trong PowerShell:

```powershell
docker version
docker compose version
```

Từ thư mục gốc, chuẩn bị cấu hình:

```powershell
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
notepad backend/.env
```

Trong môi trường hiện tại, `backend/.env` đã được tạo với mật khẩu cục bộ sinh ngẫu nhiên; giữ nguyên file để dùng database đã khởi tạo. Khi thiết lập ở máy khác, thay giá trị minh họa bằng cấu hình cục bộ. `DATABASE_URL` dùng dạng `postgresql+psycopg://USER:PASSWORD@127.0.0.1:PORT/DATABASE`; ký tự đặc biệt trong user/password cần URL encode. Các biến `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` phải khớp URL. Không commit `.env` hoặc ghi thông tin đăng nhập thật vào log.

Khởi chạy PostgreSQL riêng bằng Compose từ thư mục gốc. Nếu cổng 5432 đã được dùng, chọn `POSTGRES_PORT` khác và cập nhật cổng trong URL tương ứng:

```powershell
docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env up -d --wait --wait-timeout 120
docker compose --env-file backend/.env ps
```

Healthcheck tự dùng user/database trong container. Dùng `config --quiet` để kiểm tra mà không in thông tin đăng nhập. Có thể dừng riêng dịch vụ bằng `docker compose --env-file backend/.env stop`, rồi dùng lệnh `up` để chạy lại. Không xóa volume. Đổi biến khởi tạo không đổi tài khoản của volume đã có. Tham khảo [image PostgreSQL chính thức](https://hub.docker.com/_/postgres).

## Chạy trên Windows bằng PowerShell

Môi trường đã dùng: Python **3.11.9**. Cài Python phiên bản này và bảo đảm lệnh `python` có trong PATH. Từ thư mục gốc dự án:

```powershell
python --version
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Không cần kích hoạt môi trường ảo; các lệnh gọi trực tiếp Python trong `.venv`, không cài thư viện toàn cục. `requirements.txt` khóa cả dependency trực tiếp và phụ thuộc gián tiếp của môi trường đã kiểm tra.

Ứng dụng đọc **`backend/.env`** theo đường dẫn tính từ `app/config.py`, độc lập thư mục chạy. Biến môi trường của process được ưu tiên hơn `.env`. Không có URL hoặc URL không hợp lệ thì health database trả 503; ứng dụng vẫn khởi động. Chỉ hỗ trợ driver `postgresql+psycopg` đồng bộ với [SQLAlchemy/psycopg](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg). Mỗi kiểm tra dùng connection riêng, đóng qua context manager và dispose engine; timeout kết nối 3 giây, timeout câu SQL 3.000 ms.

Mở `http://127.0.0.1:8000/docs` để xem Swagger UI và endpoint health. Dừng server bằng Ctrl+C.

Trong cửa sổ PowerShell khác, kiểm tra HTTP:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health | Select-Object StatusCode, Content
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health/db | Select-Object StatusCode, Content
```

## Nhập CSV tạo bộ dữ liệu mới

Khởi chạy PostgreSQL, chạy migration và backend như hướng dẫn trên. Mở `http://127.0.0.1:8000/docs`, chọn **POST /api/datasets/import → Try it out**:

1. Chọn file `backend/samples/import_demo.csv` trong trường `file`.
2. Nhập `name` (bắt buộc, không chỉ có khoảng trắng); `description`, `source`, `owner` tùy chọn.
3. Nhấn Execute. HTTP 201 trả dataset_id, version_id, version_number=1, name, column_count, row_count.

Chỉ chấp nhận đuôi `.csv` không phân biệt hoa/thường; nội dung vẫn được xác thực bằng parser. Lỗi trả `{ "error": { "code": "...", "message": "...", "row_number": null } }`; 413 khi vượt 5 MiB, 422 khi metadata/CSV không hợp lệ, 503 khi mất kết nối database, 500 khi lỗi ghi khác. Trường bắt buộc bị thiếu dùng phản hồi validation 422 mặc định FastAPI (`detail`).

Endpoint chỉ đọc tối đa 5 MiB + 1 byte từ UploadFile và đóng file sau xử lý. Framework multipart có thể spool upload ra file tạm trước khi endpoint chạy; đây chưa phải giới hạn tổng request ở tầng mạng. Không lưu CSV gốc lâu dài, chỉ lưu basename làm metadata. Các bản ghi ghi theo lô 1.000 trong một transaction; toàn bộ nội dung được parse trước khi ghi. `inferred_types=[]` nghĩa là **chưa suy luận**, không gán kiểu giả.

Bộ dữ liệu demo đã giữ trong PostgreSQL ứng dụng: **Demo CSV 07**, dataset_id **17**, version_id **17**, phiên bản **1**, **3 cột / 2 bản ghi**. CSV có số 0 đầu, Unicode, chuỗi NULL, khoảng trắng và multiline. Có thể xem qua các API đọc bên dưới. Upload lại tạo dataset mới, chưa nhập phiên bản tiếp theo.

## Đọc danh mục và dữ liệu

Thử trong Swagger `/docs` hoặc PowerShell:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/datasets?page=1&page_size=20'
Invoke-RestMethod 'http://127.0.0.1:8000/api/datasets/17'
Invoke-RestMethod 'http://127.0.0.1:8000/api/datasets/17/versions/17/rows?page=1&page_size=1'
```

Danh sách trả items/total/page/page_size; mỗi item có metadata và version_count, sắp xếp created_at giảm dần rồi id giảm dần. Chi tiết trả metadata, columns theo position và versions theo version_number giảm dần, không nhúng bản ghi.

API rows trả header theo thứ tự cột, items gồm row_number/values và total/page/page_size. Phân trang dùng LIMIT/OFFSET tại PostgreSQL; page mặc định 1, page_size mặc định 20, tối đa 100. Trang vượt dữ liệu có items rỗng, total đúng. Không tồn tại hoặc version thuộc dataset khác trả 404; phân trang sai trả 422; mất kết nối database trả 503, không lộ SQL/cấu hình.

Đã đọc Demo CSV 07 qua HTTP thật, đối chiếu giá trị gốc và không sửa/xóa dữ liệu demo.

## Migration và kiểm tra model PostgreSQL

Sau khi PostgreSQL healthy và dependency đã cài, từ `backend`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

Migration đầu tiên `0001_csv_storage.py` tạo bốn bảng lưu CSV; chạy lại `upgrade head` an toàn. Alembic đọc cùng DATABASE_URL và đường dẫn `.env` với backend. Không dùng `create_all`. Quy trình theo [tài liệu Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

Kiểm tra PostgreSQL thật (ngoài các test health/mock):

```powershell
$env:RUN_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:RUN_POSTGRES_TESTS
```

Dữ liệu mẫu trong database ứng dụng được rollback. Test migration tạo database riêng tên `webb_migration_test_<uuid>`, thử upgrade/downgrade/upgrade rồi xóa đúng database thử nghiệm này; tài khoản kiểm thử cần quyền CREATE DATABASE. Không downgrade database ứng dụng hoặc xóa volume. Khi không bật biến trên, hai test PostgreSQL được skip rõ ràng.

## Kiểm thử health và dependency

Từ thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

Kiểm thử health dùng pytest và TestClient theo [hướng dẫn FastAPI](https://fastapi.tiangolo.com/tutorial/testing/).

Các test database trong pytest dùng **mock**, không chứng minh kết nối PostgreSQL thật. Cần gọi HTTP database khi PostgreSQL hoạt động để xác minh nhánh thành công.

Kiểm tra `SELECT 1` qua lớp kết nối backend, từ thư mục `backend`:

```powershell
.\.venv\Scripts\python.exe -c "from app.database import check_database; assert check_database(); print('Backend SELECT 1: success')"
```

Để thử nhánh không kết nối được, dùng cửa sổ PowerShell riêng, từ `backend`, chọn cổng database không có dịch vụ lắng nghe:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://test:example_only@127.0.0.1:65432/test'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Gọi `/api/health/db` tại cổng 8001: mong đợi 503; `/api/health` vẫn 200. PowerShell `Invoke-WebRequest` ném lỗi khi nhận 503; có thể dùng `curl.exe -i http://127.0.0.1:8001/api/health/db` để xem status và JSON. Dừng server bằng Ctrl+C, rồi `Remove-Item Env:DATABASE_URL` trong cửa sổ thử nghiệm. Không cần dừng PostgreSQL dùng chung.

## Frontend React cục bộ

Môi trường đã dùng: Node.js **22.22.3**, npm **10.9.8**, React/React DOM **19.3.0**, TypeScript **7.0.2**, Vite **8.3.4**, plugin React **6.1.2**. Giữ `frontend/package-lock.json`, dùng `npm.cmd ci` để tái lập. Node hiện có tương thích; không cài phần mềm hệ thống. PowerShell chặn `npm.ps1`, vì vậy dùng `npm.cmd` thay vì đổi execution policy.

Cửa sổ PowerShell 1, từ thư mục gốc:

```powershell
docker compose --env-file backend/.env up -d --wait --wait-timeout 120
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Cửa sổ PowerShell 2, từ thư mục gốc:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Mở **http://127.0.0.1:5173/**. Cổng cố định với strictPort; nếu đang bị chiếm, Vite báo lỗi thay vì đổi URL. Trang danh sách gọi API thật với page_size=20, có tải/trống/lỗi/thử lại và tổng số dataset; ngày giờ dùng múi giờ trình duyệt. AbortController và cờ hiệu lực ngăn kết quả cũ ghi đè sau khi đổi trang.

Vite dev proxy chuyển `/api` tới `http://127.0.0.1:8000`; chỉ phục vụ phát triển. Build không cung cấp proxy này; hosting chưa triển khai. Không thay đổi CORS backend.

```powershell
npm.cmd run typecheck
npm.cmd run build
```

Đã xác minh build/TypeScript và HTTP qua proxy có Demo CSV 07. Chưa xác minh render hoặc tương tác trong trình duyệt vì không có công cụ trình duyệt trong phiên làm việc. Ctrl+C dừng từng server; hiện hai server được giữ chạy để kiểm tra, PostgreSQL vẫn chạy.

## Nhập CSV từ website

Mở http://127.0.0.1:5173/, nhấn **Nhập CSV**. Điền tên, metadata tùy chọn và chọn file; có thể dùng `backend/samples/import_demo.csv`. Client kiểm tra tên, đuôi .csv và 5 MiB; backend xác thực nội dung, encoding và giới hạn 10.000 bản ghi.

Khi đang gửi, form vô hiệu hóa cả gửi và đóng; không tự retry POST. Lỗi giữ nguyên metadata/file. Khi mất kết nối hoặc không xác nhận được kết quả, kiểm tra danh sách trước khi gửi lại vì server có thể đã lưu. Thành công đóng/reset form, báo số cột/bản ghi và tải danh sách ở trang 1; thông báo thành công vẫn giữ nếu tải danh sách thất bại.

Đã kiểm tra hàm API frontend qua proxy, tạo **Demo CSV 10**, dataset/version **22**, 3 cột/2 bản ghi và đối chiếu GET. Đây không phải kiểm thử form trong trình duyệt. Chưa có công cụ trình duyệt để xác minh UI.

Checklist thủ công: nhập file mẫu hợp lệ và xem dataset mới; thử tên chỉ khoảng trắng/file sai đuôi/file >5 MiB/CSV lỗi; xác nhận lỗi giữ metadata và file; dùng mạng chậm để thử gửi lặp và đóng khi đang nhập; thử lỗi mạng rồi kiểm tra danh sách trước khi gửi lại; thử lỗi GET sau POST thành công và kiểm tra thông báo thành công vẫn còn. Kiểm tra Tab/Enter, label và focus.

Backend và frontend đang chạy để kiểm tra, PostgreSQL vẫn chạy. Không sửa/xóa Demo CSV 07.

## Chi tiết bộ dữ liệu

Tại http://127.0.0.1:5173/, chọn **Xem chi tiết** ở mỗi dataset. URL dùng hash `#dataset/<id>` để hỗ trợ liên kết trực tiếp và nút Back của trình duyệt, không cần thêm thư viện routing.

Màn hình dùng các API đọc đã có: metadata, cột theo position, phiên bản lớn nhất được chọn mặc định, thông tin file/ngày nhập/dung lượng và dữ liệu phân trang 20. Đổi phiên bản về trang 1; không có inferred_types thì hiển thị **Chưa suy luận**. Bảng cuộn ngang, giữ khoảng trắng/xuống dòng; ∅ là ký hiệu chuỗi rỗng với chú giải, giá trị CSV render như văn bản.

Dataset/phiên bản/trang đổi sẽ tạo view dữ liệu mới và hủy request cũ; có tải/lỗi/không tìm thấy/thử lại, không giữ bản ghi cũ dưới tên mới. Danh sách và form nhập được giữ lại khi mở chi tiết.

Đã kiểm tra build/TypeScript, hàm API frontend và đối chiếu GET thật của ba dataset hiện có; không sửa/xóa demo. Chưa xác minh UI trong trình duyệt. Checklist riêng hạng mục 09–11: [UI_CHECKLIST.md](docs/UI_CHECKLIST.md).

## Quản lý quy tắc qua API

Chạy `alembic upgrade head` từ backend để áp dụng **0002**. Trong `/docs`, dùng POST/GET `/api/datasets/{dataset_id}/rules` và PATCH `/api/datasets/{dataset_id}/rules/{rule_id}`. GET phân trang mặc định 1/20, tối đa 100, id tăng dần, gồm bật/tắt.

Body tạo ví dụ:

```json
{"name":"Mã bắt buộc","rule_type":"required","columns":["code"],"config":{},"is_active":true}
```

required/unique config phải `{}`; numeric_range ví dụ `{"min":"0.01","max":"100"}` với hai biên chuỗi hữu hạn. Không cho thuộc tính cấu hình thừa, cột không tồn tại/lặp hoặc sai số cột. PATCH gửi các trường cần đổi; toàn bộ cấu hình sau hợp nhất phải hợp lệ. `config` nếu gửi sẽ thay cả object, không chỉ hợp nhất riêng min/max. Trường null bị từ chối. 404 khi dataset/rule không phù hợp, 422 cấu hình/input sai, 503 database không truy cập được.

Quy tắc demo đã tạo HTTP 201: dataset **17** (Demo CSV 07), rule **1**, required cho cột **code**, đang bật. Dữ liệu CSV không thay đổi. Chưa có xóa quy tắc, chạy kiểm tra/snapshot/kết quả hoặc giao diện quy tắc.

## Chạy kiểm tra chất lượng qua API

Trong `/docs`, dùng **POST /api/datasets/{dataset_id}/versions/{version_id}/runs**; không gửi kết quả, số đếm hoặc snapshot. Ví dụ với demo hiện có:

```powershell
Invoke-RestMethod -Method Post 'http://127.0.0.1:8000/api/datasets/17/versions/17/runs'
```

HTTP 201 trả run_id, dataset_id, version_id, status, số đếm, error_row_rate dạng chuỗi 4 chữ số thập phân, started_at/finished_at và duration_seconds. Quy tắc đang bật được lấy theo id; không có quy tắc bật trả 422/NO_ACTIVE_RULES, dataset/version không phù hợp trả 404, lỗi kết nối trả 503, lỗi xử lý trả 500 kèm run_id nếu đã tạo.

Đây là **chạy đồng bộ** trong endpoint sync của FastAPI. Transaction đọc REPEATABLE READ lấy cột/bản ghi/quy tắc nhất quán, kết thúc trước tính toán; snapshot được chụp một lần, run running commit trước engine; kết quả hoàn tất atomically. Khi lỗi, cố gắng đánh dấu failed bằng transaction riêng. Nếu không ghi được trạng thái, response nêu run có thể còn running với failure_recorded=false.

Chưa có hàng đợi, tự retry, phục hồi run sau khi tiến trình dừng, API đọc kết quả hoặc frontend chạy kiểm tra. Không đảm bảo mọi run sẽ kết thúc khi database/tiến trình mất hoạt động.

Demo HTTP thật: dataset/version **17**, run **1**, completed, total_rows=2, error_row_count=0, violation_count=0, error_row_rate="0.0000"; snapshot và thống kê đã đọc lại PostgreSQL, dữ liệu CSV không thay đổi.

## Đọc lịch sử và kết quả chất lượng

- GET `/api/datasets/{dataset_id}/runs`: page/page_size mặc định 1/20, tối đa 100; version_id tùy chọn; started_at/id giảm dần. Không nhúng snapshot hoặc violations.
- GET `/api/datasets/{dataset_id}/runs/{run_id}`: snapshot/engine version/thống kê; running/failed giữ null, completed trả tỷ lệ chuỗi 4 chữ số. Failure chỉ hiển thị mã allowlist/thông báo chung an toàn, không trả nội dung exception thủ công hoặc cũ.
- GET `/api/datasets/{dataset_id}/runs/{run_id}/violations`: page/page_size, rule_id_snapshot và row_number tùy chọn; LIMIT/OFFSET tại DB, thứ tự row_number/rule_order/id; tên quy tắc từ snapshot. Chưa completed trả 409/RUN_NOT_COMPLETED. Không khớp bộ lọc/trang vượt dữ liệu trả items rỗng/total đúng.

404 khi dataset/run/version không phù hợp; 422 khi tham số sai; 503 khi mất kết nối. Các GET chỉ đọc.

Demo được giữ: **Demo Quality Errors 16**, dataset/version **28**, run **2**, rule **2** (Code required), rule **3** (Amount 0 to 100). File mẫu `backend/samples/quality_errors_demo.csv`; đáp án 4 bản ghi, 2 bản ghi lỗi, 3 vi phạm, tỷ lệ **50.0000**:

| Bản ghi | Quy tắc | Giá trị lỗi | Mã |
| --- | --- | --- | --- |
| 1 | Code required | chuỗi rỗng | REQUIRED_MISSING |
| 1 | Amount 0 to 100 | 101 | NUMERIC_OUT_OF_RANGE |
| 2 | Amount 0 to 100 | -1 | NUMERIC_OUT_OF_RANGE |

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/datasets/28/runs'
Invoke-RestMethod 'http://127.0.0.1:8000/api/datasets/28/runs/2'
Invoke-RestMethod 'http://127.0.0.1:8000/api/datasets/28/runs/2/violations?page=1&page_size=20'
```

HTTP thật đã đối chiếu toàn bộ snapshot/thống kê/lỗi với đáp án; run 1 của dataset 17 vẫn completed, tỷ lệ 0.0000 và không lỗi. Không sửa/xóa CSV demo trước. Chưa có frontend kết quả hoặc biểu đồ.

## Giao diện quản lý quy tắc

Mở chi tiết dataset, khu vực **Quy tắc chất lượng** có danh sách phân trang 20, tạo/sửa và bật/tắt bằng API thật. Không có xóa hoặc nút chạy kiểm tra trong khu vực này.

Tên bắt buộc; cột lấy từ metadata. required/numeric_range dùng một cột, unique dùng một hoặc nhiều cột. Đổi loại reset cột và min/max; required/unique gửi config `{}`. Min/max nhập dạng text và gửi nguyên chuỗi; backend kiểm tra Decimal, frontend không chuyển sang Number/parseFloat.

Khi request đang chạy, khóa thao tác lặp; lỗi giữ form, hiển thị thông báo API. Không tự retry POST; khi mất kết nối cần kiểm tra danh sách trước khi gửi lại. Lưu thành công và tải lại danh sách là hai trạng thái riêng: lỗi GET không xóa thông báo lưu thành công.

Đã kiểm tra API client thật trên dataset riêng **29 — Rules UI Test 17**, giữ lại 3 quy tắc **4, 5, 6** để thử UI. Không thay đổi quy tắc dataset 28 hoặc dữ liệu demo trước. Build/TypeScript đạt; UI chưa xác minh vì không có công cụ trình duyệt. Xem checklist hạng mục 17 trong [UI_CHECKLIST.md](docs/UI_CHECKLIST.md). Các server vẫn chạy tại frontend 5173/backend 8000.

## Giao diện chạy kiểm tra và lịch sử

Trong chi tiết dataset, chọn phiên bản tại bộ chọn hiện có, rồi dùng khu vực **Kiểm tra chất lượng và lịch sử**. Nút Chạy kiểm tra dùng POST thật cho đúng phiên bản, khóa gửi lặp và không tự retry. Lỗi mạng cần xem lịch sử trước khi chạy lại; lỗi có run_id có nút mở lần chạy.

Kết quả lấy bằng GET đã lưu: trạng thái/thời gian/phiên bản và thống kê; null là Chưa có kết quả. Completed không lỗi chỉ nói không phát hiện lỗi theo quy tắc đã áp dụng. Snapshot/engine trong phần mở rộng. Lỗi phân trang20/lọc snapshot rule và số bản ghi; ∅ biểu diễn chuỗi rỗng, ⟨null⟩ biểu diễn null, text không diễn giải HTML. Lịch sử phân trang20 và lọc phiên bản; tải lại lịch sử lỗi không xóa kết quả thành công. Chưa polling/hàng đợi/biểu đồ.

Kịch bản demo: mở **Demo Quality Errors 16 (dataset28)** → xem required code/range amount → chọn phiên bản1 → Chạy kiểm tra → đối chiếu **4/2/3 và 50.0000%** → lọc Amount 0 to 100, bản ghi1 (giá trị101) → mở lại run2 từ lịch sử. Dataset17/run1 là ví dụ không lỗi. Chạy lại tạo run mới nhưng không sửa dữ liệu CSV hoặc quy tắc.

Build/TypeScript và API client đọc run2/run1 đã đạt; chưa kiểm thử form/tương tác trình duyệt. Xem checklist18 trong docs/UI_CHECKLIST.md. Các server vẫn chạy tại http://127.0.0.1:5173/ và backend8000.

## Nhập phiên bản CSV mới (19A)

POST `/api/datasets/{dataset_id}/versions/import` nhận multipart chỉ có file, cùng giới hạn/validation CSV. Header phải khớp chính xác tên và thứ tự cột; khác cấu trúc trả 422/CSV_SCHEMA_MISMATCH và hướng dẫn tạo dataset khác. File được parse trước giữ khóa; khóa dòng dataset khi cấp số, ghi version/rows cùng transaction. Metadata/cột/phiên bản cũ không đổi; inferred_types=[]; không tự chạy kiểm tra.

CSV demo đã sửa: `backend/samples/quality_errors_fixed.csv`. **Đáp án ghi trước khi chạy:** header code,amount; 4 bản ghi; code không thiếu, amount trong [0,100]; theo hai quy tắc dataset28 phải có **0 bản ghi lỗi, 0 vi phạm, 0.0000%**. Run2 phiên bản1 phải giữ **2 bản ghi lỗi, 3 vi phạm, 50.0000%**.

Dùng Swagger `/docs` để upload vào dataset28; sau đó dùng POST chạy với version_id mới. Không xóa phiên bản cũ. Chưa có frontend nhập phiên bản.

Đã xác minh HTTP thật: dataset28 phiên bản **2**, version_id **30**, run_id **5**, completed, 4 bản ghi/0 bản ghi lỗi/0 vi phạm/0.0000%. Phiên bản1 (version28) và run2 giữ nguyên. Cả hai phiên bản và các lần chạy được giữ để demo đối chiếu trước/sau.

## Giao diện nhập phiên bản (19B)

Trong chi tiết dataset, chọn **Nhập phiên bản mới**, chỉ chọn file CSV. Form ghi rõ dataset đích và header phải khớp tên/thứ tự cột. Backend xác thực nội dung, client kiểm tra đuôi/5 MiB. Gửi FormData không tự đặt Content-Type; khóa gửi/đóng, giữ file khi lỗi và không tự retry POST. Schema khác hướng dẫn tạo dataset khác; mạng lỗi cần kiểm tra phiên bản trước khi gửi lại.

Thành công báo số phiên bản/bản ghi, đóng/reset form, tải lại chi tiết và chọn đúng version_id trả về, page1. Thông báo thành công giữ nếu GET lỗi; dùng Thử lại, không upload lại. Chọn phiên bản mới xóa lựa chọn run/bộ lọc cũ; không tự chạy kiểm tra. Lịch sử cũ vẫn mở được theo phiên bản.

API client đã kiểm tra trên dataset riêng **30 — Version UI Test 19B**, giữ version1 và version2 (ID32), không có run tự động. Dataset28 không upload thêm. UI chưa xác minh trong trình duyệt; xem checklist19B riêng.

Đối chiếu demo chỉ đọc: dataset28 phiên bản1/version28, mở run2 → **50.0000%** (2 bản ghi lỗi, 3 vi phạm); phiên bản2/version30, mở run5 → **0.0000%** theo cùng hai quy tắc. Muốn chạy lại phải chủ động nhấn Chạy kiểm tra, sẽ tạo run mới.

## Sửa metadata qua API (21A)

PATCH `/api/datasets/{dataset_id}` nhận name/description/source/owner. PATCH `/api/datasets/{dataset_id}/columns/{column_id}` chỉ nhận description. Ví dụ body dataset `{"description":"Mô tả mới","source":null}`; body cột `{"description":"Ý nghĩa cột"}`.

Trường không gửi giữ nguyên; tùy chọn null xóa giá trị, chuỗi rỗng giữ nguyên. Name nếu gửi phải có nội dung. Trường ngoài phạm vi/PATCH rỗng/input sai trả422, dataset/cột không phù hợp404, database unavailable503. Thành công200 trả metadata đã lưu. Transaction cập nhật cả Dataset.updated_at khi sửa cột, rollback khi lỗi.

Không đổi dữ liệu CSV/cấu trúc cột/versions/lịch sử; tên dataset hiện tại không có lịch sử tên. Chưa frontend sửa; AC-04 chưa nghiệm thu đầy đủ. Các demo đối chiếu không được dùng để thử ghi.

## Sửa metadata trong Tổng quan (21B)

Trong chi tiết dataset, tab Tổng quan → **Sửa thông tin** hoặc **Sửa mô tả** từng cột. Lưu chỉ PATCH trường thay đổi; không đổi thì không gửi request. Tên/vị trí/kiểu cột chỉ đọc. **Xóa giá trị** gửi null; xóa nội dung ô rồi lưu gửi chuỗi rỗng; mở form không tự đổi null.

Khi lưu, Lưu/Hủy bị khóa; lỗi giữ form và không tự retry PATCH. Lỗi mạng cần tải lại thông tin để xác nhận trước khi lưu lại. Response thành công cập nhật metadata trực tiếp, không refresh toàn bộ chi tiết nên giữ phiên bản/run/bộ lọc; chuyển tab giữ draft. Quay lại danh sách tải thông tin mới.

Build/TypeScript và API client trên dataset thử **37 — Metadata UI Test 21B updated** đạt; không sửa demo28. Chưa nghiệm thu UI; checklist21B còn mở và AC04 chưa hoàn thành đầy đủ. Không có suy luận kiểu dữ liệu.

## Tài liệu

- [Bối cảnh dự án](docs/PROJECT_CONTEXT.md)
- [Phạm vi demo](docs/MVP_SCOPE.md)
- [Tiến độ](docs/PROGRESS.md)
- [Model dữ liệu](docs/DATA_MODEL.md)
- [Kiểm tra UI còn mở](docs/UI_CHECKLIST.md)

Đã có model/migration, API nhập CSV tạo dataset mới và API đọc. Chưa có API sửa, nhập phiên bản tiếp theo, suy luận kiểu, quy tắc chất lượng, frontend, tài khoản hoặc AI.
