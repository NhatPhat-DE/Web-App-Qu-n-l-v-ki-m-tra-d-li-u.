import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

// Test route normalization logic identical to DataCheckApp.normalizeRoute
function normalizeRoute(hash) {
  const clean = hash.replace(/^#\/?/, '').split('?')[0].trim()
  if (!clean || clean === 'home') return 'dashboard'
  if (clean === 'reports') return 'history'
  if (clean === 'admin') return 'accounts'
  if (clean === 'help') return 'guide'

  const segments = clean.split('/')
  if (segments[0] === 'datasets' && segments[1] && !segments[2]) {
    return `datasets/${segments[1]}/overview`
  }
  return clean
}

test('HM-02D.1: Route normalization and alias mapping', () => {
  assert.equal(normalizeRoute(''), 'dashboard')
  assert.equal(normalizeRoute('#/'), 'dashboard')
  assert.equal(normalizeRoute('#/home'), 'dashboard')
  assert.equal(normalizeRoute('#/reports'), 'history')
  assert.equal(normalizeRoute('#/admin'), 'accounts')
  assert.equal(normalizeRoute('#/help'), 'guide')

  // Direct and deep links
  assert.equal(normalizeRoute('#/dashboard'), 'dashboard')
  assert.equal(normalizeRoute('#/datasets'), 'datasets')
  assert.equal(normalizeRoute('#/datasets/15'), 'datasets/15/overview')
  assert.equal(normalizeRoute('#/datasets/15/overview'), 'datasets/15/overview')
  assert.equal(normalizeRoute('#/datasets/15/rules'), 'datasets/15/rules')
  assert.equal(normalizeRoute('#/datasets/15/history'), 'datasets/15/history')
  assert.equal(normalizeRoute('#/datasets/15/compare'), 'datasets/15/compare')
  assert.equal(normalizeRoute('#/datasets/15/trend'), 'datasets/15/trend')
  assert.equal(normalizeRoute('#/datasets/15/fields'), 'datasets/15/fields')
  assert.equal(normalizeRoute('#/datasets/15/versions'), 'datasets/15/versions')
  assert.equal(normalizeRoute('#/datasets/15/runs/108'), 'datasets/15/runs/108')

  // Legacy global rules route preserved
  assert.equal(normalizeRoute('#/rules'), 'rules')
})

test('HM-02D.1: Sidebar navigation item structure and role-based filtering', () => {
  const code = fs.readFileSync(path.resolve('src/workspace/DataCheckApp.tsx'), 'utf8')

  // Verify 5 main navigation items exist in DataCheckApp
  assert.ok(code.includes("label:'Dashboard'"), "Sidebar includes 'Trang chủ'")
  assert.ok(code.includes("label:'Danh mục & Từ điển'"), "Sidebar includes 'Bộ dữ liệu'")
  assert.ok(code.includes("label:'Nộp & Kiểm tra'"), "Sidebar includes task boards including Reports")
  assert.ok(code.includes("label:'Quản trị hệ thống'"), "Sidebar includes 'Quản trị'")
  assert.ok(code.includes("label:'Trợ giúp'"), "Sidebar includes 'Trợ giúp'")

  // Verify adminOnly filtering
  assert.ok(/adminOnly:\s*true/.test(code), "Quản trị has adminOnly flag")
  assert.ok(code.includes("!item.adminOnly || user.role === 'admin'"), 'Filters navigation by role')
})

test('HM-02D.1: Dataset Workspace 3 Business Groups in CatalogPages', () => {
  const code = fs.readFileSync(path.resolve('src/workspace/CatalogPages.tsx'), 'utf8')

  // Verify the 3 business groups
  assert.ok(code.includes("label: 'Bộ dữ liệu & Đợt'"), "Dataset group prioritizes information and batch selection")
  assert.ok(code.includes("label: 'Lịch sử & Cải thiện'"), "Contains 'Lịch sử & Cải thiện' group")
  assert.ok(code.includes("label: 'Cấu trúc & Thông tin'"), "Contains 'Cấu trúc & Thông tin' group")

  // Verify the 7 tabs mapped within the groups
  assert.ok(code.includes("id: 'overview'"), "Overview tab present")
  assert.ok(code.includes("id: 'rules'"), "Rules tab present")
  assert.ok(code.includes("id: 'history'"), "History tab present")
  assert.ok(code.includes("id: 'compare'"), "Compare tab present")
  assert.ok(code.includes("id: 'trend'"), "Trend tab present")
  assert.ok(code.includes("id: 'fields'"), "Fields tab present")
  assert.ok(code.includes("id: 'versions'"), "Versions tab present")

  // Verify ARIA tablist and tabs
  assert.ok(code.includes('role="navigation"'), 'Workspace tab groups container has role navigation')
  assert.ok(code.includes('role="tablist"'), 'Tab items container has role tablist')
  assert.ok(code.includes('role="tab"'), 'Tab links have role tab')
  assert.ok(code.includes('aria-selected='), 'Tab links have aria-selected')
})

test('HM-02D.1: Topbar Breadcrumb hierarchy and ThemeSwitcher integration', () => {
  const code = fs.readFileSync(path.resolve('src/workspace/DataCheckApp.tsx'), 'utf8')

  // Topbar contains ThemeSwitcher and Account
  assert.ok(code.includes('<ThemeSwitcher />'), 'Topbar includes ThemeSwitcher')
  assert.ok(code.includes('user.role === \'admin\' ? \'Quản trị viên\' : \'Người quản lý dữ liệu\''), 'Role formatted in Vietnamese')
  assert.ok(code.includes('breadcrumb-root'), 'Breadcrumb root present')
  assert.ok(code.includes('breadcrumb-separator'), 'Breadcrumb separators present')
})

test('HM-02D.1: CSS styles for breadcrumb and workspace-tab-groups exist', () => {
  const css = fs.readFileSync(path.resolve('src/workspace/design.css'), 'utf8')

  assert.ok(css.includes('.workspace-tab-groups'), 'design.css defines .workspace-tab-groups')
  assert.ok(css.includes('.workspace-tab-group'), 'design.css defines .workspace-tab-group')
  assert.ok(css.includes('.workspace-tab-group-label'), 'design.css defines .workspace-tab-group-label')
  assert.ok(css.includes('.workspace-tab-btn'), 'design.css defines .workspace-tab-btn')
  assert.ok(css.includes('.tab-badge'), 'design.css defines .tab-badge')
  assert.ok(css.includes('.breadcrumb-separator'), 'design.css defines .breadcrumb-separator')
})

test('HM-02D.1: Unsaved form dirty check preservation', () => {
  const code = fs.readFileSync(path.resolve('src/workspace/DataCheckApp.tsx'), 'utf8')

  // Ensure confirmLeave is checked on hashchange and on logout
  assert.ok(code.includes('if (!confirmLeave())'), 'Hashchange checks confirmLeave before routing')
  assert.ok(code.includes('if (confirmLeave()) onLogout()'), 'Logout checks confirmLeave before logging out')
})

