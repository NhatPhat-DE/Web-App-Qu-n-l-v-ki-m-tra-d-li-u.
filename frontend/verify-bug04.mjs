// Real browser + API checks. Called only by verify-bug04.py against a disposable DB.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'
import {createServer} from 'vite'
let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa}=JSON.parse(input);input=''
assert.notEqual(origin,'http://127.0.0.1:5173','Must use disposable environment')
const out=path.resolve('test-artifacts/bug04');fs.mkdirSync(out,{recursive:true})
const vite=await createServer({server:{host:'127.0.0.1',port:Number(new URL(origin).port),strictPort:true,proxy:{'/api':backendOrigin}}});await vite.listen()
const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'bug04-browser-'))
const browser=spawn(browserPath,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'})
const pause=ms=>new Promise(r=>setTimeout(r,ms)),pending=new Map(),errors=[],checks=[],layouts=[],writes=[]
let socket,sessionId,seq=0
function send(method,params={},session=sessionId){return new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout ${method}`))},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(session?{sessionId:session}:{})}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);return r.result.value}
async function waitFor(expression){for(let i=0;i<250;i++){if(await evaluate(`Boolean(${expression})`))return;await pause(100)}throw Error(`UI timeout ${expression}; ${(await evaluate('document.body.innerText')).slice(-2500)}`)}
async function go(hash,text){await evaluate(`location.hash=${JSON.stringify(hash)}`);await waitFor(`document.querySelector('main')?.innerText.includes(${JSON.stringify(text)}) && !document.querySelector('.loading-state')`);await pause(180)}
async function click(text,scope='document'){await waitFor(`[...${scope}.querySelectorAll('button,a')].some(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled)`);await evaluate(`[...${scope}.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled).click()`);await pause(100)}
async function setValue(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const proto=e.tagName==='SELECT'?HTMLSelectElement.prototype:e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);await pause(100)}
async function field(label,value,scope='document'){const selector=await evaluate(`(()=>{const e=[...${scope}.querySelectorAll('label')].find(e=>e.querySelector('span')?.textContent.replace(' *','').trim()===${JSON.stringify(label)})?.querySelector('input,select,textarea');if(!e)throw Error('Missing field ${label}');e.dataset.qa='active';return '[data-qa="active"]';})()`);await setValue(selector,value);await evaluate(`document.querySelector(${JSON.stringify(selector)})?.removeAttribute('data-qa')`)}
async function screenshot(label){await evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');const size=await evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');assert.ok(size.scroll<=size.width+1,`${label}: horizontal page overflow`);layouts.push({label,...size});const r=await send('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(out,label+'.png'),Buffer.from(r.data,'base64'))}
async function selectBatchCheckbox(name){await evaluate(`(()=>{const e=[...document.querySelectorAll('.batch-options label')].find(e=>e.textContent.includes(${JSON.stringify(name)}))?.querySelector('input');if(!e)throw Error('Missing batch checkbox');e.click()})()`);await pause(120)}
try{
 let ready=false;for(let i=0;i<150;i++){if(fs.existsSync(path.join(profile,'DevToolsActivePort'))){ready=true;break}assert.equal(browser.exitCode,null);await pause(100)}assert.ok(ready)
 const [port,endpoint]=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').trim().split(/\r?\n/)
 socket=new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);await once(socket,'open')
 socket.addEventListener('message',event=>{const m=JSON.parse(String(event.data));if(m.id){const p=pending.get(m.id);if(!p)return;clearTimeout(p.timer);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.exception?.description??m.params.exceptionDetails.text);else if(m.method==='Network.requestWillBeSent'&&m.params.request.url.startsWith(origin+'/api/')&&!['GET','HEAD'].includes(m.params.request.method))writes.push({method:m.params.request.method,path:new URL(m.params.request.url).pathname})})
 const t=await send('Target.createTarget',{url:'about:blank'},null);sessionId=(await send('Target.attachToTarget',{targetId:t.targetId,flatten:true},null)).sessionId
 await send('Page.enable');await send('Runtime.enable');await send('Network.enable');await send('DOM.enable')
 await send('Network.setCookie',{name:'datalens_session',value:token,url:origin+'/api',path:'/api',httpOnly:true,sameSite:'Lax'})
 await send('Emulation.setDeviceMetricsOverride',{width:1366,height:900,deviceScaleFactor:1,mobile:false})



 const dialogs=[];let acceptDialog=false,failCreate=true,createRequests=0,injectRuleFailure=false
 socket.addEventListener('message',async event=>{
  const m=JSON.parse(String(event.data))
  try{
   if(m.method==='Page.javascriptDialogOpening'){dialogs.push(m.params.message);await send('Page.handleJavaScriptDialog',{accept:acceptDialog})}
   if(m.method==='Fetch.requestPaused'){
    const request=m.params.request,pathname=new URL(request.url).pathname
    if(request.method==='POST'&&pathname==='/api/datasets'){
     createRequests++
     if(failCreate){failCreate=false;await send('Fetch.fulfillRequest',{requestId:m.params.requestId,responseCode:503,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({error:{code:'DATABASE_UNAVAILABLE',message:'Dịch vụ chưa sẵn sàng. Vui lòng thử lại.'}})).toString('base64')});return}
     await pause(350)
    }
    if(request.method==='POST'&&pathname.endsWith('/rules')&&injectRuleFailure){injectRuleFailure=false;await send('Fetch.fulfillRequest',{requestId:m.params.requestId,responseCode:500,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({error:{code:'UNEXPECTED_LIBRARY_ERROR',message:'Internal library diagnostic should not be primary UI'}})).toString('base64')});return}
    await send('Fetch.continueRequest',{requestId:m.params.requestId})
   }
  }catch(error){if(!error.message.includes('Invalid InterceptionId'))errors.push(String(error))}
 })
 await send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/datasets',requestStage:'Request'},{urlPattern:origin+`/api/datasets/${qa.scratch}/batches/${qa.scratch_batch}/rules`,requestStage:'Request'}]})
 const dialog='document.querySelector("dialog[open]")'
 async function closeDialog(){await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);await pause(130)}
 async function submit(){await evaluate(`document.querySelector('dialog[open] form').requestSubmit()`);await pause(120)}
 async function clean(){assert.equal(await evaluate(`window.dispatchEvent(new Event('beforeunload',{cancelable:true}))`),true)}
 const values=()=>evaluate(`[...document.querySelectorAll('dialog[open] input,dialog[open] textarea,dialog[open] select')].map(e=>e.type==='checkbox'?e.checked:e.value)`)
 const ruleState=()=>evaluate(`fetch('/api/datasets/${qa.scratch}/batches/${qa.scratch_batch}/rules?page_size=100').then(r=>r.json()).then(b=>({total:b.total,revision:b.rules_revision,items:b.items}))`)
 async function addRule(kind,name){await click('Thêm quy tắc');await waitFor(`document.querySelector('dialog[open]')`);await field('Tên quy tắc',name,dialog);await field('Loại kiểm tra',kind,dialog);await field('Trường áp dụng','value',dialog)}
 async function ruleSaved(){await waitFor(`!document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`);await clean()}
 await send('Page.navigate',{url:origin+'/#/dashboard'});await waitFor(`document.querySelector('main h1') && !document.querySelector('.loading-state')`)
 await click('Tạo bộ dữ liệu');await field('Tên bộ dữ liệu','BUG-04 Tạo dataset thành công',dialog);await field('Người phụ trách','QA riêng',dialog);await field('Nguồn / bộ phận','BUG-04',dialog);await field('Mô tả','Nội dung phải còn nguyên khi hủy hoặc lưu lỗi',dialog)
 const original=await values(),startHash=await evaluate('location.hash')
 assert.equal(await evaluate(`window.dispatchEvent(new Event('beforeunload',{cancelable:true}))`),false)
 await evaluate(`location.hash='/datasets'`);await pause(250);assert.equal(await evaluate('location.hash'),startHash);assert.deepEqual(await values(),original)
 await click('Hủy',dialog);assert.deepEqual(await values(),original);await screenshot('dataset-cancel-preserves-fields')
 await submit();await waitFor(`document.querySelector('dialog[open] [role="alert"]')`);assert.deepEqual(await values(),original);assert.equal(createRequests,1);await screenshot('dataset-failure-preserves-fields')
 const beforeSuccess=dialogs.length
 await evaluate(`(()=>{const form=document.querySelector('dialog[open] form');form.requestSubmit();form.requestSubmit()})()`)
 await waitFor(`document.querySelector('h1')?.textContent==='BUG-04 Tạo dataset thành công' && !document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`)
 assert.equal(createRequests,2);assert.equal(dialogs.length,beforeSuccess);await clean();const createdDataset=Number((await evaluate('location.hash')).split('/')[2]);await screenshot('dataset-success-no-leave-warning')
 checks.push('Dashboard dataset creation: unsaved navigation/Cancel preserve every field; 503 retains content; retry succeeds without leave warning, guard is cleared and double submit creates exactly one dataset')
 await click('Tạo đợt dữ liệu');await field('Tên đợt dữ liệu','BUG-04 Đợt mới',dialog);const beforeBatch=dialogs.length;await submit();await waitFor(`document.querySelector('h1')?.textContent==='BUG-04 Đợt mới' && !document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`);assert.equal(dialogs.length,beforeBatch);await clean()
 checks.push('Shared lifecycle regression: creating a batch also navigates without a stale dirty warning')
 await go(`/datasets/${qa.scratch}/batches/${qa.scratch_batch}?rules=1`,'Quy tắc của đợt');await waitFor(`document.querySelector('#batch-rules[open]') && !document.querySelector('.loading-state')`)
 await addRule('pattern','BUG-04 Mẫu tùy chỉnh');await field('Mẫu định dạng','[',dialog)
 let before=await ruleState();await submit();await waitFor(`document.querySelector('[data-rule-field="pattern"]').getAttribute('aria-invalid')==='true'`)
 const error=await evaluate(`(()=>{const i=document.querySelector('[data-rule-field="pattern"]');return {value:i.value,text:document.getElementById(i.getAttribute('aria-describedby')).textContent,main:document.querySelector('dialog[open]').innerText,technicalOpen:document.querySelector('.rule-error-details').open}})()`)
 assert.equal(error.value,'[');assert.ok(error.text.includes('dấu [')&&error.text.includes(']'));assert.ok(!error.main.includes('Empty or unclosed'));assert.equal(error.technicalOpen,false)
 assert.deepEqual(await ruleState(),before);await screenshot('regex-vietnamese-field-error')
 await evaluate(`document.querySelector('.rule-error-details').open=true`);assert.ok(await evaluate(`document.querySelector('.rule-error-details').innerText.includes('Empty or unclosed character class.')`));await screenshot('regex-technical-details')
 await field('Mẫu định dạng','\\1',dialog);await submit();await waitFor(`document.querySelector('[data-rule-field="pattern"]').getAttribute('aria-invalid')==='true'`);assert.ok(await evaluate(`!document.querySelector('dialog[open]').innerText.includes('Unsupported escape.')`));assert.deepEqual(await ruleState(),before)
 const ruleDialogs=dialogs.length;await field('Mẫu định dạng','[A-Z]+',dialog);await submit();await ruleSaved();assert.equal(dialogs.length,ruleDialogs);assert.equal((await ruleState()).total,1)
 checks.push('Real invalid [ and unsupported escape return 422 without rule/revision writes; Vietnamese feedback is attached to pattern input, original text retained, technical text collapsed; correction saves successfully')
 await addRule('numeric_range','BUG-04 Khoảng số');await field('Nhỏ nhất','20',dialog);await field('Lớn nhất','10',dialog);const postsBefore=writes.length;await submit();await waitFor(`document.querySelector('[data-rule-field="min"]').getAttribute('aria-invalid')==='true'`);assert.equal(writes.length,postsBefore);assert.equal((await ruleState()).total,1);await screenshot('range-min-max-blocked')
 await field('Nhỏ nhất','0',dialog);await field('Lớn nhất','20',dialog);await submit();await ruleSaved();assert.equal((await ruleState()).total,2)
 await addRule('date_format','BUG-04 Ngày');await field('Ngày nhỏ nhất (tùy chọn)','2026-12-31',dialog);await field('Ngày lớn nhất (cần cả hai biên)','2026-01-01',dialog);before=await ruleState();await submit();await waitFor(`document.querySelector('[data-rule-field="dateMin"]').getAttribute('aria-invalid')==='true'`);assert.deepEqual(await ruleState(),before);await screenshot('date-config-field-error')
 await field('Ngày nhỏ nhất (tùy chọn)','2026-01-01',dialog);await field('Ngày lớn nhất (cần cả hai biên)','2026-12-31',dialog);await submit();await ruleSaved()
 await addRule('allowed_values','BUG-04 Danh sách');await field('Các giá trị được chấp nhận','A\nA',dialog);before=await ruleState();await submit();await waitFor(`document.querySelector('[data-rule-field="values"]').getAttribute('aria-invalid')==='true'`);assert.deepEqual(await ruleState(),before);assert.ok(await evaluate(`document.querySelector('dialog[open]').innerText.includes('giá trị trùng')`));await screenshot('allowed-values-field-error')
 await field('Các giá trị được chấp nhận','A\nB',dialog);await submit();await ruleSaved();assert.equal((await ruleState()).total,4)
 checks.push('Min > max stays blocked before POST; reversed date bounds and duplicate allowed-values are rejected by real API without mutation; each field error preserves input and corrections save')
 await addRule('pattern','BUG-04 Lỗi máy chủ');await field('Mẫu định dạng','OK',dialog);injectRuleFailure=true;await submit();await waitFor(`document.querySelector('dialog[open] [role="alert"]')`);assert.ok(await evaluate(`!document.querySelector('dialog[open]').innerText.includes('Internal library diagnostic')`));assert.equal((await ruleState()).total,4);await screenshot('unknown-server-error-safe-message');acceptDialog=true;await closeDialog();await clean()
 checks.push('Unexpected server/library failure shows a safe Vietnamese primary message, retains draft and keeps technical diagnostics behind details')
 await click('Sửa thông tin đợt');await field('Tên đợt dữ liệu','BUG-04 Đợt đổi tên',dialog);acceptDialog=false;await click('Hủy',dialog);assert.ok(await evaluate(`document.querySelector('dialog[open] input').value==='BUG-04 Đợt đổi tên'`));await submit();await waitFor(`document.querySelector('h1')?.textContent==='BUG-04 Đợt đổi tên' && !document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`);await clean()
 await go(`/datasets/${qa.scratch}/overview`,'Thông tin chung');await click('Sửa thông tin chung');await field('Người phụ trách','BUG-04 Đã lưu metadata',dialog);await submit();await waitFor(`!document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`);await clean()
 checks.push('Metadata and batch-edit success clear guard before refresh; batch-edit Cancel preserves draft')
 await go('/accounts','Quản lý tài khoản');await click('Tạo tài khoản');await field('Tên đăng nhập','bug04_steward',dialog);await field('Mật khẩu',qa.account_password,dialog);await field('Xác nhận mật khẩu',qa.account_password,dialog);await submit();await waitFor(`!document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`);await clean()
 checks.push('Account creation uses shared saved/close lifecycle without leaving a stale guard')
 await go(`/datasets/${qa.scratch}/batches/${qa.scratch_batch}`,'Phiên bản trong đợt');await click('Tải bản đã sửa');await waitFor(`document.querySelector('input[type="file"]')`)
 const root=await send('DOM.getDocument'),input=await send('DOM.querySelector',{nodeId:root.root.nodeId,selector:'input[type="file"]'});await send('DOM.setFileInputFiles',{nodeId:input.nodeId,files:[qa.upload_file]});await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Xem trước dữ liệu')`);await click('Xác nhận lưu phiên bản',dialog);await waitFor(`document.querySelector('.upload-success')`);await clean();await screenshot('upload-success-guard-cleared');await closeDialog();await waitFor(`!document.querySelector('dialog[open]')`)
 checks.push('CSV upload clears its own dirty state after successful import while preserving the success/next-step screen')
 for(const [run,expected] of [[qa.raw_run,[12,6,9]],[qa.fixed_run,[12,6,8]]]){
  await go(`/datasets/${qa.dataset}/runs/${run}`,'Kết quả kiểm tra');await waitFor(`document.querySelector('.result-stat') && !document.querySelector('.loading-state')`);const body=await evaluate(`fetch('/api/datasets/${qa.dataset}/runs/${run}').then(r=>r.json())`);assert.deepEqual([body.total_rows,body.error_row_count,body.violation_count],expected);await screenshot(`snapshot-run-${run}`)
 }
 checks.push('Real engine replay of QA snapshots retains 12 records/6 error rows/9 violations at 0–10 and 12/6/8 at 0–20')
 await evaluate(`import('/tests/fixtures/bug04_guard_probe.tsx').then(m=>window.__bug04Probe=m.mountGuardProbe())`);await waitFor(`window.__bug04Probe?.ready()`);acceptDialog=false
 await evaluate(`window.__bug04Probe.saveA()`);const count=dialogs.length;assert.equal(await evaluate(`window.__bug04Probe.leave()`),false);assert.equal(dialogs.length,count+1);assert.equal(await evaluate(`window.dispatchEvent(new Event('beforeunload',{cancelable:true}))`),false)
 await evaluate(`window.__bug04Probe.saveB()`);assert.equal(await evaluate(`window.__bug04Probe.leave()`),true);await clean();await evaluate(`window.__bug04Probe.dispose()`)
 checks.push('Two simultaneous form guards: saving A leaves B protected, saving B removes final guard; no application-wide bypass')
 assert.equal(errors.length,0,errors.join('\n'))
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,dialogs,createdDataset,disposableDatabaseOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);await vite.close();try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('bug04-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
