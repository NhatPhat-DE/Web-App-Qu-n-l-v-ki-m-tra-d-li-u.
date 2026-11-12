import type { RuleConfig } from './rules'
import { businessFetch } from './business'
export interface RunSummary {
  batch_id?: number; batch_rules_revision?: number | null; rules_changed?: boolean
  run_id: number; version_id: number; version_number: number; status: 'running' | 'completed' | 'failed'
  started_at: string; finished_at: string | null; total_rows: number | null
  error_row_count: number | null; violation_count: number | null; error_row_rate: string | null
}
export interface RunDetail extends RunSummary {
  supplier?:import('../workspace/Suppliers').Supplier|null
  is_current?: boolean; rules_changed?: boolean; current_rules_revision?: number
  schema_snapshot?: {name: string; position: number; description: string | null}[] | null
  dataset_id: number; engine_version: string; failure_code: string | null; failure_message: string | null
  rule_snapshot: { id: number; name: string; rule_type: string; columns: string[]; config: RuleConfig }[]
}
export interface ComparisonSide {
  run_id: number; version: { id: number; version_number: number; original_filename: string }
  status: 'completed'; started_at: string; finished_at: string; engine_version: string
  rule_set_fingerprint: string; total_rows: number; error_row_count: number; violation_count: number
  error_row_rate: string; pass_rate: string; rule_snapshot: RunDetail['rule_snapshot']
}
export interface RunComparison {
  dataset_id: number; a: ComparisonSide; b: ComparisonSide; same_run: boolean; comparable: boolean
  non_comparable_reasons: ('ENGINE_VERSION_DIFFERENT' | 'RULE_SET_FINGERPRINT_DIFFERENT' | 'BATCH_DIFFERENT' | 'RULE_REVISION_DIFFERENT')[]
  delta: { total_rows: number; error_row_count: number; violation_count: number; error_row_rate: string; pass_rate: string } | null
}
export interface Violation {
  related_rows?: number[]
  id: number; row_number: number; rule_id_snapshot: number; rule_name: string
  columns: string[]; values: (string | null)[]; message: string; error_code: string
}
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export type QualityDimension = 'completeness' | 'uniqueness' | 'validity' | 'domain_conformance'
export interface QualityCounts { violation_count: number; violating_row_count: number }
export interface QualitySummary {
  summary_schema_version: '1'
  context: { dataset_id: number; version_id: number; version_number: number; original_filename: string
    run_id: number; status: 'completed'; started_at: string; finished_at: string; engine_version: string
    rule_set_fingerprint: string; rule_snapshot_source: 'saved_run' }
  overall: { total_rows: number; error_row_count: number; violation_count: number; error_row_rate: string; pass_rate: string }
  dimensions: (QualityCounts & { dimension: QualityDimension; label: string; rule_count: number; assessment_status: 'configured' | 'not_assessed' })[]
  rules: Page<QualityCounts & { rule_order: number; rule_id_snapshot: number; name: string; rule_type: string
    columns: string[]; config: RuleConfig; dimension: QualityDimension }>
  column_scopes: Page<QualityCounts & { scope_kind: 'column' | 'column_group'; columns: string[]; rule_ids: number[]; rule_count: number }>
  breakdown_note: string
}
export class RunAPIError extends Error {
  runId?: number
  code?: string
  constructor(message: string, runId?: number, code?: string) { super(message); this.runId = runId; this.code = code }
}
async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  try {
    return await businessFetch(url, options, async response => {
      const body = await response.json().catch(() => null)
      if (!response.ok) {
        throw new RunAPIError(typeof body?.error?.message === 'string' ? body.error.message
          : options.method === 'POST' ? 'Không xác nhận được kết quả. Hãy kiểm tra lịch sử trước khi chạy lại.' : 'Tham số không hợp lệ hoặc không thể tải dữ liệu.',
          typeof body?.error?.run_id === 'number' ? body.error.run_id : undefined,
          typeof body?.error?.code === 'string' ? body.error.code : undefined)
      }
      if (body === null) throw new RunAPIError('Không đọc được phản hồi. Nếu vừa chạy kiểm tra, hãy xem lịch sử trước khi chạy lại.')
      return body as T
    })
  } catch (cause) {
    if (options.signal?.aborted || cause instanceof RunAPIError || cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new RunAPIError(options.method === 'POST'
      ? 'Mất kết nối. Kiểm tra lịch sử trước khi chạy lại; máy chủ có thể đã tạo lần chạy. Hệ thống không tự gửi lại.'
      : 'Không thể tải dữ liệu kiểm tra. Vui lòng thử lại.')
  }
}
export const startRun = (dataset: number, version: number, signal?: AbortSignal) => request<{ run_id: number }>(`/api/datasets/${dataset}/versions/${version}/runs`, { method: 'POST', signal })
export const fetchRun = (dataset: number, run: number, signal: AbortSignal) => request<RunDetail>(`/api/datasets/${dataset}/runs/${run}`, { signal })
export async function fetchQualitySummary(dataset: number, run: number, rulePage: number, columnPage: number, signal: AbortSignal): Promise<QualitySummary> {
  const data = await request<QualitySummary>(`/api/datasets/${dataset}/runs/${run}/quality-summary?${new URLSearchParams({ rule_page: String(rulePage), column_page: String(columnPage), page_size: '20' })}`, { signal })
  const count = (value: unknown) => Number.isSafeInteger(value) && (value as number) >= 0
  const positive = (value: unknown) => count(value) && (value as number) > 0
  const counts = (item: QualityCounts) => item && count(item.violation_count) && count(item.violating_row_count)
  const columns = (value: unknown): value is string[] => Array.isArray(value) && value.length > 0 && value.every(column => typeof column === 'string')
  const dimensions: QualityDimension[] = ['completeness', 'uniqueness', 'validity', 'domain_conformance']
  const page = <T,>(value: Page<T>, expected: number, valid: (item: T) => boolean) => value && count(value.total)
    && value.page === expected && value.page_size === 20 && Array.isArray(value.items) && value.items.length <= 20 && value.items.every(valid)
  if (!data || data.summary_schema_version !== '1' || data.context?.dataset_id !== dataset || data.context?.run_id !== run
    || data.context.status !== 'completed' || data.context.rule_snapshot_source !== 'saved_run'
    || !positive(data.context.version_id) || !positive(data.context.version_number)
    || !['original_filename', 'started_at', 'finished_at', 'engine_version', 'rule_set_fingerprint'].every(key => typeof data.context[key as keyof QualitySummary['context']] === 'string')
    || !data.overall || !['total_rows', 'error_row_count', 'violation_count'].every(key => count(data.overall[key as keyof QualitySummary['overall']]))
    || ![data.overall.error_row_rate, data.overall.pass_rate].every(rate => typeof rate === 'string' && /^[0-9]+\.[0-9]{4}$/.test(rate))
    || !Array.isArray(data.dimensions) || data.dimensions.length !== 4
    || !data.dimensions.every((item, index) => counts(item) && item.dimension === dimensions[index] && typeof item.label === 'string'
      && count(item.rule_count) && ['configured', 'not_assessed'].includes(item.assessment_status))
    || !page(data.rules, rulePage, item => counts(item) && count(item.rule_order) && positive(item.rule_id_snapshot)
      && typeof item.name === 'string' && typeof item.rule_type === 'string' && dimensions.includes(item.dimension)
      && columns(item.columns) && !!item.config && typeof item.config === 'object' && !Array.isArray(item.config))
    || !page(data.column_scopes, columnPage, item => counts(item) && columns(item.columns)
      && (item.scope_kind === 'column' ? item.columns.length === 1 : item.scope_kind === 'column_group' && item.columns.length > 1)
      && positive(item.rule_count) && Array.isArray(item.rule_ids) && item.rule_ids.length === item.rule_count && item.rule_ids.every(positive))
    || typeof data.breakdown_note !== 'string') throw new RunAPIError('Phản hồi Dashboard không hợp lệ hoặc không khớp lần chạy/trang đang mở.')
  return data
}
function comparisonSideValid(side: ComparisonSide) {
  return side && Number.isSafeInteger(side.run_id) && side.version && Number.isSafeInteger(side.version.id)
    && Number.isSafeInteger(side.version.version_number) && typeof side.version.original_filename === 'string'
    && typeof side.started_at === 'string' && typeof side.finished_at === 'string'
    && typeof side.engine_version === 'string' && typeof side.rule_set_fingerprint === 'string'
    && ['total_rows', 'error_row_count', 'violation_count'].every(key => Number.isSafeInteger(side[key as keyof ComparisonSide]))
    && [side.error_row_rate, side.pass_rate].every(rate => typeof rate === 'string' && /^[0-9]+\.[0-9]{4}$/.test(rate))
    && Array.isArray(side.rule_snapshot) && side.rule_snapshot.every(rule => rule && typeof rule.name === 'string'
      && typeof rule.rule_type === 'string' && Array.isArray(rule.columns) && rule.columns.every(column => typeof column === 'string')
      && rule.config && typeof rule.config === 'object')
}
export async function fetchRunComparison(dataset: number, a: number, b: number, signal: AbortSignal): Promise<RunComparison> {
  const data = await request<RunComparison>(`/api/datasets/${dataset}/run-comparison?${new URLSearchParams({ a_run_id: String(a), b_run_id: String(b) })}`, { signal })
  if (!data || data.dataset_id !== dataset || !comparisonSideValid(data.a) || !comparisonSideValid(data.b) || data.a?.run_id !== a || data.b?.run_id !== b
      || data.a.status !== 'completed' || data.b.status !== 'completed'
      || typeof data.comparable !== 'boolean' || data.same_run !== (a === b)
      || !Array.isArray(data.non_comparable_reasons)
      || !data.non_comparable_reasons.every(reason => ['ENGINE_VERSION_DIFFERENT','RULE_SET_FINGERPRINT_DIFFERENT','BATCH_DIFFERENT','RULE_REVISION_DIFFERENT'].includes(reason))
      || (data.comparable ? data.non_comparable_reasons.length !== 0 : data.non_comparable_reasons.length === 0)
      || (data.comparable ? !data.delta || !['total_rows','error_row_count','violation_count'].every(key => Number.isSafeInteger(data.delta![key as keyof NonNullable<RunComparison['delta']>]))
        || ![data.delta.error_row_rate, data.delta.pass_rate].every(rate => typeof rate === 'string' && /^-?[0-9]+\.[0-9]{4}$/.test(rate)) : data.delta !== null))
    throw new RunAPIError('Phản hồi đối chiếu không khớp cặp lần chạy đã chọn.')
  return data
}
export const fetchHistory = (dataset: number, page: number, version: string, signal: AbortSignal) =>
  request<Page<RunSummary>>(`/api/datasets/${dataset}/runs?${new URLSearchParams({ page: String(page), page_size: '20', ...(version ? { version_id: version } : {}) })}`, { signal })
