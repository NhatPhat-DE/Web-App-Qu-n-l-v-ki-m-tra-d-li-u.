import { businessFetch } from './business'
import type { DatasetColumn, DatasetDetail } from './datasets'
export type DatasetMetadata = Pick<DatasetDetail, 'id' | 'name' | 'description' | 'source' | 'owner' | 'created_at' | 'updated_at'>
export type DatasetChanges = Partial<Pick<DatasetMetadata, 'name' | 'description' | 'source' | 'owner'>>
async function patch<T>(url: string, changes: object, signal?: AbortSignal): Promise<T> {
  let response: Response
  try { response = await businessFetch(url, { method: 'PATCH', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(changes) }) }
  catch { throw new Error('Mất kết nối khi lưu. Hãy tải lại thông tin để xác nhận trước khi lưu lại; hệ thống không tự gửi lại.') }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.error?.message ?? 'Thông tin không hợp lệ hoặc không thể lưu. Hãy tải lại thông tin để xác nhận trước khi lưu lại.')
  }
  try { return await response.json() as T }
  catch { throw new Error('Không đọc được kết quả lưu. Hãy tải lại thông tin để xác nhận trước khi lưu lại.') }
}
export const patchDatasetMetadata = (id: number, changes: DatasetChanges, signal?: AbortSignal) => patch<DatasetMetadata>(`/api/datasets/${id}`, changes, signal)
export const patchColumnDescription = (id: number, column: number, description: string | null) => patch<DatasetColumn>(`/api/datasets/${id}/columns/${column}`, { description })
export function changedFields(original: Record<string, string | null>, draft: Record<string, string | null>) {
  return Object.fromEntries(Object.entries(draft).filter(([key, value]) => value !== original[key]))
}
