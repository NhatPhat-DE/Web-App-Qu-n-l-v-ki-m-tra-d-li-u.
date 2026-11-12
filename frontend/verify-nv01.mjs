// Real headless Chromium QA against only the named NV-01 dataset. Session on stdin.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
let input='';for await(const chunk of process.stdin)input+=chunk
const {token,qa}=JSON.parse(input);input=''
const out=path.resolve('test-artifacts/nv01');fs.mkdirSync(out,{recursive:true})
const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'nv01-browser-'))
const browser=spawn(browserPath,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'})
const pause=ms=>new Promise(r=>setTimeout(r,ms));const pending=new Map();const checks=[],errors=[];let socket,sessionId,seq=0
function send(method,params={},session=sessionId){return new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout ${method}`))},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(session?{sessionId:session}:{})}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);return r.result.value}
async function waitFor(expression){for(let i=0;i<150;i++){if(await evaluate(`Boolean(${expression})`))return;await pause(100)}throw Error(`UI timeout: ${expression}; ${(await evaluate('document.body.innerText')).slice(-2000)}`)}
async function go(hash,text){await evaluate(`location.hash=${JSON.stringify(hash)}`);await waitFor(`document.querySelector('main')?.innerText.includes(${JSON.stringify(text)}) && !document.querySelector('.loading-state')`);await pause(150)}
async function screenshot(label){const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,label+'.png'),Buffer.from(r.data,'base64'))}
async function click(text){await evaluate(`[...document.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled).click()`);await pause(150)}
try{
  let ready=false;for(let i=0;i<150;i++){if(fs.existsSync(path.join(profile,'DevToolsActivePort'))){ready=true;break}assert.equal(browser.exitCode,null);await pause(100)}assert.ok(ready,'Browser startup timeout')
  const [port,endpoint]=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').trim().split(/\r?\n/)
  socket=new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);await once(socket,'open')
  socket.addEventListener('message',event=>{const m=JSON.parse(String(event.data));if(m.id){const p=pending.get(m.id);if(!p)return;clearTimeout(p.timer);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description??m.params.exceptionDetails.text)})
  const t=await send('Target.createTarget',{url:'about:blank'},null);sessionId=(await send('Target.attachToTarget',{targetId:t.targetId,flatten:true},null)).sessionId
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('DOM.enable')
  await send('Network.setCookie',{name:'datalens_session',value:token,url:'http://127.0.0.1:5173/api',path:'/api',httpOnly:true,sameSite:'Lax'})
  await send('Emulation.setDeviceMetricsOverride',{width:1366,height:900,deviceScaleFactor:1,mobile:false})
  await send('Page.navigate',{url:'http://127.0.0.1:5173/#/dashboard'})
  await waitFor(`document.querySelector('h1')?.textContent==='Bàn làm việc theo đợt dữ liệu' && !document.querySelector('.loading-state')`)
  await screenshot('dashboard');checks.push('Dashboard rendered from current versions per batch')
  await evaluate(`(()=>{const e=document.querySelector('main select[multiple]');for(const o of e.options)o.selected=o.value===${JSON.stringify(String(qa.january_batch_id))};e.dispatchEvent(new Event('change',{bubbles:true}));})()`)
  await waitFor(`document.querySelectorAll('main tbody tr').length===1 && document.querySelector('main').innerText.includes('Chưa kiểm tra') && !document.querySelector('.loading-state')`)
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('.result-stat strong')].map(e=>e.textContent)`),['0','0','0','Chưa có mẫu số'])
  await screenshot('dashboard-unchecked-current');checks.push('January current v3 unchecked: zero assessed rows and no fallback to v2')
  await evaluate(`(()=>{const e=document.querySelector('main select[multiple]');for(const o of e.options)o.selected=${JSON.stringify([String(qa.january_batch_id),String(qa.february_batch_id)])}.includes(o.value);e.dispatchEvent(new Event('change',{bubbles:true}));})()`)
  await waitFor(`document.querySelectorAll('main tbody tr').length===2 && document.querySelector('.result-stat strong')?.textContent==='12' && !document.querySelector('.loading-state')`)
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('.result-stat strong')].map(e=>e.textContent)`),['12','9','16','75.0000%'])
  await screenshot('dashboard-two-batches');checks.push('Selected January+February: only current completed February run contributes 12/9/16')
  await go(`/datasets/${qa.dataset_id}/batches/${qa.january_batch_id}`,'Quy tắc riêng của đợt')
  assert.ok(await evaluate(`document.querySelector('main').innerText.includes('v3') && document.querySelector('main').innerText.includes('Hiện hành')`))
  await screenshot('january-batch');checks.push('Jan v1,v2,v3, current and independent rules revision visible')
  await click('Thêm quy tắc');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Đợt #${qa.january_batch_id}')`)
  await screenshot('batch-rule-form');await click('Hủy');checks.push('Manual rule dialog bound to explicit batch')
  await go(`/datasets/${qa.dataset_id}/runs/${qa.january_runs[0].run_id}`,'Kết quả kiểm tra')
  await waitFor(`document.querySelector('.result-stat')`);await screenshot('raw-result')
  assert.ok(await evaluate(`document.querySelector('main').innerText.includes('16') && document.querySelector('main').innerText.includes('Đợt #${qa.january_batch_id}')`))
  await waitFor(`!document.querySelector('button:disabled')?.textContent.includes('Tải lên bản đã sửa')`)
  await click('Tải lên bản đã sửa');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('NV-01 Tháng 01/2026')`)
  await screenshot('correct-batch-upload');await click('Hủy');checks.push('Result upload is locked to original January batch')
  await go(`/datasets/${qa.dataset_id}/compare?a=${qa.january_runs[0].run_id}&b=${qa.january_runs[1].run_id}`,'Kết quả đối chiếu')
  assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Cùng điều kiện')`));await screenshot('same-batch-comparison')
  checks.push('Same batch same revision comparison rendered with limits on row identity')
  await go(`/datasets/${qa.dataset_id}/compare?a=${qa.january_runs[0].run_id}&b=${qa.february_run.run_id}`,'Kết quả đối chiếu')
  assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Hai đợt khác nhau') && document.querySelector('main').innerText.includes('Không áp dụng')`));await screenshot('cross-batch-comparison')
  checks.push('Cross-batch comparison rejects improvement delta')
  await go(`/datasets/${qa.dataset_id}/runs/${qa.february_run.run_id}`,'Kết quả thuộc cấu hình trước')
  await screenshot('stale-revision');checks.push('Changing February rules marks saved result stale')
  await go(`/datasets/${qa.dataset_id}/batches/${qa.january_batch_id}`,'Quy tắc riêng của đợt');await click('Kiểm tra');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Quy tắc revision')`)
  await screenshot('run-review');await click('Hủy');checks.push('Run review shows batch/version/revision without executing')
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await screenshot('mobile-batch')
  assert.equal(errors.length,0,errors.join('\n'))
  fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,consoleErrors:errors,qaDataset:qa.dataset_id},null,2));console.log(JSON.stringify({passed:checks.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser test closed'))}socket?.close();browser.kill();await once(browser,'exit').catch(()=>{});try{fs.rmSync(profile,{recursive:true,force:true})}catch{}}
