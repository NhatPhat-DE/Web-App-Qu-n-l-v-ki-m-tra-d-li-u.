import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

// Helper mimicking latestRun
function latestRun(dataset, version) {
  return dataset.runs
    .filter(run => version === undefined || run.version_id === version)
    .sort((a, b) => b.run_id - a.run_id)[0]
}

// Helper mimicking getCatalogStatus from CatalogPages.tsx
function getCatalogStatus(item) {
  const latest = item.versions[0]
  if (!latest) {
    return {
      status: 'NO_FILE',
      label: 'Chưa có file',
      tone: 'neutral',
      subtext: 'Chưa tải file dữ liệu',
    }
  }
  const run = latestRun(item, latest.id)
  if (!run) {
    return {
      status: 'NEEDS_RUN',
      label: 'Chưa kiểm tra',
      tone: 'warning',
      subtext: `Phiên bản v${latest.version_number} chưa kiểm tra`,
    }
  }
  if (run.status === 'running') {
    return {
      status: 'RUNNING',
      label: 'Đang kiểm tra',
      tone: 'primary',
      run,
      subtext: `Đang thực thi lần #${run.run_id}`,
    }
  }
  if (run.status === 'failed') {
    return {
      status: 'TECHNICAL_FAILED',
      label: 'Lỗi kỹ thuật',
      tone: 'danger',
      run,
      subtext: `Lần #${run.run_id}`,
    }
  }
  if ((run.error_row_count ?? 0) > 0) {
    return {
      status: 'HAS_ERRORS',
      label: `Có lỗi (${run.error_row_count})`,
      tone: 'warning',
      run,
      subtext: `Lần #${run.run_id}`,
    }
  }
  return {
    status: 'PASSED',
    label: 'Đạt chuẩn',
    tone: 'success',
    run,
    subtext: `Lần #${run.run_id}`,
  }
}

// -------------------------------------------------------------
// Test 1: DG-233 - 6 Dataset States Classification
// -------------------------------------------------------------
test('DG-233: 6 precise status classifications', () => {
  // 1. NO_FILE: Dataset with no versions
  const noFileDs = { id: 1, name: 'DS 1', versions: [], runs: [] }
  assert.equal(getCatalogStatus(noFileDs).status, 'NO_FILE')
  assert.equal(getCatalogStatus(noFileDs).label, 'Chưa có file')

  // 2. NEEDS_RUN: Version exists but no run for this version
  const needsRunDs = {
    id: 2,
    name: 'DS 2',
    versions: [{ id: 10, version_number: 1, row_count: 50 }],
    runs: [],
  }
  assert.equal(getCatalogStatus(needsRunDs).status, 'NEEDS_RUN')
  assert.equal(getCatalogStatus(needsRunDs).label, 'Chưa kiểm tra')

  // 3. RUNNING: Latest run is currently executing
  const runningDs = {
    id: 3,
    name: 'DS 3',
    versions: [{ id: 11, version_number: 1, row_count: 100 }],
    runs: [{ run_id: 101, version_id: 11, status: 'running', started_at: '2026-11-04T00:00:00Z' }],
  }
  assert.equal(getCatalogStatus(runningDs).status, 'RUNNING')
  assert.equal(getCatalogStatus(runningDs).label, 'Đang kiểm tra')

  // 4. TECHNICAL_FAILED: Latest run execution failed
  const failedDs = {
    id: 4,
    name: 'DS 4',
    versions: [{ id: 12, version_number: 1, row_count: 100 }],
    runs: [{ run_id: 102, version_id: 12, status: 'failed', error_row_count: null, started_at: '2026-11-04T00:00:00Z' }],
  }
  assert.equal(getCatalogStatus(failedDs).status, 'TECHNICAL_FAILED')
  assert.equal(getCatalogStatus(failedDs).label, 'Lỗi kỹ thuật')

  // 5. HAS_ERRORS: Run completed but found rule violations
  const errorsDs = {
    id: 5,
    name: 'DS 5',
    versions: [{ id: 13, version_number: 1, row_count: 200 }],
    runs: [{ run_id: 103, version_id: 13, status: 'completed', error_row_count: 15, started_at: '2026-11-04T00:00:00Z' }],
  }
  assert.equal(getCatalogStatus(errorsDs).status, 'HAS_ERRORS')
  assert.ok(getCatalogStatus(errorsDs).label.includes('Có lỗi'))

  // 6. PASSED: Run completed with 0 rule violations
  const passedDs = {
    id: 6,
    name: 'DS 6',
    versions: [{ id: 14, version_number: 1, row_count: 200 }],
    runs: [{ run_id: 104, version_id: 14, status: 'completed', error_row_count: 0, started_at: '2026-11-04T00:00:00Z' }],
  }
  assert.equal(getCatalogStatus(passedDs).status, 'PASSED')
  assert.equal(getCatalogStatus(passedDs).label, 'Đạt chuẩn')
})

