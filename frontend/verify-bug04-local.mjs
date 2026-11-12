// Read-only existing QA checks, called by verify-bug04-local.py.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'

let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa}=JSON.parse(input);input=''
assert.equal(origin,'http://127.0.0.1:5173','Read-only local QA verification')
const out=path.resolve('test-artifacts/bug04-local');fs.mkdirSync(out,{recursive:true})

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




 await send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{const original=window.fetch;window.fetch=function(input,init){const method=(init?.method??input?.method??'GET').toUpperCase();if(!['GET','HEAD'].includes(method))throw Error('Read-only QA: blocked '+method);return original.call(this,input,init)}})()`})
 const dialogs=[];let acceptDialog=false
 socket.addEventListener('message',event=>{const m=JSON.parse(String(event.data));if(m.method==='Page.javascriptDialogOpening'){dialogs.push(m.params.message);void send('Page.handleJavaScriptDialog',{accept:acceptDialog})}})
 await send('Page.navigate',{url:origin+'/#/dashboard'});await waitFor(`document.querySelector('main h1') && !document.querySelector('.loading-state')`)
 await click('Tạo bộ dữ liệu');await field('Tên bộ dữ liệu','BUG-04 Bản nháp local không lưu','document.querySelector("dialog[open]")');const hash=await evaluate('location.hash')
 await evaluate(`location.hash='/datasets'`);await pause(200);assert.equal(await evaluate('location.hash'),hash);assert.ok(await evaluate(`document.querySelector('dialog[open] input').value==='BUG-04 Bản nháp local không lưu'`));await screenshot('local-dataset-unsaved-cancel')
 await click('Hủy','document.querySelector("dialog[open]")');assert.ok(await evaluate(`Boolean(document.querySelector('dialog[open]'))`));acceptDialog=true;await click('Hủy','document.querySelector("dialog[open]")');await waitFor(`!document.querySelector('dialog[open]')`);assert.equal(await evaluate(`window.dispatchEvent(new Event('beforeunload',{cancelable:true}))`),true)
 checks.push('Running local Dashboard dataset form protects unsaved draft and Cancel keeps content; confirmed discard releases only the form guard')
 await go(`/datasets/${qa.dataset}/batches/${qa.batch}?rules=1`,'Quy tắc của đợt');await waitFor(`document.querySelector('#batch-rules[open]') && !document.querySelector('.loading-state')`)
 await click('Thêm quy tắc');await field('Tên quy tắc','BUG-04 Bản nháp regex không lưu','document.querySelector("dialog[open]")');await field('Loại kiểm tra','pattern','document.querySelector("dialog[open]")');await field('Mẫu định dạng','[','document.querySelector("dialog[open]")');await screenshot('local-rule-draft')
 acceptDialog=false;await click('Hủy','document.querySelector("dialog[open]")');assert.equal(await evaluate(`document.querySelector('[data-rule-field="pattern"]').value`),'[');acceptDialog=true;await click('Hủy','document.querySelector("dialog[open]")');await waitFor(`!document.querySelector('dialog[open]')`)
 checks.push('QA dataset 55/batch 31 rule editor renders new code and preserves regex draft when discard confirmation is canceled; no rule POST is sent')
 for(const [run,expected,max] of [[66,[12,6,9],'10'],[67,[12,6,8],'20']]){
  await go(`/datasets/${qa.dataset}/runs/${run}`,'Kết quả kiểm tra');await waitFor(`document.querySelector('.result-stat') && !document.querySelector('.loading-state')`)
  const body=await evaluate(`fetch('/api/datasets/${qa.dataset}/runs/${run}').then(r=>r.json())`);assert.deepEqual([body.total_rows,body.error_row_count,body.violation_count],expected);assert.ok(body.rule_snapshot.some(r=>r.rule_type==='numeric_range'&&r.config.min==='0'&&r.config.max===max));await screenshot(`local-run-${run}`)
 }
 checks.push('Existing run 66 retains 12/6/9 with range 0–10; run 67 retains 12/6/8 with range 0–20 on live local API/UI')
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,dialogs,existingQAReadOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('bug04-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
