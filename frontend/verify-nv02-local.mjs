// Read-only existing QA checks, called by verify-nv02-local.py.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'

let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa}=JSON.parse(input);input=''
assert.equal(origin,'http://127.0.0.1:5173','Read-only local QA verification')
const out=path.resolve('test-artifacts/nv02-local');fs.mkdirSync(out,{recursive:true})

const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'nv02-local-browser-'))
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
 await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset_id}/overview`});await waitFor(`document.querySelector('#record-identity')?.innerText.includes('id + part')&&!document.querySelector('.loading-state')`)
 const get=async url=>evaluate(`fetch(${JSON.stringify(url)}).then(r=>{if(!r.ok)throw Error('GET '+r.status);return r.json()})`)
 for(const [ds,run,total,rows,violations] of [[52,59,12,9,16],[52,60,12,2,2],[52,61,12,0,0],[55,66,12,6,9],[55,67,12,6,8]]){
  const r=await get(`/api/datasets/${ds}/runs/${run}`);assert.deepEqual([r.total_rows,r.error_row_count,r.violation_count],[total,rows,violations])
 }
 checks.push('Existing QA52 runs59/60/61 and QA55 runs66/67 retain their exact 12-row result counts')
 for(const b of qa.batches){
  await go(`/datasets/${qa.dataset_id}/batches/${b.id}?issues=1`,'Xử lý lỗi');await waitFor(`document.querySelector('#batch-workflow .workflow-counts')&&!document.querySelector('.loading-state')`)
  const state=await get(`/api/datasets/${qa.dataset_id}/batches/${b.id}/workflow`);assert.deepEqual(state.counts,b.final.counts);assert.equal(state.business_state,b.final.business_state)
  if(b.id===qa.batches[2].id){
   assert.equal(state.completion.can_complete,false);assert.equal(state.reconciliations[0].counts.UNKNOWN,3)
   await evaluate(`document.querySelector('#batch-workflow details').open=true`)
   assert.ok(await evaluate(`document.querySelector('#batch-workflow').innerText.includes('Có bản ghi thiếu khóa')&&document.querySelector('#batch-workflow').innerText.includes('Chưa xác định')`))
  }
  if(b.id===qa.batches[3].id){
   assert.equal(state.events[0].evidence.ignored.length,3)
   assert.ok(await evaluate(`document.querySelector('#batch-workflow').innerText.includes('ngoại lệ')`))
  }
  await evaluate(`document.querySelector('#batch-workflow').scrollIntoView()`);await screenshot('local-batch-'+b.id)
  for(const stage of b.stages){const r=await get(`/api/datasets/${qa.dataset_id}/runs/${stage.run_id}`);for(const [key,value] of Object.entries(stage.quality))assert.equal(r[key],value)}
 }
 checks.push('All four persistent NV-02 batches match manifest states, issue counts and every run; invalid identity is visibly unknown and completed exceptions retain acknowledgement evidence')
 const a=qa.batches[0],old=a.stages[0],current=a.stages.at(-1)
 await go(`/datasets/${qa.dataset_id}/runs/${old.run_id}`,'Kết quả kiểm tra');await waitFor(`[...document.querySelectorAll('main button')].some(b=>b.textContent.includes('Issue #'))`)
 assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Lịch sử')||document.querySelector('main').innerText.includes('lịch sử')`))
 assert.ok(await evaluate(`[...document.querySelectorAll('a')].some(a=>a.textContent==='Về đợt dữ liệu'&&a.hash.includes('/batches/${a.id}'))`));await screenshot('local-historical-run-'+old.run_id)
 await click('Về đợt dữ liệu');await waitFor(`document.querySelector('.batch-current')?.innerText.includes('v3')&&!document.querySelector('.loading-state')`)
 await send('Page.reload');await waitFor(`document.querySelector('#batch-workflow')?.innerText.includes('Đã hoàn tất')&&!document.querySelector('.loading-state')`)
 checks.push('Historical v1 result still links to its issue and returns to correct completed batch/current v3; reload retains context')
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,existingQAReadOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))

}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('nv02-local-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
