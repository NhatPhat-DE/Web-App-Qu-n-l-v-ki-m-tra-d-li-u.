export interface AuthUser { id: number; username: string; role: 'admin' | 'data_steward' | 'data_owner' }
export type AuthState = { authenticated: true; user: AuthUser; expires_at: string; csrf_token: string } | { authenticated: false; csrf_token: string }
export class AuthError extends Error {
  status: number
  retryAfter: number
  constructor(message: string, status = 0, retryAfter = 0) { super(message); this.status = status; this.retryAfter = retryAfter }
}
async function send(path: string, options: RequestInit = {}) {
  let response: Response
  try { response = await fetch(`/api/auth/${path}`, { credentials: 'same-origin', ...options }) }
  catch (cause) {
    if (options.signal?.aborted) throw cause
    throw new AuthError('Mất kết nối. Trạng thái phiên chưa được xác nhận; hãy kiểm tra lại phiên trước khi thử thao tác lần nữa.')
  }
  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (path === 'me' && response.status === 401 && typeof body?.csrf_token === 'string') return { authenticated: false, csrf_token: body.csrf_token } as const
  if (!response.ok) throw new AuthError(typeof body?.error?.message === 'string' ? body.error.message : 'Không thể xác nhận phiên đăng nhập.', response.status, /^\d+$/.test(response.headers.get('retry-after') ?? '') ? Number(response.headers.get('retry-after')) : 0)
  if (response.status === 204) return null
  if (!body?.user || typeof body.csrf_token !== 'string' || typeof body.expires_at !== 'string') throw new AuthError('Phản hồi phiên không hợp lệ. Hãy kiểm tra lại phiên.')
  return { authenticated: true, ...body } as AuthState
}
export const fetchMe = (signal: AbortSignal) => send('me', { signal }) as Promise<AuthState>
export const login = (username: string, password: string, csrf: string, signal: AbortSignal) => send('login', {
  method: 'POST', signal, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify({ username, password }),
}) as Promise<AuthState>
export const logout = (csrf: string, signal: AbortSignal) => send('logout', { method: 'POST', signal, headers: { 'X-CSRF-Token': csrf } })
