import { ruleFeedback } from '../api/ruleErrors'
import { useId, useRef, useState } from 'react'
import { Check, LoaderCircle } from 'lucide-react'
import { patchColumnDescription, patchDatasetMetadata } from '../api/metadata'
import { createRule, patchRule } from '../api/rules'
import type { DatasetColumn } from '../api/datasets'
import type { QualityRule, RuleConfig, RuleType } from '../api/rules'
import type { CatalogEntry } from './api'
import { Button, Dialog, Field, Notice, ruleLabels, useFormGuard } from './ui'

export function MetadataDialog({ dataset, column, onClose, saved }: { dataset: CatalogEntry; column?: DatasetColumn; onClose: () => void; saved: () => void }) {
  const initial = { name: dataset.name, owner: dataset.owner ?? '', source: dataset.source ?? '', description: column ? column.description ?? '' : dataset.description ?? '' }
  const [draft, setDraft] = useState(initial)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const lock = useRef(false)
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial)
  const guard = useFormGuard(dirty, busy, onClose)
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (lock.current || !dirty) return
    lock.current = true; setBusy(true); setError('')
    try {
      if (column) await patchColumnDescription(dataset.id, column.id, draft.description || null)
      else await patchDatasetMetadata(dataset.id, Object.fromEntries(Object.entries(draft).filter(([key, value]) => value !== initial[key as keyof typeof initial])))
      guard.markSaved(); onClose(); saved()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Không thể lưu thay đổi.') }
    finally { lock.current = false; setBusy(false) }
  }
  return <Dialog title={column ? `Mô tả trường: ${column.name}` : 'Chỉnh sửa bộ dữ liệu'} onClose={guard.close} busy={busy}><form className="form-stack" onSubmit={save}>{error && <Notice kind="error">{error}</Notice>}<fieldset disabled={busy} className="form-stack">
    {!column && <><Field label="Tên bộ dữ liệu" required><input required pattern=".*\S.*" value={draft.name} onChange={event => setDraft({ ...draft, name: event.target.value })} /></Field><Field label="Người phụ trách" required hint="Thông tin người liên hệ, không thay đổi quyền truy cập."><input required pattern=".*\S.*" value={draft.owner} onChange={event => setDraft({ ...draft, owner: event.target.value })} /></Field><Field label="Nguồn / bộ phận"><input value={draft.source} onChange={event => setDraft({ ...draft, source: event.target.value })} /></Field></>}
    <Field label={column ? 'Ý nghĩa và ví dụ giá trị' : 'Mô tả'} hint={column ? 'Ví dụ: Mã định danh duy nhất của khách hàng, như KH001.' : undefined}><textarea rows={4} value={draft.description} onChange={event => setDraft({ ...draft, description: event.target.value })} /></Field>
    <div className="dialog-footer"><Button onClick={guard.close}>Hủy</Button><Button tone="primary" type="submit" disabled={!dirty || busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />}Lưu thay đổi</Button></div></fieldset></form></Dialog>
}

