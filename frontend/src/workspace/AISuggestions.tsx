import { useEffect, useRef, useState } from 'react'
import { Check, RefreshCw, Sparkles } from 'lucide-react'
import { AIError, createAIRule, initialDraft, previewAI, suggestAI } from '../api/ai'
import type { AIRuleInput, AIRuleType, Preview, Suggestion } from '../api/ai'
import { getRules } from './api'
import type { CatalogEntry } from './api'
import { Badge, Button, Dialog, Empty, Field, Notice, date, ruleLabels } from './ui'

export default function AISuggestions({ dataset, close, saved }: { dataset: CatalogEntry; close: () => void; saved: () => void }) {
  const [version, setVersion] = useState(dataset.versions[0]?.id ?? 0)
  const [columns, setColumns] = useState<string[]>([])
  const [descriptions, setDescriptions] = useState(true)
  const [statistics, setStatistics] = useState(true)
  const [preview, setPreview] = useState<Preview | null>(null)
  const [confirmed, setConfirmed] = useState(false)
  const [items, setItems] = useState<Suggestion[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [saving, setSaving] = useState(0)
  const [error, setError] = useState('')
  const [now, setNow] = useState(Date.now())
  const request = useRef<AbortController | null>(null)
  const lock = useRef(false)
  useEffect(() => () => request.current?.abort(), [])
  useEffect(() => { if (!preview || items) return; const timer = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(timer) }, [preview, items])
  const expired = !!preview && now >= Date.parse(preview.expires_at)
  const configured = preview?.provider_status === 'configured' && !!preview.provider && !!preview.model
  function invalidate() { request.current?.abort(); setPreview(null); setItems(null); setConfirmed(false); setError('') }
  async function send(kind: 'preview' | 'suggest') {
    if (lock.current || saving) return
    lock.current = true; setBusy(true); setError('')
    request.current?.abort(); const controller = new AbortController(); request.current = controller
    try {
      if (kind === 'preview') {
        setItems(null); setPreview(null); setConfirmed(false)
        const result = await previewAI(dataset.id, { version_id: version, columns, include_descriptions: descriptions, include_statistics: statistics }, controller.signal)
        if (!controller.signal.aborted) { setPreview(result); setNow(Date.now()) }
      } else if (preview) {
        const result = await suggestAI(dataset.id, version, preview, confirmed, controller.signal)
        if (!controller.signal.aborted) { setItems(result.suggestions); setConfirmed(false) }
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        setError(cause instanceof Error ? cause.message : 'Không lấy được gợi ý. Không tự gửi lại.'); setConfirmed(false)
        if (cause instanceof AIError && cause.status === 409) { setPreview(null); setItems(null) }
      }
    } finally { lock.current = false; if (!controller.signal.aborted) setBusy(false) }
  }
  return <Dialog title="AI gợi ý quy tắc" description={dataset.name} onClose={close} busy={busy || saving > 0} dirty={columns.length > 0 || !!preview || items !== null} wide><div className="form-stack">
    <Notice>Chỉ gửi thông tin cột và thống kê tổng hợp do bạn chọn, không gửi dữ liệu từng bản ghi hay giá trị mẫu. Mô tả cột cũng có thể chứa thông tin nhạy cảm; hãy xem đầy đủ nội dung trước khi đồng ý gửi.</Notice>
    <fieldset disabled={busy || saving > 0} className="form-stack"><Field label="Phiên bản dùng để gợi ý"><select value={version} onChange={event => { invalidate(); setVersion(Number(event.target.value)) }}>{dataset.versions.map(item => <option key={item.id} value={item.id}>v{item.version_number} · {item.original_filename}</option>)}</select></Field>
    <fieldset className="checkbox-list"><legend>Chọn cột (tối đa 30)</legend>{dataset.columns.map(column => <label key={column.id}><input type="checkbox" checked={columns.includes(column.name)} onChange={event => { invalidate(); setColumns(event.target.checked ? [...columns, column.name] : columns.filter(name => name !== column.name)) }} />{column.name}</label>)}</fieldset>
    <div className="form-grid"><label className="check-line"><input type="checkbox" checked={descriptions} onChange={event => { invalidate(); setDescriptions(event.target.checked) }} />Bao gồm mô tả cột</label><label className="check-line"><input type="checkbox" checked={statistics} onChange={event => { invalidate(); setStatistics(event.target.checked) }} />Bao gồm số bản ghi và số giá trị thiếu</label></div>
    {columns.length > 30 && <Notice kind="error">Chỉ chọn tối đa 30 cột mỗi lần xem trước.</Notice>}
    <div><Button disabled={!version || !columns.length || columns.length > 30} onClick={() => void send('preview')}><Sparkles size={17} />{busy ? 'Đang xử lý…' : 'Xem trước nội dung gửi'}</Button></div></fieldset>
    {error && <Notice kind="error">{error}</Notice>}
    {preview && <section className="ai-preview"><div className="section-label"><h3>Nội dung sẽ gửi</h3><Badge tone={configured ? 'primary' : 'warning'}>{configured ? `${preview.provider} · ${preview.model}` : 'AI chưa được cấu hình'}</Badge></div><p className="helper-text">Bản xem trước hết hạn lúc {date(preview.expires_at)}.</p><pre className="payload-preview" tabIndex={0} aria-label="Nội dung AI đầy đủ">{JSON.stringify(preview.payload, null, 2)}</pre>
      {!configured && <Notice kind="warning">Dịch vụ AI chưa được cấu hình trên máy chủ. Bạn vẫn có thể tạo đầy đủ quy tắc thủ công; không nhập khóa dịch vụ tại đây.</Notice>}
      {expired && items === null && <Notice kind="warning">Bản xem trước đã hết hạn. Bấm “Xem trước nội dung gửi” để tạo lại và xác nhận lại.</Notice>}
      {items === null && <div className="form-stack"><label className="check-line"><input type="checkbox" checked={confirmed} disabled={busy || !configured || expired} onChange={event => setConfirmed(event.target.checked)} />Tôi đã xem và đồng ý gửi đúng nội dung trên tới dịch vụ và mô hình đang hiển thị.</label><Button tone="primary" disabled={!confirmed || !configured || expired || busy} onClick={() => void send('suggest')}><Sparkles size={17} />{busy ? 'Đang chờ phản hồi…' : 'Xác nhận gửi và lấy gợi ý'}</Button></div>}
    </section>}
    {items !== null && (items.length ? <><Notice>AI chỉ gợi ý ba loại: không thiếu, duy nhất và khoảng số. Kiểm tra lý do, chỉnh cấu hình và xác nhận từng giả định trước khi lưu. Quy tắc mặc định tắt, áp dụng cho bộ dữ liệu và không tự chạy kiểm tra.</Notice>{items.map(item => <AIDraft key={item.suggestion_id} item={item} dataset={dataset} saved={saved} busyChange={delta => setSaving(count => count + delta)} />)}</> : <Empty title="Không có gợi ý đủ căn cứ" text="Đây không phải kết luận dữ liệu đạt chất lượng. Bạn vẫn có thể tạo quy tắc thủ công." />)}
  </div></Dialog>
}
function AIDraft({ item, dataset, saved, busyChange }: { item: Suggestion; dataset: CatalogEntry; saved: () => void; busyChange: (delta: number) => void }) {
  const [draft, setDraft] = useState<AIRuleInput>(() => initialDraft(item))
  const [assumptions, setAssumptions] = useState<boolean[]>(item.assumptions.map(() => false))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [uncertain, setUncertain] = useState(false)
  const [savedId, setSavedId] = useState<number | null>(null)
  const [comparison, setComparison] = useState<string[] | null>(null)
  const request = useRef<AbortController | null>(null)
  const lock = useRef(false)
  useEffect(() => () => request.current?.abort(), [])
  async function submit(event: React.FormEvent) {
    event.preventDefault(); if (lock.current || uncertain || savedId !== null || !assumptions.every(Boolean)) return
    if (!draft.columns.length) { setError('Chọn ít nhất một cột.'); return }
    lock.current = true; setBusy(true); busyChange(1); setError(''); const controller = new AbortController(); request.current = controller
    try { const rule = await createAIRule(dataset.id, draft, controller.signal); if (!controller.signal.aborted) { setSavedId(rule.id); saved() } }
    catch (cause) { if (!controller.signal.aborted) { const message = cause instanceof Error ? cause.message : 'Không thể lưu quy tắc.'; setError(message); setUncertain(/Mất kết nối|Không đọc|Không xác nhận/.test(message)) } }
    finally { lock.current = false; busyChange(-1); if (!controller.signal.aborted) setBusy(false) }
  }
  async function compare() {
    if (lock.current) return
    lock.current = true; setBusy(true); busyChange(1); const controller = new AbortController(); request.current = controller
    try { const rules = await getRules(dataset.id, controller.signal); if (!controller.signal.aborted) setComparison(rules.map(rule => `#${rule.id} · ${rule.name} · ${rule.columns.join(' + ')} · ${rule.is_active ? 'Đang bật' : 'Đã tắt'}`)) }
    catch (cause) { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Không thể đối chiếu quy tắc.') }
    finally { lock.current = false; busyChange(-1); if (!controller.signal.aborted) setBusy(false) }
  }
  return <article className="ai-draft"><div className="section-label"><h3>{item.name}</h3><Badge tone={savedId ? 'success' : 'neutral'}>{savedId ? `Đã lưu #${savedId}` : 'Chưa lưu'}</Badge></div><p><strong>Lý do gợi ý:</strong> {item.reason}</p>{error && <Notice kind="error">{error}</Notice>}{savedId !== null ? <Notice kind="success">Quy tắc đã được lưu. Đề xuất này không thể gửi lại.</Notice> : <form onSubmit={submit} className="form-stack"><fieldset disabled={busy} className="form-stack"><fieldset className="checkbox-list"><legend>Những giả định cần bạn xác nhận</legend>{item.assumptions.map((text, index) => <label key={index}><input type="checkbox" checked={assumptions[index]} onChange={event => setAssumptions(values => values.map((value, i) => i === index ? event.target.checked : value))} />{text}</label>)}</fieldset><div className="form-grid"><Field label="Tên quy tắc" required><input required pattern=".*\S.*" value={draft.name} onChange={event => setDraft({ ...draft, name: event.target.value })} /></Field><Field label="Loại quy tắc"><select value={draft.rule_type} onChange={event => { const rule_type = event.target.value as AIRuleType; setDraft({ ...draft, rule_type, columns: rule_type === 'unique' ? draft.columns : draft.columns.slice(0, 1), config: rule_type === 'numeric_range' ? { min: '0', max: '100' } : {} }) }}>{(['required', 'unique', 'numeric_range'] as const).map(type => <option key={type} value={type}>{ruleLabels[type]}</option>)}</select></Field></div>
    {draft.rule_type === 'unique' ? <fieldset className="checkbox-list"><legend>Trường cần duy nhất</legend>{dataset.columns.map(column => <label key={column.id}><input type="checkbox" checked={draft.columns.includes(column.name)} onChange={event => setDraft({ ...draft, columns: event.target.checked ? [...draft.columns, column.name] : draft.columns.filter(name => name !== column.name) })} />{column.name}</label>)}</fieldset> : <Field label="Trường áp dụng"><select value={draft.columns[0]} onChange={event => setDraft({ ...draft, columns: [event.target.value] })}>{dataset.columns.map(column => <option key={column.id}>{column.name}</option>)}</select></Field>}
    {draft.rule_type === 'numeric_range' && <div className="form-grid"><Field label="Nhỏ nhất" required><input required value={draft.config.min ?? ''} onChange={event => setDraft({ ...draft, config: { ...draft.config, min: event.target.value } })} /></Field><Field label="Lớn nhất" required><input required value={draft.config.max ?? ''} onChange={event => setDraft({ ...draft, config: { ...draft.config, max: event.target.value } })} /></Field></div>}
    <label className="check-line"><input type="checkbox" checked={draft.is_active} onChange={event => setDraft({ ...draft, is_active: event.target.checked })} />Bật quy tắc sau khi lưu (mặc định tắt)</label><Button tone="primary" type="submit" disabled={!assumptions.every(Boolean) || uncertain || busy}><Check size={17} />{busy ? 'Đang lưu…' : 'Lưu đề xuất thành quy tắc'}</Button></fieldset>
    {uncertain && <Notice kind="warning">Chưa xác nhận được kết quả ghi. Đối chiếu danh sách trước khi thử lại để tránh tạo quy tắc trùng.<div className="button-row"><Button disabled={busy} onClick={() => void compare()}><RefreshCw size={15} />Đối chiếu danh sách quy tắc</Button>{comparison && <Button onClick={() => { setUncertain(false); setError('') }}>Đã đối chiếu, cho phép thử lại thủ công</Button>}</div>{comparison && <ul>{comparison.map(value => <li key={value}>{value}</li>)}</ul>}</Notice>}
  </form>}</article>
}
