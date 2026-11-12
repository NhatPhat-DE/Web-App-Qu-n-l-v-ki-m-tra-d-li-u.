import { useEffect, useRef, useState } from 'react'
import { Check, Pencil, Plus, Users } from 'lucide-react'
import { createUser, fetchUsers, patchUser, roleLabel, userChanges, validateCreate } from '../api/admin'
import type { AdminUser, UserRole } from '../api/admin'
import type { AuthUser } from '../api/auth'
import { Badge, Button, Dialog, Empty, Field, LoadState, Notice, PageTitle, Pager, date, useLoad, useFormGuard } from './ui'

export default function Accounts({ user }: { user: AuthUser }) {
  if (user.role !== 'admin') return <Notice kind="error">Bạn không đủ quyền quản lý tài khoản. Chỉ quản trị viên được truy cập chức năng này. <a href="#/dashboard">Về tổng quan</a></Notice>
  return <AccountList user={user} />
}
function AccountList({ user }: { user: AuthUser }) {
  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState<AdminUser | 'create' | null>(null)
  const [message, setMessage] = useState('')
  const list = useLoad(signal => fetchUsers(page, signal), [page])
  return <><PageTitle eyebrow="QUẢN TRỊ HỆ THỐNG" title="Quản lý tài khoản" description="Cấp tài khoản và quản lý hai vai trò hiện có của hệ thống." action={<Button tone="primary" onClick={() => setDialog('create')}><Plus size={17} />Tạo tài khoản</Button>} />
    {message && <Notice kind="success">{message}</Notice>}<Notice>Thay đổi vai trò hoặc vô hiệu hóa tài khoản sẽ thu hồi các phiên đăng nhập hiện có của tài khoản đó. Không thể tự hạ quyền hoặc tự vô hiệu hóa.</Notice>
    <section className="panel"><div className="panel-heading"><h2><Users size={18} />Danh sách tài khoản</h2></div><LoadState loading={list.loading} error={list.error} retry={list.reload} />{list.data && (list.data.items.length ? <><div className="table-scroll"><table><thead><tr><th>Tên đăng nhập</th><th>Vai trò</th><th>Trạng thái</th><th>Ngày tạo</th><th>Cập nhật</th><th></th></tr></thead><tbody>{list.data.items.map(item => <tr key={item.id}><td><strong>{item.username}</strong>{item.id === user.id && <small>Tài khoản của bạn</small>}</td><td>{roleLabel(item.role)}</td><td><Badge tone={item.is_active ? 'success' : 'neutral'}>{item.is_active ? 'Đang hoạt động' : 'Đã vô hiệu hóa'}</Badge></td><td>{date(item.created_at)}</td><td>{date(item.updated_at)}</td><td><Button tone="ghost" disabled={item.id === user.id} title={item.id === user.id ? 'Không thể tự đổi vai trò hoặc trạng thái.' : undefined} aria-label={`Sửa tài khoản ${item.username}`} onClick={() => setDialog(item)}><Pencil size={16} />Chỉnh sửa</Button></td></tr>)}</tbody></table></div><Pager page={page} total={list.data.total} size={20} change={setPage} /></> : <Empty text="Không có tài khoản trong trang này." action={page > 1 && <Button onClick={() => setPage(1)}>Về trang đầu</Button>} />)}</section>
    {dialog && <AccountDialog item={dialog === 'create' ? undefined : dialog} close={() => setDialog(null)} saved={() => { setDialog(null); setMessage(dialog === 'create' ? 'Đã tạo tài khoản.' : 'Đã cập nhật tài khoản. Các phiên bị ảnh hưởng đã được thu hồi.'); list.reload() }} />}
  </>
}
function AccountDialog({ item, close, saved }: { item?: AdminUser; close: () => void; saved: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [role, setRole] = useState<UserRole>(item?.role ?? 'data_steward')
  const [active, setActive] = useState(item?.is_active ?? true)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fieldError, setFieldError] = useState<Record<string, string>>({})
  const controller = useRef<AbortController | null>(null)
  const lock = useRef(false)
  useEffect(() => () => controller.current?.abort(), [])
  const changes = item ? userChanges(item, role, active) : {}
  const dirty = item ? Object.keys(changes).length > 0 : !!username || !!password || !!confirmation || role !== 'data_steward'
  const guard=useFormGuard(dirty,busy,close)
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (lock.current) return
    setError(''); setFieldError({})
    if (!item) {
      const failure = validateCreate({ username, password, role }, confirmation)
      if (failure) { setFieldError({ [failure.includes('Tên đăng nhập') ? 'username' : failure.includes('Xác nhận') ? 'confirmation' : 'password']: failure }); return }
    } else if (!dirty || !confirmed) return
    lock.current = true; setBusy(true); const request = new AbortController(); controller.current = request
    try {
      if (item) await patchUser(item.id, changes, request.signal)
      else await createUser({ username, password, role }, confirmation, request.signal)
      if (!request.signal.aborted) { guard.markSaved(); setPassword(''); setConfirmation(''); saved() }
    } catch (cause) {
      if (!request.signal.aborted) { const message = cause instanceof Error ? cause.message : 'Không thể lưu tài khoản.'; setError(message); if (message.includes('Tên đăng nhập đã tồn tại')) setFieldError({ username: message }) }
    } finally { lock.current = false; if (!request.signal.aborted) setBusy(false) }
  }
  return <Dialog title={item ? `Chỉnh sửa: ${item.username}` : 'Tạo tài khoản'} onClose={guard.close} busy={busy}><form onSubmit={save} className="form-stack">{error && <Notice kind="error">{error}</Notice>}<fieldset disabled={busy} className="form-stack">
    {!item && <><Field label="Tên đăng nhập" required hint="3–64 ký tự: chữ Latin, số, dấu chấm, gạch dưới hoặc gạch ngang."><input required autoComplete="off" value={username} onChange={event => setUsername(event.target.value)} aria-invalid={!!fieldError.username} />{fieldError.username && <small className="field-validation" role="alert">{fieldError.username}</small>}</Field><Field label="Mật khẩu" required hint="12–128 ký tự. Không tự bỏ khoảng trắng trong mật khẩu."><input required type="password" autoComplete="new-password" value={password} onChange={event => setPassword(event.target.value)} aria-invalid={!!fieldError.password} />{fieldError.password && <small className="field-validation" role="alert">{fieldError.password}</small>}</Field><Field label="Xác nhận mật khẩu" required><input required type="password" autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} aria-invalid={!!fieldError.confirmation} />{fieldError.confirmation && <small className="field-validation" role="alert">{fieldError.confirmation}</small>}</Field></>}
    <Field label="Vai trò"><select value={role} onChange={event => { setRole(event.target.value as UserRole); setConfirmed(false) }}><option value="data_steward">Người phụ trách dữ liệu</option><option value="data_owner">Data Owner</option><option value="admin">Quản trị viên</option></select></Field>
    {item && <><label className="check-line"><input type="checkbox" checked={active} onChange={event => { setActive(event.target.checked); setConfirmed(false) }} />Tài khoản đang hoạt động</label><Notice kind="warning">Sau khi lưu, tài khoản này cần đăng nhập lại nếu vai trò hoặc trạng thái thay đổi.{!active && ' Tài khoản vô hiệu hóa sẽ không thể đăng nhập.'}</Notice><label className="check-line"><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />Tôi xác nhận thay đổi và thu hồi các phiên bị ảnh hưởng.</label></>}
    <div className="dialog-footer"><Button onClick={guard.close}>Hủy</Button><Button tone="primary" type="submit" disabled={busy || (item ? !dirty || !confirmed : false)}><Check size={17} />{busy ? 'Đang lưu…' : item ? 'Lưu thay đổi' : 'Xác nhận tạo'}</Button></div>
  </fieldset></form></Dialog>
}
