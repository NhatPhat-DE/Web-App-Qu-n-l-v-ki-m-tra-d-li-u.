// Real browser + API checks. Called only by verify-nv02.py against a disposable DB.
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
const out=path.resolve('test-artifacts/nv02');fs.mkdirSync(out,{recursive:true})
const vite=await createServer({server:{host:'127.0.0.1',port:Number(new URL(origin).port),strictPort:true,proxy:{'/api':backendOrigin}}});await vite.listen()
const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'nv02-browser-'))
const browser=spawn(browserPath,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'})
const pause=ms=>new Promise(r=>setTimeout(r,ms)),pending=new Map(),errors=[],checks=[],layouts=[],writes=[]
let socket,sessionId,seq=0
function send(method,params={},session=sessionId){return new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout ${method}`))},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(session?{sessionId:session}:{})}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);return r.result.value}
async function waitFor(expression){for(let i=0;i<250;i++){if(await evaluate(`Boolean(${expression})`))return;await pause(100)}throw Error(`UI timeout ${expression}; ${(await evaluate('document.body.innerText')).slice(-2500)}`)}
async function go(hash,text){await evaluate(`location.hash=${JSON.stringify(hash)}`);await waitFor(`document.querySelector('main')?.innerText.includes(${JSON.stringify(text)}) && !document.querySelector('.loading-state')`);await pause(180)}
async function click(text,scope='document'){await waitFor(`(()=>{const scope=${scope};if(!scope)return false;const e=[...scope.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(text)}&&!e.disabled);if(!e)return false;e.click();return true})()`);await pause(120)}
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
 const ds=qa.dataset,batch=qa.batch,base=`/api/datasets/${ds}/batches/${batch}/workflow`
 const api=async suffix=>evaluate(`fetch(${JSON.stringify(base+suffix)}).then(r=>r.json())`)
 const closeDialog=async()=>{await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);await waitFor(`!document.querySelector('dialog[open]')`)}
 const confirm=async title=>{await waitFor(`document.querySelector('dialog[open]')`);await evaluate(`document.querySelector('dialog[open] input[type=checkbox]').click()`);await click(title,'document.querySelector("dialog[open]")');await waitFor(`!document.querySelector('dialog[open]')&&!document.querySelector('.loading-state')`)}
 const issueCounts=async expected=>{for(let i=0;i<80;i++){const s=await api('');if(Object.entries(expected).every(([key,value])=>s.counts[key]===value))return s;await pause(100)}assert.fail('Issue counts do not match '+JSON.stringify(expected))}
 const openIssue=async id=>{await click(`Chi tiết / xử lý #${id}`,'document.querySelector("#batch-workflow")');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Lịch sử xử lý')`)}
 const changeIssue=async(id,status)=>{await openIssue(id);await field('Trạng thái xử lý mới',status,'document.querySelector("dialog[open]")');await field('Ghi chú xử lý','NV-02 browser: gửi bản sửa để kiểm tra lại','document.querySelector("dialog[open]")');await click('Lưu trạng thái xử lý','document.querySelector("dialog[open]")');await waitFor(`!document.querySelector('dialog[open]')&&!document.querySelector('.loading-state')`)}
 const runDialog=async()=>{await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Chạy kiểm tra dữ liệu')`);await waitFor(`[...document.querySelectorAll('dialog[open] button')].some(b=>b.textContent.trim()==='Bắt đầu kiểm tra'&&!b.disabled)`);await click('Bắt đầu kiểm tra','document.querySelector("dialog[open]")');await waitFor(`location.hash.includes('/runs/')&&!document.querySelector('dialog[open]')&&document.querySelector('main')?.innerText.includes('Kết quả kiểm tra')&&!document.querySelector('.loading-state')`);await pause(250)}
 const uploadAndRun=async filename=>{
  await click('Tải lên bản đã sửa');await waitFor(`document.querySelector('dialog[open] input[type=file]')`)
  const root=(await send('DOM.getDocument')).root.nodeId
  const file=(await send('DOM.querySelector',{nodeId:root,selector:'dialog[open] input[type=file]'})).nodeId
  await send('DOM.setFileInputFiles',{nodeId:file,files:[path.join(out,filename)]})
  await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Xem trước dữ liệu')`)
  await click('Xác nhận lưu phiên bản','document.querySelector("dialog[open]")');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Đã lưu phiên bản')`)
  await click('Chạy kiểm tra','document.querySelector("dialog[open]")');await runDialog()
 }
 const dialogs=[];socket.addEventListener('message',async event=>{const m=JSON.parse(String(event.data));if(m.method==='Page.javascriptDialogOpening'){dialogs.push(m.params.message);await send('Page.handleJavaScriptDialog',{accept:false})}})
 await send('Page.navigate',{url:origin+`/#/datasets/${ds}/overview`});await waitFor(`document.querySelector('#record-identity')?.innerText.includes('Chưa cấu hình')&&!document.querySelector('.loading-state')`)
 await click('Cấu hình khóa nhận diện');await waitFor(`document.querySelector('dialog[open] fieldset')`)
 for(const col of ['id','part'])await evaluate(`(()=>{const e=[...document.querySelectorAll('dialog[open] fieldset label')].find(l=>l.textContent===${JSON.stringify(col)});e.querySelector('input').click()})()`)
 await click('Lưu khóa nhận diện','document.querySelector("dialog[open]")');await waitFor(`!document.querySelector('dialog[open]')&&document.querySelector('#record-identity')?.innerText.includes('id + part')`)
 await go(`/datasets/${ds}/batches/${batch}`,'Xử lý lỗi');await click('Bật xử lý lỗi cho đợt');await confirm('Bật quản lý xử lý lỗi')
 assert.equal((await api('')).enabled,true);await click('Chạy kiểm tra bản hiện hành');await runDialog()
 const firstHash=await evaluate('location.hash');assert.deepEqual((await api('')).counts,{OPEN:3,IN_PROGRESS:0,PENDING_RECHECK:0,RESOLVED:0,IGNORED:0})
 await waitFor(`[...document.querySelectorAll('main button')].some(b=>b.textContent.includes('Issue #'))`)
 await evaluate(`[...document.querySelectorAll('main button')].find(b=>b.textContent.includes('Issue #')).click()`);await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Lịch sử xử lý')`);await screenshot('violation-to-issue');await closeDialog()
 await evaluate(`document.querySelector('button[aria-label="Xem bản ghi 1"]').click()`);await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Bản ghi 1')`)
 assert.equal(await evaluate(`[...document.querySelectorAll('dialog[open] button')].filter(b=>b.textContent.includes('Issue #')).length`),2)
 await evaluate(`[...document.querySelectorAll('dialog[open] button')].find(b=>b.textContent.includes('Issue #')).click()`);await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Lịch sử xử lý')`);assert.equal(await evaluate(`document.querySelectorAll('dialog[open]').length`),1);await closeDialog()
 checks.push('Composite identity saved in UI, workflow explicitly enabled; v1 has 3 issues; violation and record details link to the correct issues without stacked dialogs')
 await go(`/datasets/${ds}/batches/${batch}?issues=1`,'Xử lý lỗi');await waitFor(`document.querySelectorAll('#batch-workflow tbody tr').length===3`)
 const firstIssues=(await api('/issues')).items
 for(const i of firstIssues){await changeIssue(i.id,'IN_PROGRESS');await changeIssue(i.id,'PENDING_RECHECK')}
 await issueCounts({PENDING_RECHECK:3,OPEN:0});await screenshot('v1-pending-recheck')
 assert.equal((await api('')).completion.can_complete,false)
 checks.push('All v1 issues moved OPEN → IN_PROGRESS → PENDING_RECHECK with notes/history; completion remains blocked')
 await go(firstHash,'Kết quả kiểm tra');await uploadAndRun('v2.csv')
 const secondHash=await evaluate('location.hash'),v2=await issueCounts({OPEN:2,RESOLVED:2,PENDING_RECHECK:0})
 assert.deepEqual(v2.reconciliations[0].counts,{NEW:1,PERSISTING:1,RESOLVED:2,UNKNOWN:0})
 await go(`/datasets/${ds}/batches/${batch}?issues=1`,'Xử lý lỗi');await waitFor(`document.querySelectorAll('#batch-workflow tbody tr').length===4`)
 await evaluate(`document.querySelector('#batch-workflow details').open=true`);await screenshot('v2-reordered-reconciliation')
 checks.push('Uploaded v2 through results: reordered records still reconcile by composite key; 2 resolved, 1 persisting, 1 newly open')
 await go(secondHash,'Kết quả kiểm tra');await uploadAndRun('v3.csv');await issueCounts({RESOLVED:4,OPEN:0,IN_PROGRESS:0,PENDING_RECHECK:0,IGNORED:0})
 await go(`/datasets/${ds}/batches/${batch}?issues=1`,'Xử lý lỗi');await waitFor(`[...document.querySelectorAll('#batch-workflow button')].some(b=>b.textContent.trim()==='Xác nhận hoàn tất đợt'&&!b.disabled)`)
 await click('Xác nhận hoàn tất đợt','document.querySelector("#batch-workflow")');await confirm('Xác nhận hoàn tất đợt');assert.equal((await api('')).business_state,'COMPLETED')
 assert.ok(await evaluate(`[...document.querySelectorAll('main button')].filter(b=>b.textContent.includes('Tải bản đã sửa')||b.textContent==='Chỉnh sửa đợt').every(b=>b.disabled)`))
 await evaluate(`document.querySelector('#batch-workflow').scrollIntoView()`);await screenshot('completed-batch')
 const blocked=await evaluate(`(async()=>{const auth=await fetch('/api/auth/me').then(r=>r.json());const form=new FormData();form.append('file',new File(['id,part,amount,name\\nA,X,2,Able\\n'],'blocked.csv'));const r=await fetch('/api/datasets/${ds}/batches/${batch}/versions/import',{method:'POST',headers:{'X-CSRF-Token':auth.csrf_token},body:form});return {status:r.status,body:await r.json()}})()`)
 assert.equal(blocked.status,409,JSON.stringify(blocked))
 checks.push('Clean v3 resolves all 4 issues; explicit confirmation completes batch; closed upload UI is locked and direct upload API returns 409')
 await send('Page.reload');await waitFor(`document.querySelector('#batch-workflow')?.innerText.includes('Đã hoàn tất')&&!document.querySelector('.loading-state')`)
 for(const width of [1366,1024,768]){await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await screenshot('completed-width-'+width)}
 await send('Emulation.setDeviceMetricsOverride',{width:1366,height:900,deviceScaleFactor:1,mobile:false})
 await click('Mở lại đợt','document.querySelector("#batch-workflow")');await waitFor(`document.querySelector('dialog[open] textarea[required]')`)
 await field('Lý do mở lại','QA NV-02: tiếp nhận kỳ hiệu chỉnh tiếp theo','document.querySelector("dialog[open]")');await confirm('Mở lại đợt');assert.equal((await api('')).business_state,'PROCESSING')
 assert.equal((await api('')).events[0].note,'QA NV-02: tiếp nhận kỳ hiệu chỉnh tiếp theo')
 await waitFor(`[...document.querySelectorAll('#batch-workflow summary')].some(s=>s.textContent==='Lịch sử nghiệp vụ của đợt')`)
 await evaluate(`[...document.querySelectorAll('#batch-workflow summary')].find(s=>s.textContent==='Lịch sử nghiệp vụ của đợt').parentElement.open=true`)
 await screenshot('reopened-with-history')
 assert.equal(dialogs.length,0,'Successful saves must not trigger dirty guard');assert.equal(errors.length,0,errors.join('\n'))
 checks.push('Reload retains completed context; 1366/1024/768px have no page overflow; reopen requires a reason and records history; successful forms trigger no unsaved warning')
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,dialogs,disposableDatabaseOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))

}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);await vite.close();try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('nv02-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
