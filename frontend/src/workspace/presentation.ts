import type { DataBatchItem } from '../api/datasets'
import type { CatalogEntry } from './api'

/** Display only: API decimal strings and stored snapshots are never rounded here. */
export function percent(value: string | number | null | undefined): string {
  if (value == null || !Number.isFinite(Number(value))) return 'Chưa có kết quả'
  return Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 2 }) + '%'
}
export function amount(value: string | number): string {
  return Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 2 })
}
export function resultText(total: number, errors: number, violations: number): string {
  const n = (value: number) => value.toLocaleString('vi-VN')
  return `${n(total)} bản ghi · ${n(errors)} dòng lỗi · ${n(violations)} lượt vi phạm`
}
export function batchText(batch?: Pick<DataBatchItem, 'name' | 'period_label'> | null): string {
  return batch ? `${batch.name}${batch.period_label && !batch.name.includes(batch.period_label) ? ` · ${batch.period_label}` : ''}` : 'Đang tải tên đợt…'
}
export function initialComparisonBatch(dataset: CatalogEntry, a: number, b: number): string {
  const batchFor = (run: number) => {
    const summary = dataset.runs.find(r=>r.run_id===run)
    return summary?.batch_id ?? dataset.versions.find(v=>v.id===summary?.version_id)?.batch_id
  }
  const first = batchFor(a), second = batchFor(b)
  if (a && b) return first && first===second ? String(first) : ''
  return first ? String(first) : ''
}
