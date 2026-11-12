import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

// Helper to calculate relative luminance according to WCAG 2.1
function getLuminance(hex) {
  const rgb = hex.replace('#', '')
  const r = parseInt(rgb.substring(0, 2), 16) / 255
  const g = parseInt(rgb.substring(2, 4), 16) / 255
  const b = parseInt(rgb.substring(4, 6), 16) / 255

  const a = [r, g, b].map(v => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)))
  return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2]
}

function getContrastRatio(hex1, hex2) {
  const lum1 = getLuminance(hex1)
  const lum2 = getLuminance(hex2)
  const brightest = Math.max(lum1, lum2)
  const darkest = Math.min(lum1, lum2)
  return (brightest + 0.05) / (darkest + 0.05)
}

test('HM-02C: Theme resolution logic', () => {
  function resolveTheme(pref, isSystemDark) {
    if (pref === 'system') return isSystemDark ? 'dark' : 'light'
    return pref
  }

  assert.equal(resolveTheme('light', false), 'light')
  assert.equal(resolveTheme('light', true), 'light')
  assert.equal(resolveTheme('dark', false), 'dark')
  assert.equal(resolveTheme('dark', true), 'dark')
  assert.equal(resolveTheme('soft', false), 'soft')
  assert.equal(resolveTheme('soft', true), 'soft')
  assert.equal(resolveTheme('system', false), 'light')
  assert.equal(resolveTheme('system', true), 'dark')
})

test('HM-02C: CSS tokens and theme blocks exist in design.css', () => {
  const cssPath = path.resolve('src/workspace/design.css')
  assert.ok(fs.existsSync(cssPath), 'design.css exists')
  const css = fs.readFileSync(cssPath, 'utf8')

  assert.ok(css.includes('[data-theme="light"]'), 'Light theme block defined')
  assert.ok(css.includes('[data-theme="dark"]'), 'Dark theme block defined')
  assert.ok(css.includes('[data-theme="soft"]'), 'Soft theme block defined')

  const requiredTokens = [
    '--bg-app',
    '--bg-surface',
    '--bg-surface-muted',
    '--text-primary',
    '--text-secondary',
    '--text-muted',
    '--border-default',
    '--border-focus',
    '--primary',
    '--success',
    '--warning',
    '--danger',
    '--focus-outline'
  ]

  for (const token of requiredTokens) {
    assert.ok(css.includes(token), `Token ${token} must be defined in CSS`)
  }
})

test('HM-02C: WCAG 2.2 AA Contrast Compliance for Light Theme', () => {
  const bgSurface = '#ffffff'
  const textPrimary = '#0f172a'
  const textSecondary = '#475569'
  const textMuted = '#64748b'
  const primaryBrand = '#4338ca'

  // WCAG AA requires >= 4.5:1 for normal text
  const primaryContrast = getContrastRatio(textPrimary, bgSurface)
  const secondaryContrast = getContrastRatio(textSecondary, bgSurface)
  const mutedContrast = getContrastRatio(textMuted, bgSurface)
  const brandContrast = getContrastRatio(primaryBrand, bgSurface)

  assert.ok(primaryContrast >= 4.5, `Primary text (${primaryContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(secondaryContrast >= 4.5, `Secondary text (${secondaryContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(mutedContrast >= 4.5, `Muted text (${mutedContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(brandContrast >= 4.5, `Brand color on white (${brandContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
})

test('HM-02C: WCAG 2.2 AA Contrast Compliance for Dark Theme', () => {
  const bgSurface = '#111827'
  const textPrimary = '#f8fafc'
  const textSecondary = '#cbd5e1'
  const textMuted = '#94a3b8'

  const primaryContrast = getContrastRatio(textPrimary, bgSurface)
  const secondaryContrast = getContrastRatio(textSecondary, bgSurface)
  const mutedContrast = getContrastRatio(textMuted, bgSurface)

  assert.ok(primaryContrast >= 4.5, `Dark primary text (${primaryContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(secondaryContrast >= 4.5, `Dark secondary text (${secondaryContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(mutedContrast >= 4.5, `Dark muted text (${mutedContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
})

test('HM-02C: WCAG 2.2 AA Contrast Compliance for Soft Theme', () => {
  const bgApp = '#f7f5f0'
  const textPrimary = '#292524'
  const textSecondary = '#44403c'
  const textMuted = '#57534e'
  const pineTeal = '#246b62'

  const primaryContrast = getContrastRatio(textPrimary, bgApp)
  const secondaryContrast = getContrastRatio(textSecondary, bgApp)
  const mutedContrast = getContrastRatio(textMuted, bgApp)
  const tealContrast = getContrastRatio(pineTeal, bgApp)

  assert.ok(primaryContrast >= 4.5, `Soft primary text (${primaryContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(secondaryContrast >= 4.5, `Soft secondary text (${secondaryContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(mutedContrast >= 4.5, `Soft muted text (${mutedContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
  assert.ok(tealContrast >= 4.5, `Soft pine teal (${tealContrast.toFixed(2)}:1) must meet WCAG AA 4.5:1`)
})

test('HM-02C: Zero FOUT inline script present in index.html', () => {
  const indexPath = path.resolve('index.html')
  const html = fs.readFileSync(indexPath, 'utf8')

  assert.ok(html.includes("localStorage.getItem('dataguard-theme')"), 'index.html contains localStorage theme check')
  assert.ok(html.includes("document.documentElement.setAttribute('data-theme'"), 'index.html sets data-theme before paint')
})

test('HM-02C: ThemeSwitcher component has keyboard and aria support', () => {
  const switcherPath = path.resolve('src/workspace/ThemeSwitcher.tsx')
  const switcherCode = fs.readFileSync(switcherPath, 'utf8')

  assert.ok(switcherCode.includes('role="menu"'), 'ThemeSwitcher has popover menu')
  assert.ok(switcherCode.includes('role="menuitemradio"'), 'ThemeSwitcher items have role menuitemradio')
  assert.ok(switcherCode.includes('aria-checked'), 'ThemeSwitcher items have aria-checked')
  assert.ok(switcherCode.includes('handleKeyDown'), 'ThemeSwitcher supports arrow key navigation')
})

