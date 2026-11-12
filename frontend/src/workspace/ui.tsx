import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { ButtonHTMLAttributes, DependencyList, ReactNode } from 'react'
import { AlertCircle, ArrowLeft, ArrowRight, Check, CheckCircle2, CircleDashed, Database, FileSearch, LoaderCircle, X } from 'lucide-react'
import type { RunSummary } from '../api/runs'

export const number = (value: number | null | undefined) => value == null ? '—' : value.toLocaleString('vi-VN')
export const date = (value?: string | null, time = true) => value ? new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', ...(time ? { timeStyle: 'short' as const } : {}) }).format(new Date(value)) : '—'
export const ruleLabels: Record<string, string> = { required: 'Không được thiếu', unique: 'Không được trùng', pattern: 'Đúng mẫu định dạng', data_type: 'Đúng kiểu dữ liệu', date_format: 'Đúng ngày tháng', numeric_range: 'Trong khoảng số', allowed_values: 'Thuộc danh sách cho phép' }
export const typeLabels: Record<string, string> = { integer: 'Số nguyên', decimal: 'Số thập phân', boolean: 'Đúng / sai', date: 'Ngày tháng', text: 'Văn bản', unknown: 'Chưa xác định' }
const dirtyForms = new Set<string>()
export const confirmLeave = () => !dirtyForms.size || window.confirm('Bạn có thay đổi chưa lưu. Rời đi và bỏ các thay đổi này?')
export function useDebounced<T>(value: T, delay = 250) {
  const [settled, setSettled] = useState(value)
  useEffect(() => { const timer = window.setTimeout(() => setSettled(value), delay); return () => window.clearTimeout(timer) }, [value, delay])
  return settled
}
export function useDirty(dirty: boolean) {
  const id = useId()
  const cleanup = useRef<(() => void) | null>(null)
  // Successful saves may navigate before React commits the next render.
  // Release only this form's guard synchronously; other forms stay protected.
  const clearDirty = useCallback(() => { cleanup.current?.(); cleanup.current = null }, [])
  useEffect(() => {
    if (!dirty) return
    dirtyForms.add(id)
    const listener = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', listener)
    cleanup.current = () => { dirtyForms.delete(id); window.removeEventListener('beforeunload', listener) }
    return clearDirty
  }, [dirty, id, clearDirty])
  return clearDirty
}
/** Own one guard per form; release it before success callbacks can navigate. */
export function useFormGuard(dirty: boolean, busy: boolean, onClose: () => void) {
  const [saved, setSaved] = useState(false)
  const clearDirty = useDirty(dirty && !saved)
  return {
    markSaved() { setSaved(true); clearDirty() },
    close() {
      if (busy || (!saved && dirty && !window.confirm('Bỏ các thay đổi chưa lưu và đóng cửa sổ này?'))) return false
      clearDirty(); onClose(); return true
    },
  }
}
export function useLoad<T>(loader: (signal: AbortSignal) => Promise<T>, deps: DependencyList) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setData(null)
    loader(controller.signal).then(value => { if (!controller.signal.aborted) setData(value) }).catch(cause => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Không thể tải dữ liệu.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [...deps, revision])
  return { data, error, loading, reload: () => setRevision(value => value + 1) }
}
export function Button({ children, className = '', tone = 'secondary', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: 'primary' | 'secondary' | 'ghost' | 'danger' }) {
  return <button type="button" className={`button button-${tone} ${className}`} {...props}>{children}</button>
}
export function PageTitle({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-title"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1><p>{description}</p></div>{action && <div className="page-actions">{action}</div>}</div>
}
export function Notice({ children, kind = 'info', action }: { children: ReactNode; kind?: 'info' | 'error' | 'success' | 'warning'; action?: ReactNode }) {
  return <div className={`notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{kind === 'success' ? <CheckCircle2 size={19} /> : <AlertCircle size={19} />}<div>{children}</div>{action}</div>
}
export function LoadState({ loading, error, retry }: { loading: boolean; error?: string; retry?: () => void }) {
  if (loading) return <div className="loading-state" role="status"><LoaderCircle className="spin" size={24} /><span>Đang tải dữ liệu…</span></div>
  if (error) return <Notice kind="error" action={retry && <Button onClick={retry}>Thử lại</Button>}>{error}</Notice>
  return null
}
export function Empty({ title = 'Chưa có dữ liệu', text, action }: { title?: string; text: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><FileSearch size={29} /></div><h3>{title}</h3><p>{text}</p>{action}</div>
}
export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'primary' }) {
  return <span className={`badge badge-${tone}`}>{tone === 'success' ? <Check size={13} /> : tone === 'warning' || tone === 'danger' ? <AlertCircle size={13} /> : <CircleDashed size={13} />}{children}</span>
}
export function QualityBadge({ run }: { run?: RunSummary }) {
  if (!run) return <Badge>Chưa kiểm tra</Badge>
  if (run.status === 'running') return <Badge tone="primary">Đang kiểm tra</Badge>
  if (run.status === 'failed') return <Badge tone="danger">Thực thi thất bại</Badge>
    if (run.rules_changed) return <Badge tone="warning">Cấu hình trước — kiểm tra lại</Badge>
  return run.error_row_count === 0 ? <Badge tone="success">Đạt quy tắc</Badge> : <Badge tone="warning">Có lỗi dữ liệu</Badge>
}
export function ExecutionBadge({ status }: { status: RunSummary['status'] }) {
  return <Badge tone={status === 'completed' ? 'success' : status === 'failed' ? 'danger' : 'primary'}>{status === 'completed' ? 'Hoàn tất' : status === 'failed' ? 'Thực thi thất bại' : 'Đang kiểm tra'}</Badge>
}
export function Pager({ page, total, size = 10, change }: { page: number; total: number; size?: number; change: (page: number) => void }) {
  const count = Math.max(1, Math.ceil(total / size))
  return <div className="pagination"><span>{total ? `${number((page - 1) * size + 1)}–${number(Math.min(page * size, total))} trong ${number(total)} kết quả` : '0 kết quả'}</span><div><Button aria-label="Trang trước" disabled={page <= 1} onClick={() => change(page - 1)}><ArrowLeft size={15} /></Button><span>Trang {page} / {count}</span><Button aria-label="Trang sau" disabled={page >= count} onClick={() => change(page + 1)}><ArrowRight size={15} /></Button></div></div>
}
export function Dialog({ title, description, children, onClose, dirty = false, busy = false, wide = false }: { title: string; description?: string; children: ReactNode; onClose: () => void; dirty?: boolean; busy?: boolean; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null)
  const id = useId()
  useDirty(dirty)
  function close() { if (!busy && (!dirty || window.confirm('Bỏ các thay đổi chưa lưu và đóng cửa sổ này?'))) onClose() }
  useEffect(() => {
    const dialog = ref.current!
    const before = document.activeElement as HTMLElement | null
    dialog.showModal()
    dialog.querySelector<HTMLElement>('[autofocus], input:not([type="hidden"]), select, textarea')?.focus()
    return () => { dialog.close(); before?.focus() }
  }, [])
  return <dialog ref={ref} className={`dialog ${wide ? 'dialog-wide' : ''}`} aria-labelledby={id} onKeyDown={event => {
    if (event.key !== 'Tab') return
    const items = [...ref.current!.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled):not([type="hidden"]), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')].filter(item => item.getClientRects().length > 0)
    const first = items[0], last = items.at(-1)
    if (!first) { event.preventDefault(); ref.current?.focus(); return }
    if (event.shiftKey && (document.activeElement === first || document.activeElement === ref.current)) { event.preventDefault(); last?.focus() }
    else if (!event.shiftKey && (document.activeElement === last || document.activeElement === ref.current)) { event.preventDefault(); first.focus() }
  }} onCancel={event => { event.preventDefault(); close() }}><div className="dialog-heading"><div><h2 id={id}>{title}</h2>{description && <p>{description}</p>}</div><Button tone="ghost" disabled={busy} aria-label="Đóng" onClick={close}><X size={20} /></Button></div><div className="dialog-content">{children}</div></dialog>
}
export function Field({ label, hint, error, errorId, children, required = false }: { label: string; hint?: string; error?: string; errorId?: string; children: ReactNode; required?: boolean }) {
  const [validation, setValidation] = useState('')
  function clear(event: React.FormEvent<HTMLLabelElement>) {
    const control = event.target
    if (control instanceof HTMLInputElement || control instanceof HTMLSelectElement || control instanceof HTMLTextAreaElement) { control.setCustomValidity(''); control.removeAttribute('aria-invalid'); setValidation('') }
  }
  const activeError = error || validation
  return <label className="field" onInput={clear} onChange={clear} onInvalid={event => {
    const control = event.target
    if (control instanceof HTMLInputElement || control instanceof HTMLSelectElement || control instanceof HTMLTextAreaElement) {
      const message = control.validity.valueMissing ? `Vui lòng nhập ${label.toLocaleLowerCase('vi')}.` : control.validity.patternMismatch ? 'Thông tin không được chỉ có khoảng trắng.' : 'Giá trị chưa hợp lệ. Hãy kiểm tra lại.'
      control.setCustomValidity(message); control.setAttribute('aria-invalid', 'true'); setValidation(message)
    }
  }}><span>{label}{required && <span className="required"> *</span>}</span>{children}{activeError && <small id={errorId} className="field-validation" role="alert">{activeError}</small>}{hint && !activeError && <small>{hint}</small>}</label>
}
export function DatasetMark({ name, small = false }: { name: string; small?: boolean }) {
  const tone = [...name].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 4
  return <span className={`dataset-mark mark-${tone} ${small ? 'mark-small' : ''}`}><Database size={small ? 17 : 22} /></span>
}
export function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; document.body.append(anchor); anchor.click(); anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
