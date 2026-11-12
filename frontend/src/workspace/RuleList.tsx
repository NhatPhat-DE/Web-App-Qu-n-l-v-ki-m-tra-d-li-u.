import RuleEditorDialog from './RuleEditorDialog'
import type { RuleEditorIntent } from './RuleEditorDialog'
import { useState } from 'react'
import { Pencil, Plus, Search, Sparkles } from 'lucide-react'
import type { QualityRule } from '../api/rules'
import type { CatalogEntry } from './api'
import { getRulePage, getRules } from './api'
import { ruleDescription } from './EditDialogs'
import AISuggestions from './AISuggestions'
import { Badge, Button, Dialog, Empty, Field, LoadState, Notice, PageTitle, Pager, ruleLabels, useDebounced, useLoad } from './ui'

export default function RuleList({ datasets, embedded = false, batchId, changed, readOnly=false }: { datasets: CatalogEntry[]; embedded?: boolean; batchId?: number; changed?: () => void;readOnly?:boolean }) {
  const [selected, setSelected] = useState(embedded ? String(datasets[0]?.id ?? '') : '')
  const query=new URLSearchParams(location.hash.split('?')[1]),search=query.get('rule_q')??'',page=Math.max(1,Number(query.get('rule_page'))||1)
  function ruleQuery(patch:Record<string,string|null>,replace=false){const p=new URLSearchParams(location.hash.split('?')[1]);for(const [key,value] of Object.entries(patch)){if(value)p.set(key,value);else p.delete(key)}const href=location.hash.split('?')[0]+'?'+p;if(replace){history.replaceState(null,'',href);dispatchEvent(new HashChangeEvent('hashchange'))}else if(href!==location.hash)location.hash=href}
  const setSearch=(v:string)=>ruleQuery({rule_q:v||null,rule_page:null},true),setPage=(v:number)=>ruleQuery({rule_page:v>1?String(v):null})
  const q = useDebounced(search)
  const [edit, setEdit] = useState<{ dataset: CatalogEntry; intent: RuleEditorIntent } | null>(null)
  const [ai, setAI] = useState<CatalogEntry | null>(null)
  const [pick, setPick] = useState<'rule' | 'ai' | null>(null)
  const [pickId, setPickId] = useState(datasets[0]?.id ?? 0)
  const [message, setMessage] = useState('')
  const serverPaged = !!selected && !q
  const currentDataset = datasets.find(item => String(item.id) === selected) ?? datasets[0]
  const hasColumns = !embedded || (currentDataset?.columns?.length ?? 0) > 0

  const list = useLoad(async signal => {
    const chosen = selected ? datasets.filter(item => String(item.id) === selected) : datasets
    if (serverPaged && chosen[0]) { const data = await getRulePage(chosen[0].id, page, signal, batchId); return { items: data.items.map(rule => ({ dataset: chosen[0], rule })), total: data.total } }
    const items: { dataset: CatalogEntry; rule: QualityRule }[] = []
    let cursor = 0
    await Promise.all(Array.from({ length: Math.min(4, chosen.length) }, async () => { while (cursor < chosen.length) { const dataset = chosen[cursor++]; const rules = await getRules(dataset.id, signal, batchId); items.push(...rules.map(rule => ({ dataset, rule }))) } }))
    const filtered = items.filter(item => item.rule.name.toLocaleLowerCase('vi').includes(q.toLocaleLowerCase('vi'))).sort((a, b) => b.rule.id - a.rule.id)
    return { items: filtered.slice((page - 1) * 10, page * 10), total: filtered.length }
  }, [selected, datasets, q, page, serverPaged, batchId])
  function open(dataset: CatalogEntry, mode: 'rule' | 'ai') { if (mode === 'ai') setAI(dataset); else setEdit({ dataset, intent:{mode:'create'} }) }
  function add(mode: 'rule' | 'ai') { const dataset = datasets.find(item => String(item.id) === selected); if (dataset) open(dataset, mode); else setPick(mode) }
  function saved() { setMessage('Đã lưu quy tắc.'); list.reload(); changed?.() }
  const buttons = <><Button disabled={readOnly || !datasets.length || !hasColumns || !!batchId} title={batchId ? "AI hiện lưu vào mẫu; cấu hình đợt dùng form thủ công" : undefined} onClick={() => add('ai')}><Sparkles size={16} />AI gợi ý quy tắc</Button><Button tone="primary" disabled={readOnly || !datasets.length || !hasColumns} onClick={() => add('rule')}><Plus size={16} />{batchId?'Thêm quy tắc':'Thêm quy tắc mẫu'}</Button></>
  return <>{!embedded && <PageTitle eyebrow="CHẤT LƯỢNG DỮ LIỆU" title="Quy tắc mẫu" description="Chỉ dùng để sao chép khi tạo đợt dữ liệu mới. Sửa mẫu không thay đổi các đợt đã tạo." action={buttons} />}{message && <Notice kind="success">{message}</Notice>}<section className="panel"><div className="panel-heading"><div><h2>{batchId ? 'Quy tắc riêng của đợt' : 'Quy tắc mẫu của bộ dữ liệu'}</h2><p>{batchId?'Chỉ áp dụng trong đợt này. Thay đổi dành cho các lần kiểm tra tiếp theo, kết quả cũ giữ nguyên.':'Chỉ sao chép khi tạo đợt mới. Sửa mẫu không cập nhật quy tắc của các đợt đã tạo.'}</p></div>{embedded && <div className="button-row">{buttons}</div>}</div>
    {embedded && !hasColumns && <Notice kind="warning">Bộ dữ liệu chưa có file dữ liệu nào. Vui lòng tải file CSV đầu tiên để nhận diện các cột trước khi thiết lập quy tắc.</Notice>}
    <div className="filter-bar"><Field label="Tìm quy tắc"><div className="search-input"><Search size={17} /><input type="search" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} placeholder="Tìm theo tên quy tắc…" /></div></Field>{!embedded && <Field label="Bộ dữ liệu"><select value={selected} onChange={event => { setSelected(event.target.value); setPage(1) }}><option value="">Tất cả bộ dữ liệu</option>{datasets.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>}</div>
    {!serverPaged && <p className="helper-text panel-pad">Tìm tên và tổng hợp nhiều bộ dữ liệu áp dụng trên toàn bộ quy tắc đã tải đủ. Khi chọn một bộ dữ liệu, danh sách dùng phân trang trên máy chủ.</p>}<LoadState loading={list.loading} error={list.error} retry={list.reload} />{list.data && (list.data.items.length ? <><div className="table-scroll"><table><thead><tr><th>Quy tắc</th>{!embedded && <th>Bộ dữ liệu</th>}<th>Trường áp dụng</th><th>Loại kiểm tra</th><th>Cấu hình</th><th>Trạng thái</th><th></th></tr></thead><tbody>{list.data.items.map(({ dataset, rule }) => <tr key={rule.id}><td><strong>{rule.name}</strong></td>{!embedded && <td><a href={`#/datasets/${dataset.id}/rules`}>{dataset.name}</a></td>}<td><code>{rule.columns.join(' + ')}</code></td><td>{ruleLabels[rule.rule_type]}</td><td className="wrap-cell">{ruleDescription(rule)}</td><td><Badge tone={rule.is_active ? 'success' : 'neutral'}>{rule.is_active ? 'Đang bật' : 'Đã tắt'}</Badge></td><td><Button disabled={readOnly} tone="ghost" aria-label={`Sửa quy tắc ${rule.name}`} onClick={() => setEdit({ dataset, intent:{mode:'edit',ruleId:rule.id} })}><Pencil size={16} />Sửa</Button></td></tr>)}</tbody></table></div><Pager page={page} total={list.data.total} change={setPage} /></> : <Empty title={q ? 'Không tìm thấy quy tắc' : 'Chưa có quy tắc kiểm tra'} text={!hasColumns ? 'Bộ dữ liệu chưa có file nào. Hãy tải file CSV đầu tiên để nhận diện các cột trước khi thêm quy tắc.' : datasets.length ? 'Thêm quy tắc hoặc thử tên tìm kiếm khác.' : 'Tạo bộ dữ liệu và tải CSV trước khi thêm quy tắc.'} action={datasets.length > 0 && hasColumns && <Button onClick={() => add('rule')}><Plus size={16} />Thêm quy tắc đầu tiên</Button>} />)}</section>
    {pick && <Dialog title="Chọn bộ dữ liệu" onClose={() => setPick(null)}><div className="form-stack"><Field label="Áp dụng cho bộ dữ liệu"><select value={pickId} onChange={event => setPickId(Number(event.target.value))}>{datasets.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field><Button tone="primary" onClick={() => { const dataset = datasets.find(item => item.id === pickId); if (dataset) { open(dataset, pick); setPick(null) } }}>Tiếp tục</Button></div></Dialog>}
    {edit && <RuleEditorDialog batchId={batchId} dataset={edit.dataset} intent={edit.intent} saved={saved} onClose={() => setEdit(null)} />}
    {ai && <AISuggestions dataset={ai} close={() => setAI(null)} saved={saved} />}
  </>
}