export const fetchViolations = (dataset: number, run: number, page: number, rule: string, row: string, signal: AbortSignal) =>
  request<Page<Violation>>(`/api/datasets/${dataset}/runs/${run}/violations?${new URLSearchParams({ page: String(page), page_size: '20', ...(rule ? { rule_id_snapshot: rule } : {}), ...(row ? { row_number: row } : {}) })}`, { signal })

export type ReportFormat = 'xlsx' | 'json'
const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

async function checkWorkbook(blob: Blob) {
  const invalid = () => new RunAPIError('Phản hồi không phải workbook Excel hợp lệ. Không có file nào được tải.')
  if (blob.size < 22) throw invalid()
  const head = new Uint8Array(await blob.slice(0, 4).arrayBuffer())
  if (head[0] !== 80 || head[1] !== 75 || head[2] !== 3 || head[3] !== 4) throw invalid()
  const start = Math.max(0, blob.size - 65557)
  const tail = new DataView(await blob.slice(start).arrayBuffer())
  let end = -1
  for (let i = tail.byteLength - 22; i >= 0; i--) {
    if (tail.getUint32(i, true) === 0x06054b50 && i + 22 + tail.getUint16(i + 20, true) === tail.byteLength) { end = i; break }
  }
  if (end < 0 || tail.getUint16(end + 4, true) || tail.getUint16(end + 6, true)) throw invalid()
  const entries = tail.getUint16(end + 10, true), size = tail.getUint32(end + 12, true), offset = tail.getUint32(end + 16, true)
  if (!entries || entries !== tail.getUint16(end + 8, true) || size > 4 * 1024 * 1024 || offset + size !== start + end) throw invalid()
  const bytes = new Uint8Array(await blob.slice(offset, offset + size).arrayBuffer()), directory = new DataView(bytes.buffer)
  const names = new Set<string>(); let position = 0
  for (let index = 0; index < entries; index++) {
    if (position + 46 > size || directory.getUint32(position, true) !== 0x02014b50) throw invalid()
    const length = directory.getUint16(position + 28, true), extra = directory.getUint16(position + 30, true), comment = directory.getUint16(position + 32, true)
    if (position + 46 + length + extra + comment > size) throw invalid()
    names.add(new TextDecoder('utf-8', { fatal: true }).decode(bytes.slice(position + 46, position + 46 + length)))
    position += 46 + length + extra + comment
  }
  if (position !== size || !['[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml', 'xl/worksheets/sheet1.xml'].every(name => names.has(name))) throw invalid()
}

