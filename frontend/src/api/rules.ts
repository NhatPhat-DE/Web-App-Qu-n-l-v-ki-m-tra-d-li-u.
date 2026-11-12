import { businessFetch } from './business'
import { RuleAPIError } from './ruleErrors'
export type RuleType = 'required' | 'unique' | 'numeric_range' | 'data_type' | 'date_format' | 'allowed_values' | 'pattern'
export type DataType = 'integer' | 'decimal' | 'boolean'
export type DateFormat = 'YYYY-MM-DD' | 'DD/MM/YYYY' | 'MM/DD/YYYY'
export interface RuleConfig { min?: string; max?: string; type?: string; format?: string; values?: string[]; pattern?: string; dialect?: string }
export interface RuleInput { name: string; rule_type: RuleType; columns: string[]; config: RuleConfig; is_active: boolean }
export interface QualityRule extends RuleInput { id: number; dataset_id: number; batch_id?: number | null; created_at: string; updated_at: string }
export interface RulePage { items: QualityRule[]; total: number; page: number; page_size: number }

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response
  try { response = await businessFetch(url, options) }
  catch (error) {
    if (options?.signal?.aborted) throw error
    throw new RuleAPIError(options?.method && options.method !== 'GET' ? 'NETWORK_ERROR' : 'NETWORK_READ_ERROR',0)
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new RuleAPIError(typeof body?.error?.code === 'string' ? body.error.code : 'INVALID_INPUT',response.status,typeof body?.error?.message === 'string' ? body.error.message : undefined)
  }
  try { const data = await response.json() as T; if (options?.signal?.aborted) throw new DOMException('Request cancelled', 'AbortError'); return data }
  catch { throw new RuleAPIError(options?.method && options.method !== 'GET' ? 'INVALID_RESPONSE' : 'INVALID_READ_RESPONSE',0) }
}
export const fetchRules = (dataset: number, page: number, signal: AbortSignal) =>
  request<RulePage>(`/api/datasets/${dataset}/rules?page=${page}&page_size=20`, { signal })
export const ruleScope = (dataset: number, batch?: number) => `/api/datasets/${dataset}${batch ? `/batches/${batch}` : ''}/rules`
export const createRule = (dataset: number, body: RuleInput, signal?: AbortSignal, batch?: number) =>
  request<QualityRule>(ruleScope(dataset, batch), { method: 'POST', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const patchRule = (dataset: number, rule: number, body: Partial<RuleInput>, signal?: AbortSignal, batch?: number) =>
  request<QualityRule>(`${ruleScope(dataset, batch)}/${rule}`, { method: 'PATCH', signal, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
