// Read-only existing QA checks, called by verify-exp01-local.py.
import assert from 'node:assert/strict'
import Papa from 'papaparse'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'

let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa}=JSON.parse(input);input=''
assert.equal(origin,'http://127.0.0.1:5173','Read-only local QA verification')
const out=path.resolve('test-artifacts/exp01-local');fs.mkdirSync(out,{recursive:true})

const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'exp01-local-browser-'))
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


 const filename=path.join(out,'loi-kiem-tra-83.csv')
 if(fs.existsSync(filename))fs.unlinkSync(filename)
 await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:out,eventsEnabled:true},null)
 await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset}/runs/${qa.run}`})
 await waitFor(`document.querySelector('main')?.innerText.includes('Kết quả kiểm tra')&&!document.querySelector('.loading-state')`)
 const context=await evaluate(`fetch('/api/datasets/58/runs/83/error-export-context').then(r=>{if(!r.ok)throw Error('Context '+r.status);return r.json()})`)
 assert.equal(context.dataset.id,58);assert.equal(context.batch.id,39);assert.equal(context.run_id,83)
 assert.deepEqual(context.identity.columns,['id','part']);assert.equal(context.identity_source,'first_reconciliation_snapshot')
 await click('Xuất CSV lỗi');await waitFor(`document.querySelector('main')?.innerText.includes('Đã xuất 3 lượt vi phạm')`)
 for(let i=0;i<100&&!fs.existsSync(filename);i++)await pause(100)
 assert.ok(fs.existsSync(filename),'Actual browser CSV download missing')
 const text=fs.readFileSync(filename,'utf8');assert.equal(text.charCodeAt(0),0xfeff)
 const parsed=Papa.parse(text);assert.deepEqual(parsed.errors,[])
 const [header,...records]=parsed.data;assert.deepEqual(header.slice(0,6),['Bản ghi','Trường','Giá trị','Loại lỗi','Quy tắc','Gợi ý'])
 assert.equal(records.length,3)
 const report=await evaluate(`fetch('/api/datasets/58/runs/83/report').then(r=>r.json())`)
 for(const row of records){
  const v=Object.fromEntries(header.map((name,index)=>[name,row[index]]))
  assert.equal(v['ID bộ dữ liệu'],'58');assert.equal(v['ID đợt'],'39');assert.equal(v.Run,'83');assert.equal(v['Phiên bản'],'v1')
  assert.equal(v['ID phiên bản'],String(context.version.id))
  const expected=context.rows.find(r=>String(r.row_number)===v['Bản ghi']).values
  assert.deepEqual([v['Khóa: id'],v['Khóa: part']],expected)
  assert.deepEqual(JSON.parse(v['Khóa gốc (JSON)']),expected)
  assert.ok(report.violations.some(item=>String(item.row_number)===v['Bản ghi']&&item.rule_name===v['Quy tắc']&&JSON.stringify(item.values)===v['Giá trị lỗi gốc (JSON)']))
 }
 checks.push('Downloaded actual CSV for run83/58/39: original six error columns retained; dataset/batch/version/run and separate id+part key columns match archived run reconciliation')
 checks.push('All three violation rows and raw JSON values match read-only report/source version; UTF-8 BOM and CSV parsing valid; current metadata is not substituted for missing historical name snapshots')
 await screenshot('run83-csv-exported');assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,context,header,rows:records,actualDownload:path.basename(filename),existingQAReadOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))

}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('exp01-local-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
