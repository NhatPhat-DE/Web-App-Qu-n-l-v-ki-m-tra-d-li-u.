// Real browser + API checks. Called only by verify-ux03-navigation.py against a disposable DB.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'

let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa}=JSON.parse(input);input=''
assert.equal(origin,'http://127.0.0.1:5173','Read-only local QA verification')
const out=path.resolve('test-artifacts/ux03-navigation-local');fs.mkdirSync(out,{recursive:true})

const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'ux03-navigation-browser-'))
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



 // Prevent writes before they reach the network in this read-only QA browser.
 await send('Page.addScriptToEvaluateOnNewDocument',{source:`(()=>{const fetchOriginal=window.fetch;window.fetch=function(input,init){const method=(init?.method??input?.method??'GET').toUpperCase();if(!['GET','HEAD'].includes(method))throw Error('Read-only QA: blocked '+method);return fetchOriginal.call(this,input,init)};const open=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(method,...args){if(!['GET','HEAD'].includes(method.toUpperCase()))throw Error('Read-only QA: blocked '+method);return open.call(this,method,...args)}})()`})
 const batchPath=`#/datasets/${qa.dataset}/batches/${qa.batch}`
 const historyPath=`#/datasets/${qa.dataset}/history?batch_id=${qa.batch}`
 async function loaded(){await waitFor(`(()=>{if(!document.querySelector('main h1')||document.querySelector('.loading-state'))return false;if(location.hash.includes('/runs/')){const c=document.querySelector('.result-context');return c&&!c.innerText.includes('Đang tải')}if(location.hash.includes('/history'))return Boolean(document.querySelector('main tbody tr'));if(location.hash.includes('/compare'))return Boolean(document.querySelector('.comparison-picks'));return Boolean(document.querySelector('.workspace-tab-groups')||document.querySelector('.batch-current'))})()`);await pause(100)}
 async function reload(){await evaluate('window.__ux03Reload=true');await send('Page.reload',{ignoreCache:true});await waitFor('!window.__ux03Reload');await loaded()}
 await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset}/overview`});await loaded()
 for(const width of [1280,1024,768]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await pause(100)
  assert.ok(await evaluate(`(()=>{const nav=document.querySelector('.workspace-tab-groups');return nav.scrollWidth<=nav.clientWidth+1&&[...nav.querySelectorAll('a')].length===8})()`))
  await screenshot(`qa52-tabs-${width}`)
 }
 checks.push('Real local dataset 52 renders all eight tabs without horizontal navigation scroll at 1280/1024/768')
 for(const [index,run] of qa.runs.entries()){
  await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset}/runs/${run}`});await loaded()
  assert.ok(await evaluate(`[...document.querySelectorAll('.breadcrumb a')].some(a=>a.getAttribute('href')===${JSON.stringify(batchPath)})`))
  const expected=index===2?'Bản hiện hành':'Bản lịch sử'
  assert.ok(await evaluate(`document.querySelector('.result-context').innerText.includes(${JSON.stringify(expected)})`));await reload()
  await screenshot(`qa52-run-${run}`)
  if(index<2){await click('Về đợt dữ liệu');await waitFor(`document.querySelector('.batch-current')?.innerText.includes('v${qa.current}')`);await evaluate('history.back()');await waitFor(`document.querySelector('.result-context')?.innerText.includes(${JSON.stringify(expected)})`)}
 }
 checks.push('Direct URLs and reload of real runs 59/60/61 retain batch 27; historical v1/v2 return to current version and Back restores result')
 await click('Lịch sử kiểm tra của đợt');await waitFor(`document.querySelector('main tbody tr') && !document.querySelector('.loading-state')`);assert.equal(await evaluate('location.hash'),historyPath)
 assert.ok(await evaluate(`[...document.querySelectorAll('main tbody tr')].every(tr=>tr.cells[1].querySelector('a').getAttribute('href')===${JSON.stringify(batchPath)})`));await reload();await screenshot('qa52-batch27-history')
 await click('Đối chiếu hai lần');await waitFor(`document.querySelector('.comparison-picks') && !document.querySelector('.loading-state')`)
 assert.ok(await evaluate(`location.hash.includes('batch_id=${qa.batch}')`));await screenshot('qa52-batch27-comparison-filter')
 await go(`/datasets/${qa.dataset}/compare?a=59&b=60`,'Kết quả đối chiếu');await loaded();assert.ok(await evaluate(`[...document.querySelectorAll('nav[aria-label="Điều hướng đối chiếu"] a')].some(a=>a.getAttribute('href')===${JSON.stringify(batchPath)})`));await screenshot('qa52-comparison-59-60')
 checks.push('Real batch history and comparison preserve batch 27; legacy comparison URL 59/60 provides batch return')
 await go(`/datasets/${qa.dataset}/overview`,'Thông tin chung');await loaded();await go(`/datasets/${qa.dataset}/versions`,'Lịch sử phiên bản');await loaded();await click('Xem dữ liệu');await waitFor(`document.querySelector('dialog[open] tbody tr')`)
 await evaluate('history.back()');await waitFor(`location.hash.endsWith('/overview') && !document.querySelector('dialog[open]') && !document.querySelector('.loading-state')`);await screenshot('qa52-preview-back-closes-dialog')
 checks.push('Browser Back from legacy version preview dismisses the modal and restores previous dataset tab')
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,existingQAReadOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('ux03-navigation-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
