// Read-only existing QA checks, called by verify-bug04-followup-local.py.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'

let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa}=JSON.parse(input);input=''
assert.equal(origin,'http://127.0.0.1:5173','Read-only local QA verification')
const out=path.resolve('test-artifacts/bug04-followup-local');fs.mkdirSync(out,{recursive:true})

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





 await send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{const original=window.fetch;window.fetch=function(input,init){if(!['GET','HEAD'].includes((init?.method??input?.method??'GET').toUpperCase()))throw Error('Read-only QA');return original.call(this,input,init)}})()`})
 let delayRead=false,heldReads=[]
 socket.addEventListener('message',async event=>{
  const m=JSON.parse(String(event.data))
  if(m.method==='Fetch.requestPaused')try{
   const url=new URL(m.params.request.url)
   if(delayRead&&m.params.request.method==='GET'&&url.searchParams.get('page_size')==='100'){heldReads.push(m.params);return}
   await send('Fetch.continueRequest',{requestId:m.params.requestId})
  }catch(error){if(!error.message.includes('Invalid InterceptionId'))errors.push(String(error))}
 })
 await send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/datasets/55/rules*',requestStage:'Request'}]})
 await send('Page.navigate',{url:origin+'/#/datasets/55/compare?a=66&b=67'});await waitFor(`document.querySelector('main')?.innerText.includes('Kết quả đối chiếu')&&!document.querySelector('.loading-state')`)
 const warning=await evaluate(`[...document.querySelectorAll('.notice-warning')].find(n=>n.innerText.includes('Hai lần kiểm tra không cùng điều kiện.')).innerText`);assert.equal(warning.match(/Bộ quy tắc đã thay đổi\./g)?.length,1)
 assert.equal(await evaluate(`[...document.querySelectorAll('main tbody tr')].filter(tr=>tr.lastElementChild?.textContent==='Không áp dụng').length`),5);await evaluate(`[...document.querySelectorAll('.notice-warning')].find(n=>n.innerText.includes('Hai lần kiểm tra không cùng điều kiện.')).scrollIntoView({block:'center'})`);await screenshot('qa55-comparison-one-rule-reason')
 checks.push('Exact local QA URL 55/compare?a=66&b=67 renders one rules-changed sentence and all five deltas remain Not applicable')
 await go('/datasets/55/rules','Quy tắc mẫu của bộ dữ liệu');await waitFor(`document.querySelector('main tbody tr button')&&!document.querySelector('.loading-state')`)
 const target=await evaluate(`fetch('/api/datasets/55/rules?page_size=100').then(r=>r.json()).then(b=>({id:b.items[0].id,name:b.items[0].name}))`)
 delayRead=true;await evaluate(`[...document.querySelectorAll('main button')].find(b=>b.getAttribute('aria-label')===${JSON.stringify('Sửa quy tắc ')}+${JSON.stringify(target.name)}).click()`);await waitFor(`document.querySelector('dialog[open] .loading-state')`)
 assert.ok(await evaluate(`document.querySelector('dialog[open] h2').textContent==='Chỉnh sửa quy tắc'&&!document.querySelector('dialog[open] form')&&[...document.querySelectorAll('dialog[open] button')].find(b=>b.textContent.trim()==='Lưu quy tắc').disabled`));await screenshot('qa55-edit-loading-locked')
 assert.ok(heldReads.length);delayRead=false;for(const held of heldReads.splice(0)){try{await send('Fetch.continueRequest',{requestId:held.requestId})}catch(error){assert.ok(error.message.includes('Invalid InterceptionId'))}}await waitFor(`document.querySelector('form[data-rule-mode="edit"][data-rule-id="${target.id}"]')`)
 assert.equal(await evaluate(`document.querySelector('[data-rule-field="name"]').value`),target.name);await screenshot('qa55-edit-correct-prefill');await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);await waitFor(`!document.querySelector('dialog[open]')`)
 checks.push('Local template Edit remains loading/locked while scoped read is delayed, then opens edit mode with matching ID/name; closed without saving')
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,existingQAReadOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('bug04-followup-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