export async function fetchReport(dataset: number, run: number, signal: AbortSignal, format: ReportFormat = 'json'): Promise<{ blob: Blob; filename: string }> {
  if (!['xlsx', 'json'].includes(format)) throw new RunAPIError('Định dạng báo cáo không hợp lệ.')
  try {
    return await businessFetch(`/api/datasets/${dataset}/runs/${run}/report${format === 'xlsx' ? '.xlsx' : ''}`, { signal }, async response => {
      const mime = response.ok ? response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() : undefined
      if (!response.ok || (format === 'xlsx' && mime === 'application/json')) {
        const body = await response.json().catch(() => null)
        throw new RunAPIError(typeof body?.error?.message === 'string' ? body.error.message : 'Không thể tải báo cáo. Vui lòng thử lại.')
      }
      if (mime !== (format === 'xlsx' ? XLSX_MIME : 'application/json')) throw new RunAPIError('Phản hồi không đúng định dạng báo cáo đã chọn.')
      const blob = await response.blob()
      if (signal.aborted) throw new DOMException('Request cancelled', 'AbortError')
      if (format === 'xlsx') await checkWorkbook(blob)
      else {
        let data
        try { data = JSON.parse(await blob.text()) } catch { throw new RunAPIError('Phản hồi không phải báo cáo JSON hợp lệ.') }
        if (data?.report_schema_version !== '1' || data?.dataset?.id !== dataset || data?.run?.id !== run || data?.run?.status !== 'completed'
          || !Array.isArray(data.rule_snapshot) || !Array.isArray(data.violations)) throw new RunAPIError('Nội dung JSON không khớp lần chạy đã chọn hoặc không phải báo cáo đầy đủ.')
      }
      const fallback = `dataset-${dataset}-run-${run}-report.${format}`
      const disposition = response.headers.get('content-disposition') ?? ''
      const match = /^attachment\s*;\s*filename=(?:"([A-Za-z0-9_-]+\.(?:json|xlsx))"|([A-Za-z0-9_-]+\.(?:json|xlsx)))\s*$/i.exec(disposition)
      const candidate = match?.[1] ?? match?.[2]
      const safe = candidate && candidate.length <= 180 && candidate.toLowerCase().endsWith('.' + format)
        && !/^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])\./i.test(candidate)
      return { blob, filename: safe ? candidate : fallback }
    })
  } catch (cause) {
    if (signal.aborted || cause instanceof RunAPIError || cause instanceof DOMException && cause.name === 'AbortError') throw cause
    throw new RunAPIError('Không thể tải hoặc đọc báo cáo. Kiểm tra kết nối và thử lại bằng thao tác của bạn.')
  }
}
