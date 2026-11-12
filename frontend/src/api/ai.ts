import { businessFetch } from './business'
import type { RuleInput } from './rules'
import { createRule } from './rules'
// Independent AI scope: do not derive this allowlist from manual RuleType.
export type AIRuleType = 'required' | 'unique' | 'numeric_range'
export interface AIRuleInput extends Omit<RuleInput, 'rule_type' | 'config'> { rule_type: AIRuleType; config: Record<string, string> }
export const isAIRuleType = (type: unknown): type is AIRuleType => typeof type === 'string' && ['required', 'unique', 'numeric_range'].includes(type)
export interface AIPayload { schema_version: number; row_count?: number; columns: { name: string; description?: string; inferred_type: string; missing_count?: number }[] }
export interface Preview { payload: AIPayload; preview_token: string; expires_at: string; provider: string | null; model: string | null; provider_status: string }
export interface Suggestion extends Omit<AIRuleInput, 'is_active'> { suggestion_id: string; reason: string; assumptions: string[] }
export interface SuggestionResult { request_id: string; dataset_id: number; version_id: number; suggestions: Suggestion[] }
export interface Selection { version_id: number; columns: string[]; include_descriptions: boolean; include_statistics: boolean }
export class AIError extends Error {
  status: number
  retryAfter: number
  constructor(message: string, status = 0, retryAfter = 0) { super(message); this.status = status; this.retryAfter = retryAfter }
}
async function post<T>(url: string, body: object, signal: AbortSignal): Promise<T> {
  let response: Response
  try { response = await businessFetch(url, { method: 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) }
  catch (error) {
    if (signal.aborted || (error instanceof DOMException && error.name === 'AbortError')) throw error
    throw new AIError('Mất kết nối; chưa xác nhận được kết quả. Không tự gửi lại. Yêu cầu Gemini đã nhận có thể vẫn tính lượt; chỉ thử lại thủ công.')
  }
  const result = await response.json().catch(() => null)
  if (signal.aborted) throw new DOMException('Request cancelled', 'AbortError')
  if (!response.ok) {
    const code = result?.error?.code ?? result?.detail?.code
    const retry = Number(response.headers.get('Retry-After')) || 0
    const message = response.status === 409 ? 'Preview đã hết hạn, khác phiên/model hoặc nội dung đã thay đổi. Hãy xem trước và xác nhận lại.'
      : response.status === 429 ? `Đã đạt giới hạn lượt hoặc đang có yêu cầu chạy. ${retry ? `Chờ ít nhất ${retry} giây. ` : ''}Không tự gửi lại.`
      : response.status === 504 ? 'Gemini quá thời gian chờ. Không có kết quả được xác nhận; hệ thống không tự gọi lại.'
      : code === 'AI_NOT_CONFIGURED' || code === 'AI_PREVIEW_NOT_CONFIGURED' ? 'AI chưa được cấu hình. Bạn vẫn có thể tạo quy tắc thủ công.'
      : code === 'AI_PROVIDER_AUTH_ERROR' ? 'Gemini từ chối xác thực. Hãy kiểm tra cấu hình backend; không nhập API key tại đây.'
      : response.status === 401 ? 'Phiên không còn hợp lệ. Vui lòng đăng nhập lại.'
      : response.status === 403 ? 'Không đủ quyền hoặc CSRF không hợp lệ. Hãy kiểm tra lại phiên rồi thử thủ công.'
      : response.status === 502 ? 'Phản hồi Gemini bị chặn, cắt dở hoặc không hợp lệ. Không có đề xuất nào được chấp nhận.'
      : response.status === 422 || response.status === 413 ? 'Lựa chọn hoặc payload vượt giới hạn/không hợp lệ. Hãy giảm số cột hoặc bỏ mô tả/thống kê rồi xem trước lại.'
      : 'Dịch vụ AI chưa sẵn sàng. Không tự gọi lại; chức năng tạo quy tắc thủ công vẫn dùng được.'
    throw new AIError(message, response.status, retry)
  }
  if (!result) throw new AIError('Không đọc được phản hồi AI. Không tự gửi lại.')
  return result as T
}
export const previewAI = (dataset: number, selection: Selection, signal: AbortSignal) => post<Preview>(`/api/datasets/${dataset}/ai-rule-suggestions/preview`, selection, signal)
export const suggestAI = (dataset: number, version: number, preview: Preview, confirmed: boolean, signal: AbortSignal) => {
  if (!confirmed || !preview.provider || !preview.model || preview.provider_status !== 'configured') return Promise.reject(new AIError('Cần xem payload, kiểm tra cấu hình và xác nhận trước khi gửi.', 422))
  if (Date.parse(preview.expires_at) <= Date.now()) return Promise.reject(new AIError('Preview đã hết hạn. Hãy xem trước và xác nhận lại.', 409))
  return post<SuggestionResult>(`/api/datasets/${dataset}/ai-rule-suggestions`, { version_id: version, preview_token: preview.preview_token, confirmed: true }, signal).then(result => {
    if (!Array.isArray(result.suggestions) || result.suggestions.some(item => !isAIRuleType(item?.rule_type))) throw new AIError('Phản hồi AI chứa loại quy tắc không được phép. Không có đề xuất nào được chấp nhận.', 502)
    return result
  })
}
export const initialDraft = (suggestion: Suggestion): AIRuleInput => {
  if (!isAIRuleType(suggestion.rule_type)) throw new AIError('Loại quy tắc không được phép trong đề xuất AI.', 502)
  return { name: suggestion.name, rule_type: suggestion.rule_type, columns: [...suggestion.columns], config: { ...suggestion.config }, is_active: false }
}
export const createAIRule = (dataset: number, input: AIRuleInput, signal?: AbortSignal) => {
  if (!isAIRuleType(input.rule_type)) return Promise.reject(new AIError('Không thể lưu loại quy tắc này từ luồng đề xuất AI.', 422))
  return createRule(dataset, input, signal)
}