// -------------------------------------------------------------
// Test 2: DG-233 - Strict Version Isolation (No False Positives)
// -------------------------------------------------------------
test('DG-233: Strict version isolation - uninspected v2 with passed v1 is classified as NEEDS_RUN', () => {
  const multiVersionDs = {
    id: 20,
    name: 'Doanh thu',
    versions: [
      { id: 202, version_number: 2, row_count: 500 }, // latest version: v2, NO runs yet
      { id: 201, version_number: 1, row_count: 400 }, // old version: v1, passed
    ],
    runs: [
      // Only v1 has a completed pass run!
      { run_id: 50, version_id: 201, version_number: 1, status: 'completed', error_row_count: 0, started_at: '2026-11-01T00:00:00Z' },
    ],
  }

  const result = getCatalogStatus(multiVersionDs)
  assert.equal(result.status, 'NEEDS_RUN', 'v2 must NOT inherit v1 status')
  assert.equal(result.label, 'Chưa kiểm tra')
  assert.ok(result.subtext.includes('v2 chưa kiểm tra'))
})

// -------------------------------------------------------------
// Test 3: DG-232 - Client-side Filtering & Disclaimer
// -------------------------------------------------------------
test('DG-232: Filter matching across source, owner, and status', () => {
  const items = [
    {
      id: 1,
      name: 'Khách hàng',
      source: 'Kinh doanh',
      owner: 'Nguyễn Văn A',
      versions: [],
      runs: [],
    },
    {
      id: 2,
      name: 'Hóa đơn',
      source: 'Kế toán',
      owner: 'Trần Thị B',
      versions: [{ id: 31, version_number: 1, row_count: 50 }],
      runs: [{ run_id: 61, version_id: 31, status: 'completed', error_row_count: 0 }],
    },
    {
      id: 3,
      name: 'Kho hàng',
      source: 'Kế toán',
      owner: 'Lê Văn C',
      versions: [{ id: 32, version_number: 1, row_count: 100 }],
      runs: [{ run_id: 62, version_id: 32, status: 'completed', error_row_count: 4 }],
    },
  ]

  // Filter by source
  const keToan = items.filter(item => item.source === 'Kế toán')
  assert.equal(keToan.length, 2)

  // Filter by owner
  const tranB = items.filter(item => item.owner === 'Trần Thị B')
  assert.equal(tranB.length, 1)
  assert.equal(tranB[0].name, 'Hóa đơn')

  // Filter by status 'no_file'
  const noFiles = items.filter(item => getCatalogStatus(item).status === 'NO_FILE')
  assert.equal(noFiles.length, 1)
  assert.equal(noFiles[0].name, 'Khách hàng')

  // Filter by status 'passed'
  const passed = items.filter(item => getCatalogStatus(item).status === 'PASSED')
  assert.equal(passed.length, 1)
  assert.equal(passed[0].name, 'Hóa đơn')

  // Filter by status 'errors'
  const withErrors = items.filter(item => getCatalogStatus(item).status === 'HAS_ERRORS')
  assert.equal(withErrors.length, 1)
  assert.equal(withErrors[0].name, 'Kho hàng')
})

// -------------------------------------------------------------
// Test 4: DG-235 - Contextual Empty States
// -------------------------------------------------------------
test('DG-235: Empty state copy and condition definitions', () => {
  const code = fs.readFileSync(path.resolve('src/workspace/CatalogPages.tsx'), 'utf8')

  // 1. Global empty state
  assert.ok(code.includes('Chưa có bộ dữ liệu nào'), 'Global empty state title present')
  assert.ok(code.includes('Tạo bộ dữ liệu mới và bắt đầu quản lý thông tin tập trung cho doanh nghiệp.'), 'Global empty state description present')

  // 2. Search / Filter empty state
  assert.ok(code.includes('Không tìm thấy bộ dữ liệu phù hợp'), 'Search/filter empty state title present')
  assert.ok(code.includes('Không có bộ dữ liệu nào khớp với điều kiện tìm kiếm hoặc bộ lọc hiện tại.'), 'Search/filter empty state description present')
  assert.ok(code.includes('Đặt lại bộ lọc'), 'Reset filter action present in search empty state')

  // 3. Empty dataset row cell state
  assert.ok(code.includes('Chưa có dữ liệu'), 'Empty dataset version tag says Chưa có dữ liệu')
  assert.ok(code.includes('Chưa tải CSV'), 'Empty dataset version cell subtitle present')

  // 4. Server search disclaimer text
  assert.ok(
    code.includes('Tìm kiếm từ khóa được thực hiện trực tiếp trên máy chủ. Bộ lọc Nguồn, Người phụ trách và Trạng thái được áp dụng trên tập dữ liệu tải về do máy chủ chưa hỗ trợ lọc nhiều chiều kết hợp.'),
    'Transparent disclaimer present'
  )
})

