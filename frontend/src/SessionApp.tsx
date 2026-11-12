import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, Check, Database, Eye, EyeOff, FileSpreadsheet, ShieldCheck } from 'lucide-react'
import App from './workspace/DataCheckApp'
import { Button, Notice } from './workspace/ui'
import { ThemeSwitcher } from './workspace/ThemeSwitcher'
import { fetchMe, login, logout, AuthError } from './api/auth'
import type { AuthState } from './api/auth'
import { configureBusiness, disconnectBusiness, clearBusinessRequests } from './api/business'

function LoginForm({ csrf, busy, message, submit, refresh }: { csrf: string; busy: boolean; message: string; submit: (username: string, password: string) => Promise<boolean>; refresh: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { input.current?.focus() }, [])
  async function send(event: FormEvent) {
    event.preventDefault()
    if (!busy && await submit(username, password)) setPassword('')
  }
  return <div className="auth-shell"><aside className="auth-story"><a className="brand" href="#"><span><Database size={24} /></span><div>DataCheck<small>Danh mục & chất lượng dữ liệu</small></div></a><div className="auth-story-main"><span className="eyebrow">KHÔNG GIAN CHO DỮ LIỆU TỐT HƠN</span><h2>Hiểu dữ liệu.<br />Yên tâm làm việc.</h2><p>Tập trung danh mục, quản lý phiên bản và kiểm tra chất lượng trong một luồng rõ ràng.</p><div className="auth-illustration"><div className="auth-file"><FileSpreadsheet size={27} /><div><strong>Dữ liệu khách hàng.csv</strong><span>Phiên bản mới · Sẵn sàng kiểm tra</span></div><Check size={20} /></div><div className="auth-check"><ShieldCheck size={23} /><div><strong>Mỗi quy tắc, một bước an tâm.</strong><span>Đầy đủ · Duy nhất · Đúng định dạng</span></div></div></div><ul><li><Check size={17} />Biết dữ liệu ở đâu và ai phụ trách</li><li><Check size={17} />Tìm đúng bản ghi cần kiểm tra lại</li><li><Check size={17} />Giữ lại lịch sử của từng phiên bản</li></ul></div><p className="auth-footer">DataCheck · Danh mục và chất lượng dữ liệu</p></aside><main className="auth-main"><div className="auth-theme-bar"><ThemeSwitcher /></div><section className="login-card"><span className="auth-glyph"><Database size={26} /></span><h1>Chào mừng trở lại</h1><p>Đăng nhập để tiếp tục quản lý dữ liệu của bạn.</p>{message && <Notice kind="error">{message}</Notice>}
    <form onSubmit={send} aria-busy={busy}><fieldset disabled={busy} className="form-stack"><label className="field" htmlFor="login-username"><span>Tên đăng nhập</span><input ref={input} id="login-username" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder="Nhập tên đăng nhập" required /></label><label className="field" htmlFor="login-password"><span>Mật khẩu</span></label><div className="password-field"><input id="login-password" type={visible ? 'text' : 'password'} autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Nhập mật khẩu" required /><button type="button" className="password-toggle" aria-label={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'} aria-pressed={visible} onClick={() => setVisible(v => !v)}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button></div><Button tone="primary" className="login-submit" type="submit" disabled={!csrf}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}<ArrowRight size={17} /></Button></fieldset></form><Button tone="ghost" disabled={busy} onClick={refresh}>Kiểm tra lại phiên đăng nhập</Button><p className="login-note"><ShieldCheck size={17} />Sử dụng tài khoản đã được cấp bởi quản trị viên.</p></section></main></div>
}

