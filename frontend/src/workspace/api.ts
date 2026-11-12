import { businessFetch } from '../api/business'
import type { DatasetDetail, DatasetItem } from '../api/datasets'
import type { Page, RunDetail, RunSummary, Violation } from '../api/runs'
import type { QualityRule } from '../api/rules'

export interface CatalogEntry extends DatasetDetail { runs: RunSummary[]; batch_summaries?: import('./BatchDashboard').BatchMetric[] }
export interface NamedRun extends RunSummary { dataset: CatalogEntry }
export async function request<T>(url: string, signal?: AbortSignal): Promise<T> {
  try { return await businessFetch(url, { signal }, async response => {
    const body = await response.json().catch(() => null)
    if (!response.ok) throw new Error(body?.error?.message ?? (response.status === 403 ? 'Bạn không có quyền thực hiện thao tác này.' : 'Không thể tải dữ liệu. Vui lòng thử lại.'))
    if (body === null) throw new Error('Không đọc được phản hồi của hệ thống. Vui lòng thử lại.')
    return body as T
  }) } catch (cause) {
    if (signal?.aborted || cause instanceof DOMException && cause.name === 'AbortError') throw cause
    if (cause instanceof TypeError) throw new Error('Mất kết nối với hệ thống. Kiểm tra kết nối rồi bấm Thử lại.')
    throw cause
  }
}
export async function allPages<T>(url: string, signal?: AbortSignal): Promise<T[]> {
  const items: T[] = []
  for (let page = 1; ; page++) {
    const data = await request<Page<T>>(`${url}${url.includes('?') ? '&' : '?'}page=${page}&page_size=100`, signal)
    items.push(...data.items)
    if (items.length >= data.total || !data.items.length) return items
  }
}
export async function loadCatalog(signal: AbortSignal): Promise<CatalogEntry[]> {
  const batchSummary = await request<import('./BatchDashboard').BatchDashboardData>('/api/batch-dashboard', signal)
  const datasets = await allPages<DatasetItem>('/api/datasets', signal)
  const entries = new Array<CatalogEntry>(datasets.length)
  let cursor = 0
  await Promise.all(Array.from({ length: Math.min(4, datasets.length) }, async () => {
    while (cursor < datasets.length) {
      const index = cursor++
      const item = datasets[index]
      const [detail, runs] = await Promise.all([
        request<DatasetDetail>(`/api/datasets/${item.id}`, signal),
        allPages<RunSummary>(`/api/datasets/${item.id}/runs`, signal),
      ])
      const batches = batchSummary.items.filter(b=>b.dataset_id===item.id)
      entries[index] = { ...detail, runs: runs.map(run=>({...run, rules_changed: run.batch_rules_revision !== batches.find(b=>b.batch_id===run.batch_id)?.rules_revision})), batch_summaries: batches }
    }
  }))
  return entries
}
export const getRules = (id: number, signal?: AbortSignal, batch?: number) => allPages<QualityRule>(`/api/datasets/${id}${batch ? `/batches/${batch}` : ""}/rules`, signal)
export const getRun = (id: number, run: number, signal?: AbortSignal) => request<RunDetail>(`/api/datasets/${id}/runs/${run}`, signal)
export const getViolations = (id: number, run: number, signal?: AbortSignal) => allPages<Violation>(`/api/datasets/${id}/runs/${run}/violations`, signal)
export const getRulePage = (id: number, page: number, signal: AbortSignal, batch?: number) => request<Page<QualityRule>>(`/api/datasets/${id}${batch ? `/batches/${batch}` : ""}/rules?page=${page}&page_size=10`, signal)
export const getRunPage = (id: number, page: number, version: string, signal: AbortSignal, batch = '') => request<Page<RunSummary>>(`/api/datasets/${id}/runs?${new URLSearchParams({ page: String(page), page_size: '10', ...(version ? { version_id: version } : {}), ...(batch ? { batch_id: batch } : {}) })}`, signal)
export async function catalogSelection(known: CatalogEntry[], q: string, page: number, full: boolean, signal: AbortSignal): Promise<Page<CatalogEntry>> {
  const url = `/api/datasets?${new URLSearchParams(q ? { q } : {})}`
  const source = full ? { items: await allPages<DatasetItem>(url, signal), total: 0, page: 1, page_size: 10 } : await request<Page<DatasetItem>>(`${url}&page=${page}&page_size=10`, signal)
  const items: CatalogEntry[] = []
  for (const item of source.items) {
    const existing = known.find(value => value.id === item.id)
    if (existing) items.push({ ...existing, ...item })
    else {
      const [detail, runs] = await Promise.all([request<DatasetDetail>(`/api/datasets/${item.id}`, signal), allPages<RunSummary>(`/api/datasets/${item.id}/runs`, signal)])
      items.push({ ...detail, runs })
    }
  }
  return { ...source, items, total: full ? items.length : source.total }
}
export const namedRuns = (items: CatalogEntry[]): NamedRun[] => items.flatMap(dataset => dataset.runs.map(run => ({ ...run, dataset }))).sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at) || b.run_id - a.run_id)
export const latestRun = (dataset: CatalogEntry, version?: number) => dataset.runs.filter(run => version === undefined || run.version_id === version).sort((a, b) => b.run_id - a.run_id)[0]
