import { businessFetch } from './business'
import { UploadAcknowledgementError } from '../workspace/uploadAcknowledgement'

export interface CreateDatasetInput {
  name: string
  description?: string | null
  source?: string | null
  owner?: string | null
}

export interface CreatedDataset {
  id: number
  name: string
  description: string | null
  source: string | null
  owner: string | null
  created_at: string
  updated_at: string
}

export async function createDataset(input: CreateDatasetInput, signal?: AbortSignal): Promise<CreatedDataset> {
  const payload = {
    name: input.name.trim(),
    description: input.description?.trim() || null,
    source: input.source?.trim() || null,
    owner: input.owner?.trim() || null,
  }
  let response: Response
  try {
    response = await businessFetch('/api/datasets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    })
  } catch {
    throw new Error('Mất kết nối khi tạo bộ dữ liệu. Hãy kiểm tra kết nối mạng và thử lại.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (typeof body?.error?.message === 'string') throw new Error(body.error.message)
    if (response.status === 400 || response.status === 422) {
      if (body?.error?.code === 'DATASET_NAME_EMPTY' || body?.error?.code === 'INVALID_NAME') {
        throw new Error('Tên bộ dữ liệu không được để trống hoặc chỉ chứa khoảng trắng.')
      }
      if (body?.error?.code === 'DATASET_NAME_TOO_LONG') {
        throw new Error('Tên bộ dữ liệu tối đa 200 ký tự.')
      }
      throw new Error('Thông tin bộ dữ liệu không hợp lệ.')
    }
    throw new Error(response.status === 403 ? 'Bạn không có quyền thực hiện thao tác này.' : 'Không thể tạo bộ dữ liệu. Vui lòng thử lại.')
  }
  try {
    return await response.json() as CreatedDataset
  } catch {
    throw new Error('Không đọc được phản hồi khi tạo bộ dữ liệu. Vui lòng kiểm tra danh mục.')
  }
}

export interface DatasetItem {
  id: number
  name: string
  description: string | null
  source: string | null
  owner: string | null
  created_at: string
  version_count: number
  batch_count?: number
}

export interface DatasetPage {
  items: DatasetItem[]
  total: number
  page: number
  page_size: number
}

export interface ImportResult {
  batch_id?: number
  dataset_id: number
  version_id: number
  version_number: number
  name: string
  column_count: number
  row_count: number
}

export type VersionImportResult = Omit<ImportResult, 'name'> & { batch_id?: number }
export async function importVersion(datasetId: number, file: File, batchId?: number, signal?: AbortSignal): Promise<VersionImportResult> {
  const form = new FormData()
  form.set('file', file)
  let response: Response
  const url = batchId
    ? `/api/datasets/${datasetId}/batches/${batchId}/versions/import`
    : `/api/datasets/${datasetId}/versions/import`
  try { response = await businessFetch(url, { method: 'POST', body: form, signal }) }
  catch { throw new UploadAcknowledgementError('Mất kết nối khi nhập. Máy chủ có thể đã lưu phiên bản; hãy kiểm tra danh sách phiên bản trước khi gửi lại. Không tự gửi lại.') }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (body?.error?.code === 'CSV_SCHEMA_MISMATCH') throw new Error('Tên và thứ tự cột không khớp dataset. Hãy tạo bộ dữ liệu khác nếu cấu trúc thay đổi.')
    if(response.status>=500)throw new UploadAcknowledgementError('Chưa xác nhận được kết quả nhập từ máy chủ. Phiên bản có thể đã được lưu; hãy kiểm tra trước khi gửi lại.')
    if (typeof body?.error?.message === 'string') throw new Error(body.error.message)
    throw new Error(response.status === 413 ? 'File vượt giới hạn 5 MiB.'
      : response.status === 422 ? 'File CSV thiếu hoặc không hợp lệ.'
      : 'Không xác nhận được kết quả nhập. Hãy kiểm tra danh sách phiên bản trước khi gửi lại.')
  }
  try {
    const value=await response.json() as VersionImportResult
    if(!Number.isSafeInteger(value.version_id)||value.version_id<1||!Number.isSafeInteger(value.version_number)||value.version_number<1||value.dataset_id!==datasetId||(batchId!==undefined&&value.batch_id!==batchId))throw new Error('Invalid acknowledgement')
    return value
  }
  catch { throw new UploadAcknowledgementError('Không đọc được kết quả nhập. Máy chủ có thể đã lưu phiên bản; hãy kiểm tra danh sách phiên bản trước khi gửi lại.') }
}

export interface DatasetColumn { id: number; name: string; position: number; description: string | null }
export interface InferredColumn {
  column_name: string; position: number
  inferred_type: 'integer' | 'decimal' | 'boolean' | 'date' | 'text' | 'unknown'
  non_missing_count: number; missing_count: number
}
export interface DatasetVersion {
  id: number
  dataset_id?: number
  batch_id?: number
  is_current?: boolean
  version_number: number
  original_filename: string
  file_size_bytes: number
  row_count: number
  imported_at: string
  inferred_types: InferredColumn[]
}

export interface CreateBatchInput {
  store_id?:number
  name: string
  period_label?: string | null
  description?: string | null
  copy_template_rules?: boolean
}

export interface DataBatchItem {
  store_id?:number|null;supplier?:import('../workspace/Suppliers').Supplier|null
  business_state?: string
  workflow_enabled?: boolean
  id: number
  rules_revision?: number
  dataset_id: number
  name: string
  description: string | null
  period_label: string | null
  created_at: string
  updated_at: string
  version_count: number
  latest_version?: {
    id: number
    version_number: number
    original_filename: string
    row_count: number
    file_size_bytes: number
    imported_at: string
    latest_run?: {
      batch_rules_revision?: number | null
      engine_version?: string
      rules_changed?: boolean
      run_id: number
      status: string
      started_at: string
      error_row_count: number | null
      violation_count: number | null
      total_rows: number | null
    } | null
  } | null
}

export interface BatchDetail extends DataBatchItem {
  versions: (DatasetVersion & {
    latest_run?: {
      batch_rules_revision?: number | null
      engine_version?: string
      rules_changed?: boolean
      run_id: number
      status: string
      started_at: string
      error_row_count: number | null
      violation_count: number | null
      total_rows: number | null
    } | null
  })[]
}

export async function createBatch(datasetId: number, input: CreateBatchInput, signal?: AbortSignal): Promise<DataBatchItem> {
  const payload = {
    store_id: input.store_id,
    name: input.name.trim(),
    description: input.description?.trim() || null,
    period_label: input.period_label?.trim() || null,
    copy_template_rules: input.copy_template_rules ?? true,
  }
  const response = await businessFetch(`/api/datasets/${datasetId}/batches`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.error?.message ?? 'Không thể tạo đợt dữ liệu. Vui lòng thử lại.')
  }
  return response.json() as Promise<DataBatchItem>
}