export default function SessionApp() {
  const [state, setState] = useState<AuthState | null>(null)
  const [checking, setChecking] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const current = useRef<AbortController | null>(null)
  const sequence = useRef(0)
  const alive = useRef(false)
  const lock = useRef(false)
  async function check(keepBusiness = false) {
    const preserve = keepBusiness && state?.authenticated
    const id = ++sequence.current
    current.current?.abort(); const controller = new AbortController(); current.current = controller
    if (!preserve) setChecking(true)
    setError('')
    try {
      const data = await fetchMe(controller.signal)
      if (alive.current && id === sequence.current) { setState(data); setChecking(false); if (preserve) setMessage('Đã làm mới trạng thái phiên. Hãy thử lại thao tác thủ công; hệ thống không tự gửi lại.') }
    } catch (cause) {
      if (alive.current && id === sequence.current) {
        const message = cause instanceof Error ? cause.message : 'Không thể kiểm tra phiên.'
        if (preserve) setMessage(message); else setError(message)
        setChecking(false)
      }
    }
  }
  useEffect(() => { alive.current = true; void check(); return () => { alive.current = false; sequence.current++; current.current?.abort(); disconnectBusiness() } }, [])
  useEffect(() => {
    if (!state?.authenticated) { disconnectBusiness(); return }
    configureBusiness(state.csrf_token, reason => {
      if (reason === 'expired') { clearBusinessRequests(); setState(null); setMessage('Phiên không còn hiệu lực. Vui lòng đăng nhập lại.'); void check() }
      else setMessage('CSRF không hợp lệ. Bấm Kiểm tra lại phiên rồi thử thao tác thủ công; không tự gửi lại.')
    })
    return () => disconnectBusiness()
  }, [state])
  useEffect(() => {
    if (!state?.authenticated || busy) return
    const remaining = Date.parse(state.expires_at) - Date.now()
    const timeout = window.setTimeout(() => { if (!lock.current) { setMessage('Phiên đã hết hạn. Vui lòng đăng nhập lại.'); void check() } }, Math.max(0, remaining))
    const focus = () => { if (!lock.current && Date.now() >= Date.parse(state.expires_at)) { setMessage('Kiểm tra lại phiên đã hết hạn.'); void check() } }
    window.addEventListener('focus', focus)
    return () => { clearTimeout(timeout); window.removeEventListener('focus', focus) }
  }, [state, busy])
  async function mutate(kind: 'login' | 'logout', username = '', password = '') {
    if (lock.current || !state) return false
    lock.current = true; setBusy(true); setMessage('')
    const id = ++sequence.current
    current.current?.abort(); const controller = new AbortController(); current.current = controller
    try {
      if (kind === 'login') {
        const data = await login(username, password, state.csrf_token, controller.signal)
        if (alive.current && id === sequence.current) setState(data)
      } else {
        await logout(state.csrf_token, controller.signal)
        if (alive.current && id === sequence.current) { clearBusinessRequests(); setState(null); await check() }
      }
      return true
    } catch (cause) {
      if (alive.current && id === sequence.current) {
        const failure = cause instanceof Error ? cause.message : 'Không thể xác nhận thao tác.'
        setMessage(cause instanceof AuthError && cause.status === 429 ? `${failure} Chờ ${cause.retryAfter} giây trước khi thử lại.` : failure)
        if (cause instanceof AuthError && cause.status === 403) { setMessage(`${failure} Đang lấy challenge mới; hãy nhập và gửi lại thủ công.`); await check(kind === 'logout') }
      }
      return false
    } finally { lock.current = false; if (alive.current) setBusy(false) }
  }
  if (checking || error || !state) return <div className="session-check"><section className="login-card"><span className="auth-glyph"><Database size={26} /></span><h1>DataCheck</h1>{checking ? <p role="status">Đang kiểm tra phiên đăng nhập…</p> : <><Notice kind="error">{error || 'Chưa xác nhận được phiên.'}</Notice><Button onClick={() => void check()}>Thử lại</Button></>}</section></div>
  if (!state.authenticated) return <LoginForm csrf={state.csrf_token} busy={busy} message={message} submit={(name, pass) => mutate('login', name, pass)} refresh={() => void check()} />
  return <App key={state.user.id + ':' + state.user.role} user={state.user} logoutBusy={busy} logoutMessage={message} onLogout={() => void mutate('logout')} onCheckSession={() => void check(true)} />
}
