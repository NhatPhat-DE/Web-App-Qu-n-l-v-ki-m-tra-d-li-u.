import CellValue from './CellValue'
import {supplierLabel} from './Suppliers'
import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, ArrowRight, Check, CheckCircle2, FileSpreadsheet, FolderOpen, LoaderCircle, Upload, X } from 'lucide-react'
import { getBatch, importDataset, importVersion } from '../api/datasets'
import type { BatchDetail } from '../api/datasets'
import { UploadAcknowledgementError, pendingUploadKey, readPendingUpload } from './uploadAcknowledgement'
import type { PendingUpload } from './uploadAcknowledgement'
import { allPages } from './api'
import { batchText } from './presentation'
import type { DataBatchItem } from '../api/datasets'
import type { CatalogEntry } from './api'
import { Button, Dialog, Field, Notice, download, number, useLoad, LoadState, useFormGuard } from './ui'
import { previewCSV, samples } from './csv'
import type { CSVPreview } from './csv'

export default function UploadDialog({
  dataset,
  batch,
  onClose,
  onSaved,
  next,
}: {
  dataset?: CatalogEntry
  batch?: DataBatchItem | null
  onClose: () => void
  onSaved: (id: number) => void
  next: (id: number, tab: string, batchId?: number, versionId?: number) => void
}) {
  const batches = useLoad(signal => dataset && !batch ? allPages<DataBatchItem>(`/api/datasets/${dataset.id}/batches`,signal) : Promise.resolve([]),[dataset?.id,batch?.id])
  const [selectedBatch,setSelectedBatch] = useState(0)
  const targetBatch = batch ?? batches.data?.find(b=>b.id===selectedBatch)
  const pendingKey=pendingUploadKey(dataset?.id,targetBatch?.id)
  const [pending,setPending]=useState<PendingUpload|null>(()=>readPendingUpload(localStorage,pendingKey))
  const [verified,setVerified]=useState<BatchDetail|null>(null),[checking,setChecking]=useState(false),[recoveryError,setRecoveryError]=useState('')
  useEffect(()=>{setPending(readPendingUpload(localStorage,pendingKey));setVerified(null)},[pendingKey])
  const [step, setStep] = useState(dataset ? 1 : 0)
  const [metadata, setMetadata] = useState({ name: '', description: '', source: '', owner: '' })
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<CSVPreview | null>(null)
  const [error, setError] = useState('')
  const [reading, setReading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<{ id: number; version: number; batchId?: number; versionId: number } | null>(null)
  const sequence = useRef(0)
  const saveLock = useRef(false)
  const mounted = useRef(true)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; sequence.current++ } }, [])
  const dirty = !result && !pending && (!!file || Object.values(metadata).some(Boolean))
  const guard=useFormGuard(dirty,saving||reading,onClose)
  const cancel=guard.close
  const isFirstVersion = targetBatch ? targetBatch.version_count === 0 : (!!dataset && dataset.versions.length === 0)
  const oldHeader = dataset?.columns.map(column => column.name) ?? []
  const hasExistingSchema = (dataset?.columns.length ?? 0) > 0 && (dataset?.versions.length ?? 0) > 0
  const missing = preview && hasExistingSchema ? oldHeader.filter(column => !preview.header.includes(column)) : []
  const added = preview && hasExistingSchema ? preview.header.filter(column => !oldHeader.includes(column)) : []
  const mismatch = hasExistingSchema && !!preview && (oldHeader.length !== preview.header.length || oldHeader.some((name, index) => name !== preview.header[index]))
  async function choose(selected?: File) {
    if (!selected || reading || saving || pending) return
    const issued = ++sequence.current
    setFile(selected); setError(''); setPreview(null); setReading(true)
    try { const value = await previewCSV(selected); if (mounted.current && issued === sequence.current) { setPreview(value); setStep(2) } }
    catch (cause) { if (mounted.current && issued === sequence.current) setError(cause instanceof Error ? cause.message : 'Không đọc được file.') }
    finally { if (mounted.current && issued === sequence.current) setReading(false) }
  }
  async function save() {
    if (!file || !preview || mismatch || saveLock.current || pending) return
    if (dataset && (!targetBatch || (!batch && (batches.loading || batches.error)))) { setError('Chọn đúng đợt dữ liệu trước khi lưu bản sửa.'); return }
    saveLock.current = true; setSaving(true); setError('')
    let marker:PendingUpload|null=null
    try {
      const existing=readPendingUpload(localStorage,pendingKey)
      if(existing){setPending(existing);return}
      // Preflight failure sends no POST. Persist intent before POST so reload
      // cannot turn an uncertain outcome into an unprotected retry.
      const before=dataset&&targetBatch?await getBatch(dataset.id,targetBatch.id):null
      marker={filename:file.name,size:file.size,rowCount:preview.rowCount,startedAt:new Date().toISOString(),beforeIds:before?.versions.map(v=>v.id)??[]}
      localStorage.setItem(pendingKey,JSON.stringify(marker))
      let id: number; let version: number; let versionId: number; let savedBatch: number | undefined
      if (dataset) {
        const value = await importVersion(dataset.id, file, targetBatch?.id)
        id = dataset.id
        version = value.version_number
        versionId = value.version_id
        savedBatch = targetBatch?.id ?? value.batch_id
      } else {
        const form = new FormData(); form.set('file', file)
        for (const [key, value] of Object.entries(metadata)) form.set(key, value.trim())
        const value = await importDataset(form); id = value.dataset_id; version = value.version_number
        versionId = value.version_id
        savedBatch = targetBatch?.id ?? value.batch_id
      }
      localStorage.removeItem(pendingKey)
      if (mounted.current) { guard.markSaved(); setResult({ id, version, versionId, batchId:savedBatch }); setStep(3); onSaved(id) }
    } catch (cause) {
      if(cause instanceof UploadAcknowledgementError&&marker){if(mounted.current)setPending(marker)}
      else if(marker)localStorage.removeItem(pendingKey)
      if (mounted.current) setError(cause instanceof Error ? cause.message : 'Chưa xác nhận được kết quả lưu. Hãy kiểm tra danh mục trước khi gửi lại.')
    }
    finally { saveLock.current = false; if (mounted.current) setSaving(false) }
  }
  async function verifySaved(){if(!dataset||!targetBatch||checking)return;setChecking(true);setRecoveryError('');setVerified(null);try{setVerified(await getBatch(dataset.id,targetBatch.id))}catch(cause){setRecoveryError(cause instanceof Error?cause.message:'Chưa tải được phiên bản; chưa thể thử lại.')}finally{setChecking(false)}}
  const candidates=verified?.versions.filter(v=>!pending?.beforeIds.includes(v.id))??[]
  function useSaved(version:BatchDetail['versions'][number]){if(!dataset||!targetBatch)return;localStorage.removeItem(pendingKey);setPending(null);guard.markSaved();setResult({id:dataset.id,version:version.version_number,versionId:version.id,batchId:targetBatch.id});setStep(3);setError('');onSaved(dataset.id)}
  function viewVersions(){if(dataset)onSaved(dataset.id);onClose();location.hash=dataset&&targetBatch?`#/datasets/${dataset.id}/batches/${targetBatch.id}?tab=intake`:'#/datasets'}
  function allowRetry(legacy=false){if(!legacy&&(!verified||candidates.length||checking))return;if(!window.confirm('Bạn đã kiểm tra danh sách phiên bản? Yêu cầu trước có thể vẫn hoàn tất muộn; gửi lại có thể tạo thêm phiên bản. Chỉ tiếp tục nếu muốn gửi một yêu cầu mới.'))return;localStorage.removeItem(pendingKey);setPending(null);setVerified(null);setError('');setStep(dataset?(file&&preview?2:1):0)}
  const steps = dataset ? ['Chọn file CSV', 'Xem trước & lưu', 'Hoàn tất'] : ['Thông tin bộ dữ liệu', 'Chọn file CSV', 'Xem trước & lưu', 'Hoàn tất']
  const displayedStep = dataset ? step - 1 : step

  const dialogTitle = pending ? 'Kiểm tra kết quả tải CSV' : targetBatch
    ? isFirstVersion
      ? `Tải file đầu tiên cho đợt "${targetBatch!.name}" (v1)`
      : `Tải bản đã sửa cho đợt "${targetBatch!.name}" (v${targetBatch!.version_count + 1})`
    : dataset
    ? isFirstVersion
      ? 'Tải file CSV đầu tiên'
      : 'Tải phiên bản mới'
    : 'Tạo bộ dữ liệu'

  const dialogDesc = pending ? 'Phản hồi tải file chưa được xác nhận. Kiểm tra phiên bản trên máy chủ trước khi quyết định gửi yêu cầu mới.' : targetBatch
    ? isFirstVersion
      ? `Đợt: ${targetBatch!.name}. File đầu tiên sẽ tạo phiên bản v1 và nhận diện cột dữ liệu.`
      : `Đợt: ${targetBatch!.name}. Tải file đã sửa bên ngoài để tạo phiên bản tiếp theo trong đợt này.`
    : dataset
    ? isFirstVersion
      ? `Bộ dữ liệu: ${dataset.name}. Tải file CSV đầu tiên để tạo phiên bản v1 và nhận diện cột.`
      : `Bộ dữ liệu: ${dataset.name}. Phiên bản cũ luôn được giữ lại.`
    : 'Bắt đầu với thông tin mô tả và file CSV đầu tiên.'

  return <Dialog
    title={dialogTitle}
    description={dialogDesc}
    onClose={guard.close}
    busy={saving || reading}
    wide
  >
    {dataset && !batch && <><LoadState loading={batches.loading} error={batches.error} retry={batches.reload}/><Field label="Đợt nhận phiên bản CSV"><select value={targetBatch?.id ?? 0} onChange={e=>setSelectedBatch(Number(e.target.value))}><option value={0}>{batches.data?.length ? 'Chọn đợt nhận file CSV' : 'Chưa có đợt — hãy tạo đợt trước'}</option>{batches.data?.map(b=><option key={b.id} value={b.id}>{batchText(b)} · {supplierLabel(b.supplier)}</option>)}</select></Field><p className="helper-text"><a href={`#/datasets/${dataset.id}/batches`} onClick={event=>{if(!guard.close())event.preventDefault()}}>Mở danh sách đợt / tạo đợt dữ liệu</a>. Phiên bản là file đầy đủ thay thế bản hiện hành trong đợt đã chọn.</p></>}
    {targetBatch&&<Notice><strong>{dataset?.name} / {batchText(targetBatch)}</strong>. Nguồn cung cấp: {supplierLabel(targetBatch.supplier)}. File được lưu vào đúng đợt này.</Notice>}<ol className="wizard-steps">{steps.map((label, index) => <li key={label} className={index === displayedStep ? 'current' : index < displayedStep ? 'done' : ''}><span>{index < displayedStep ? <Check size={14} /> : index + 1}</span>{label}</li>)}</ol>
    {error && <Notice kind="error">{error}</Notice>}
    {pending&&<section className="form-stack" data-upload-recovery><Notice kind="warning"><strong>Chưa xác nhận được kết quả lưu — không gửi lại ngay.</strong><p>Máy chủ có thể đã lưu {pending.filename} ({number(pending.size)} byte, {number(pending.rowCount)} bản ghi). Hãy kiểm tra dữ liệu trên máy chủ trước khi gửi thêm.</p></Notice><div className="button-row">{dataset&&targetBatch&&<Button disabled={checking} onClick={()=>void verifySaved()}>{checking?'Đang kiểm tra phiên bản…':'Kiểm tra phiên bản đã lưu'}</Button>}<Button onClick={viewVersions}>Mở danh sách phiên bản để xem dữ liệu</Button>{!dataset&&<Button onClick={()=>allowRetry(true)}>Tôi đã kiểm tra danh mục — cho phép nhập lại</Button>}</div>{recoveryError&&<Notice kind="error">{recoveryError}</Notice>}{verified&&<>{candidates.length?<><p>Có phiên bản mới trong đợt. Hãy đối chiếu file và dữ liệu trước khi chọn; hệ thống không tự suy phiên bản nào là file vừa gửi.</p><div className="table-scroll"><table><thead><tr><th>Phiên bản</th><th>File</th><th>Bản ghi</th><th></th></tr></thead><tbody>{candidates.map(v=><tr key={v.id}><td>v{v.version_number} · #{v.id}</td><td>{v.original_filename}</td><td>{number(v.row_count)}</td><td><Button onClick={()=>useSaved(v)}>Dùng phiên bản v{v.version_number} đã lưu</Button></td></tr>)}</tbody></table></div></>:<><p>Chưa thấy phiên bản mới; yêu cầu trước có thể vẫn đang xử lý. Có thể kiểm tra lại trước khi quyết định gửi một yêu cầu mới.</p><Button disabled={checking} onClick={()=>allowRetry()}>Cho phép thử lại sau khi kiểm tra</Button></>}</>}</section>}
    {!pending && step === 0 && <form onSubmit={event => { event.preventDefault(); setStep(1) }} className="form-stack">
      <div className="form-grid"><Field label="Tên bộ dữ liệu" required hint="Ví dụ: Danh sách khách hàng tháng 11"><input required maxLength={200} value={metadata.name} onChange={event => setMetadata({ ...metadata, name: event.target.value })} pattern=".*\S.*" autoFocus /></Field><Field label="Người phụ trách" required hint="Tên người liên hệ về nội dung dữ liệu; không cấp quyền tài khoản."><input required maxLength={200} value={metadata.owner} pattern=".*\S.*" onChange={event => setMetadata({ ...metadata, owner: event.target.value })} /></Field></div>
      <Field label="Nguồn / bộ phận" hint="Lưu dưới dạng thông tin nguồn dữ liệu, ví dụ: Kinh doanh."><input value={metadata.source} maxLength={200} onChange={event => setMetadata({ ...metadata, source: event.target.value })} /></Field>
      <Field label="Mô tả"><textarea rows={3} value={metadata.description} onChange={event => setMetadata({ ...metadata, description: event.target.value })} placeholder="Bộ dữ liệu này chứa thông tin gì và dùng để làm gì?" /></Field>
      <Notice>Thông tin đang là bản nháp trong cửa sổ này. Bộ dữ liệu được tạo sau khi bạn xác nhận lưu file CSV ở bước tiếp theo.</Notice>
      <div className="dialog-footer"><Button onClick={cancel}>Hủy</Button><Button tone="primary" type="submit">Tiếp tục: chọn CSV <ArrowRight size={16} /></Button></div>
    </form>}
    {!pending && step === 1 && <div className="form-stack"><div className="upload-zone" onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); if (event.dataTransfer.files.length !== 1) { setError('Mỗi lần chỉ chọn một file CSV.'); return }; void choose(event.dataTransfer.files[0]) }}><div className="upload-icon"><Upload size={29} /></div><h3>Kéo thả file CSV vào đây</h3><p>hoặc chọn file từ máy tính của bạn</p><Button tone="primary" disabled={reading} onClick={() => input.current?.click()}>{reading ? <LoaderCircle className="spin" size={17} /> : <FolderOpen size={17} />} Chọn file CSV</Button><small>UTF-8 hoặc UTF-8 BOM · Tối đa 5 MiB · 10.000 bản ghi</small><input ref={input} type="file" accept=".csv,text/csv" aria-label="Chọn file CSV" hidden onChange={event => { void choose(event.target.files?.[0]); event.target.value = '' }} /></div>
      {file && !preview && <p className="muted">Đã chọn: {file.name}</p>}
      <div className="sample-download"><FileSpreadsheet size={19} /><div><strong>Cần một file để thử?</strong><p>File mẫu chứa dữ liệu giả lập, có cả trường hợp lỗi.</p></div><Button onClick={() => download(new Blob(['\uFEFF', samples.customers.content], { type: 'text/csv;charset=utf-8' }), samples.customers.filename)}>Tải CSV mẫu</Button></div>
      <div className="dialog-footer"><Button onClick={() => dataset ? cancel() : setStep(0)}><ArrowLeft size={16} />{dataset ? 'Hủy' : 'Quay lại'}</Button><span className="muted">Chọn file để tiếp tục</span></div>
    </div>}
    {!pending && step === 2 && preview && file && <div className="form-stack"><div className="file-summary"><FileSpreadsheet size={28} /><div><strong>{file.name}</strong><p>{number(file.size)} byte · {number(preview.rowCount)} bản ghi · {number(preview.header.length)} cột</p></div><Button disabled={saving} tone="ghost" onClick={() => { setStep(1); setError('') }}><X size={16} />Đổi file</Button></div>
      {mismatch ? <Notice kind="error"><strong>Cấu trúc khác các phiên bản đã lưu.</strong><p>{missing.length > 0 && `Cột thiếu: ${missing.join(', ')}. `}{added.length > 0 && `Cột mới: ${added.join(', ')}. `}{!missing.length && !added.length && 'Thứ tự cột đã thay đổi. '}Các phiên bản phải có cùng tên và thứ tự cột. Hãy chỉnh lại file hoặc tạo bộ dữ liệu khác; cột đang được quy tắc sử dụng không được bỏ qua.</p></Notice> : <Notice kind="success">Cấu trúc CSV hợp lệ{dataset && !isFirstVersion ? ' và khớp phiên bản trước' : ''}. Hãy xem lại dữ liệu trước khi lưu.</Notice>}
      <div><div className="section-label"><h3>Xem trước dữ liệu</h3><span>Tối đa 10 bản ghi đầu</span></div><div className="table-scroll"><table><thead><tr><th>Bản ghi</th>{preview.header.map(name => <th key={name}>{name}</th>)}</tr></thead><tbody>{preview.rows.map((row, index) => <tr key={index}><td>{index + 1}</td>{row.map((value, cell) => <td key={cell}><CellValue value={value} /></td>)}</tr>)}</tbody></table></div></div>
      <Notice>Đây là kiểm tra cấu trúc file. Sau khi lưu, hãy thiết lập quy tắc và chạy kiểm tra để phát hiện lỗi nội dung.</Notice>
      <div className="dialog-footer"><Button disabled={saving} onClick={() => setStep(1)}><ArrowLeft size={16} />Quay lại</Button><Button tone="primary" disabled={mismatch || saving || (!!dataset && !targetBatch)} onClick={() => void save()}>{saving ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />}{saving ? 'Đang lưu phiên bản…' : 'Xác nhận lưu phiên bản'}</Button></div>
    </div>}
    {step === 3 && result && <div className="upload-success"><div><CheckCircle2 size={42} /></div><h3>Đã lưu phiên bản {result.version}</h3><p>{number(preview?.rowCount)} bản ghi đã sẵn sàng. Bước tiếp theo là thiết lập quy tắc hoặc chạy kiểm tra.</p><div className="button-row"><Button onClick={() => { onClose(); next(result.id, 'rules', result.batchId, result.versionId) }}>Thiết lập quy tắc</Button><Button tone="primary" onClick={() => { onClose(); next(result.id, 'run', result.batchId, result.versionId) }}>Chạy kiểm tra <ArrowRight size={16} /></Button></div></div>}
  </Dialog>
}