const EMAIL = '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}'
const kinds = [ ['required', 'Không được thiếu'], ['unique', 'Không được trùng'], ['email', 'Định dạng email'], ['integer', 'Số nguyên'], ['decimal', 'Số thập phân'], ['date_format', 'Ngày tháng'], ['boolean', 'Đúng / sai'], ['numeric_range', 'Khoảng giá trị số'], ['allowed_values', 'Danh sách giá trị'], ['pattern', 'Mẫu tùy chỉnh (nâng cao)'] ]
function kindOf(rule?: QualityRule) { return rule?.rule_type === 'data_type' ? rule.config.type ?? 'integer' : rule?.rule_type === 'pattern' && rule.config.pattern === EMAIL ? 'email' : rule?.rule_type ?? 'required' }
type RuleDialogProps = {dataset:CatalogEntry;saved:()=>void;onClose:()=>void;batchId?:number} & ({mode:'create';rule?:never}|{mode:'edit';rule:QualityRule})
export function RuleDialog({ dataset, rule, mode, saved, onClose, batchId }: RuleDialogProps) {
  const [name, setName] = useState(rule?.name ?? '')
  const [kind, setKind] = useState(kindOf(rule))
  const [columns, setColumns] = useState(rule?.columns ?? [dataset.columns[0]?.name ?? ''])
  const [active, setActive] = useState(rule?.is_active ?? true)
  const [format, setFormat] = useState(rule?.config.format ?? 'YYYY-MM-DD')
  const [dateMin, setDateMin] = useState(rule?.rule_type === 'date_format' ? rule.config.min ?? '' : '')
  const [dateMax, setDateMax] = useState(rule?.rule_type === 'date_format' ? rule.config.max ?? '' : '')
  const [min, setMin] = useState(rule?.config.min ?? '0')
  const [max, setMax] = useState(rule?.config.max ?? '100')
  const [values, setValues] = useState(rule?.config.values?.join('\n') ?? '')
  const [pattern, setPattern] = useState(rule?.config.pattern ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors,setFieldErrors] = useState<Record<string,string>>({})
  const [technical,setTechnical] = useState('')
  const feedbackId=useId()
  const lock = useRef(false)
  const initial = useRef(JSON.stringify({ name, kind, columns, active, format, min, max, dateMin, dateMax, values, pattern }))
  const dirty = initial.current !== JSON.stringify({ name, kind, columns, active, format, min, max, dateMin, dateMax, values, pattern })
  const guard = useFormGuard(dirty, busy, onClose)
  const errorProps=(field:string)=>({'aria-invalid':!!fieldErrors[field],'aria-describedby':fieldErrors[field]?`${feedbackId}-${field}`:undefined})
  function changeKind(value: string) { setFieldErrors({});setError('');setTechnical(''); setKind(value); if (value !== 'unique') setColumns(columns.slice(0, 1)) }
  async function save(event: React.FormEvent) {
    event.preventDefault(); if (lock.current) return
    setFieldErrors({});setError('');setTechnical('')
    if (!columns.length || columns.some(column => !column)) { setFieldErrors({columns:'Chọn ít nhất một trường áp dụng.'}); return }
    let rule_type: RuleType = kind as RuleType; let config: RuleConfig = {}
    if (['integer', 'decimal', 'boolean'].includes(kind)) { rule_type = 'data_type'; config = { type: kind } }
    else if (kind === 'date_format') config = { format, ...((dateMin || dateMax) ? { min: dateMin, max: dateMax } : {}) }
    else if (kind === 'numeric_range') {
      if (!min.trim() || !max.trim() || !Number.isFinite(Number(min)) || !Number.isFinite(Number(max)) || Number(min) > Number(max)) { const message='Hai biên phải là số hữu hạn; giá trị nhỏ nhất không được lớn hơn giá trị lớn nhất.';setFieldErrors({min:message,max:message});return }
      config = { min, max }
    } else if (kind === 'allowed_values') config = { values: values.split('\n').filter(value => value.trim().length > 0) }
    else if (kind === 'email' || kind === 'pattern') { rule_type = 'pattern'; config = { pattern: kind === 'email' ? EMAIL : pattern, dialect: 're2-v1' } }
    lock.current = true; setBusy(true); setError('')
    try {
      const body = { name: name.trim(), rule_type, columns, config, is_active: active }
      if (mode==='edit') await patchRule(dataset.id, rule.id, body, undefined, batchId); else await createRule(dataset.id, body, undefined, batchId)
      guard.markSaved(); onClose(); saved()
    } catch (cause) {
      const feedback=ruleFeedback(cause,kind)
      const fields=feedback.field==='range'?['min','max']:feedback.field==='dates'?['dateMin','dateMax']:feedback.field?[feedback.field]:[]
      if(fields.length)setFieldErrors(Object.fromEntries(fields.map(field=>[field,feedback.message])));else setError(feedback.message)
      setTechnical(feedback.detail??'')
    }
    finally { lock.current = false; setBusy(false) }
  }
  return <Dialog title={mode==='edit' ? 'Chỉnh sửa quy tắc' : 'Thêm quy tắc kiểm tra'} description={`${dataset.name} · ${batchId ? `Đợt #${batchId}` : "Quy tắc mẫu"}`} busy={busy} onClose={guard.close}><form className="form-stack" data-rule-mode={mode} data-rule-id={rule?.id} onSubmit={save} onChange={event=>{if(event.target instanceof HTMLElement){const field=event.target.dataset.ruleField;if(field){setFieldErrors(current=>{const next={...current};delete next[field];if(field==='min'||field==='max'){delete next.min;delete next.max}if(field==='dateMin'||field==='dateMax'){delete next.dateMin;delete next.dateMax}return next});setTechnical('')}}}}>{error && <Notice kind="error">{error}</Notice>}{technical&&<details className="rule-error-details"><summary>Chi tiết kỹ thuật</summary><p>{technical}</p></details>}<fieldset disabled={busy} className="form-stack">
    <Field error={fieldErrors.name} errorId={`${feedbackId}-name`} label="Tên quy tắc" required hint="Đặt tên dễ hiểu, ví dụ: Mã khách hàng không được thiếu."><input data-rule-field="name" {...errorProps('name')} required pattern=".*\S.*" value={name} onChange={event => setName(event.target.value)} /></Field>
    <Field error={fieldErrors.kind} errorId={`${feedbackId}-kind`} label="Loại kiểm tra" required><select data-rule-field="kind" {...errorProps('kind')} value={kind} onChange={event => changeKind(event.target.value)}>{kinds.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></Field>
    {kind === 'unique' ? <fieldset className="checkbox-list"><legend>Trường cần duy nhất *</legend>{dataset.columns.map(column => <label key={column.id}><input type="checkbox" checked={columns.includes(column.name)} onChange={event => setColumns(event.target.checked ? [...columns, column.name] : columns.filter(name => name !== column.name))} />{column.name}</label>)}{fieldErrors.columns&&<small role="alert">{fieldErrors.columns}</small>}<small>Chọn nhiều trường để kiểm tra tổ hợp giá trị duy nhất.</small></fieldset> : <Field error={fieldErrors.columns} errorId={`${feedbackId}-columns`} label="Trường áp dụng" required><select data-rule-field="columns" {...errorProps('columns')} value={columns[0]} onChange={event => setColumns([event.target.value])}>{dataset.columns.map(column => <option key={column.id}>{column.name}</option>)}</select></Field>}
    {kind === 'date_format' && <Field label="Định dạng ngày" hint="Kiểm tra cả định dạng lẫn ngày có tồn tại trong lịch."><select value={format} onChange={event => setFormat(event.target.value)}><option>YYYY-MM-DD</option><option>DD/MM/YYYY</option><option>MM/DD/YYYY</option></select></Field>}
    {kind === 'date_format' && <div className="form-grid"><Field error={fieldErrors.dateMin} errorId={`${feedbackId}-dateMin`} label="Ngày nhỏ nhất (tùy chọn)"><input data-rule-field="dateMin" {...errorProps('dateMin')} type="date" value={dateMin} onChange={e => setDateMin(e.target.value)} /></Field><Field error={fieldErrors.dateMax} errorId={`${feedbackId}-dateMax`} label="Ngày lớn nhất (cần cả hai biên)"><input data-rule-field="dateMax" {...errorProps('dateMax')} type="date" value={dateMax} onChange={e => setDateMax(e.target.value)} /></Field></div>}
    {kind === 'numeric_range' && <div className="form-grid"><Field error={fieldErrors.min} errorId={`${feedbackId}-min`} label="Nhỏ nhất" required><input data-rule-field="min" {...errorProps('min')} required inputMode="decimal" value={min} onChange={event => setMin(event.target.value)} /></Field><Field error={fieldErrors.max} errorId={`${feedbackId}-max`} label="Lớn nhất" required><input data-rule-field="max" {...errorProps('max')} required inputMode="decimal" value={max} onChange={event => setMax(event.target.value)} /></Field></div>}
    {kind === 'allowed_values' && <Field error={fieldErrors.values} errorId={`${feedbackId}-values`} label="Các giá trị được chấp nhận" required hint="Mỗi dòng một giá trị, tối đa 100. Phân biệt hoa thường và khoảng trắng."><textarea data-rule-field="values" {...errorProps('values')} required rows={4} value={values} onChange={event => setValues(event.target.value)} /></Field>}
    {kind === 'pattern' && <Field error={fieldErrors.pattern} errorId={`${feedbackId}-pattern`} label="Mẫu định dạng" required hint="Dành cho người có kinh nghiệm. Toàn bộ giá trị phải khớp mẫu; phân biệt hoa thường."><input data-rule-field="pattern" {...errorProps('pattern')} required value={pattern} onChange={event => setPattern(event.target.value)} /></Field>}
    <div className="rule-example">{kind === 'required' ? <><strong>Giá trị nào được coi là thiếu?</strong><p>Ô trống hoặc chỉ có khoảng trắng đều là lỗi.</p></> : kind === 'unique' ? <><strong>Mỗi giá trị chỉ xuất hiện một lần</strong><p>Giữ nguyên hoa thường và khoảng trắng. Các giá trị trống được bỏ qua.</p></> : <><strong>Ví dụ {kind === 'email' ? 'email' : kind === 'date_format' ? 'ngày tháng' : kind === 'integer' ? 'số nguyên' : kind === 'decimal' ? 'số thập phân' : kind === 'boolean' ? 'đúng / sai' : 'áp dụng'}</strong><p>{kind === 'email' ? 'Hợp lệ: mau@example.com · Không hợp lệ: mau@' : kind === 'integer' ? 'Hợp lệ: 12, -3 · Không hợp lệ: 12.5' : kind === 'decimal' ? 'Hợp lệ: 12.5, -3 · Không hợp lệ: mười' : kind === 'date_format' ? `Hợp lệ: ${format === 'YYYY-MM-DD' ? '2026-12-31' : format === 'DD/MM/YYYY' ? '31/12/2026' : '12/31/2026'} · Ngày 30/02 luôn không hợp lệ.` : kind === 'boolean' ? 'Chỉ chấp nhận true hoặc false viết thường.' : kind === 'numeric_range' ? `Chấp nhận cả hai biên: ${min} đến ${max}.` : 'Giá trị phải phù hợp với cấu hình phía trên.'}</p><small>Giá trị trống được bỏ qua. Thêm quy tắc “Không được thiếu” nếu trường bắt buộc.</small></>}</div>
    <label className="check-line"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />Bật quy tắc khi chạy kiểm tra</label>
    <div className="dialog-footer"><Button onClick={guard.close}>Hủy</Button><Button tone="primary" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />}Lưu quy tắc</Button></div>
  </fieldset></form></Dialog>
}
export function ruleDescription(rule: Pick<QualityRule, 'rule_type' | 'config'>) {
  if (rule.rule_type === 'numeric_range') return `${rule.config.min} ≤ giá trị ≤ ${rule.config.max}`
  if (rule.rule_type === 'date_format') return `${rule.config.format}${rule.config.min ? ` · [${rule.config.min}, ${rule.config.max}]` : ''}`
  if (rule.rule_type === 'data_type') return ({ integer: 'Số nguyên', decimal: 'Số thập phân', boolean: 'true / false' } as Record<string, string>)[rule.config.type ?? '']
  if (rule.rule_type === 'allowed_values') return rule.config.values?.join(', ')
  if (rule.rule_type === 'pattern') return rule.config.pattern === EMAIL ? 'Email · ví dụ: mau@example.com' : rule.config.pattern
  return ruleLabels[rule.rule_type]
}
