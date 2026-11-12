import { businessFetch } from './business'
export type UserRole = 'admin' | 'data_steward' | 'data_owner'
export interface AdminUser { id: number; username: string; role: UserRole; is_active: boolean; created_at: string; updated_at: string }
export interface UserPage { items: AdminUser[]; total: number; page: number; page_size: number }
export interface UserCreate { username: string; password: string; role: UserRole }
export type UserChanges = Partial<Pick<AdminUser, 'role' | 'is_active'>>
export const roleLabel = (role: UserRole) => role === 'admin' ? 'Quản trị viên' : role === 'data_owner' ? 'Data Owner' : 'Người phụ trách dữ liệu'
export class AdminError extends Error {
  status: number
  constructor(message: string, status = 0) { super(message); this.status = status }
}
export function validateCreate(data: UserCreate, confirmation: string) {
  if (!/^[\x00-\x7F]*$/.test(data.username) || !/^[a-z0-9][a-z0-9_.-]{2,63}$/.test(data.username.trim().toLowerCase())) return 'Tên đăng nhập gồm 3–64 ký tự ASCII: chữ, số, dấu chấm, gạch dưới hoặc gạch ngang.'
  if (Array.from(data.password).length < 12 || Array.from(data.password).length > 128) return 'Mật khẩu phải có 12–128 ký tự.'
  if (data.password !== confirmation) return 'Xác nhận mật khẩu không khớp.'
  if (!['admin', 'data_steward', 'data_owner'].includes(data.role)) return 'Vai trò không hợp lệ.'
  return ''
}
export function userChanges(user: AdminUser, role: UserRole, active: boolean): UserChanges {
  return { ...(role !== user.role ? { role } : {}), ...(active !== user.is_active ? { is_active: active } : {}) }
}
async function send<T>(path: string, options: RequestInit, writing = false): Promise<T> {
  const uncertain = 'Hãy kiểm tra danh sách trước khi gửi lại; hệ thống không tự gửi lại.'
  let response: Response
  try { response = await businessFetch(`/api/admin/users${path}`, options) }
  catch (cause) {
    if (options.signal?.aborted || (cause instanceof DOMException && cause.name === 'AbortError')) throw cause
    throw new AdminError(writing ? `Mất kết nối. Máy chủ có thể đã lưu thay đổi. ${uncertain}` : 'Không thể tải danh sách. Hãy kiểm tra kết nối và thử lại.')
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const code = body?.error?.code ?? body?.detail?.code
    const message = response.status === 401 ? 'Phiên không còn hiệu lực. Vui lòng đăng nhập lại.'
      : response.status === 403 ? (code === 'CSRF_REJECTED' ? 'CSRF không hợp lệ. Hãy kiểm tra lại phiên và thử thủ công.' : 'Bạn không đủ quyền quản lý tài khoản.')
      : response.status === 409 ? (code === 'USERNAME_EXISTS' ? 'Tên đăng nhập đã tồn tại.' : code === 'SELF_ADMIN_CHANGE' ? 'Không được tự vô hiệu hóa hoặc tự hạ quyền.' : 'Phải giữ ít nhất một quản trị viên đang hoạt động.')
      : response.status === 422 ? 'Thông tin tài khoản không hợp lệ. Hãy kiểm tra các trường đã nhập.'
      : response.status === 404 ? 'Tài khoản không còn tồn tại. Hãy tải lại danh sách.'
      : response.status === 503 ? 'Dịch vụ dữ liệu chưa sẵn sàng. Hãy thử lại sau.'
      : `Không xác nhận được kết quả. ${uncertain}`
    throw new AdminError(message, response.status)
  }
  if (!body) throw new AdminError(`Không đọc được phản hồi. ${uncertain}`)
  if (options.signal?.aborted) throw new DOMException('Request cancelled', 'AbortError')
  return body as T
}
export const fetchUsers = (page: number, signal: AbortSignal) => send<UserPage>(`?page=${page}&page_size=20`, { signal })
export function createUser(data: UserCreate, confirmation: string, signal: AbortSignal) {
  const error = validateCreate(data, confirmation)
  if (error) return Promise.reject(new AdminError(error, 422))
  return send<AdminUser>('', { method: 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...data, username: data.username.trim().toLowerCase() }) }, true)
}
export function patchUser(id: number, changes: UserChanges, signal: AbortSignal) {
  if (!Object.keys(changes).length || Object.keys(changes).some(key => !['role', 'is_active'].includes(key)) ||
      ('role' in changes && !['admin', 'data_steward', 'data_owner'].includes(changes.role!)) || ('is_active' in changes && typeof changes.is_active !== 'boolean')) return Promise.reject(new AdminError('Cần ít nhất một thay đổi hợp lệ.', 422))
  return send<AdminUser>(`/${id}`, { method: 'PATCH', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(changes) }, true)
}
