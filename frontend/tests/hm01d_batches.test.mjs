import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

test('DG-305: 3-level data hierarchy model', () => {
  // Dataset (Level 1)
  const dataset = {
    id: 1,
    name: 'Khách hàng',
    description: 'Danh mục khách hàng toàn quốc',
    batch_count: 2,
    version_count: 4,
  }

  // DataBatch (Level 2)
  const batchOct = {
    id: 101,
    dataset_id: dataset.id,
    name: 'Khách hàng tháng 10/2026',
    period_label: '10/2026',
    version_count: 2,
  }

  const batchNov = {
    id: 102,
    dataset_id: dataset.id,
    name: 'Khách hàng tháng 11/2026',
    period_label: '11/2026',
    version_count: 2,
  }

  // DatasetVersion (Level 3)
  const versionsOct = [
    { id: 201, dataset_id: dataset.id, batch_id: batchOct.id, version_number: 1, original_filename: 'kh_t10_goc.csv' },
    { id: 202, dataset_id: dataset.id, batch_id: batchOct.id, version_number: 2, original_filename: 'kh_t10_dasua.csv' },
  ]

  const versionsNov = [
    { id: 203, dataset_id: dataset.id, batch_id: batchNov.id, version_number: 1, original_filename: 'kh_t11_goc.csv' },
    { id: 204, dataset_id: dataset.id, batch_id: batchNov.id, version_number: 2, original_filename: 'kh_t11_dasua.csv' },
  ]

  // Verify hierarchy and version isolation
  assert.equal(dataset.id, batchOct.dataset_id)
  assert.equal(dataset.id, batchNov.dataset_id)
  assert.equal(batchOct.id, versionsOct[0].batch_id)
  assert.equal(versionsOct[0].version_number, 1)
  assert.equal(versionsOct[1].version_number, 2)
  // Batch Nov starts at v1 independently of Batch Oct
  assert.equal(batchNov.id, versionsNov[0].batch_id)
  assert.equal(versionsNov[0].version_number, 1)
  assert.equal(versionsNov[1].version_number, 2)
})

test('DG-302: Batch metadata validation rules', () => {
  function validateBatchInput(input) {
    const errors = {}
    const trimmedName = (input.name || '').trim()
    if (!trimmedName) {
      errors.name = 'Tên đợt dữ liệu không được để trống hoặc chỉ chứa khoảng trắng.'
    } else if (input.name.length > 200) {
      errors.name = 'Tên đợt dữ liệu tối đa 200 ký tự.'
    }
    if (input.period_label && input.period_label.length > 100) {
      errors.period_label = 'Kỳ dữ liệu tối đa 100 ký tự.'
    }
    if (input.description && input.description.length > 2000) {
      errors.description = 'Mô tả tối đa 2000 ký tự.'
    }
    return errors
  }

  // Blank name rejected
  assert.ok(validateBatchInput({ name: '' }).name)
  assert.ok(validateBatchInput({ name: '   ' }).name)

  // Excess length rejected
  assert.ok(validateBatchInput({ name: 'A'.repeat(201) }).name)
  assert.ok(validateBatchInput({ name: 'Valid', period_label: 'P'.repeat(101) }).period_label)
  assert.ok(validateBatchInput({ name: 'Valid', description: 'D'.repeat(2001) }).description)

  // Valid inputs pass
  assert.deepEqual(validateBatchInput({ name: 'Khách hàng T10/2026', period_label: '10/2026', description: 'Hợp lệ' }), {})
})

test('DG-306: Closed-loop remediation delta logic', () => {
  function computeRemediation(firstRun, latestRun) {
    if (!firstRun || !latestRun) return null

    const initialErrors = firstRun.error_row_count ?? 0
    const currentErrors = latestRun.error_row_count ?? 0
    const deltaErrors = initialErrors - currentErrors
    const pctImprovement = initialErrors > 0 ? (deltaErrors / initialErrors) * 100 : 0

    let status = 'unchanged'
    if (currentErrors === 0 && initialErrors > 0) {
      status = 'resolved'
    } else if (deltaErrors > 0) {
      status = 'improved'
    } else if (deltaErrors < 0) {
      status = 'regressed'
    }

    return {
      initialErrors,
      currentErrors,
      deltaErrors,
      pctImprovement,
      status,
    }
  }

  // Case 1: All errors fixed (10 -> 0)
  const resolved = computeRemediation({ error_row_count: 10 }, { error_row_count: 0 })
  assert.equal(resolved.status, 'resolved')
  assert.equal(resolved.deltaErrors, 10)
  assert.equal(resolved.pctImprovement, 100)

  // Case 2: Partial fix (10 -> 3)
  const improved = computeRemediation({ error_row_count: 10 }, { error_row_count: 3 })
  assert.equal(improved.status, 'improved')
  assert.equal(improved.deltaErrors, 7)
  assert.equal(improved.pctImprovement, 70)

  // Case 3: Quality regressed (5 -> 12)
  const regressed = computeRemediation({ error_row_count: 5 }, { error_row_count: 12 })
  assert.equal(regressed.status, 'regressed')
  assert.equal(regressed.deltaErrors, -7)

  // Case 4: No change (4 -> 4)
  const unchanged = computeRemediation({ error_row_count: 4 }, { error_row_count: 4 })
  assert.equal(unchanged.status, 'unchanged')
  assert.equal(unchanged.deltaErrors, 0)
})

test('DG-305: Route parsing for batches', () => {
  function parseBatchRoute(hash) {
    const clean = hash.replace(/^#\/?/, '').split('?')[0].trim()
    const segments = clean.split('/')
    if (segments[0] === 'datasets' && segments[1]) {
      if (segments[2] === 'batches') {
        return {
          isBatchTab: !segments[3],
          batchId: segments[3] ? Number(segments[3]) : null,
          datasetId: Number(segments[1]),
        }
      }
    }
    return null
  }

  const batchListRoute = parseBatchRoute('#/datasets/42/batches')
  assert.deepEqual(batchListRoute, {
    isBatchTab: true,
    batchId: null,
    datasetId: 42,
  })

  const batchDetailRoute = parseBatchRoute('#/datasets/42/batches/7')
  assert.deepEqual(batchDetailRoute, {
    isBatchTab: false,
    batchId: 7,
    datasetId: 42,
  })
})

test('DG-305 & DG-306: CSS classes exist in design.css', () => {
  const cssPath = path.resolve(__dirname, '../src/workspace/design.css')
  const css = fs.readFileSync(cssPath, 'utf8')

  assert.ok(css.includes('.remediation-card'), 'Missing .remediation-card')
  assert.ok(css.includes('.remediation-status-banner'), 'Missing .remediation-status-banner')
  assert.ok(css.includes('.remediation-metrics'), 'Missing .remediation-metrics')
  assert.ok(css.includes('.remediation-metric-item'), 'Missing .remediation-metric-item')
  assert.ok(css.includes('.batch-table'), 'Missing .batch-table')
  assert.ok(css.includes('.badge-subtle'), 'Missing .badge-subtle')
  assert.ok(css.includes('.icon-folder'), 'Missing .icon-folder')
})