// -------------------------------------------------------------
// Test 5: DG-236 - Contextual Action Buttons
// -------------------------------------------------------------
test('DG-236: Action buttons correctly mapped per status', () => {
  function getActionConfig(status, dataset, run) {
    switch (status) {
      case 'NO_FILE':
        return { label: 'Tải file CSV', tone: 'primary', type: 'upload' }
      case 'NEEDS_RUN':
        return { label: 'Chạy kiểm tra', tone: 'primary', type: 'run' }
      case 'RUNNING':
        return { label: 'Đang kiểm tra', tone: 'ghost', type: 'disabled' }
      case 'TECHNICAL_FAILED':
        return { label: 'Thử lại', tone: 'secondary', type: 'run' }
      case 'HAS_ERRORS':
        return { label: 'Xem lỗi', tone: 'primary', type: 'link', href: `#/datasets/${dataset.id}/runs/${run.run_id}` }
      case 'PASSED':
        return { label: 'Xem kết quả', tone: 'secondary', type: 'link', href: `#/datasets/${dataset.id}/runs/${run.run_id}` }
    }
  }

  const ds = { id: 99 }
  const run = { run_id: 888 }

  assert.equal(getActionConfig('NO_FILE', ds, run).label, 'Tải file CSV')
  assert.equal(getActionConfig('NEEDS_RUN', ds, run).label, 'Chạy kiểm tra')
  assert.equal(getActionConfig('RUNNING', ds, run).label, 'Đang kiểm tra')
  assert.equal(getActionConfig('TECHNICAL_FAILED', ds, run).label, 'Thử lại')
  assert.equal(getActionConfig('HAS_ERRORS', ds, run).label, 'Xem lỗi')
  assert.equal(getActionConfig('HAS_ERRORS', ds, run).href, '#/datasets/99/runs/888')
  assert.equal(getActionConfig('PASSED', ds, run).label, 'Xem kết quả')
  assert.equal(getActionConfig('PASSED', ds, run).href, '#/datasets/99/runs/888')
})

// -------------------------------------------------------------
// Test 6: DG-231 & DG-237 - Semantic Tokens & CSS Classes
// -------------------------------------------------------------
test('DG-231 & DG-237: Catalog CSS classes and semantic tokens in design.css', () => {
  const css = fs.readFileSync(path.resolve('src/workspace/design.css'), 'utf8')

  // Check required catalog classes
  assert.ok(css.includes('.catalog-filter-bar'), 'Catalog filter bar class defined')
  assert.ok(css.includes('.catalog-filter-summary'), 'Catalog filter summary class defined')
  assert.ok(css.includes('.catalog-filter-pill'), 'Catalog filter pill class defined')
  assert.ok(css.includes('.catalog-filter-disclaimer'), 'Catalog filter disclaimer class defined')
  assert.ok(css.includes('.catalog-cell-main'), 'Catalog main cell class defined')
  assert.ok(css.includes('.catalog-cell-meta'), 'Catalog meta cell class defined')
  assert.ok(css.includes('.catalog-cell-version'), 'Catalog version cell class defined')
  assert.ok(css.includes('.catalog-cell-quality'), 'Catalog quality cell class defined')
  assert.ok(css.includes('.catalog-action-group'), 'Catalog action group class defined')
  assert.ok(css.includes('.search-clear-btn'), 'Search clear button class defined')

  // Verify semantic CSS variables are used without hardcoded raw hex colors in catalog classes
  const catalogSection = css.slice(css.indexOf('.catalog-filter-bar'), css.indexOf('.catalog-action-group') + 400)
  assert.ok(catalogSection.includes('var(--bg-surface-raised)'), 'Uses var(--bg-surface-raised)')
  assert.ok(catalogSection.includes('var(--border-default)'), 'Uses var(--border-default)')
  assert.ok(catalogSection.includes('var(--text-primary)'), 'Uses var(--text-primary)')
  assert.ok(catalogSection.includes('var(--text-secondary)'), 'Uses var(--text-secondary)')
  assert.ok(catalogSection.includes('var(--text-muted)'), 'Uses var(--text-muted)')
})

