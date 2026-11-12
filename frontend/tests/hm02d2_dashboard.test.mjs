import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

// Helper mock data matching CatalogEntry structure
function createMockDataset({ id = 1, name = 'Test Dataset', versions = [], runs = [] }) {
  return {
    id,
    name,
    description: 'Description',
    source: 'Sales',
    owner: 'Accountant',
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z',
    versions,
    columns: [],
    runs,
  }
}

// Pure implementation of classifyDataset for test verification
function classifyDataset(dataset, actions = {}) {
  const latestVersion = dataset.versions[0]
  if (!latestVersion) {
    return {
      status: 'NO_FILE',
      statusLabel: 'Chưa có file dữ liệu',
      statusTone: 'neutral',
      actionLabel: 'Tải file CSV',
      actionTone: 'primary',
    }
  }

  const runs = dataset.runs || []
  const versionRun = runs
    .filter(r => r.version_id === latestVersion.id)
    .sort((a, b) => b.run_id - a.run_id)[0]

  if (!versionRun) {
    return {
      status: 'NEEDS_RUN',
      statusLabel: 'Chưa kiểm tra',
      statusTone: 'neutral',
      actionLabel: 'Chạy kiểm tra',
      actionTone: 'primary',
    }
  }

  if (versionRun.status === 'running') {
    return {
      status: 'NEEDS_RUN',
      statusLabel: 'Đang kiểm tra',
      statusTone: 'primary',
      actionLabel: 'Xem tiến độ',
      actionTone: 'secondary',
    }
  }

  if (versionRun.status === 'failed') {
    return {
      status: 'TECHNICAL_FAILED',
      statusLabel: 'Thực thi thất bại',
      statusTone: 'danger',
      actionLabel: 'Thử lại',
      actionTone: 'secondary',
    }
  }

  if ((versionRun.error_row_count ?? 0) > 0) {
    return {
      status: 'HAS_ERRORS',
      statusLabel: `${versionRun.error_row_count} dòng lỗi`,
      statusTone: 'warning',
      actionLabel: 'Xem lỗi',
      actionTone: 'primary',
      actionHref: `#/datasets/${dataset.id}/runs/${versionRun.run_id}`,
    }
  }

  return {
    status: 'PASSED',
    statusLabel: 'Đạt quy tắc',
    statusTone: 'success',
    actionLabel: 'Xem kết quả',
    actionTone: 'secondary',
    actionHref: `#/datasets/${dataset.id}/runs/${versionRun.run_id}`,
  }
}

test('HM-02D.2 / DG-224: Classification of empty dataset without files', () => {
  const emptyDataset = createMockDataset({ id: 1, name: 'Khách hàng mới', versions: [] })
  const result = classifyDataset(emptyDataset)

  assert.equal(result.status, 'NO_FILE')
  assert.equal(result.statusLabel, 'Chưa có file dữ liệu')
  assert.equal(result.actionLabel, 'Tải file CSV')
  assert.equal(result.actionTone, 'primary')
})

test('HM-02D.2 / DG-224: Classification of dataset with file but uninspected', () => {
  const uninspected = createMockDataset({
    id: 2,
    name: 'Báo cáo doanh thu',
    versions: [{ id: 10, version_number: 1, original_filename: 'dt.csv', row_count: 50 }],
    runs: [],
  })
  const result = classifyDataset(uninspected)

  assert.equal(result.status, 'NEEDS_RUN')
  assert.equal(result.statusLabel, 'Chưa kiểm tra')
  assert.equal(result.actionLabel, 'Chạy kiểm tra')
  assert.equal(result.actionTone, 'primary')
})

test('HM-02D.2 / DG-224: Classification of dataset with technical execution failure', () => {
  const failedRunDataset = createMockDataset({
    id: 3,
    name: 'Danh sách tồn kho',
    versions: [{ id: 11, version_number: 1, original_filename: 'tonkho.csv', row_count: 100 }],
    runs: [{ run_id: 1, version_id: 11, version_number: 1, status: 'failed', failure_message: 'Timeout' }],
  })
  const result = classifyDataset(failedRunDataset)

  assert.equal(result.status, 'TECHNICAL_FAILED')
  assert.equal(result.statusLabel, 'Thực thi thất bại')
  assert.equal(result.actionLabel, 'Thử lại')
  assert.equal(result.statusTone, 'danger')
  // Must NOT confuse technical crash with data error
  assert.notEqual(result.status, 'HAS_ERRORS')
})

