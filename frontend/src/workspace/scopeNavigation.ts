import type { CatalogEntry } from './api'

export const isScopeId = (value: string) => /^[1-9]\d*$/.test(value) && Number.isSafeInteger(Number(value))
export function queryBatch(query: URLSearchParams): string {
  const value = query.get('batch_id') ?? ''
  return !value || value === 'all' || isScopeId(value) ? value : 'invalid'
}
export function runBatch(dataset: CatalogEntry, runId: number): number | undefined {
  const run = dataset.runs.find(item => item.run_id === runId)
  return run?.batch_id ?? dataset.versions.find(item => item.id === run?.version_id)?.batch_id
}
export const batchHref = (dataset: number, batch: number) => `#/datasets/${dataset}/batches/${batch}`
export function historyHref(dataset: number, batch?: number | string): string {
  return `#/datasets/${dataset}/history${batch && isScopeId(String(batch)) ? `?batch_id=${batch}` : ''}`
}
export function globalHistoryHref(dataset = '', batch = ''): string {
  const query = new URLSearchParams()
  if (isScopeId(dataset)) query.set('dataset_id', dataset)
  if (isScopeId(dataset) && isScopeId(batch)) query.set('batch_id', batch)
  return `#/history${query.size ? `?${query}` : ''}`
}
export function comparisonHref(dataset: number, batch = '', version = '', a = 0, b = 0): string {
  const query = new URLSearchParams()
  if (batch === 'all' || isScopeId(batch)) query.set('batch_id', batch)
  if (isScopeId(version)) query.set('version_id', version)
  if (a && b) { query.set('a', String(a)); query.set('b', String(b)) }
  return `#/datasets/${dataset}/compare${query.size ? `?${query}` : ''}`
}
export function comparisonScope(dataset: CatalogEntry, query: URLSearchParams): string {
  const a = Number(query.get('a')), b = Number(query.get('b'))
  // Explicit URL pairs define the visible scope, never hide one side behind a filter.
  if (a && b) {
    const left = runBatch(dataset, a), right = runBatch(dataset, b)
    return left && left === right ? String(left) : 'all'
  }
  return queryBatch(query)
}
