import { useEffect, useRef, useState } from 'react'
import { ArrowRight, FileSpreadsheet, LoaderCircle, Play, ShieldCheck } from 'lucide-react'
import { RunAPIError, startRun } from '../api/runs'
import type { DatasetDetail, DataBatchItem, BatchDetail } from '../api/datasets'
import { getRules, request as readRequest, allPages } from './api'
import type { CatalogEntry } from './api'
import { batchText } from './presentation'
import { Button, Dialog, Field, LoadState, Notice, number, ruleLabels, useLoad } from './ui'

export default function RunDialog({datasets,datasetId,versionId,onClose,started}:{datasets:CatalogEntry[];datasetId?:number;versionId?:number;onClose:()=>void;started:(dataset:number,run:number)=>void}) {
  const [selected,setSelected]=useState(datasetId??0)
  const [version,setVersion]=useState(versionId??0)
  const [selectedBatch,setSelectedBatch]=useState(0)
  const detail=useLoad(signal=>selected?readRequest<DatasetDetail>(`/api/datasets/${selected}`,signal):Promise.resolve(null),[selected])
  const batches=useLoad(signal=>selected?allPages<DataBatchItem>(`/api/datasets/${selected}/batches`,signal):Promise.resolve([]),[selected])
  const dataset=detail.data
  const chosen=dataset?.versions.find(v=>v.id===version)
  // A version explicitly clicked by the user identifies its batch; no default batch.
  const batchId=selectedBatch||chosen?.batch_id||0
  const batch=useLoad(signal=>selected&&batchId?readRequest<BatchDetail>(`/api/datasets/${selected}/batches/${batchId}`,signal):Promise.resolve(null),[selected,batchId])
  const rules=useLoad(signal=>selected&&batchId?getRules(selected,signal,batchId):Promise.resolve([]),[selected,batchId])
  const active=(rules.data??[]).filter(r=>r.is_active)
  const [busy,setBusy]=useState(false)
  const [error,setError]=useState('')
  const [recorded,setRecorded]=useState<number|null>(null)
  const [uncertain,setUncertain]=useState(false)
  const lock=useRef(false),request=useRef<AbortController|null>(null)
  useEffect(()=>()=>request.current?.abort(),[])
  const invalid=active.some(r=>r.columns.some(c=>!dataset?.columns.some(item=>item.name===c)))
  const blocked=busy||detail.loading||batch.loading||rules.loading||!!detail.error||!!batch.error||!!rules.error||!chosen||!batchId||!active.length||invalid||uncertain||recorded!==null
  async function run(){
    if(blocked||lock.current||!dataset||!chosen)return
    lock.current=true;setBusy(true);setError('')
    const controller=new AbortController();request.current=controller
    try{const result=await startRun(dataset.id,chosen.id,controller.signal);if(!controller.signal.aborted){started(dataset.id,result.run_id);onClose()}}
    catch(cause){if(!controller.signal.aborted){setError(cause instanceof Error?cause.message:'Chưa xác nhận được lần kiểm tra. Hãy xem lịch sử trước khi chạy lại.');if(cause instanceof RunAPIError&&cause.runId)setRecorded(cause.runId);else if(/Mất kết nối|Không đọc|Không xác nhận/.test(cause instanceof Error?cause.message:''))setUncertain(true)}}
    finally{lock.current=false;if(!controller.signal.aborted)setBusy(false)}
  }
  return <Dialog title="Chạy kiểm tra dữ liệu" description="Chọn rõ bộ dữ liệu, đợt và phiên bản trước khi bắt đầu." onClose={onClose} busy={busy}>
    <div className="form-stack">{error&&<Notice kind="error">{error}{recorded&&<a href={`#/datasets/${selected}/runs/${recorded}`} onClick={onClose}>Xem lần kiểm tra đã ghi</a>}{uncertain&&<a href={`#/datasets/${selected}/history`} onClick={onClose}>Xem lịch sử trước khi thử lại</a>}</Notice>}
    <fieldset disabled={busy} className="form-stack">
      <Field label="Bộ dữ liệu" required><select value={selected} onChange={e=>{setSelected(Number(e.target.value));setSelectedBatch(0);setVersion(0);setError('');setRecorded(null);setUncertain(false)}}><option value={0}>Chọn bộ dữ liệu</option>{datasets.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select></Field>
      {!!selected&&<><LoadState loading={detail.loading||batches.loading} error={detail.error||batches.error} retry={()=>{detail.reload();batches.reload()}}/>
      <Field label="Đợt dữ liệu" required><select value={batchId} disabled={detail.loading||batches.loading} onChange={e=>{const id=Number(e.target.value);setSelectedBatch(id);setVersion(dataset?.versions.find(v=>v.batch_id===id&&v.is_current)?.id??0);setError('');setRecorded(null);setUncertain(false)}}><option value={0}>Chọn đợt cần kiểm tra</option>{batches.data?.map(b=><option key={b.id} value={b.id}>{batchText(b)}</option>)}</select></Field></>}
      {!!batchId&&<><Field label="Phiên bản kiểm tra" required><select value={version} onChange={e=>{setVersion(Number(e.target.value));setRecorded(null);setUncertain(false)}}><option value={0}>Chọn phiên bản</option>{dataset?.versions.filter(v=>v.batch_id===batchId).map(v=><option key={v.id} value={v.id}>v{v.version_number} · {v.is_current?'Hiện hành':'Lịch sử'} · {v.original_filename}</option>)}</select></Field><LoadState loading={batch.loading||rules.loading} error={batch.error||rules.error} retry={()=>{batch.reload();rules.reload()}}/></>}
      {chosen&&batch.data&&<Notice>{dataset?.name} / <strong>{batchText(batch.data)}</strong> / v{chosen.version_number} ({chosen.is_current?'hiện hành':'lịch sử'}). Dùng {active.length} quy tắc đang bật của đợt này.</Notice>}
      {chosen&&<div className="run-file"><FileSpreadsheet size={24}/><div><strong>{chosen.original_filename}</strong><p>{number(chosen.row_count)} bản ghi · {number(dataset?.columns.length)} cột</p></div></div>}
      {!!batchId&&!rules.loading&&!rules.error&&<div className="active-rules"><h3><ShieldCheck size={18}/>Quy tắc sẽ áp dụng</h3>{active.length?<details><summary>Xem {active.length} quy tắc đang bật</summary><ul>{active.map(r=><li key={r.id}><strong>{r.name}</strong><small>{ruleLabels[r.rule_type]} · {r.columns.join(', ')}</small></li>)}</ul></details>:<Notice kind="warning">Chưa có quy tắc đang bật. <a href={`#/datasets/${selected}/batches/${batchId}`} onClick={onClose}>Mở đợt để thiết lập quy tắc <ArrowRight size={13}/></a></Notice>}</div>}
      {!!batchId&&!detail.loading&&!dataset?.versions.some(v=>v.batch_id===batchId)&&<Notice>Đợt này chưa có file. <a href={`#/datasets/${selected}/batches/${batchId}`} onClick={onClose}>Mở đợt để tải CSV</a></Notice>}
      {invalid&&<Notice kind="error">Quy tắc đang tham chiếu cột không có trong dữ liệu. Hãy sửa trước khi kiểm tra.</Notice>}
      {batch.data&&<details><summary>Chi tiết cấu hình kiểm tra</summary><p>Phiên bản cấu hình: {batch.data.rules_revision}. Máy chủ lưu chính xác quy tắc và cấu trúc cột tại thời điểm kiểm tra. Kết quả cũ được giữ nguyên.</p></details>}
      <div className="dialog-footer"><Button onClick={onClose}>Hủy</Button><Button tone="primary" disabled={blocked} onClick={()=>void run()}>{busy?<LoaderCircle className="spin" size={17}/>:<Play size={17}/>} {busy?'Đang kiểm tra…':'Bắt đầu kiểm tra'}</Button></div>
    </fieldset></div>
  </Dialog>
}
