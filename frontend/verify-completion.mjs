import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'

export async function verifyCompletion(ctx) {
  const { evaluate, waitFor, clickText, value, field, go, screenshot, send, socket, confirmHandler, pause, apiCalls, checks, artifactRoot, dataset, firstRun, secondRun, credentials } = ctx
  assert.equal(await evaluate('location.origin'), 'http://127.0.0.1:5174')
  const limitations = []
  const stewardPassword = 'Ui-verification-' + Date.now() + '-secret'
  await clickText('Kết nối hệ thống'); await waitFor(`document.querySelectorAll('dialog .badge-success').length===2`); await screenshot('completion-system-status')
  await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }); await clickText('Kiểm tra lại kết nối'); await waitFor(`document.querySelectorAll('dialog .badge-danger').length===2`); await screenshot('completion-system-offline')
  await send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }); await clickText('Kiểm tra lại kết nối'); await waitFor(`document.querySelectorAll('dialog .badge-success').length===2`); await evaluate(`document.querySelector('dialog button[aria-label="Đóng"]').click()`)
  checks.push('System connection: real application/database health, offline error and manual recovery without fabricated success')
  async function api(url, method = 'GET', body) {
    return evaluate(`(async()=>{const session=await fetch('/api/auth/me').then(r=>r.json());const r=await fetch(${JSON.stringify(url)},{method:${JSON.stringify(method)},headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},${body === undefined ? '' : `body:JSON.stringify(${JSON.stringify(body)}),`}});return {status:r.status,body:await r.json().catch(()=>null)}})()`)
  }
  async function closeDirty() { socket.addEventListener('message', confirmHandler); try { await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`); await waitFor(`!document.querySelector('dialog[open]')`) } finally { socket.removeEventListener('message', confirmHandler) } }
  function fixture(data) {
    const result = spawnSync(path.resolve('../backend/.venv/Scripts/python.exe'), ['verify-completion-fixtures.py'], { input: JSON.stringify(data), encoding: 'utf8', windowsHide: true })
    assert.equal(result.status, 0, 'Disposable database fixture failed: ' + result.stderr)
  }
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await go('/accounts', 'Danh sách tài khoản'); await screenshot('completion-desktop-accounts')
  assert.equal(await evaluate(`document.querySelector('[aria-label="Sửa tài khoản frontend_test_admin"]').disabled`), true)
  const selfId = (await api('/api/auth/me')).body.user.id
  assert.equal((await api(`/api/admin/users/${selfId}`, 'PATCH', { role: 'data_steward' })).status, 409)
  await clickText('Tạo tài khoản'); await field('Tên đăng nhập', '??'); await field('Mật khẩu', stewardPassword); await field('Xác nhận mật khẩu', stewardPassword); await clickText('Xác nhận tạo'); await waitFor(`document.querySelector('dialog [role="alert"]')`)
  await field('Tên đăng nhập', 'verify_steward'); await clickText('Xác nhận tạo'); await waitFor(`!document.querySelector('dialog[open]') && document.querySelector('main').innerText.includes('verify_steward')`)
  await clickText('Tạo tài khoản'); await field('Tên đăng nhập', 'verify_steward'); await field('Mật khẩu', stewardPassword); await field('Xác nhận mật khẩu', stewardPassword); await clickText('Xác nhận tạo'); await waitFor(`document.querySelector('dialog .notice-error')?.textContent.includes('đã tồn tại')`); await screenshot('completion-account-conflict'); await closeDirty()
  await evaluate(`(async()=>{const session=await fetch('/api/auth/me').then(r=>r.json());for(let i=1;i<=21;i++){const r=await fetch('/api/admin/users',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf_token},body:JSON.stringify({username:'page_user_'+i,password:${JSON.stringify(stewardPassword)},role:'data_steward'})});if(!r.ok)throw Error('Account fixture failed')}})()`)
  await go('/dashboard', 'Lần kiểm tra gần đây'); await go('/accounts', 'Danh sách tài khoản'); await evaluate(`document.querySelector('[aria-label="Trang sau"]').click()`); await waitFor(`document.querySelector('.pagination')?.innerText.includes('Trang 2') && !document.querySelector('.loading-state')`); assert.equal(await evaluate(`document.querySelectorAll('tbody tr').length`), 3)
  await evaluate(`document.querySelector('[aria-label="Trang trước"]').click()`); await waitFor(`document.querySelector('[aria-label="Sửa tài khoản verify_steward"]')`)
  await evaluate(`document.querySelector('[aria-label="Sửa tài khoản verify_steward"]').click()`); await field('Vai trò', 'admin'); await evaluate(`document.querySelectorAll('dialog .check-line input')[0].click();document.querySelectorAll('dialog .check-line input')[1].click()`); await clickText('Lưu thay đổi'); await waitFor(`!document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`)
  await pause(150); await waitFor(`document.querySelector('[aria-label="Sửa tài khoản verify_steward"]')`); await evaluate(`document.querySelector('[aria-label="Sửa tài khoản verify_steward"]').click()`); await field('Vai trò', 'data_steward'); await evaluate(`document.querySelectorAll('dialog .check-line input')[0].click();document.querySelectorAll('dialog .check-line input')[1].click()`); await clickText('Lưu thay đổi'); await waitFor(`!document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`)
  checks.push('Accounts: real create, inline validation, duplicate 409, server pagination, role/activation changes with confirmation, self-change protected by UI and backend')
  await go(`/datasets/${dataset}/compare`, 'Đối chiếu hai lần kiểm tra'); await evaluate(`document.querySelector('[aria-label="Chọn lần ${firstRun} cho A"]').click();document.querySelector('[aria-label="Chọn lần ${secondRun} cho B"]').click()`); await evaluate(`document.querySelector('.comparison-selection button').click()`); await waitFor(`document.body.innerText.includes('Kết quả đối chiếu')`); assert.equal(await evaluate(`document.body.innerText.includes('Cùng điều kiện')`), true); await screenshot('completion-comparison-comparable')
  await send('Page.reload'); await waitFor(`document.body.innerText.includes('Kết quả đối chiếu') && !document.querySelector('.loading-state')`)
  await go(`/datasets/${dataset}/overview`, 'Phiên bản mới nhất'); await clickText('Chạy kiểm tra'); await waitFor(`document.querySelector('.active-rules ul li')`); await clickText('Bắt đầu kiểm tra'); await waitFor(`document.querySelector('.result-stat') && !document.querySelector('.loading-state')`)
  const thirdRun = await evaluate(`Number(location.hash.split('/')[4])`)
  await go(`/datasets/${dataset}/compare?a=${firstRun}&b=${thirdRun}`, 'Kết quả đối chiếu'); assert.equal(await evaluate(`document.body.innerText.includes('không cùng điều kiện')`), true); assert.equal(await evaluate(`document.querySelector('tbody')?.innerText.includes('Không áp dụng')`), false) // first table is the picker
  assert.equal(await evaluate(`[...document.querySelectorAll('td')].filter(e=>e.textContent==='Không áp dụng').length`), 5); await screenshot('completion-comparison-different')
  checks.push('Comparison: real comparable/different snapshots, server picker, direct A/B link and reload; no delta for different conditions')
  await go(`/datasets/${dataset}/trend`, 'Xu hướng chất lượng'); await waitFor(`document.querySelector('.trend-chart')`); assert.equal(await evaluate(`document.querySelectorAll('.trend-chart circle').length`), 3); assert.equal(await evaluate(`document.querySelectorAll('.trend-chart line[stroke-width="2.5"]').length`), 1); await screenshot('completion-trend')
  await value('.filter-bar select', String((await api(`/api/datasets/${dataset}`)).body.versions.find(item => item.version_number === 1).id)); await waitFor(`document.querySelectorAll('.trend-chart circle').length===1`)
  checks.push('Trend: real saved points, version filter, no joining different condition groups')
  await go(`/datasets/${dataset}/fields`, 'Giải thích các trường dữ liệu'); await waitFor(`document.querySelector('.inference-details')`); await evaluate(`document.querySelector('.inference-details').open=true`); assert.equal(await evaluate(`document.querySelector('.inference-details dl').innerText.includes('Giá trị thiếu')`), true)
  const firstVersion = (await api(`/api/datasets/${dataset}`)).body.versions.find(item => item.version_number === 1).id
  await value('.filter-bar select', String(firstVersion)); await waitFor(`document.querySelector('.inference-details dd')?.textContent==='v1'`); assert.equal(await evaluate(`document.querySelector('.inference-details dl div:last-child dd').textContent`), '1'); await screenshot('completion-inference-details')
  await go(`/datasets/${dataset}/runs/${firstRun}`, 'Các lỗi cần kiểm tra lại'); await clickText('Phân tích chất lượng'); await waitFor(`document.querySelector('.trace-context')`); await evaluate(`document.querySelector('.trace-context').open=true`); assert.match(await evaluate(`document.querySelector('.trace-context code').textContent`), /^rules-v[12]:[a-f0-9]{64}$/); await screenshot('completion-run-trace')
  checks.push('Inference: per-version missing/nonmissing counts; saved result exposes actual engine and rule fingerprint for traceability')
  await go(`/datasets/${dataset}/rules`, 'Quy tắc của bộ dữ liệu'); await clickText('AI gợi ý quy tắc'); await evaluate(`[...document.querySelectorAll('dialog .checkbox-list input')].forEach(e=>e.click())`)
  const sendsBefore = apiCalls.filter(item => item.path.endsWith('/ai-rule-suggestions')).length
  await clickText('Xem trước nội dung gửi'); await waitFor(`document.querySelector('.payload-preview') || document.querySelector('dialog .notice-error')`)
  if (await evaluate(`!!document.querySelector('.payload-preview')`)) {
    const payload = await evaluate(`JSON.parse(document.querySelector('.payload-preview').textContent)`)
    assert.equal(Array.isArray(payload.columns), true); assert.equal(JSON.stringify(payload).includes('Khách hàng mẫu B'), false)
    assert.equal(apiCalls.filter(item => item.path.endsWith('/ai-rule-suggestions')).length, sendsBefore)
    assert.equal(await evaluate(`[...document.querySelectorAll('dialog button')].find(e=>e.textContent.includes('Xác nhận gửi và lấy gợi ý')).disabled`), true)
    await screenshot('completion-ai-preview')
    const configured = await evaluate(`!document.querySelector('.ai-preview').innerText.includes('AI chưa được cấu hình')`)
    if (configured) {
      const columnId = (await api(`/api/datasets/${dataset}`)).body.columns[0].id
      assert.equal((await api(`/api/datasets/${dataset}/columns/${columnId}`, 'PATCH', { description: 'Mã khách hàng bắt buộc và duy nhất. Metadata đã đổi trong kiểm thử; ví dụ KH001.' })).status, 200)
      await evaluate(`document.querySelector('.ai-preview .check-line input').click()`); await clickText('Xác nhận gửi và lấy gợi ý'); await waitFor(`document.querySelector('dialog .notice-error') && !document.querySelector('.payload-preview')`); await screenshot('completion-ai-preview-invalidated')
      assert.equal(apiCalls.filter(item => item.path.endsWith('/ai-rule-suggestions')).length, sendsBefore + 1)
      await clickText('Xem trước nội dung gửi'); await waitFor(`document.querySelector('.payload-preview')`)
      assert.equal(await evaluate(`document.querySelector('.ai-preview .check-line input').checked`), false)
      checks.push('AI changed-metadata 409 clears the old preview and consent; a new preview and explicit consent are required before another dispatch')
      await evaluate(`document.querySelector('.ai-preview .check-line input').click()`); await clickText('Xác nhận gửi và lấy gợi ý')
      const deadline = Date.now() + 90000
      while (Date.now() < deadline && !await evaluate(`!!document.querySelector('.ai-draft') || !!document.querySelector('dialog .notice-error') || document.querySelector('dialog').innerText.includes('Không có gợi ý đủ căn cứ')`)) await pause(250)
      if (await evaluate(`!!document.querySelector('.ai-draft')`)) {
        assert.equal(await evaluate(`document.querySelector('.ai-draft .check-line input').checked`), false)
        assert.equal(await evaluate(`document.querySelector('.ai-draft button[type=submit]').disabled`), true)
        await evaluate(`document.querySelectorAll('.ai-draft')[0].querySelectorAll('.checkbox-list input').forEach(e=>{if(!e.checked)e.click()})`)
        await evaluate(`document.querySelector('.ai-draft input').dispatchEvent(new Event('change',{bubbles:true}))`)
        await evaluate(`document.querySelector('.ai-draft button[type=submit]').click()`); await waitFor(`document.querySelector('.ai-draft').innerText.includes('Quy tắc đã được lưu') || document.querySelector('.ai-draft .notice-error')`)
        assert.equal(await evaluate(`document.querySelector('.ai-draft').innerText.includes('Quy tắc đã được lưu')`), true)
        await screenshot('completion-ai-saved'); checks.push('AI live Gemini: preview, consent before dispatch, returned suggestions, assumptions, default off, real rule save, prevention of repeated save')
      } else {
        const status = await evaluate(`document.querySelector('dialog .notice-error')?.textContent || 'Gemini returned no supported suggestions.'`)
        limitations.push({ feature: 'AI live generation/draft saving', reason: status }); checks.push('AI real preview/consent and provider error or empty state verified; live draft success remains in limitations')
      }
    } else limitations.push({ feature: 'AI live generation', reason: 'Provider not configured in test backend.' })
  } else limitations.push({ feature: 'AI preview', reason: await evaluate(`document.querySelector('dialog .notice-error')?.textContent`) })
  await closeDirty()
  // Create 20 real errors and 12 rules/runs to exercise actual server pages.
  const csv = 'code,label\n' + Array.from({ length: 20 }, (_, i) => `,Nhãn kiểm thử ${i + 1}`).join('\n') + '\n'
  const imported = await evaluate(`(async()=>{const s=await fetch('/api/auth/me').then(r=>r.json());const body=new FormData();body.set('name','Kiểm thử phân trang lỗi');body.set('owner','Người thực hành');body.set('file',new File([${JSON.stringify(csv)}],'20-errors.csv',{type:'text/csv'}));const r=await fetch('/api/datasets/import',{method:'POST',headers:{'X-CSRF-Token':s.csrf_token},body});if(!r.ok)throw Error('Import fixture failed');return r.json()})()`)
  const extra = imported.dataset_id, version = imported.version_id
  for (let i = 0; i < 12; i++) assert.equal((await api(`/api/datasets/${extra}/rules`, 'POST', { name: `Quy tắc phân trang ${i + 1}`, rule_type: i === 0 ? 'data_type' : 'required', columns: [i === 0 ? 'label' : 'code'], config: i === 0 ? { type: 'integer' } : {}, is_active: i === 0 })).status, 201)
  const runIds = []
  for (let i = 0; i < 12; i++) { const result = await api(`/api/datasets/${extra}/versions/${version}/runs`, 'POST'); assert.equal(result.status, 201); runIds.push(result.body.run_id) }
  await clickText('Làm mới dữ liệu'); await go(`/datasets/${extra}/rules`, 'Quy tắc của bộ dữ liệu'); await waitFor(`document.querySelectorAll('tbody tr').length===10`); await evaluate(`document.querySelector('[aria-label="Trang sau"]').click()`); await waitFor(`document.querySelectorAll('tbody tr').length===2`)
  await go(`/datasets/${extra}/history`, 'Lịch sử của bộ dữ liệu'); await waitFor(`document.querySelectorAll('tbody tr').length===10`); await evaluate(`document.querySelector('[aria-label="Trang sau"]').click()`); await waitFor(`document.querySelectorAll('tbody tr').length===2`)
  await go(`/datasets/${extra}/runs/${runIds[0]}`, 'Các lỗi cần kiểm tra lại'); assert.equal(await evaluate(`document.querySelectorAll('tbody tr').length`), 10); await evaluate(`document.querySelector('[aria-label="Trang sau"]').click()`); await waitFor(`document.querySelector('.pagination')?.innerText.includes('Trang 2') && !document.querySelector('.loading-state')`)
  await clickText('Xuất CSV lỗi'); await waitFor(`document.body.innerText.includes('Đã xuất 20 lượt vi phạm')`)
  await value('.filter-bar input[type=number]', '15'); await waitFor(`document.querySelectorAll('tbody tr').length===1`); assert.equal(await evaluate(`document.querySelector('.row-number').textContent`), '15')
  await clickText('Đặt lại'); await value('.filter-bar input[type=search]', 'Nhãn kiểm thử 20'); await waitFor(`document.querySelectorAll('tbody tr').length===1`)
  await clickText('Đặt lại'); await screenshot('completion-server-violations')
  assert.ok(apiCalls.some(item => item.path.endsWith('/violations') && new URLSearchParams(item.query).get('page') === '2' && new URLSearchParams(item.query).get('page_size') === '10'))
  assert.ok(apiCalls.some(item => item.path.endsWith('/rules') && new URLSearchParams(item.query).get('page') === '2'))
  assert.ok(apiCalls.some(item => item.path.endsWith('/runs') && new URLSearchParams(item.query).get('page') === '2'))
  checks.push('Server pages: 12 rules, 12 runs, 20 violations; row filter, whole-set value search, CSV contains all 20 errors even from page 2')
  await go(`/datasets/${extra}/rules`, 'Quy tắc của bộ dữ liệu')
  for (const kind of ['numeric_range', 'allowed_values', 'integer']) {
    await clickText('Thêm quy tắc'); await field('Tên quy tắc', 'Biểu mẫu kiểm thử ' + kind); await field('Loại kiểm tra', kind)
    if (kind === 'allowed_values') await field('Các giá trị được chấp nhận', 'A\nB')
    await evaluate(`document.querySelector('dialog .check-line input').click()`); await clickText('Lưu quy tắc'); await waitFor(`!document.querySelector('dialog[open]')`); await pause(150); await waitFor(`!document.querySelector('.loading-state')`)
  }
  checks.push('Manual rule forms exercise all seven backend rule types across baseline and completion scenarios')
  fixture({ action: 'install_failure' })
  await go(`/datasets/${extra}/overview`, 'Phiên bản mới nhất'); await clickText('Chạy kiểm tra'); await waitFor(`document.querySelector('.active-rules ul li')`); await clickText('Bắt đầu kiểm tra'); await waitFor(`document.querySelector('dialog .notice-error a')`)
  assert.equal(await evaluate(`[...document.querySelectorAll('dialog button')].find(e=>e.textContent.includes('Bắt đầu kiểm tra')).disabled`), true)
  await evaluate(`document.querySelector('dialog .notice-error a').click()`); await waitFor(`document.body.innerText.includes('Thử lại bằng lần kiểm tra mới') && !document.querySelector('.loading-state')`); await screenshot('completion-recorded-failure')
  fixture({ action: 'remove_failure' }); socket.addEventListener('message', confirmHandler); await clickText('Thử lại bằng lần kiểm tra mới'); socket.removeEventListener('message', confirmHandler); await waitFor(`document.querySelector('.active-rules ul li')`); await clickText('Bắt đầu kiểm tra'); await waitFor(`document.querySelector('.result-stat') && !document.querySelector('.loading-state')`)
  checks.push('Real backend persistence failure in disposable DB: run_id error link, failed execution display, blocked replay, confirmed new run after recovery')
  await go('/datasets', 'Tất cả bộ dữ liệu'); await value('.search-input input', 'Thông tin được giữ'); await waitFor(`document.querySelectorAll('tbody tr').length===1`); assert.ok(apiCalls.some(item => item.path === '/api/datasets' && new URLSearchParams(item.query).get('q') === 'Thông tin được giữ')); checks.push('Catalog delegates multi-metadata search and pagination to backend')
  for (const route of [['accounts', 'Danh sách tài khoản'], [`datasets/${dataset}/compare?a=${firstRun}&b=${secondRun}`, 'Kết quả đối chiếu'], [`datasets/${dataset}/trend`, 'Xu hướng chất lượng']]) { await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: false }); await go('/' + route[0], route[1]); await screenshot('completion-mobile-' + (route[0].startsWith('accounts') ? 'accounts' : route[0].includes('compare') ? 'comparison' : 'trend')) }
  await go(`/datasets/${dataset}/rules`, 'Quy tắc của bộ dữ liệu'); await clickText('AI gợi ý quy tắc'); await screenshot('completion-mobile-ai'); await closeDirty()
  await evaluate(`document.querySelector('[aria-label="Đăng xuất"]').click()`); await waitFor(`document.querySelector('#login-username')`); await value('#login-username', 'verify_steward'); await value('#login-password', stewardPassword); await clickText('Đăng nhập'); await waitFor(`document.querySelector('.main-content') && !document.querySelector('.loading-state')`)
  assert.equal(await evaluate(`!!document.querySelector('nav a[href="#/accounts"]')`), false)
  await go('/accounts', 'Bạn không đủ quyền'); const forbidden = await api('/api/admin/users'); assert.equal(forbidden.status, 403); await screenshot('completion-role-forbidden')
  fixture({ action: 'expire', username: 'verify_steward' }); await clickText('Làm mới dữ liệu'); await waitFor(`document.querySelector('#login-username')`); await screenshot('completion-session-expired')
  await value('#login-username', 'verify_steward'); await value('#login-password', stewardPassword); await clickText('Đăng nhập'); await waitFor(`document.querySelector('.main-content') && !document.querySelector('.loading-state')`)
  checks.push('Steward: admin menu absent, direct route denied, real API 403; true expired server session returns to login and manual login recovers')
  fs.writeFileSync(path.join(artifactRoot, 'completion-details.json'), JSON.stringify({ limitations, testsUseOnlyDisposableDatabase: true, liveAICallContainsOnlySyntheticMetadata: true }, null, 2))
}
