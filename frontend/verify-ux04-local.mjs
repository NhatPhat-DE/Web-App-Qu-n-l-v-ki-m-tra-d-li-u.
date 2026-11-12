// Read-only existing QA checks, called by verify-ux04-local.py.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'

let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa}=JSON.parse(input);input=''
assert.equal(origin,'http://127.0.0.1:5173','Read-only local QA verification')
const out=path.resolve('test-artifacts/ux04-local');fs.mkdirSync(out,{recursive:true})

const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'ux04-local-browser-'))
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

 const reads=[];socket.addEventListener('message',event=>{const m=JSON.parse(String(event.data));if(m.method==='Network.requestWillBeSent'&&m.params.request.url.startsWith(origin+'/api/'))reads.push(new URL(m.params.request.url).pathname)})
 await send('Page.navigate',{url:origin+'/#/dashboard'});await waitFor(`document.querySelector('main')?.innerText.includes('Bàn làm việc theo đợt dữ liệu')&&!document.querySelector('.loading-state')`)
 const query=qa.batches.map(id=>'batch_id='+id).join('&')
 const data=await evaluate(`fetch('/api/batch-dashboard?${query}').then(r=>r.json())`)
 assert.deepEqual([data.total_rows,data.violated_rows_count,data.total_violations_count,data.violation_rate],[15,3,4,'20.0000'])
 for(const item of data.items)await selectBatchCheckbox(item.batch_name)
 await waitFor(`document.querySelectorAll('main [data-workflow-batch]').length===5&&!document.querySelector('.loading-state')`)
 assert.deepEqual(await evaluate(`[...document.querySelectorAll('.result-stat strong')].map(s=>s.textContent)`),['15','3','4','20%'])
 const row36=await evaluate(`document.querySelector('[data-workflow-batch="36"]').closest('tr').innerText`)
 assert.ok(row36.includes('Đạt quy tắc')&&row36.includes('3 issue chưa xử lý')&&row36.includes('3 chưa thể đối soát'))
 const row38=await evaluate(`document.querySelector('[data-workflow-batch="38"]').closest('tr').innerText`)
 assert.ok(row38.includes('1 lượt vi phạm')&&row38.includes('3 issue chưa xử lý')&&row38.includes('3 chưa thể đối soát'))
 for(const id of [36,38])await evaluate(`document.querySelector('[data-workflow-batch="${id}"] details').open=true`)
 assert.ok(await evaluate(`document.querySelector('[data-workflow-batch="36"]').innerText.includes('Có bản ghi thiếu khóa')`))
 assert.ok(await evaluate(`document.querySelector('[data-workflow-batch="38"]').innerText.includes('Quy tắc, cấu trúc hoặc cách kiểm tra đã thay đổi')`))
 checks.push('QA57 batches34–38: totals remain 15 records / 3 error rows / 4 violations / 20%; clean batch36 and one-violation batch38 each show 3 open/uncertain issues with correct blockers')
 assert.equal(await evaluate(`document.querySelectorAll('main td a[href$="?issues=1"]').length`),5)
 for(const item of data.items){
  const text=await evaluate(`document.querySelector('[data-workflow-batch="${item.batch_id}"]').innerText`)
  if(item.workflow.enabled){assert.ok(text.includes(item.workflow.unprocessed_count+' issue chưa xử lý'));assert.ok(text.includes(item.workflow.ignored_count+' ngoại lệ'))}
 }
 await evaluate(`document.querySelector('[data-workflow-batch="36"]').scrollIntoView({block:'center'})`);await screenshot('dashboard-qa57-issues')
 const dashboardReads=[...reads];assert.ok(!dashboardReads.some(p=>/\/batches\/\d+\/workflow/.test(p)))
 checks.push('All five rows include scoped Xử lý lỗi links and exception counts; Dashboard uses aggregate endpoint, no per-batch workflow requests')
 await send('Emulation.setDeviceMetricsOverride',{width:768,height:900,deviceScaleFactor:1,mobile:false});await screenshot('dashboard-768')
 await send('Emulation.setDeviceMetricsOverride',{width:1366,height:900,deviceScaleFactor:1,mobile:false})
 await evaluate(`document.querySelector('[data-workflow-batch="36"] a').click()`);await waitFor(`location.hash==='/datasets/57/batches/36?issues=1'.replace(/^/,'#')&&document.querySelector('#batch-workflow')?.innerText.includes('3')&&!document.querySelector('.loading-state')`)
 assert.ok(await evaluate(`document.querySelector('#batch-workflow').innerText.includes('Có bản ghi thiếu khóa')`))
 checks.push('Xử lý lỗi opens correct batch36/context; 768px has no page overflow')
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,dashboardReads,metrics:{total_rows:data.total_rows,error_rows:data.violated_rows_count,violations:data.total_violations_count,rate:data.violation_rate},items:data.items,existingQAReadOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))

}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('ux04-local-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