export async function listBatches(
  datasetId: number,
  page = 1,
  pageSize = 20,
  q?: string,
  signal?: AbortSignal
): Promise<{ items: DataBatchItem[]; total: number; page: number; page_size: number }> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (q) params.set('q', q)
  const response = await businessFetch(`/api/datasets/${datasetId}/batches?${params}`, { signal })
  if (!response.ok) throw new Error('Không thể tải danh sách đợt dữ liệu.')
  return response.json() as Promise<{ items: DataBatchItem[]; total: number; page: number; page_size: number }>
}

export async function getBatch(datasetId: number, batchId: number, signal?: AbortSignal): Promise<BatchDetail> {
  const response = await businessFetch(`/api/datasets/${datasetId}/batches/${batchId}`, { signal })
  if (!response.ok) throw new Error('Không thể tải chi tiết đợt dữ liệu.')
  return response.json() as Promise<BatchDetail>
}

export async function patchBatch(
  datasetId: number,
  batchId: number,
  changes: Partial<CreateBatchInput>,
  signal?: AbortSignal
): Promise<DataBatchItem> {
  const response = await businessFetch(`/api/datasets/${datasetId}/batches/${batchId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
    signal,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.error?.message ?? 'Không thể cập nhật đợt dữ liệu.')
  }
  return response.json() as Promise<DataBatchItem>
}
export interface DatasetDetail {
  id: number; name: string; description: string | null; source: string | null; owner: string | null
  created_at: string; updated_at: string; batch_count?: number; columns: DatasetColumn[]; versions: DatasetVersion[]
}
export interface RowsPage {
  header: string[]; items: { row_number: number; values: string[] }[]
  total: number; page: number; page_size: number
}
export class ReadError extends Error {
  status: number
  constructor(status: number) {
    super(status === 404 ? 'Không tìm thấy bộ dữ liệu hoặc phiên bản.' : 'Không thể tải dữ liệu. Vui lòng thử lại.')
    this.status = status
  }
}
async function readJSON<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await businessFetch(url, { signal })
  if (!response.ok) throw new ReadError(response.status)
  return response.json() as Promise<T>
}
export const fetchDatasetDetail = (id: number, signal: AbortSignal) =>
  readJSON<DatasetDetail>(`/api/datasets/${id}`, signal)
export const fetchDatasetRows = (id: number, version: number, page: number, signal: AbortSignal) =>
  readJSON<RowsPage>(`/api/datasets/${id}/versions/${version}/rows?page=${page}&page_size=20`, signal)

export async function importDataset(form: FormData): Promise<ImportResult> {
  let response: Response
  try {
    response = await businessFetch('/api/datasets/import', { method: 'POST', body: form })
  } catch {
    throw new UploadAcknowledgementError('Mất kết nối khi nhập. Máy chủ có thể đã lưu dữ liệu. Hãy kiểm tra danh sách trước khi gửi lại; hệ thống không tự gửi lại.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if(response.status>=500)throw new UploadAcknowledgementError('Chưa xác nhận được kết quả nhập. Máy chủ có thể đã lưu dữ liệu; hãy kiểm tra danh mục trước khi gửi lại.')
    if (typeof body?.error?.message === 'string') throw new Error(body.error.message)
    if (Array.isArray(body?.detail)) {
      const labels: Record<string, string> = { name: 'Tên bộ dữ liệu', file: 'File CSV', description: 'Mô tả', source: 'Nguồn', owner: 'Người phụ trách' }
      throw new Error(body.detail.map((item: { loc?: string[]; type?: string }) => {
        const field = item.loc?.at(-1) ?? ''
        return `${labels[field] ?? 'Thông tin nhập'}: ${item.type === 'missing' ? 'bắt buộc cung cấp.' : 'không hợp lệ.'}`
      }).join(' '))
    }
    throw new Error(response.status === 413 ? 'File vượt giới hạn 5 MiB.'
      : response.status === 503 ? 'Dịch vụ dữ liệu không sẵn sàng. Vui lòng thử lại sau.'
      : response.status === 422 ? 'Metadata hoặc nội dung CSV không hợp lệ.'
      : 'Chưa xác nhận được kết quả nhập. Hãy kiểm tra danh sách trước khi gửi lại.')
  }
  try {
    const value=await response.json() as ImportResult
    if(!Number.isSafeInteger(value.dataset_id)||value.dataset_id<1||!Number.isSafeInteger(value.version_id)||value.version_id<1||!Number.isSafeInteger(value.version_number)||value.version_number<1)throw new Error('Invalid acknowledgement')
    return value
  }
  catch { throw new UploadAcknowledgementError('Không đọc được kết quả nhập. Máy chủ có thể đã lưu dữ liệu; hãy kiểm tra danh sách trước khi gửi lại.') }
}

export async function fetchDatasets(page: number, signal: AbortSignal, q = ''): Promise<DatasetPage> {
  const params = new URLSearchParams({ page: String(page), page_size: '20' })
  if (q) params.set('q', q)
  return businessFetch(`/api/datasets?${params}`, { signal }, async response => {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    if (response.status === 422 && body?.error?.code === 'INVALID_SEARCH_QUERY' && typeof body.error.message === 'string')
      throw new Error(body.error.message)
    throw new Error(response.status === 503
      ? 'Dịch vụ dữ liệu hiện không sẵn sàng. Vui lòng thử lại.'
      : 'Không thể tải danh sách bộ dữ liệu. Vui lòng thử lại.')
  }
  return response.json() as Promise<DatasetPage>
  })
}
