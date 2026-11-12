import { IssueDialog, issueLabels } from './IssueWorkflow'
import type { Workflow } from './IssueWorkflow'
import { runWorkflowMessage } from './demoUxState'
import CellValue from './CellValue'
import { useEffect, useRef, useState } from 'react'
import { Download, Eye, RefreshCw } from 'lucide-react'
import { fetchReport } from '../api/runs'
import type { Page, RunDetail, Violation } from '../api/runs'
import type { RowsPage } from '../api/datasets'
import { allPages, request } from './api'
import type { CatalogEntry } from './api'
import { csvBlob } from './csv'
import { errorCSVRows } from './errorExport'
import type { ErrorExportContext } from './errorExport'
import { Badge, Button, Dialog, Empty, Field, LoadState, Notice, Pager, download, number, ruleLabels, useDebounced, useLoad } from './ui'

export default function ViolationList({ dataset, run, userRole }: { dataset: CatalogEntry; run: RunDetail;userRole?:string }) {
  const [type, setType] = useState('')
  const [column, setColumn] = useState('')
  const [rule, setRule] = useState('')
  const [row, setRow] = useState('')
  const [search, setSearch] = useState('')
  const q = useDebounced(search)
  const [page, setPage] = useState(1)
  const [record, setRecord] = useState<number | null>(null)
  const [issueId,setIssueId]=useState(0)
  const links=useLoad(signal=>request<{violation_id:number;row_number:number;issue_id:number;batch_id:number;status:string}[]>(`/api/datasets/${dataset.id}/runs/${run.run_id}/issue-links`,signal),[dataset.id,run.run_id])
  const workflow=useLoad(signal=>run.batch_id?request<Workflow>(`/api/datasets/${dataset.id}/batches/${run.batch_id}/workflow`,signal):Promise.resolve(null),[dataset.id,run.run_id,run.batch_id])
  const workflowMessage=run.status==='completed'&&run.violation_count!==null&&!links.loading&&!links.error&&links.data&&!workflow.loading&&!workflow.error&&workflow.data?runWorkflowMessage(run.run_id,run.violation_count,links.data.length,workflow.data):''
  const linkButtons=(violationId?:number,rowNumber?:number)=><>{links.data?.filter(link=>(violationId===undefined||link.violation_id===violationId)&&(rowNumber===undefined||link.row_number===rowNumber)).map(link=><Button key={`${link.violation_id}:${link.issue_id}`} tone="ghost" onClick={()=>{setRecord(null);setIssueId(link.issue_id)}}>Issue #{link.issue_id} · {issueLabels[link.status]}</Button>)}</>
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const [exportSuccess, setExportSuccess] = useState('')
  const exportController = useRef<AbortController | null>(null)
  const exportLock = useRef(false)
  useEffect(() => () => exportController.current?.abort(), [])
  const types = new Map(run.rule_snapshot.map(item => [item.id, item.rule_type]))
  const scoped = !!type || !!column || !!rule
  const ids = run.rule_snapshot.filter(item => (!type || item.rule_type === type) && (!column || item.columns.includes(column)) && (!rule || String(item.id) === rule)).map(item => item.id)
  const scopeKey = ids.join(',')
  const invalidRow = !!row && (!Number.isSafeInteger(Number(row)) || Number(row) < 1)
  const serverPaged = !q && (!scoped || ids.length <= 1)
  const url = (id?: number) => `/api/datasets/${dataset.id}/runs/${run.run_id}/violations?${new URLSearchParams({ ...(row ? { row_number: row } : {}), ...(id !== undefined ? { rule_id_snapshot: String(id) } : {}) })}`
  async function allFiltered(signal: AbortSignal) {
    if (invalidRow || scoped && !ids.length) return []
    let values: Violation[] = []
    if (!scoped) values = await allPages<Violation>(url(), signal)
    else {
      let cursor = 0
      await Promise.all(Array.from({ length: Math.min(4, ids.length) }, async () => { while (cursor < ids.length) { const id = ids[cursor++]; values.push(...await allPages<Violation>(url(id), signal)) } }))
      values.sort((a, b) => a.row_number - b.row_number || a.id - b.id)
    }
    return values.filter(item => !q || [item.rule_name, item.message, ...item.columns, ...item.values].join(' ').toLocaleLowerCase('vi').includes(q.toLocaleLowerCase('vi')))
  }
  const list = useLoad(async signal => {
    if (invalidRow || scoped && !ids.length) return { items: [], total: 0, page, page_size: 10 }
    if (serverPaged) return request<Page<Violation>>(`${url(scoped ? ids[0] : undefined)}&page=${page}&page_size=10`, signal)
    const items = await allFiltered(signal)
    return { items: items.slice((page - 1) * 10, page * 10), total: items.length, page, page_size: 10 }
  }, [dataset.id, run.run_id, page, type, column, rule, row, q, scopeKey, invalidRow, serverPaged])
  async function exportReport(format: 'csv' | 'json' | 'xlsx') {
    if (exportLock.current) return
    exportLock.current = true; setExporting(true); setExportError(''); setExportSuccess('')
    const controller = new AbortController(); exportController.current = controller
    try {
      if (format === 'csv') {
        const values = await allFiltered(controller.signal)
        const context=await request<ErrorExportContext>(`/api/datasets/${dataset.id}/runs/${run.run_id}/error-export-context`,controller.signal)
        if (!controller.signal.aborted) { download(csvBlob(errorCSVRows(context,values,item=>ruleLabels[types.get(item.rule_id_snapshot)??'']??item.error_code)), `loi-kiem-tra-${run.run_id}.csv`); setExportSuccess(`Đã xuất ${number(values.length)} lượt vi phạm theo bộ lọc hiện tại. Khóa lấy theo snapshot; các cột JSON giữ giá trị gốc trước bảo vệ công thức Excel.`) }
      } else { const report = await fetchReport(dataset.id, run.run_id, controller.signal, format); if (!controller.signal.aborted) { download(report.blob, report.filename); setExportSuccess('Đã tải báo cáo đầy đủ của lần kiểm tra.') } }
    } catch (cause) { if (!controller.signal.aborted) setExportError(cause instanceof Error ? cause.message : 'Không tải được báo cáo.') }
    finally { exportLock.current = false; if (!controller.signal.aborted) setExporting(false) }
  }
  function reset() { setType(''); setColumn(''); setRule(''); setRow(''); setSearch(''); setPage(1) }
  return <section className="panel"><div className="panel-heading"><div><h2>Các lỗi cần kiểm tra lại</h2><p>Bản ghi 1 là bản ghi dữ liệu đầu tiên sau dòng tiêu đề, không phải số dòng vật lý của file.</p></div><div className="button-row"><Button disabled={list.loading || !!list.error || exporting || invalidRow || q !== search} onClick={() => void exportReport('csv')}><Download size={16} />Xuất CSV lỗi</Button><select className="compact-select" aria-label="Tải báo cáo đầy đủ" disabled={exporting} value="" onChange={event => { if (event.target.value) void exportReport(event.target.value as 'json' | 'xlsx') }}><option value="">Báo cáo đầy đủ…</option><option value="xlsx">Tải Excel</option><option value="json">Tải JSON</option></select></div></div>
    {exportError && <Notice kind="error">{exportError}</Notice>}{exportSuccess && <Notice kind="success">{exportSuccess}</Notice>}
    <div className="filter-bar"><Field label="Loại kiểm tra"><select value={type} onChange={event => { setType(event.target.value); setPage(1) }}><option value="">Tất cả loại lỗi</option>{[...new Set(run.rule_snapshot.map(item => item.rule_type))].map(value => <option key={value} value={value}>{ruleLabels[value] ?? value}</option>)}</select></Field><Field label="Trường dữ liệu"><select value={column} onChange={event => { setColumn(event.target.value); setPage(1) }}><option value="">Tất cả trường</option>{dataset.columns.map(item => <option key={item.id}>{item.name}</option>)}</select></Field><Field label="Quy tắc đã áp dụng"><select value={rule} onChange={event => { setRule(event.target.value); setPage(1) }}><option value="">Tất cả quy tắc</option>{run.rule_snapshot.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field><Field label="Số bản ghi"><input type="number" min="1" step="1" placeholder="Tất cả" value={row} onChange={event => { setRow(event.target.value); setPage(1) }} /></Field><Field label="Tìm nội dung lỗi"><input type="search" placeholder="Giá trị, quy tắc hoặc gợi ý…" value={search} onChange={event => { setSearch(event.target.value); setPage(1) }} /></Field><Button tone="ghost" onClick={reset}><RefreshCw size={15} />Đặt lại</Button></div>
    {invalidRow && <Notice kind="error">Số bản ghi phải là số nguyên từ 1 trở lên.</Notice>}{!serverPaged && <p className="helper-text panel-pad">Bộ lọc loại, trường hoặc nội dung được áp dụng trên toàn bộ các vi phạm thuộc quy tắc/bản ghi đã chọn, không chỉ trang đang xem.</p>}
    <LoadState loading={list.loading} error={list.error} retry={list.reload} />{list.data && (list.data.items.length ? <><div className="table-scroll"><table><thead><tr><th>Bản ghi</th><th>Trường / giá trị</th><th>Loại lỗi</th><th>Quy tắc và gợi ý</th><th></th></tr></thead><tbody>{list.data.items.map(item => <tr key={item.id}><td><span className="row-number">{item.row_number}</span></td><td>{item.columns.map((name, index) => <div key={name}><code>{name}</code><span className="cell-value"><CellValue value={item.values[index]} /></span></div>)}</td><td><Badge tone="warning">{ruleLabels[types.get(item.rule_id_snapshot) ?? ''] ?? item.error_code}</Badge></td><td className="wrap-cell"><strong>{item.rule_name}</strong><small>{item.message}</small>{item.related_rows && <small>Các bản ghi cùng nhóm trùng trong phiên bản này: {item.related_rows.join(", ")}</small>}</td><td>{linkButtons(item.id)}<Button aria-label={`Xem bản ghi ${item.row_number}`} tone="ghost" onClick={() => setRecord(item.row_number)}><Eye size={17} /></Button></td></tr>)}</tbody></table></div><Pager page={page} total={list.data.total} change={setPage} /></> : <Empty title={run.violation_count ? 'Không tìm thấy lỗi phù hợp' : 'Không có vi phạm quy tắc'} text={run.violation_count ? 'Hãy thay đổi hoặc đặt lại bộ lọc.' : 'Tất cả bản ghi đều đáp ứng các quy tắc đã áp dụng trong lần kiểm tra này.'} />)}
    {record !== null && <RecordDialog dataset={dataset} version={run.version_id} row={record} close={() => setRecord(null)} issueLinks={<>{linkButtons(undefined,record)}<a href={`#/datasets/${dataset.id}/batches/${run.batch_id}?issues=1`}>Xử lý lỗi của đợt</a></>} />}
    {links.error&&<Notice kind="warning">Chưa tải được liên kết issue. <Button onClick={links.reload}>Tải lại liên kết</Button></Notice>}
    <LoadState loading={links.loading||workflow.loading} error={workflow.error} retry={workflow.reload}/>
    {workflowMessage&&<p className="panel-pad" data-run-workflow>{workflowMessage} <a href={`#/datasets/${dataset.id}/batches/${run.batch_id}?issues=1`}>Xem xử lý lỗi và bằng chứng đối soát của đợt</a>.</p>}
    {issueId>0&&run.batch_id&&<IssueDialog key={issueId} datasetId={dataset.id} batchId={run.batch_id} issueId={issueId} role={userRole} close={()=>setIssueId(0)} saved={links.reload}/>}
  </section>
}
function RecordDialog({ dataset, version, row, close, issueLinks }: { dataset: CatalogEntry; version: number; row: number; close: () => void;issueLinks:React.ReactNode }) {
  const record = useLoad(signal => request<RowsPage>(`/api/datasets/${dataset.id}/versions/${version}/rows?page=${row}&page_size=1`, signal), [dataset.id, version, row])
  return <Dialog title={`Bản ghi ${row}`} description="Giá trị gốc trong phiên bản đã kiểm tra." onClose={close}><LoadState loading={record.loading} error={record.error} retry={record.reload} />{record.data && <dl className="record-values">{record.data.header.map((name, index) => <div key={name}><dt>{name}</dt><dd><CellValue value={record.data?.items[0]?.values[index]} /></dd></div>)}</dl>}{issueLinks}</Dialog>
}
