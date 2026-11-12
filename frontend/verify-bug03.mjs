// Real browser + API checks. Called only by verify-bug03.py against a disposable DB.
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
const out=path.resolve('test-artifacts/bug03');fs.mkdirSync(out,{recursive:true})
const vite=await createServer({server:{host:'127.0.0.1',port:Number(new URL(origin).port),strictPort:true,proxy:{'/api':backendOrigin}}});await vite.listen()
const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'bug03-browser-'))
const browser=spawn(browserPath,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'})
const pause=ms=>new Promise(r=>setTimeout(r,ms)),pending=new Map(),errors=[],checks=[],layouts=[],writes=[]
let socket,sessionId,seq=0
function send(method,params={},session=sessionId){return new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout ${method}`))},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(session?{sessionId:session}:{})}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);return r.result.value}
async function waitFor(expression){for(let i=0;i<250;i++){if(await evaluate(`Boolean(${expression})`))return;await pause(100)}throw Error(`UI timeout ${expression}; ${(await evaluate('document.body.innerText')).slice(-2500)}`)}
async function go(hash,text){await evaluate(`location.hash=${JSON.stringify(hash)}`);await waitFor(`document.querySelector('main')?.innerText.includes(${JSON.stringify(text)}) && !document.querySelector('.loading-state')`);await pause(180)}
async function click(text,scope='document'){await waitFor(`[...${scope}.querySelectorAll('button,a')].some(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled)`);await evaluate(`[...${scope}.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled).click()`);await pause(100)}
async function setValue(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const proto=e.tagName==='SELECT'?HTMLSelectElement.prototype:e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);await pause(100)}
async function field(label,value,scope='document'){const selector=await evaluate(`(()=>{const e=[...${scope}.querySelectorAll('label')].find(e=>e.querySelector('span')?.textContent.replace(' *','').trim()===${JSON.stringify(label)})?.querySelector('input,select,textarea');if(!e)throw Error('Missing field ${label}');e.dataset.qa='active';return '[data-qa="active"]';})()`);await setValue(selector,value);await evaluate(`document.querySelector(${JSON.stringify(selector)}).removeAttribute('data-qa')`)}
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

 const dialogs=[];let acceptDialog=false,failCreate=true,createRequests=0
 socket.addEventListener('message',async event=>{
  const m=JSON.parse(String(event.data))
  try{
   if(m.method==='Page.javascriptDialogOpening'){
    dialogs.push(m.params.message);await send('Page.handleJavaScriptDialog',{accept:acceptDialog})
   }
   if(m.method==='Fetch.requestPaused'){
    if(m.params.request.method==='POST' && new URL(m.params.request.url).pathname===`/api/datasets/${qa.dataset}/batches`){
     createRequests++
     if(failCreate){failCreate=false;await send('Fetch.fulfillRequest',{requestId:m.params.requestId,responseCode:503,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:Buffer.from(JSON.stringify({detail:'BUG-03 lỗi thử có chủ đích'})).toString('base64')});return}
     await pause(450)
    }
    await send('Fetch.continueRequest',{requestId:m.params.requestId})
   }
  }catch(error){errors.push(String(error))}
 })
 await send('Fetch.enable',{patterns:[{urlPattern:`${origin}/api/datasets/${qa.dataset}/batches`,requestStage:'Request'}]})
 await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset}/overview`})
 await waitFor(`document.querySelector('main')?.innerText.includes('Thông tin chung') && !document.querySelector('.loading-state')`)
 await click('Tạo đợt dữ liệu');await field('Tên đợt dữ liệu','BUG-03 Tạo đợt thành công');await field('Kỳ dữ liệu','11/2026');await field('Mô tả đợt dữ liệu','Giữ nguyên nội dung khi hủy hoặc API lỗi')
 const formValues=()=>evaluate(`[...document.querySelectorAll('dialog[open] input,dialog[open] textarea')].map(e=>e.type==='checkbox'?e.checked:e.value)`)
 const original=await formValues()
 assert.equal(await evaluate(`window.dispatchEvent(new Event('beforeunload',{cancelable:true}))`),false)
 const current=await evaluate('location.hash')
 await evaluate(`location.hash='/dashboard'`);await pause(350)
 assert.equal(await evaluate('location.hash'),current);assert.deepEqual(await formValues(),original);assert.equal(dialogs.length,1)
 await click('Hủy','document.querySelector("dialog[open]")');assert.deepEqual(await formValues(),original);assert.equal(dialogs.length,2)
 await screenshot('unsaved-cancel-keeps-form');checks.push('Unsaved navigation and Cancel show confirmation; dismissing it preserves URL and every form field; beforeunload protected')
 await evaluate(`document.querySelector('dialog[open] form').requestSubmit()`)
 await waitFor(`document.querySelector('dialog[open] [role="alert"]')`)
 assert.deepEqual(await formValues(),original);assert.equal(createRequests,1)
 await screenshot('api-failure-keeps-form');checks.push('503 creation failure preserves name, period, description and copy-template setting for retry')
 const beforeSuccess=dialogs.length
 await evaluate(`(()=>{const f=document.querySelector('dialog[open] form');f.requestSubmit();f.requestSubmit()})()`)
 assert.equal(await evaluate(`document.querySelector('dialog[open] button[type="submit"]').disabled`),true)
 await waitFor(`location.hash.includes('/batches/') && document.querySelector('h1')?.innerText==='BUG-03 Tạo đợt thành công' && !document.querySelector('dialog[open]')`)
 assert.equal(createRequests,2);assert.equal(dialogs.length,beforeSuccess)
 assert.equal(await evaluate(`window.dispatchEvent(new Event('beforeunload',{cancelable:true}))`),true)
 const createdBatch=Number((await evaluate('location.hash')).split('/')[4])
 await screenshot('created-without-unsaved-warning');checks.push('Retry succeeds with no leave warning, removes beforeunload listener, navigates to actual new batch; double submit sends only one successful request')
 await go(`/datasets/${qa.dataset}/overview`,'Thông tin chung');await click('Tạo đợt dữ liệu')
 await evaluate(`document.querySelector('dialog[open] input[type="checkbox"]').click()`)
 const prev=dialogs.length;await click('Hủy','document.querySelector("dialog[open]")');assert.equal(dialogs.length,prev+1)
 acceptDialog=true;await click('Hủy','document.querySelector("dialog[open]")');await waitFor(`!document.querySelector('dialog[open]')`)
 checks.push('Changing only copy-template checkbox is dirty; confirming discard closes form')
 await go(`/datasets/${qa.white_dataset}/batches/${qa.white_batch}`,'Phiên bản trong đợt')
 await click('Tải bản đã sửa');await waitFor(`document.querySelector('input[type="file"]')`)
 let root=await send('DOM.getDocument'),fileNode=await send('DOM.querySelector',{nodeId:root.root.nodeId,selector:'input[type="file"]'})
 await send('DOM.setFileInputFiles',{nodeId:fileNode.nodeId,files:[qa.white_file]})
 await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Xem trước dữ liệu')`)
 const uploadCells=await evaluate(`[...document.querySelectorAll('dialog[open] tbody tr')].map(tr=>tr.cells[2].textContent)`)
 assert.deepEqual(uploadCells,['Trống','Chỉ có khoảng trắng','Chỉ có khoảng trắng','Chỉ có khoảng trắng','Chỉ có khoảng trắng','0','NULL','NaN','N/A','Chỉ có khoảng trắng'])
 assert.ok(await evaluate(`[...document.querySelectorAll('dialog[open] span[title]')].some(e=>e.title.includes(${JSON.stringify('\\u0009')}))`))
 await screenshot('upload-whitespace-labels');await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`)
 await waitFor(`!document.querySelector('dialog[open]')`)
 await click('Xem dữ liệu');await waitFor(`document.querySelector('dialog[open] tbody tr')`)
 assert.deepEqual(await evaluate(`[...document.querySelectorAll('dialog[open] tbody tr')].map(tr=>tr.cells[2].textContent)`),uploadCells)
 await screenshot('version-whitespace-labels');await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`)
 checks.push('Upload and persisted-version previews consistently distinguish empty, space, tab, NBSP, em-space and NEL; zero and NULL/NaN/N/A remain literal; escaped tooltip available')
 await go(`/datasets/${qa.white_dataset}/versions`,'Lịch sử phiên bản')
 await click('Xem dữ liệu');await waitFor(`document.querySelector('dialog[open] tbody tr')`)
 assert.deepEqual(await evaluate(`[...document.querySelectorAll('dialog[open] tbody tr')].map(tr=>tr.cells[2].textContent)`),uploadCells)
 await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`)
 checks.push('Legacy all-batch version preview uses the same value rendering')
 await go(`/datasets/${qa.white_dataset}/runs/${qa.white_run}`,'Kết quả kiểm tra');await waitFor(`document.querySelector('.cell-value')`)
 assert.ok(await evaluate(`[...document.querySelectorAll('.cell-value')].some(e=>e.textContent==='Chỉ có khoảng trắng')`))
 await screenshot('violation-whitespace-labels')
 await evaluate(`(()=>{const original=URL.createObjectURL;URL.createObjectURL=function(blob){window.__bug03Export=blob;return original.call(this,blob)}})()`)
 await click('Xuất CSV lỗi');await waitFor(`window.__bug03Export`)
 const csv=await evaluate(`window.__bug03Export.text()`);fs.writeFileSync(path.join(out,'exported-errors.csv'),csv)
 const Papa=(await import('papaparse')).default,exportRows=Papa.parse(csv).data
 for(let i=0;i<qa.white_values.length;i++){
  const record=exportRows.slice(1).find(row=>row[0]===String(i+1));assert.ok(record,`Missing exported row ${i+1}`);assert.equal(record[2],qa.white_values[i])
 }
 assert.ok(!csv.includes('Chỉ có khoảng trắng'));assert.ok(!csv.includes('Trống'))
 await evaluate(`document.querySelector('button[aria-label="Xem bản ghi 3"]').click()`);await waitFor(`document.querySelector('.record-values')`)
 assert.ok(await evaluate(`document.querySelector('.record-values').innerText.includes('Chỉ có khoảng trắng')`))
 await screenshot('record-whitespace-detail');await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`)
 checks.push('Violation list and record detail label whitespace; actual downloaded CSV blob preserves every original value including tab, zero, NULL/NaN/N/A, FEFF and zero-width space with no presentation labels')
 for(const [run,expected] of [[qa.raw_run,[9,16]],[qa.fixed_run,[2,2]],[qa.clean_run,[0,0]]]){
  await go(`/datasets/${qa.dataset}/runs/${run}`,'Kết quả kiểm tra')
  const result=await evaluate(`fetch('/api/datasets/${qa.dataset}/runs/${run}').then(r=>r.json())`)
  assert.deepEqual([result.error_row_count,result.violation_count],expected)
  const stats=await evaluate(`[...document.querySelectorAll('.result-stat strong')].map(e=>e.textContent)`)
  assert.equal(stats[1],String(expected[0]));assert.equal(stats[4],String(expected[1]));await screenshot(`engine-run-${run}`)
 }
 checks.push('Real engine and browser results retain v1=9/16, v2=2/2, v3=0/0 in separate fixture')
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true})
 await go(`/datasets/${qa.white_dataset}/batches/${qa.white_batch}`,'Phiên bản trong đợt');await click('Xem dữ liệu');await waitFor(`document.querySelector('dialog[open] tbody tr')`);await screenshot('mobile-whitespace-preview')
 assert.equal(errors.length,0,errors.join('\n'))
 assert.deepEqual(writes,[{method:'POST',path:`/api/datasets/${qa.dataset}/batches`},{method:'POST',path:`/api/datasets/${qa.dataset}/batches`}])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,dialogs,createdBatch,disposableDatabaseOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);await vite.close();try{fs.rmSync(profile,{recursive:true,force:true})}catch{}}
