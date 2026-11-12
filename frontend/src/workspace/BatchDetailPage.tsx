import {supplierLabel} from './Suppliers'
import IssueWorkflow, { IdentityPanel } from './IssueWorkflow'
import type { Workflow } from './IssueWorkflow'
import { batchTabs, requestedTab, primaryStep, businessLabels, qualityLabels, boards } from './workModel'
import type { BatchMetric, BatchTab } from './workModel'
import { resultText } from './presentation'
import { historyHref } from './scopeNavigation'
import CellValue from './CellValue'
import { useEffect, useRef, useState } from 'react'
import { canSuggestCorrection } from './demoUxState'
import { ArrowLeft } from 'lucide-react'
import type { BatchDetail, DatasetVersion } from '../api/datasets'
import { getBatch, patchBatch } from '../api/datasets'
import type { CatalogEntry } from './api'
import type { DatasetActions } from './CatalogPages'
import { Button, Dialog, Empty, Field, LoadState, Notice, PageTitle, QualityBadge, Badge, date, number, useLoad, useFormGuard } from './ui'
import UploadDialog from './UploadDialog'
import RuleList from './RuleList'
import type { RowsPage } from '../api/datasets'
import { request, getRules } from './api'
import { Pager } from './ui'

function PreviewDialog({ dataset, version, onClose, batchName }: { dataset: CatalogEntry; version: DatasetVersion; onClose: () => void; batchName?: string }) {
  const [page, setPage] = useState(1)
  const rows = useLoad(signal => request<RowsPage>(`/api/datasets/${dataset.id}/versions/${version.id}/rows?page=${page}&page_size=10`, signal), [dataset.id, version.id, page])
  return (
    <Dialog title={`Phiên bản v${version.version_number} · Xem dữ liệu`} description={`${dataset.name} / ${batchName} · v${version.version_number} · ${version.is_current ? 'Bản hiện hành' : 'Bản lịch sử'} · ${version.original_filename}`} onClose={onClose} wide>
      <LoadState loading={rows.loading} error={rows.error} retry={rows.reload} />
      {rows.data && (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Bản ghi</th>
                  {rows.data.header.map(name => (
                    <th key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.data.items.map(item => (
                  <tr key={item.row_number}>
                    <td>{item.row_number}</td>
                    {item.values.map((value, index) => (
                      <td key={index}><CellValue value={value} /></td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={page} total={rows.data.total} change={setPage} />
          <p className="helper-text">Bản ghi 1 bắt đầu sau dòng tiêu đề. Dữ liệu thô giữ nguyên từ file CSV.</p>
        </>
      )}
    </Dialog>
  )
}

function EditBatchDialog({
  datasetId,
  batch,
  onClose,
  onSaved,
}: {
  datasetId: number
  batch: BatchDetail
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState(batch.name)
  const [period, setPeriod] = useState(batch.period_label || '')
  const [desc, setDesc] = useState(batch.description || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const lock=useRef(false)
  const dirty=name!==batch.name||period!==(batch.period_label??'')||desc!==(batch.description??'')
  const guard=useFormGuard(dirty,saving,onClose)
  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (lock.current || !name.trim()) return
    lock.current=true
    setSaving(true)
    setError('')
    try {
      await patchBatch(datasetId, batch.id, {
        name: name.trim(),
        period_label: period.trim() || null,
        description: desc.trim() || null,
      })
      guard.markSaved()
      onClose()
      onSaved()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Không thể cập nhật.')
    } finally {
      lock.current=false
      setSaving(false)
    }
  }

  return (
    <Dialog title="Chỉnh sửa đợt dữ liệu" description={`Đợt: ${batch.name}`} onClose={guard.close} busy={saving}>
      <form onSubmit={handleSave} className="form-stack">
        {error && <Notice kind="error">{error}</Notice>}
        <Field label="Tên đợt dữ liệu" required>
          <input required maxLength={200} value={name} onChange={e => setName(e.target.value)} autoFocus />
        </Field>
        <Field label="Kỳ dữ liệu">
          <input maxLength={100} value={period} onChange={e => setPeriod(e.target.value)} placeholder="Ví dụ: 10/2026" />
        </Field>
        <Field label="Mô tả">
          <textarea rows={3} maxLength={2000} value={desc} onChange={e => setDesc(e.target.value)} />
        </Field>
        <div className="dialog-actions">
          <Button tone="ghost" onClick={guard.close} disabled={saving}>Hủy</Button>
          <Button tone="primary" type="submit" disabled={saving}>Lưu thay đổi</Button>
        </div>
      </form>
    </Dialog>
  )
}

export default function BatchDetailPage({dataset,batchId,actions,userRole}:{dataset:CatalogEntry;batchId:number;actions:DatasetActions;userRole?:string}) {
  const [uploading,setUploading]=useState(()=>new URLSearchParams(location.hash.split('?')[1]).get('upload')==='1'),[editing,setEditing]=useState(false),[preview,setPreview]=useState<DatasetVersion|null>(null)
  const uploadSaved=useRef(false)
  const uploadIntent=new URLSearchParams(location.hash.split('?')[1]).get('upload')
  useEffect(()=>{if(uploadIntent==='1')setUploading(true)},[dataset.id,batchId,uploadIntent])
  const batchLoad=useLoad(signal=>getBatch(dataset.id,batchId,signal),[dataset.id,batchId]),batch=batchLoad.data
  const rules=useLoad(signal=>getRules(dataset.id,signal,batchId),[dataset.id,batchId,batch?.rules_revision])
  const workflow=useLoad(signal=>request<Workflow>(`/api/datasets/${dataset.id}/batches/${batchId}/workflow`,signal),[dataset.id,batchId,dataset])
  const current=batch?.versions.find(v=>v.is_current),run=current?.latest_run,active=rules.data?.filter(r=>r.is_active).length
  const closed=batch?.business_state==='COMPLETED',ready=!!batch&&!!rules.data&&!!workflow.data
  const quality=!current?'NO_FILE':run?.status==='running'?'RUNNING':run?.status==='failed'?'FAILED':run?.rules_changed?'STALE':!run?'UNCHECKED':run.error_row_count?'HAS_ERRORS':'PASSED'
  const w=workflow.data
  const metric:BatchMetric|undefined=ready?{batch_id:batchId,dataset_id:dataset.id,dataset_name:dataset.name,batch_name:batch!.name,period_label:batch!.period_label,
    business_state:batch!.business_state,rules_revision:batch!.rules_revision!,active_rule_count:active!,current_version:current?{id:current.id,version_number:current.version_number,row_count:current.row_count}:null,
    rules_changed:!!run?.rules_changed,status:quality,run:run?.status==='completed'&&run.total_rows!==null&&run.error_row_count!==null&&run.violation_count!==null?{id:run.run_id,total_rows:run.total_rows,error_row_count:run.error_row_count,violation_count:run.violation_count,batch_rules_revision:run.batch_rules_revision??null}:null,
    workflow:{enabled:w!.enabled,unprocessed_count:w!.counts.OPEN+w!.counts.IN_PROGRESS+w!.counts.PENDING_RECHECK,ignored_count:w!.counts.IGNORED,completion_blockers:w!.completion.reasons}}:undefined
  const step=metric?primaryStep(metric):undefined,stepEntry=boards.find(b=>b.id===step)
  const query=new URLSearchParams(location.hash.split('?')[1]),explicitTab=requestedTab(query)
  const tab:BatchTab=explicitTab??(closed?'acceptance':stepEntry?.tab??'intake')
  const back=query.get('from'),safeBack=back&&/^#\/(dashboard|submit|rules|issues|compare|reporting|datasets|work\/(intake|setup|quality|resolution|acceptance|reports))(\?|$)/.test(back)?back:null
  function tabHref(value:BatchTab){const next=new URLSearchParams(location.hash.split('?')[1]);next.set('tab',value);for(const key of ['rules','issues','issue'])next.delete(key);return `#/datasets/${dataset.id}/batches/${batchId}?${next}`}
  function setTab(value:BatchTab){location.hash=tabHref(value)}
  function refresh(){batchLoad.reload();rules.reload();workflow.reload();actions.changed()}
  const runs=dataset.runs.filter(r=>r.batch_id===batchId||batch?.versions.some(v=>v.id===r.version_id)).sort((a,b)=>b.run_id-a.run_id)
  const offerCorrection=canSuggestCorrection(quality,closed,w?.completion.can_complete??false)
  const completed=runs.filter(r=>r.status==='completed'),first=completed.at(-1),last=completed[0]
  const primary=closed?<Button tone="primary" onClick={()=>setTab('acceptance')}>Xem nghiệm thu</Button>:!ready?<Button disabled>Đang xác định công việc…</Button>:!current?<Button tone="primary" onClick={()=>{setTab('intake');setUploading(true)}}>Tải CSV đầu tiên</Button>:step==='setup'?<Button tone="primary" onClick={()=>setTab(!active||!w?.identity?'rules':'issues')}>{!active?'Thiết lập quy tắc':!w?.identity?'Thiết lập khóa nhận diện':'Bật xử lý lỗi'}</Button>:step==='quality'?run?.status==='running'?<a className="button button-primary" href={`#/datasets/${dataset.id}/runs/${run.run_id}`}>Xem lần đang kiểm tra</a>:<Button tone="primary" onClick={()=>actions.run(dataset,current.id)}>Kiểm tra bản hiện hành</Button>:step==='resolution'?tab==='issues'?offerCorrection?<Button tone="primary" onClick={()=>setUploading(true)}>Tải bản đã sửa</Button>:<Button tone="primary" onClick={()=>document.getElementById('batch-workflow')?.scrollIntoView({block:'start'})}>Xem điều kiện đối soát</Button>:<Button tone="primary" onClick={()=>setTab('issues')}>Mở xử lý & kiểm tra lại</Button>:<Button tone="primary" onClick={()=>setTab('acceptance')}>Xem điều kiện nghiệm thu</Button>
  return <div className="batch-workspace form-stack">{safeBack&&<a className="back-link" href={safeBack}><ArrowLeft size={15}/>Về bảng công việc đã lọc</a>}<a className="back-link" href={`#/datasets/${dataset.id}/batches`}>{dataset.name} / Các đợt dữ liệu</a><LoadState loading={batchLoad.loading} error={batchLoad.error} retry={batchLoad.reload}/>{batch&&<>
    <PageTitle eyebrow={`${dataset.name} · ${batch.period_label??'Chưa có kỳ'}`} title={batch.name} description={batch.description??'Cùng một đợt dữ liệu, tổ chức theo công việc cần làm.'} action={primary}/>
    <section className="panel panel-pad batch-current" aria-label="Phiên bản hiện hành của đợt"><div><span className="eyebrow">{closed?'ĐÃ XÁC NHẬN HOÀN TẤT':stepEntry?'BƯỚC ƯU TIÊN · '+stepEntry.label:'ĐANG XÁC ĐỊNH CÔNG VIỆC'}</span><p data-batch-supplier>Nguồn cung cấp: {supplierLabel(batch.supplier)}</p><h2>{current?`v${current.version_number} · ${current.original_filename}`:'Chưa tiếp nhận CSV'}</h2><div className="batch-statuses"><span>Trạng thái đợt</span><Badge tone={closed?'success':'neutral'}>{businessLabels[batch.business_state??'UNKNOWN']??'Chưa có trạng thái'}</Badge><span>Chất lượng file</span><Badge tone={quality==='PASSED'?'success':quality==='HAS_ERRORS'||quality==='FAILED'?'warning':'neutral'}>{qualityLabels[quality]}</Badge></div><p className="helper-text">{current?`${number(current.row_count)} bản ghi · `:''}{active===undefined?'Chưa có số quy tắc':`${active} quy tắc đang bật`}. Đạt quy tắc không đồng nghĩa hoàn tất đợt.</p></div></section>
    <LoadState loading={rules.loading||workflow.loading} error={rules.error||workflow.error} retry={()=>{rules.reload();workflow.reload()}}/>
    <nav className="batch-tabs" role="tablist" aria-label="Công việc trong đợt">{batchTabs.map((t,index)=><a key={t.id} id={'batch-tab-'+t.id} href={tabHref(t.id)} role="tab" aria-selected={t.id===tab} aria-controls="batch-tab-panel" tabIndex={t.id===tab?0:-1} onKeyDown={e=>{const next=e.key==='Home'?0:e.key==='End'?batchTabs.length-1:e.key==='ArrowRight'?(index+1)%batchTabs.length:e.key==='ArrowLeft'?(index-1+batchTabs.length)%batchTabs.length:-1;if(next>=0){e.preventDefault();setTab(batchTabs[next].id);requestAnimationFrame(()=>document.getElementById('batch-tab-'+batchTabs[next].id)?.focus())}}}>{t.label}</a>)}</nav>
    <div id="batch-tab-panel" role="tabpanel" aria-labelledby={'batch-tab-'+tab} className="form-stack">
    {tab==='intake'&&<><section className="panel" id="batch-versions"><div className="panel-heading"><div><h2>Tiếp nhận & phiên bản</h2><p>Mỗi file là bản đầy đủ trong đúng đợt. Xem được cả bản hiện hành và lịch sử.</p></div><Button disabled={closed} onClick={()=>setUploading(true)}>{current?'Tải bản đã sửa':'Tải CSV đầu tiên'}</Button></div>{closed&&<p className="helper-text panel-pad">Đợt đã hoàn tất; mở lại trong Nghiệm thu trước khi nhận bản mới.</p>}{!batch.versions.length?<Empty title="Chưa có phiên bản" text="Tải CSV đầu tiên để tạo v1 trong đợt này."/>:<div className="table-scroll" role="region" tabIndex={0} aria-label="Bảng phiên bản"><table><thead><tr><th>Phiên bản</th><th>File CSV</th><th>Ngày tải</th><th>Bản ghi</th><th>Kết quả đã lưu</th><th>Thao tác</th></tr></thead><tbody>{batch.versions.map(v=><tr key={v.id}><td><span className="version-tag">v{v.version_number}</span><small>{v.is_current?'Hiện hành':'Lịch sử'}</small></td><td>{v.original_filename}</td><td>{date(v.imported_at)}</td><td>{number(v.row_count)}</td><td>{v.latest_run?.rules_changed?<span>Cấu hình đã đổi — cần kiểm tra lại</span>:<QualityBadge run={v.latest_run as any}/>}</td><td><div className="button-row"><Button onClick={()=>setPreview(v)}>Xem dữ liệu</Button><Button disabled={closed||active===undefined||!active||!!rules.error} onClick={()=>actions.run(dataset,v.id)}>Kiểm tra v{v.version_number}</Button>{v.latest_run&&<a className="button button-ghost" href={`#/datasets/${dataset.id}/runs/${v.latest_run.run_id}`}>Kết quả v{v.version_number}</a>}</div></td></tr>)}</tbody></table></div>}</section><details className="panel panel-pad"><summary>Thông tin tiếp nhận và lịch sử</summary><p>{batch.description||'Chưa có mô tả'}</p><Button disabled={closed} onClick={()=>setEditing(true)}>Sửa thông tin đợt</Button><a className="work-sub-link" href={historyHref(dataset.id,batchId)}>Lịch sử kiểm tra của đợt</a></details></>}
    {tab==='rules'&&<><IdentityPanel dataset={dataset} role={userRole} readOnly={closed} changed={refresh}/><section id="batch-rules" className="panel"><div className="panel-heading"><div><h2>Quy tắc của đợt</h2><p>Chỉ áp dụng trong {batch.name}; không sửa kết quả đã lưu hoặc đợt khác.</p></div></div><RuleList datasets={[dataset]} embedded batchId={batchId} readOnly={closed} changed={refresh}/></section></>}
    {tab==='results'&&<><section className="panel panel-pad"><h2>Kết quả bản hiện hành</h2>{!run?<p>Chưa có lần kiểm tra cho bản hiện hành; không dùng số liệu bản cũ thay thế.</p>:<><p>{qualityLabels[quality]}</p>{run.status==='completed'&&run.total_rows!==null&&run.error_row_count!==null&&run.violation_count!==null&&<p>{resultText(run.total_rows,run.error_row_count,run.violation_count)}</p>}<a className="button button-secondary" href={`#/datasets/${dataset.id}/runs/${run.run_id}`}>Mở kết quả #{run.run_id}</a>{run.rules_changed&&<Notice kind="warning">Kết quả này dùng cấu hình đã lưu trước khi thay đổi; cần kiểm tra lại, không coi là đạt theo cấu hình hiện tại.</Notice>}</>}</section><details className="panel panel-pad" open={!run}><summary>Lịch sử lần kiểm tra trong đợt ({runs.length})</summary><div className="table-scroll" role="region" tabIndex={0} aria-label="Bảng lịch sử lần kiểm tra"><table><thead><tr><th>Lần kiểm tra</th><th>Phiên bản</th><th>Thời điểm</th><th>Kết quả đã lưu</th><th></th></tr></thead><tbody>{runs.map(r=><tr key={r.run_id}><td>#{r.run_id}</td><td>v{r.version_number}<small>{r.version_id===current?.id?'Bản hiện hành':'Bản lịch sử'}</small></td><td>{date(r.started_at)}</td><td>{r.status==='completed'&&r.total_rows!==null&&r.error_row_count!==null&&r.violation_count!==null?resultText(r.total_rows,r.error_row_count,r.violation_count):r.status==='running'?'Đang kiểm tra':'Lỗi kỹ thuật'}</td><td><a href={`#/datasets/${dataset.id}/runs/${r.run_id}`}>Mở kết quả #{r.run_id}</a></td></tr>)}</tbody></table></div><a className="work-sub-link" href={historyHref(dataset.id,batchId)}>Mở lịch sử có bộ lọc của đợt</a>{first&&last&&first.run_id!==last.run_id&&<a className="button button-secondary" href={`#/datasets/${dataset.id}/compare?a=${first.run_id}&b=${last.run_id}`}>Đối chiếu hai lần trong đợt</a>}</details></>}
    {tab==='issues'&&<IssueWorkflow key={'issues:'+query.get('issue')} dataset={dataset} batchId={batchId} role={userRole} mode="issues" changed={refresh}/>}
    {tab==='acceptance'&&<IssueWorkflow dataset={dataset} batchId={batchId} role={userRole} mode="acceptance" changed={refresh}/>}
    </div>
    <details className="panel panel-pad"><summary>Chi tiết kỹ thuật và phạm vi</summary><p>Dataset #{dataset.id} · đợt #{batchId} · cấu hình quy tắc {batch.rules_revision}. Run giữ nguyên snapshot. Chênh lệch số dòng không chứng minh lỗi cụ thể đã được sửa.</p></details>
    {uploading&&!closed&&<UploadDialog dataset={dataset} batch={batch} onClose={()=>{setUploading(false);const params=new URLSearchParams(location.hash.split('?')[1]);if(params.has('upload')){params.delete('upload');history.replaceState(null,'',location.hash.split('?')[0]+(params.size?'?'+params:''))}if(uploadSaved.current){uploadSaved.current=false;refresh()}}} onSaved={()=>{uploadSaved.current=true}} next={(_id,next,_batch,version)=>{if(next==='run'&&version)actions.run(dataset,version);else if(next==='rules')setTab('rules')}}/>}
    {editing&&<EditBatchDialog datasetId={dataset.id} batch={batch} onClose={()=>setEditing(false)} onSaved={refresh}/>}{preview&&<PreviewDialog batchName={batch.name} dataset={dataset} version={preview} onClose={()=>setPreview(null)}/>}</>}
  </div>
}
