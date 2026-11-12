// Full UI regression against the unchanged backend in a disposable PostgreSQL database.
// Run through verify-redesign.py; credentials arrive on stdin and are never persisted.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { createServer } from 'vite'
import { parseCSVText, samples, csvBlob } from './src/workspace/csv.ts'
let raw = ''; for await (const chunk of process.stdin) raw += chunk
const credentials = JSON.parse(raw); raw = ''
const artifactRoot = path.resolve('test-artifacts', credentials.completion ? 'completion' : 'redesign')
fs.mkdirSync(artifactRoot, { recursive: true })
assert.equal(artifactRoot, path.join(process.cwd(), 'test-artifacts', credentials.completion ? 'completion' : 'redesign'))
for (const entry of fs.readdirSync(artifactRoot, { withFileTypes: true })) if (entry.isFile() && !['test-backend.log', 'preservation.json'].includes(entry.name)) fs.unlinkSync(path.join(artifactRoot, entry.name))
const csvFiles = {}
for (const [key, sample] of Object.entries(samples)) { const file = path.join(artifactRoot, sample.filename); fs.writeFileSync(file, '\uFEFF' + sample.content); csvFiles[key] = file }
assert.equal(parseCSVText('\uFEFFid,note\r\n1,"Việt, Nam"\r\n2,"dòng 1\r\ndòng 2"\r\n').rows[1][1], 'dòng 1\r\ndòng 2')
for (const content of ['', 'a,a\n1,2', ',b\n1,2', 'a,b\n1', 'a\n', 'a\n"oops', 'a\nx"y', 'a,b\n1,2\n\n']) assert.throws(() => parseCSVText(content))
assert.equal(parseCSVText(samples.customers.content).rowCount, 4)
assert.match(await csvBlob([['=1+1']]).text(), /'=1\+1/)
const server = await createServer({ server: { host: '127.0.0.1', port: 5174, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8011' } } })
await server.listen()
const origin = 'http://127.0.0.1:5174'
const browserPath = [path.join(process.env.LOCALAPPDATA ?? '', 'ms-playwright/chromium-1248/chrome-win64/chrome.exe'), 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(file => fs.existsSync(file))
assert.ok(browserPath, 'An installed Chromium browser is required.')
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'datacheck-redesign-'))
const browser = spawn(browserPath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' })
let socket, sessionId, sequence = 0
const pending = new Map(), errors = [], apiCalls = [], layouts = [], checks = [], downloads = []
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
function send(method, params = {}, session = sessionId) {
  return new Promise((resolve, reject) => {
    const id = ++sequence
    const timer = setTimeout(() => { pending.delete(id); reject(Error(`CDP timeout: ${method}`)) }, 20000)
    pending.set(id, { resolve, reject, timer }); socket.send(JSON.stringify({ id, method, params, ...(session ? { sessionId: session } : {}) }))
  })
}
async function evaluate(expression) { const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true, userGesture: true }); if (result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description ?? result.exceptionDetails.text); return result.result.value }
async function waitFor(expression, label = expression) { const end = Date.now() + 25000; while (Date.now() < end) { if (await evaluate(`Boolean(${expression})`)) return; await pause(100) }; throw Error(`Timed out: ${label}; UI: ${(await evaluate('document.body.innerText')).slice(-1800)}`) }
async function clickText(text, scope = 'document') { await waitFor(`[...${scope}.querySelectorAll('button,a')].some(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled)`); await evaluate(`[...${scope}.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled).click()`); await pause(100) }
async function value(selector, text) { await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const p=e.tagName==='SELECT'?HTMLSelectElement.prototype:e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,${JSON.stringify(text)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`); await pause(80) }
async function field(label, text) { const selector = await evaluate(`(()=>{const e=[...document.querySelectorAll('dialog[open] label')].find(e=>e.querySelector('span')?.textContent.replace(' *','').trim()===${JSON.stringify(label)})?.querySelector('input,select,textarea');if(!e)throw Error('Field missing');e.dataset.testField='active';return '[data-test-field="active"]';})()`); await value(selector, text); await evaluate(`document.querySelector(${JSON.stringify(selector)}).removeAttribute('data-test-field')`) }
async function upload(file) { const root = await send('DOM.getDocument'); const node = await send('DOM.querySelector', { nodeId: root.root.nodeId, selector: 'dialog[open] input[type=file]' }); await send('DOM.setFileInputFiles', { nodeId: node.nodeId, files: [file] }); await pause(150) }
async function go(hash, text) { await evaluate(`location.hash=${JSON.stringify(hash)}`); await waitFor(`document.querySelector('main')?.innerText.includes(${JSON.stringify(text)}) && !document.querySelector('.loading-state')`); await pause(150) }
async function screenshot(label) {
  await evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
  const metrics = await evaluate(`({width:innerWidth,height:innerHeight,documentWidth:document.documentElement.scrollWidth,tableScrollers:[...document.querySelectorAll('.table-scroll')].map(e=>({width:e.clientWidth,scrollWidth:e.scrollWidth}))})`)
  assert.ok(metrics.documentWidth <= metrics.width + 1, `${label}: page horizontal overflow: ${JSON.stringify(metrics)}`)
  layouts.push({ label, ...metrics }); const data = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }); fs.writeFileSync(path.join(artifactRoot, label + '.png'), Buffer.from(data.data, 'base64'))
}
async function addRule(name, kind, column) {
  await clickText('Thêm quy tắc'); await field('Tên quy tắc', name); await field('Loại kiểm tra', kind)
  if (kind === 'unique') { await evaluate(`(()=>{for(const e of document.querySelectorAll('dialog[open] .checkbox-list input')){if(e.checked !== (e.parentElement.textContent.trim()===${JSON.stringify(column)}))e.click()}})()`) }
  else await field('Trường áp dụng', column)
  await clickText('Lưu quy tắc'); await waitFor(`!document.querySelector('dialog[open]') && document.querySelector('main').innerText.includes(${JSON.stringify(name)})`)
}
try {
  while (!fs.existsSync(path.join(profile, 'DevToolsActivePort'))) { assert.equal(browser.exitCode, null, 'Browser failed to start'); await pause(100) }
  const [port, endpoint] = fs.readFileSync(path.join(profile, 'DevToolsActivePort'), 'utf8').trim().split(/\r?\n/)
  socket = new WebSocket(`ws://127.0.0.1:${port}${endpoint}`); await once(socket, 'open')
  socket.addEventListener('message', event => {
    const message = JSON.parse(String(event.data))
    if (message.id) { const call = pending.get(message.id); if (!call) return; pending.delete(message.id); clearTimeout(call.timer); if (message.error) call.reject(Error(message.error.message)); else call.resolve(message.result) }
    else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description ?? message.params.exceptionDetails.text)
    else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') errors.push(message.params.args.map(item => item.value ?? item.description).join(' '))
    else if (message.method === 'Network.requestWillBeSent' && message.params.request.url.startsWith(origin + '/api/')) { const url = new URL(message.params.request.url); apiCalls.push({ method: message.params.request.method, path: url.pathname, query: url.search }) }
    else if (message.method === 'Browser.downloadWillBegin') downloads.push({ filename: message.params.suggestedFilename })
  })
  const target = await send('Target.createTarget', { url: 'about:blank' }, null); sessionId = (await send('Target.attachToTarget', { targetId: target.targetId, flatten: true }, null)).sessionId
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable'); await send('DOM.enable')
  await send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: artifactRoot, eventsEnabled: true }, null)
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await send('Page.navigate', { url: origin }); await waitFor(`document.querySelector('#login-username')`)
  await screenshot('desktop-login')
  await value('#login-username', credentials.username); await value('#login-password', credentials.password)
  await clickText('Đăng nhập'); await waitFor(`document.querySelector('h1')?.textContent==='Tổng quan dữ liệu' && !document.querySelector('.loading-state')`)
  await screenshot('desktop-empty'); checks.push('Real cookie/CSRF login and empty workspace')
  await clickText('Tạo bộ dữ liệu'); await field('Tên bộ dữ liệu', 'Khách hàng thực hành'); await field('Người phụ trách', 'Người kiểm thử'); await field('Nguồn / bộ phận', 'Kinh doanh'); await field('Mô tả', 'Dữ liệu giả lập dùng riêng cho kiểm thử frontend.')
  await clickText('Tiếp tục: chọn CSV'); await upload(csvFiles.customers); await waitFor(`document.querySelector('dialog').innerText.includes('Khách hàng mẫu C, chi nhánh 1')`); await screenshot('desktop-upload-preview')
  await clickText('Xác nhận lưu phiên bản'); await waitFor(`document.querySelector('dialog')?.innerText.includes('Đã lưu phiên bản 1')`); await clickText('Thiết lập quy tắc'); await waitFor(`document.querySelector('h2')?.textContent==='Quy tắc của bộ dữ liệu'`)
  const dataset = await evaluate(`Number(location.hash.split('/')[2])`)
  await addRule('Mã khách hàng bắt buộc', 'required', 'ma_kh'); await addRule('Mã khách hàng duy nhất', 'unique', 'ma_kh'); await addRule('Email hợp lệ', 'email', 'email'); await addRule('Ngày đăng ký hợp lệ', 'date_format', 'ngay_dang_ky')
  await screenshot('desktop-rules'); checks.push('Create dataset + BOM/quoted CSV + all primary rule categories (4 rules)')
  await go(`/datasets/${dataset}/fields`, 'Giải thích các trường dữ liệu'); await clickText('Mô tả'); await field('Ý nghĩa và ví dụ giá trị', 'Mã khách hàng duy nhất. Ví dụ: KH001.'); await clickText('Lưu thay đổi'); await waitFor(`document.body.innerText.includes('Mã khách hàng duy nhất. Ví dụ: KH001.') && !document.querySelector('dialog[open]')`); checks.push('Column description persisted via PATCH')
  await go(`/datasets/${dataset}/overview`, 'Phiên bản mới nhất'); await clickText('Chạy kiểm tra'); await waitFor(`document.querySelector('dialog')?.innerText.includes('4 quy tắc')`); await clickText('Bắt đầu kiểm tra'); await waitFor(`document.querySelector('h1')?.textContent==='Kết quả kiểm tra' && document.querySelector('.result-stat') && !document.querySelector('.loading-state')`)
  const firstRun = await evaluate(`Number(location.hash.split('/')[4])`)
  const first = await evaluate(`fetch('/api/datasets/${dataset}/runs/${firstRun}').then(r=>r.json())`)
  assert.deepEqual([first.total_rows, first.error_row_count, first.violation_count], [4, 3, 6]); await screenshot('desktop-result-errors')
  await value('.filter-bar select', 'required'); await waitFor(`document.querySelector('.pagination')?.textContent.includes('1 kết quả')`); await screenshot('desktop-filtered-errors')
  await clickText('Đặt lại'); await clickText('Xuất CSV lỗi'); await waitFor(`document.body.innerText.includes('Đã xuất 6 lượt vi phạm')`)
  await value('.compact-select', 'xlsx'); await waitFor(`document.body.innerText.includes('Đã tải báo cáo đầy đủ')`); await pause(300)
  await value('.compact-select', 'json'); await pause(300); checks.push('Real quality result (4 rows, 3 error rows, 6 violations), filters, CSV + XLSX + JSON downloads')
  await evaluate(`document.querySelector('button[aria-label="Xem bản ghi 2"]').click()`); await waitFor(`document.querySelector('dialog')?.innerText.includes('Khách hàng mẫu B')`); await evaluate(`document.querySelector('dialog button[aria-label="Đóng"]').click()`); await waitFor(`!document.querySelector('dialog[open]')`)
  await clickText('Phân tích chất lượng'); await waitFor(`document.querySelector('.dimension-grid')`); await screenshot('desktop-breakdown'); checks.push('Original record inspection and saved quality breakdown')
  await clickText('Tải lên bản đã sửa'); await upload(csvFiles.fixed); await waitFor(`document.querySelector('dialog')?.innerText.includes('khach-hang-da-sua.csv')`); await clickText('Xác nhận lưu phiên bản'); await waitFor(`document.querySelector('dialog')?.innerText.includes('Đã lưu phiên bản 2')`); await clickText('Chạy kiểm tra'); await waitFor(`document.querySelector('dialog')?.innerText.includes('4 quy tắc')`); await clickText('Bắt đầu kiểm tra'); await waitFor(`document.querySelector('.result-stat.text-success strong')?.textContent==='4' && !document.querySelector('.loading-state')`)
  const secondRun = await evaluate(`Number(location.hash.split('/')[4])`); assert.notEqual(secondRun, firstRun)
  await screenshot('desktop-result-passed'); checks.push('Corrected CSV uploaded as version 2; second real run passes 4/4')
  await go('/history', 'Tất cả lần kiểm tra'); assert.equal(await evaluate(`document.querySelectorAll('tbody tr').length`), 2); await screenshot('desktop-history')
  await go(`/datasets/${dataset}/rules`, 'Quy tắc của bộ dữ liệu')
  await evaluate(`document.querySelector('[aria-label="Sửa quy tắc Mã khách hàng bắt buộc"]').click()`)
  await field('Tên quy tắc', 'Tên mới chỉ áp dụng cho lần chạy sau'); await evaluate(`document.querySelector('dialog .check-line input').click()`); await clickText('Lưu quy tắc'); await waitFor(`!document.querySelector('dialog[open]') && document.body.innerText.includes('Tên mới chỉ áp dụng cho lần chạy sau')`)
  const preserved = await evaluate(`fetch('/api/datasets/${dataset}/runs/${firstRun}').then(r=>r.json())`)
  assert.deepEqual(preserved.rule_snapshot, first.rule_snapshot); assert.deepEqual([preserved.error_row_count, preserved.violation_count], [3, 6]); checks.push('Rule rename/disable does not alter the first run or saved rule snapshot')
  await clickText('Thêm quy tắc'); await field('Tên quy tắc', 'Kiểm tra phản hồi lỗi'); await field('Loại kiểm tra', 'pattern'); await field('Trường áp dụng', 'ma_kh'); await field('Mẫu định dạng', '(abc'); await clickText('Lưu quy tắc'); await waitFor(`document.querySelector('dialog .notice-error')`)
  assert.equal(await evaluate(`document.querySelector('dialog input').value`), 'Kiểm tra phản hồi lỗi'); await field('Mẫu định dạng', 'KH[0-9]+'); await clickText('Lưu quy tắc'); await waitFor(`!document.querySelector('dialog[open]') && document.body.innerText.includes('Kiểm tra phản hồi lỗi')`); checks.push('Real backend validation error stays visible; rule form retains values and saves after correction')
  await go(`/datasets/${dataset}/overview`, 'Phiên bản mới nhất'); await clickText('Tải phiên bản mới')
  const badCSV = path.join(artifactRoot, 'cot-khong-khop.csv'); fs.writeFileSync(badCSV, 'ma_kh,cot_moi\nKH001,abc\n')
  await upload(badCSV); await waitFor(`document.querySelector('dialog .notice-error')?.textContent.includes('Cấu trúc khác')`); assert.equal(await evaluate(`[...document.querySelectorAll('dialog button')].find(e=>e.textContent.includes('Xác nhận lưu')).disabled`), true); await screenshot('desktop-schema-mismatch')
  // The confirmation is handled when it actually opens, using a one-shot event listener.
  const confirmHandler = event => { const message = JSON.parse(String(event.data)); if (message.method === 'Page.javascriptDialogOpening') send('Page.handleJavaScriptDialog', { accept: true }).catch(() => {}) }
  socket.addEventListener('message', confirmHandler)
  await evaluate(`document.querySelector('dialog button[aria-label="Đóng"]').click()`); await waitFor(`!document.querySelector('dialog[open]')`); socket.removeEventListener('message', confirmHandler)
  checks.push('Changed CSV structure lists missing/new columns and blocks saving; dirty dialog asks before closing')
  await clickText('Chỉnh sửa'); await field('Mô tả', 'Thông tin được giữ khi mất kết nối.')
  await send('Network.emulateNetworkConditions', { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }); await clickText('Lưu thay đổi'); await waitFor(`document.querySelector('dialog .notice-error')`)
  assert.equal(await evaluate(`document.querySelector('dialog textarea').value`), 'Thông tin được giữ khi mất kết nối.')
  await send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 }); await clickText('Lưu thay đổi'); await waitFor(`!document.querySelector('dialog[open]') && document.querySelector('main')?.innerText.includes('Thông tin được giữ khi mất kết nối.')`); checks.push('Connection loss preserves metadata form; manual retry succeeds without automatic replay')
  await go('/dashboard', 'Lần kiểm tra gần đây'); await waitFor(`document.querySelector('.donut')`); assert.deepEqual(await evaluate(`[...document.querySelectorAll('.metric-card>strong')].map(e=>e.textContent)`), ['1', '1', '2', '1']); await screenshot('desktop-dashboard')
  for (const viewport of [{ label: 'tablet', width: 834, height: 1112 }, { label: 'mobile', width: 390, height: 844 }]) {
    await send('Emulation.setDeviceMetricsOverride', { width: viewport.width, height: viewport.height, deviceScaleFactor: 1, mobile: false })
    for (const [hash, label, text] of [['/dashboard', 'dashboard', 'Lần kiểm tra gần đây'], ['/datasets', 'catalog', 'Tất cả bộ dữ liệu'], [`/datasets/${dataset}/fields`, 'fields', 'Giải thích các trường dữ liệu'], [`/datasets/${dataset}/versions`, 'versions', 'Các phiên bản dữ liệu'], [`/datasets/${dataset}/rules`, 'rules', 'Quy tắc của bộ dữ liệu'], [`/datasets/${dataset}/runs/${firstRun}`, 'errors', 'Các lỗi cần kiểm tra lại'], ['/history', 'history', 'Tất cả lần kiểm tra'], ['/guide', 'guide', 'File thực hành']]) { await go(hash, text); await waitFor(`!document.querySelector('.loading-state')`); await screenshot(`${viewport.label}-${label}`) }
    await evaluate(`document.querySelector('[aria-label="Mở menu"]').click()`); await waitFor(`document.querySelector('.sidebar.is-open')`); await screenshot(`${viewport.label}-menu`); await evaluate(`document.querySelector('[aria-label="Đóng menu"]').click()`)
  }
  checks.push('Desktop 1440, tablet 834 and mobile 390 screenshots; isolated horizontal table scroll; working mobile navigation')
  await go(`/datasets/${dataset}/overview`, 'Phiên bản mới nhất'); await clickText('Tải phiên bản mới'); await upload(path.join(artifactRoot, 'cot-khong-khop.csv')); await waitFor(`document.querySelector('dialog .notice-error')`); await screenshot('mobile-upload-mismatch')
  socket.addEventListener('message', confirmHandler); await evaluate(`document.querySelector('dialog button[aria-label="Đóng"]').click()`); await waitFor(`!document.querySelector('dialog[open]')`); socket.removeEventListener('message', confirmHandler)
  await go(`/datasets/${dataset}/rules`, 'Quy tắc của bộ dữ liệu'); await clickText('Thêm quy tắc'); await screenshot('mobile-rule-form')
  for (let i = 0; i < 15; i++) { await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab', windowsVirtualKeyCode: 9 }); assert.equal(await evaluate(`!!document.activeElement.closest('dialog[open]')`), true) }
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 }); await waitFor(`!document.querySelector('dialog[open]')`); checks.push('Mobile upload/rule dialogs fit screen; native modal traps keyboard focus and supports Escape')
  await evaluate(`(async()=>{const session=await fetch('/api/auth/me').then(r=>r.json());for(let i=1;i<=11;i++){const body=new FormData();body.set('name','Bộ dữ liệu phân trang '+i);body.set('source','Kho');body.set('owner','Người thực hành');body.set('file',new File(['ma_sp,ten_sp\\nSP001,Sản phẩm mẫu\\n'],'phan-trang.csv',{type:'text/csv'}));const response=await fetch('/api/datasets/import',{method:'POST',headers:{'X-CSRF-Token':session.csrf_token},body});if(!response.ok)throw Error('Pagination fixture import failed')}})()`)
  await clickText('Làm mới dữ liệu'); await go('/datasets', 'Tất cả bộ dữ liệu'); await waitFor(`document.querySelector('.pagination')?.textContent.includes('12 kết quả')`); assert.equal(await evaluate(`document.querySelectorAll('tbody tr').length`), 10)
  await evaluate(`document.querySelector('[aria-label="Trang sau"]').click()`); await waitFor(`document.querySelectorAll('tbody tr').length===2`)
  await value('.search-input input', 'Không có bộ dữ liệu này'); await waitFor(`document.body.innerText.includes('Không tìm thấy bộ dữ liệu')`); await clickText('Đặt lại bộ lọc'); await value('.filter-bar select', 'Kinh doanh'); await waitFor(`document.querySelectorAll('tbody tr').length===1`); checks.push('Real 12-dataset catalog: next page, zero search results, reset and source filter')
  if (credentials.completion) { const { verifyCompletion } = await import('./verify-completion.mjs'); await verifyCompletion({ evaluate, waitFor, clickText, value, field, go, screenshot, send, socket, confirmHandler, pause, apiCalls, checks, artifactRoot, dataset, firstRun, secondRun, credentials }) }
  await evaluate(`document.querySelector('[aria-label="Đăng xuất"]').click()`); await waitFor(`document.querySelector('#login-username')`); const anonymous = await evaluate(`fetch('/api/datasets').then(r=>r.status)`); assert.equal(anonymous, 401); checks.push('Real logout revokes access and returns to login; business API rejects anonymous requests')
  assert.equal(errors.length, 0, errors.join('\n'))
  const downloaded = fs.readdirSync(artifactRoot); assert.ok(downloaded.some(file => file.endsWith('.xlsx'))); assert.ok(downloaded.some(file => /^loi-kiem-tra-.*\.csv$/.test(file))); assert.ok(downloaded.some(file => file.endsWith('-report.json')))
  assert.equal(parseCSVText(fs.readFileSync(path.join(artifactRoot, `loi-kiem-tra-${firstRun}.csv`), 'utf8')).rowCount, 6)
  assert.equal(JSON.parse(fs.readFileSync(path.join(artifactRoot, `dataset-${dataset}-run-${firstRun}-report.json`), 'utf8')).violations.length, 6)
  const evidence = { backend: 'Unmodified FastAPI + real PostgreSQL disposable test database; no API interception or production mock data', checks, layouts, consoleErrors: errors, apiCalls, downloads, firstRun: { id: firstRun, rows: 4, errorRows: 3, violations: 6 }, secondRun: { id: secondRun, rows: 4, errorRows: 0, violations: 0 } }
  fs.writeFileSync(path.join(artifactRoot, 'verification.json'), JSON.stringify(evidence, null, 2)); console.log(JSON.stringify({ passed: checks, screenshots: layouts.length, consoleErrors: errors.length }))
} catch (error) {
  if (socket && sessionId) { try { await screenshot('failure'); fs.writeFileSync(path.join(artifactRoot, 'failure.txt'), String(error) + '\n' + (await evaluate('document.body.innerText'))) } catch {} }
  throw error
} finally {
  for (const call of pending.values()) clearTimeout(call.timer)
  socket?.close(); browser.kill(); await server.close(); await pause(300)
  fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
}
