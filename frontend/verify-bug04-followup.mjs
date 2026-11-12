// Real browser + API checks. Called only by verify-bug04-followup.py against a disposable DB.
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
const out=path.resolve('test-artifacts/bug04-followup');fs.mkdirSync(out,{recursive:true})
const vite=await createServer({server:{host:'127.0.0.1',port:Number(new URL(origin).port),strictPort:true,proxy:{'/api':backendOrigin}}});await vite.listen()
const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'bug04-followup-browser-'))
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




 let readMode='normal',heldReads=[];const dialogs=[]
 socket.addEventListener('message',async event=>{
  const m=JSON.parse(String(event.data))
  try{
   if(m.method==='Page.javascriptDialogOpening'){dialogs.push(m.params.message);await send('Page.handleJavaScriptDialog',{accept:true})}
   if(m.method==='Fetch.requestPaused'){
    const url=new URL(m.params.request.url)
    if(m.params.request.method==='GET'&&url.pathname===`/api/datasets/${qa.scratch}/rules`&&url.searchParams.get('page_size')==='100'){
     const action=readMode
     if(action==='delay'){heldReads.push(m.params);return}
     if(action==='fail'){await send('Fetch.fulfillRequest',{requestId:m.params.requestId,responseCode:503,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({error:{code:'DATABASE_UNAVAILABLE',message:'Service unavailable'}})).toString('base64')});return}
     if(action==='missing'){await send('Fetch.fulfillRequest',{requestId:m.params.requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({items:[],total:0,page:1,page_size:100})).toString('base64')});return}
    }
    await send('Fetch.continueRequest',{requestId:m.params.requestId})
   }
  }catch(error){if(!error.message.includes('Invalid InterceptionId'))errors.push(String(error))}
 })
 await send('Fetch.enable',{patterns:[{urlPattern:origin+`/api/datasets/${qa.scratch}/rules*`,requestStage:'Request'}]})
 async function closeDialog(){await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);await waitFor(`!document.querySelector('dialog[open]')`)}
 async function edit(name){await evaluate(`(()=>{const button=[...document.querySelectorAll('main button')].find(e=>e.getAttribute('aria-label')===${JSON.stringify('Sửa quy tắc '+name)});if(!button)throw Error('Edit row missing');button.click()})()`);await waitFor(`document.querySelector('dialog[open]')`)}
 async function loadedEdit(id){await waitFor(`document.querySelector('dialog[open] form[data-rule-mode="edit"][data-rule-id="${id}"]') && !document.querySelector('dialog[open] .loading-state')`)}
 async function blockedEdit(){assert.ok(await evaluate(`document.querySelector('dialog[open] h2').textContent==='Chỉnh sửa quy tắc'&&!document.querySelector('dialog[open] form')&&[...document.querySelectorAll('dialog[open] button')].find(b=>b.textContent.trim()==='Lưu quy tắc').disabled`))}
 const ruleWrites=()=>writes.filter(w=>w.path.startsWith(`/api/datasets/${qa.scratch}/rules`))
 await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset}/compare?a=${qa.raw_run}&b=${qa.fixed_run}`});await waitFor(`document.querySelector('main')?.innerText.includes('Kết quả đối chiếu')&&!document.querySelector('.loading-state')`)
 const warning=await evaluate(`[...document.querySelectorAll('.notice-warning')].find(n=>n.innerText.includes('Hai lần kiểm tra không cùng điều kiện.')).innerText`)
 assert.equal(warning.match(/Bộ quy tắc đã thay đổi\./g)?.length,1)
 assert.ok(await evaluate(`[...document.querySelectorAll('main tbody tr')].filter(tr=>tr.lastElementChild?.textContent==='Không áp dụng').length===5`))
 const comparison=await evaluate(`fetch('/api/datasets/${qa.dataset}/run-comparison?a_run_id=${qa.raw_run}&b_run_id=${qa.fixed_run}').then(r=>r.json())`)
 assert.ok(comparison.non_comparable_reasons.includes('RULE_REVISION_DIFFERENT')&&comparison.non_comparable_reasons.includes('RULE_SET_FINGERPRINT_DIFFERENT'));assert.equal(comparison.delta,null);await screenshot('comparison-reason-deduplicated')
 checks.push('Two distinct server rule-difference codes render one business sentence; all five deltas remain Not applicable and API delta remains null')
 await go(`/datasets/${qa.scratch}/rules`,'Quy tắc mẫu của bộ dữ liệu');await waitFor(`document.querySelectorAll('main tbody tr').length===2&&!document.querySelector('.loading-state')`)
 await click('Thêm quy tắc mẫu');await waitFor(`document.querySelector('form[data-rule-mode="create"]')`);assert.equal(await evaluate(`document.querySelector('dialog[open] input').value`),'');await field('Tên quy tắc','Bản nháp tạo mới không lưu','document.querySelector("dialog[open]")');await closeDialog()
 readMode='delay';await edit('Mẫu A — Định dạng');await waitFor(`document.querySelector('dialog[open] .loading-state')`);await blockedEdit();assert.equal(ruleWrites().length,0);await screenshot('edit-loading-save-disabled')
 assert.ok(heldReads.length);readMode='normal';for(const held of heldReads.splice(0)){try{await send('Fetch.continueRequest',{requestId:held.requestId})}catch(error){assert.ok(error.message.includes('Invalid InterceptionId'))}}await loadedEdit(qa.first)
 assert.equal(await evaluate(`document.querySelector('[data-rule-field="name"]').value`),'Mẫu A — Định dạng');assert.equal(await evaluate(`document.querySelector('[data-rule-field="pattern"]').value`),'[A-Z]+');await screenshot('edit-pattern-prefilled')
 await field('Tên quy tắc','Mẫu A — Đã sửa','document.querySelector("dialog[open]")');await evaluate(`document.querySelector('dialog[open] form').requestSubmit()`);await waitFor(`!document.querySelector('dialog[open]')&&!document.querySelector('.loading-state')`)
 assert.deepEqual(ruleWrites(),[{method:'PATCH',path:`/api/datasets/${qa.scratch}/rules/${qa.first}`}])
 checks.push('Create and edit are separate modes: after discarding a blank create draft, delayed edit has edit title/loading/disabled save and no form; fresh template values load and save PATCHes only the intended ID')
 readMode='fail';await edit('Mẫu A — Đã sửa');await waitFor(`document.querySelector('dialog[open] [role="alert"]')`);await blockedEdit();assert.equal(ruleWrites().length,1);await screenshot('edit-read-failure-blocks-save')
 readMode='normal';await click('Thử lại','document.querySelector("dialog[open]")');await loadedEdit(qa.first);assert.equal(await evaluate(`document.querySelector('[data-rule-field="name"]').value`),'Mẫu A — Đã sửa');await closeDialog()
 readMode='missing';await edit('Mẫu A — Đã sửa');await waitFor(`document.querySelector('dialog[open] [role="alert"]')`);await blockedEdit();assert.ok(await evaluate(`document.querySelector('dialog[open]').innerText.includes('không còn tồn tại')`));await screenshot('edit-missing-never-creates');await closeDialog()
 checks.push('Failed/missing edit reads remain edit dialogs with Save disabled and no create form/POST; retry loads the existing record correctly')
 readMode='delay';await edit('Mẫu A — Đã sửa');await waitFor(`document.querySelector('dialog[open] .loading-state')`);const oldReads=heldReads.splice(0);readMode='normal';await closeDialog();await edit('Mẫu B — Khoảng số');await loadedEdit(qa.second)
 for(const held of oldReads){try{await send('Fetch.continueRequest',{requestId:held.requestId})}catch(error){assert.ok(error.message.includes('Invalid InterceptionId'))}}
 await pause(200);assert.equal(await evaluate(`document.querySelector('[data-rule-field="name"]').value`),'Mẫu B — Khoảng số');assert.equal(await evaluate(`document.querySelector('[data-rule-field="min"]').value`),'5');assert.equal(await evaluate(`document.querySelector('[data-rule-field="max"]').value`),'9');assert.equal(await evaluate(`document.querySelector('dialog[open] .check-line input').checked`),false)
 await screenshot('second-rule-own-state');await field('Lớn nhất','12','document.querySelector("dialog[open]")');await evaluate(`document.querySelector('dialog[open] form').requestSubmit()`);await waitFor(`!document.querySelector('dialog[open]')&&!document.querySelector('.loading-state')`)
 assert.deepEqual(ruleWrites(),[{method:'PATCH',path:`/api/datasets/${qa.scratch}/rules/${qa.first}`},{method:'PATCH',path:`/api/datasets/${qa.scratch}/rules/${qa.second}`}]);await pause(150);assert.equal(await evaluate(`Boolean(document.querySelector('dialog[open]'))`),false)
 checks.push('Closing a pending edit then opening a different rule cannot receive stale state; second rule retains own range and active flag, PATCHes its ID, and late response cannot reopen a dialog')
 assert.equal(errors.length,0,errors.join('\n'))
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,dialogs,disposableDatabaseOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);await vite.close();try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('bug04-followup-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
