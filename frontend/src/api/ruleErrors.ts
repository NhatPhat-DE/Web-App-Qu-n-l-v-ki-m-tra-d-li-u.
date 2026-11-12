export class RuleAPIError extends Error {
  code: string
  status: number
  technicalDetail?: string
  constructor(code: string, status: number, technicalDetail?: string) {
    super(code === 'NETWORK_READ_ERROR' ? 'Không thể tải quy tắc. Vui lòng kiểm tra kết nối và thử lại.'
      : code === 'INVALID_READ_RESPONSE' ? 'Không đọc được danh sách quy tắc. Vui lòng thử tải lại.'
      : code === 'NETWORK_ERROR' ? 'Mất kết nối khi xử lý quy tắc. Máy chủ có thể đã lưu; hãy kiểm tra danh sách trước khi gửi lại.'
      : code === 'INVALID_RESPONSE' ? 'Chưa đọc được kết quả lưu. Hãy kiểm tra danh sách trước khi gửi lại.'
      : status === 401 ? 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.'
      : status === 403 ? 'Bạn không có quyền thực hiện thao tác này hoặc phiên làm việc cần được tải lại.'
      : status === 503 ? 'Dịch vụ quy tắc chưa sẵn sàng. Vui lòng thử lại sau.'
      : status === 409 ? 'Thông tin quy tắc đã thay đổi hoặc đang được xử lý. Hãy tải lại danh sách trước khi thử lại.'
      : status >= 500 ? 'Chưa xác nhận được kết quả lưu quy tắc. Hãy kiểm tra danh sách trước khi gửi lại.'
      : 'Chưa thể lưu quy tắc. Hãy kiểm tra thông tin và thử lại.')
    this.name = 'RuleAPIError'
    this.code=code;this.status=status;this.technicalDetail=technicalDetail
  }
}

export interface RuleFeedback { message: string; field?: 'name'|'columns'|'kind'|'pattern'|'range'|'dates'|'values'; detail?: string }
const patternMessages: Record<string,string> = {
  'Empty or unclosed character class.': 'Nhóm ký tự trong mẫu đang rỗng hoặc thiếu dấu đóng ]. Hãy kiểm tra cặp dấu [ và ], ví dụ: [A-Z]+.',
  'Unclosed group.': 'Mẫu có nhóm chưa đóng. Hãy kiểm tra các cặp dấu ( và ).',
  'Unexpected closing group.': 'Mẫu có dấu ) thừa. Hãy kiểm tra các cặp dấu ( và ).',
  'Incomplete escape.': 'Dấu gạch chéo ngược ở cuối mẫu đang thiếu ký tự đi kèm.',
  'Unsupported escape.': 'Mẫu dùng cách viết ký tự đặc biệt chưa được hỗ trợ. Hãy kiểm tra lại dấu gạch chéo ngược.',
  'Range endpoints must be ordered literal code points.': 'Khoảng ký tự trong dấu ngoặc vuông phải theo thứ tự, ví dụ [A-Z] thay vì [Z-A].',
  'Reversed repetition bounds.': 'Số lần lặp nhỏ nhất không được vượt số lần lặp lớn nhất trong mẫu.',
  'Only ordinary groups are allowed.': 'Mẫu dùng kiểu nhóm chưa được hỗ trợ. Hãy dùng nhóm thông thường với dấu ( và ).',
  'Stacked/lazy/possessive quantifiers are outside re2-v1.': 'Mẫu đang dùng cách lặp chưa được hỗ trợ. Hãy dùng một dấu lặp hoặc một khoảng lặp cho mỗi nhóm ký tự.',
  'Pattern exceeds 1..512 code points / 2048 UTF-8 bytes.': 'Mẫu cần có từ 1 đến 512 ký tự và không vượt 2048 byte UTF-8.',
}
export function ruleFeedback(cause: unknown, kind: string): RuleFeedback {
  if (!(cause instanceof RuleAPIError)) return { message: 'Không thể lưu quy tắc. Vui lòng kiểm tra cấu hình và thử lại.', detail: cause instanceof Error ? cause.message : undefined }
  const detail = cause.technicalDetail ? `${cause.code} · ${cause.technicalDetail}` : undefined
  if (cause.status !== 422) return { message: cause.message, detail }
  if (cause.code === 'INVALID_NAME') return {message:'Tên quy tắc không được để trống hoặc chỉ có khoảng trắng.',field:'name',detail}
  if (['INVALID_COLUMNS','COLUMN_CARDINALITY'].includes(cause.code)) return {message:'Chọn các trường hợp lệ cho loại kiểm tra này; không chọn trùng trường.',field:'columns',detail}
  if (cause.code === 'UNSUPPORTED_RULE') return {message:'Loại kiểm tra chưa được hỗ trợ. Hãy chọn lại loại kiểm tra.',field:'kind',detail}
  if (['INVALID_CONFIG','INVALID_RANGE','INVALID_RANGE_TYPE'].includes(cause.code)) {
    if (kind === 'pattern' || kind === 'email') return {message:patternMessages[cause.technicalDetail ?? ''] ?? 'Mẫu định dạng chưa hợp lệ hoặc dùng cú pháp chưa được hỗ trợ. Hãy kiểm tra và sửa mẫu trước khi lưu.',field:kind==='pattern'?'pattern':'kind',detail}
    if (kind === 'numeric_range') return {message:'Hai biên phải là số hữu hạn; giá trị nhỏ nhất không được lớn hơn giá trị lớn nhất.',field:'range',detail}
    if (kind === 'date_format') return {message:'Kiểm tra định dạng ngày và khoảng ngày: nếu giới hạn ngày, cần nhập đủ hai biên hợp lệ và ngày nhỏ nhất không được sau ngày lớn nhất.',field:'dates',detail}
    if (kind === 'allowed_values') return {message:'Nhập từ 1 đến 100 giá trị, mỗi dòng một giá trị, không để dòng chỉ có khoảng trắng hoặc giá trị trùng. Mỗi giá trị tối đa 256 ký tự và 1024 byte UTF-8.',field:'values',detail}
    return {message:'Cấu hình chưa phù hợp với loại kiểm tra. Hãy chọn lại loại và kiểm tra các ô cấu hình.',field:'kind',detail}
  }
  return {message:'Thông tin quy tắc chưa hợp lệ. Hãy kiểm tra tên, loại, trường áp dụng và cấu hình.',detail}
}