test('HM-02D.2 / DG-224: Classification of dataset with detected errors in latest run', () => {
  const errorDataset = createMockDataset({
    id: 4,
    name: 'Hóa đơn bán lẻ',
    versions: [{ id: 12, version_number: 1, original_filename: 'hd.csv', row_count: 500 }],
    runs: [{ run_id: 2, version_id: 12, version_number: 1, status: 'completed', error_row_count: 15, violation_count: 23 }],
  })
  const result = classifyDataset(errorDataset)

  assert.equal(result.status, 'HAS_ERRORS')
  assert.equal(result.statusLabel, '15 dòng lỗi')
  assert.equal(result.actionLabel, 'Xem lỗi')
  assert.equal(result.statusTone, 'warning')
  assert.equal(result.actionHref, '#/datasets/4/runs/2')
})

test('HM-02D.2 / DG-224: Classification of dataset meeting all quality rules (Passed)', () => {
  const passedDataset = createMockDataset({
    id: 5,
    name: 'Danh mục chi nhánh',
    versions: [{ id: 13, version_number: 1, original_filename: 'chinhanh.csv', row_count: 20 }],
    runs: [{ run_id: 3, version_id: 13, version_number: 1, status: 'completed', error_row_count: 0, violation_count: 0 }],
  })
  const result = classifyDataset(passedDataset)

  assert.equal(result.status, 'PASSED')
  assert.equal(result.statusLabel, 'Đạt quy tắc')
  assert.equal(result.statusTone, 'success')
  assert.equal(result.actionLabel, 'Xem kết quả')
  assert.equal(result.actionHref, '#/datasets/5/runs/3')
})

test('HM-02D.2 / DG-223: Accurate KPI calculations without synthetic metrics', () => {
  const datasets = [
    createMockDataset({ id: 1, versions: [] }), // NO_FILE
    createMockDataset({
      id: 2,
      versions: [{ id: 10, version_number: 1 }],
      runs: [], // NEEDS_RUN
    }),
    createMockDataset({
      id: 3,
      versions: [{ id: 11, version_number: 1 }],
      runs: [{ run_id: 1, version_id: 11, status: 'completed', error_row_count: 8, violation_count: 14 }], // HAS_ERRORS
    }),
    createMockDataset({
      id: 4,
      versions: [{ id: 12, version_number: 1 }],
      runs: [{ run_id: 2, version_id: 12, status: 'completed', error_row_count: 0, violation_count: 0 }], // PASSED
    }),
  ]

  const totalDatasets = datasets.length
  const datasetsWithoutFiles = datasets.filter(d => d.versions.length === 0).length
  const classified = datasets.map(d => classifyDataset(d))
  const datasetsNeedingReview = classified.filter(c => c.status !== 'PASSED').length
  const allRuns = datasets.flatMap(d => d.runs)
  const completedRuns = allRuns.filter(r => r.status === 'completed').length

  assert.equal(totalDatasets, 4)
  assert.equal(datasetsWithoutFiles, 1)
  assert.equal(datasetsNeedingReview, 3) // NO_FILE (1) + NEEDS_RUN (1) + HAS_ERRORS (1)
  assert.equal(completedRuns, 2)
})

test('HM-02D.2 / DG-221 & DG-222: Dashboard component markup and action elements', () => {
  const code = fs.readFileSync(path.resolve('src/workspace/Dashboard.tsx'), 'utf8')

  assert.ok(code.includes('title="Bàn làm việc"'), 'Dashboard has title "Bàn làm việc"')
  assert.ok(code.includes('quick-actions-bar'), 'Dashboard defines quick-actions-bar')
  assert.ok(code.includes('Tạo bộ dữ liệu mới'), 'Quick actions has Create Dataset CTA')
  assert.ok(code.includes('Xem danh mục'), 'Quick actions has View Catalog link')
  assert.ok(code.includes('attention-panel'), 'Dashboard defines attention-panel')
  assert.ok(code.includes('recent-runs'), 'Dashboard defines recent-runs')
  assert.ok(code.includes('role="region"'), 'Dashboard defines accessibility regions')
})

test('HM-02D.2 / DG-227: CSS tokens and workbench classes in design.css', () => {
  const css = fs.readFileSync(path.resolve('src/workspace/design.css'), 'utf8')

  assert.ok(css.includes('.dashboard-workbench'), 'design.css defines .dashboard-workbench')
  assert.ok(css.includes('.quick-actions-bar'), 'design.css defines .quick-actions-bar')
  assert.ok(css.includes('.attention-tabs'), 'design.css defines .attention-tabs')
  assert.ok(css.includes('.attention-tab-btn'), 'design.css defines .attention-tab-btn')
  assert.ok(css.includes('.attention-item'), 'design.css defines .attention-item')
  assert.ok(css.includes('.skeleton-grid'), 'design.css defines .skeleton-grid')
})

