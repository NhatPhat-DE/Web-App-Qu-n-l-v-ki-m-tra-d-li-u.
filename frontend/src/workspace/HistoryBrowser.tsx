import { batchHref, historyHref, comparisonHref, queryBatch, globalHistoryHref, isScopeId } from './scopeNavigation'
import { batchText } from './presentation'
import type { DataBatchItem } from '../api/datasets'
import { useEffect, useState } from 'react'
import { ArrowLeftRight, ArrowUpRight, Play, Search, TrendingUp } from 'lucide-react'
import { allPages, getRunPage, namedRuns } from './api'
import type { CatalogEntry, NamedRun } from './api'
import type { RunSummary } from '../api/runs'
import { Button, Empty, ExecutionBadge, Field, LoadState, PageTitle, Pager, QualityBadge, Notice, date, number, useLoad } from './ui'

const batchName=(d:CatalogEntry,id?:number)=>{const b=d.batch_summaries?.find(b=>b.batch_id===id);return b?`${b.batch_name}${b.period_label&&!b.batch_name.includes(b.period_label)?` · ${b.period_label}`:''}`:'Tên đợt chưa tải'}

export function HistoryPage({ datasets, embedded = false, run }: { datasets: CatalogEntry[]; embedded?: boolean; run: () => void }) {
  const [search, setSearch] = useState('')
  const [dataset, setDataset] = useState(() => {const id=new URLSearchParams(location.hash.split('?')[1]).get('dataset_id')??'';return embedded?String(datasets[0]?.id??''):isScopeId(id)?id:''})
  const [batch,setBatch] = useState(() => { const scope=queryBatch(new URLSearchParams(location.hash.split('?')[1])); return scope==='all'?'':scope })
  const [version, setVersion] = useState('')
  const [status, setStatus] = useState('')
  const [quality, setQuality] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [page, setPage] = useState(1)
  const selected = datasets.find(item => String(item.id) === dataset)
  const batches=useLoad(signal=>selected?allPages<DataBatchItem>(`/api/datasets/${selected.id}/batches`,signal):Promise.resolve([]),[selected?.id])
  const invalidScope=!!batch && (!selected||batch==='invalid'||!!batches.data&&!batches.data.some(item=>String(item.id)===batch))
  const scopeName=batchText(batches.data?.find(item=>String(item.id)===batch))
  const name=(entry:CatalogEntry,id?:number)=>entry.id===selected?.id?batchText(batches.data?.find(item=>item.id===id)):batchName(entry,id)
  function chooseBatch(value:string){setVersion('');setPage(1);if(selected)location.hash=embedded?historyHref(selected.id,value):globalHistoryHref(String(selected.id),value);else setBatch(value)}
  useEffect(() => setPage(1), [search, dataset, batch, version, status, quality, from, to])
  const invalidDates = !!from && !!to && from > to
  const serverPaged = !!selected && !search && !status && !quality && !from && !to
  const list = useLoad(async signal => {
    if (invalidScope) return {items:[],total:0,page,page_size:10}
    if (serverPaged && selected) { const data = await getRunPage(selected.id, page, version, signal,batch); return { ...data, items: data.items.map(item => ({ ...item, dataset: selected })) } }
    let items: NamedRun[]
    if (selected) {
      const runs = await allPages<RunSummary>(`/api/datasets/${selected.id}/runs?${new URLSearchParams({...(version?{version_id:version}:{}),...(batch?{batch_id:batch}:{})})}`, signal)
      items = runs.map(item => ({ ...item, dataset: selected }))
    } else items = namedRuns(datasets)
    const filtered = items.filter(item => {
      const local = new Date(item.started_at)
      const day = `${local.getFullYear()}-${String(local.getMonth() + 1).padStart(2, '0')}-${String(local.getDate()).padStart(2, '0')}`
      return (!batch||String(item.batch_id)===batch) && !invalidDates && (!status || item.status === status) && (!quality || item.status === 'completed' && (quality === 'passed' ? item.error_row_count === 0 : (item.error_row_count ?? 0) > 0)) && (!from || day >= from) && (!to || day <= to) && `${item.dataset.name} #${item.run_id}`.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))
    })
    return { items: filtered.slice((page - 1) * 10, page * 10), total: filtered.length, page, page_size: 10 }
  }, [datasets, dataset, batch, version, search, status, quality, from, to, page, invalidDates, serverPaged,invalidScope])
  return <>{!embedded && <PageTitle eyebrow="THEO DÕI CHẤT LƯỢNG" title="Lịch sử kiểm tra" description="Mỗi lần chạy là một kết quả riêng, cùng các quy tắc đã áp dụng tại thời điểm đó." action={<Button tone="primary" disabled={!datasets.length} onClick={run}><Play size={17} />Chạy kiểm tra</Button>} />}<section className="panel"><div className="panel-heading"><div><h2>{batch ? `Lịch sử kiểm tra · ${invalidScope?'Đợt không hợp lệ':scopeName}` : embedded ? 'Lịch sử kiểm tra · tất cả đợt của bộ dữ liệu' : 'Lịch sử kiểm tra · tất cả bộ dữ liệu và đợt'}</h2><p>Đây là khu vực tổng hợp lịch sử; mỗi kết quả bên dưới vẫn thuộc đúng một đợt và phiên bản.</p></div>{selected && <div className="button-row"><a className="button button-secondary" href={comparisonHref(selected.id,batch)}><ArrowLeftRight size={16} />Đối chiếu hai lần</a><a className="button button-secondary" href={`#/datasets/${selected.id}/trend`}><TrendingUp size={16} />Xu hướng · tất cả đợt</a></div>}</div>
    {selected&&batch&&<nav className="scope-actions panel-pad" aria-label="Phạm vi lịch sử">{!invalidScope&&<a className="button button-secondary" href={batchHref(selected.id,Number(batch))}>Về đợt dữ liệu</a>}<a href={historyHref(selected.id)}>Lịch sử tất cả đợt</a></nav>}
    {invalidScope&&<Notice kind="error">Đợt trong URL không thuộc bộ dữ liệu này hoặc không hợp lệ. Chọn một đợt hợp lệ hoặc mở lịch sử tất cả đợt.</Notice>}
    <LoadState loading={batches.loading} error={batches.error} retry={batches.reload}/>
    <div className="filter-bar"><Field label="Tìm lần kiểm tra"><div className="search-input"><Search size={16} /><input type="search" placeholder="Tên dữ liệu hoặc #mã lần chạy…" value={search} onChange={event => setSearch(event.target.value)} /></div></Field>{!embedded && <Field label="Bộ dữ liệu"><select value={dataset} onChange={event => { location.hash=globalHistoryHref(event.target.value) }}><option value="">Tất cả bộ dữ liệu</option>{datasets.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>}
    <Field label="Đợt dữ liệu"><select value={batch} disabled={!selected||batches.loading} onChange={event=>chooseBatch(event.target.value)}><option value="">Tất cả đợt</option>{invalidScope&&<option value={batch} disabled>Đợt không hợp lệ</option>}{batches.data?.map(item=><option key={item.id} value={item.id}>{batchText(item)}</option>)}</select></Field>
    <Field label="Phiên bản"><select value={version} disabled={!selected} onChange={event => setVersion(event.target.value)}><option value="">Tất cả phiên bản</option>{selected?.versions.filter(item=>!batch||String(item.batch_id)===batch).map(item => <option key={item.id} value={item.id}>{name(selected!,item.batch_id)} · v{item.version_number}</option>)}</select></Field><Field label="Thực thi"><select value={status} onChange={event => setStatus(event.target.value)}><option value="">Mọi trạng thái</option><option value="completed">Hoàn tất</option><option value="running">Đang kiểm tra</option><option value="failed">Thực thi thất bại</option></select></Field><Field label="Chất lượng"><select value={quality} onChange={event => setQuality(event.target.value)}><option value="">Tất cả kết quả</option><option value="passed">Đạt quy tắc</option><option value="errors">Có lỗi dữ liệu</option></select></Field><Field label="Từ ngày"><input type="date" value={from} onChange={event => setFrom(event.target.value)} /></Field><Field label="Đến ngày"><input type="date" value={to} min={from} onChange={event => setTo(event.target.value)} /></Field></div>
    {!serverPaged && <p className="helper-text panel-pad">Tìm kiếm, lọc thời gian/trạng thái và tổng hợp nhiều bộ dữ liệu áp dụng trên tập lịch sử đầy đủ. Chọn một bộ dữ liệu để dùng phân trang và lọc phiên bản trên máy chủ.</p>}{invalidDates && <p className="form-error">Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.</p>}<LoadState loading={list.loading} error={list.error} retry={list.reload} />
    {list.data && (list.data.items.length ? <><div className="table-scroll"><table><thead><tr><th>Lần kiểm tra</th>{!embedded && <th>Bộ dữ liệu</th>}<th>Đợt dữ liệu</th><th>Phiên bản</th><th>Thời điểm</th><th>Thực thi</th><th>Chất lượng</th><th>Tổng bản ghi</th><th>Bản ghi lỗi</th><th></th></tr></thead><tbody>{list.data.items.map(item => <tr key={item.run_id}><td><strong className="run-id">#{item.run_id}</strong></td>{!embedded && <td><a href={`#/datasets/${item.dataset.id}/overview`}>{item.dataset.name}</a></td>}<td><a href={`#/datasets/${item.dataset.id}/batches/${item.batch_id}`}>{name(item.dataset,item.batch_id)}</a></td><td><span className="version-tag">v{item.version_number}</span></td><td className="nowrap">{date(item.started_at)}</td><td><ExecutionBadge status={item.status} /></td><td><QualityBadge run={item} /></td><td>{number(item.total_rows)}</td><td>{item.status === 'completed' ? number(item.error_row_count) : '—'}</td><td><a className="button button-ghost" aria-label={`Xem lần kiểm tra ${item.run_id}`} href={`#/datasets/${item.dataset.id}/runs/${item.run_id}`}><ArrowUpRight size={17} />Chi tiết</a></td></tr>)}</tbody></table></div><Pager page={page} total={list.data.total} change={setPage} /></> : <Empty title="Không tìm thấy lần kiểm tra" text="Thử đổi bộ lọc hoặc chạy kiểm tra nếu bộ dữ liệu chưa có lịch sử." action={<Button onClick={() => { setSearch(''); setVersion(''); setStatus(''); setQuality(''); setFrom(''); setTo(''); setPage(1) }}>Đặt lại bộ lọc</Button>} />)}
  </section></>
}
