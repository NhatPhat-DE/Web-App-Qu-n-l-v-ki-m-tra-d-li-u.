let csrfToken = ''
let generation = 0
let notify: ((reason: 'expired' | 'csrf') => void) | undefined
const pending = new Set<AbortController>()
export function clearBusinessRequests() { generation++; for (const controller of pending) controller.abort(); pending.clear(); csrfToken = '' }
export function configureBusiness(csrf: string, listener: (reason: 'expired' | 'csrf') => void) { csrfToken = csrf; notify = listener }
export function disconnectBusiness() { clearBusinessRequests(); notify = undefined }
export const getBusinessGeneration = () => generation
export function businessFetch(url: string, options?: RequestInit): Promise<Response>
export function businessFetch<T>(url: string, options: RequestInit, consume: (response: Response) => Promise<T>): Promise<T>
export async function businessFetch<T>(url: string, options: RequestInit = {}, consume?: (response: Response) => Promise<T>): Promise<Response | T> {
  const issuedGeneration = generation
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (options.signal?.aborted) controller.abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  const headers = new Headers(options.headers)
  if (options.method && !['GET','HEAD','OPTIONS'].includes(options.method.toUpperCase())) headers.set('X-CSRF-Token', csrfToken)
  pending.add(controller)
  try {
    const response = await fetch(url, { ...options, headers, credentials: 'same-origin', signal: controller.signal })
    if (controller.signal.aborted || issuedGeneration !== generation) throw new DOMException('Request cancelled', 'AbortError')
    if (response.status === 401) { clearBusinessRequests(); notify?.('expired') }
    if (response.status === 403) {
      const body = await response.clone().json().catch(() => null)
      if (!controller.signal.aborted && issuedGeneration === generation && (body?.detail?.code ?? body?.error?.code) === 'CSRF_REJECTED') notify?.('csrf')
    }
    if (!consume) return response
    // Downloads keep the controller registered until the body has been consumed.
    const result = await consume(response)
    if (controller.signal.aborted || issuedGeneration !== generation) throw new DOMException('Request cancelled', 'AbortError')
    return result
  } finally { pending.delete(controller); options.signal?.removeEventListener('abort', abort) }
}
