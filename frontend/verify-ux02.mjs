// Real browser + API checks. Called only by verify-ux02.py against a disposable DB.
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
const out=path.resolve('test-artifacts/ux02');fs.mkdirSync(out,{recursive:true})
const vite=await createServer({server:{host:'127.0.0.1',port:Number(new URL(origin).port),strictPort:true,proxy:{'/api':backendOrigin}}});await vite.listen()
const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'ux02-browser-'))
const browser=spawn(browserPath,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'})
const pause=ms=>new Promise(r=>setTimeout(r,ms)),pending=new Map(),errors=[],checks=[],layouts=[],writes=[]
let socket,sessionId,seq=0
function send(method,params={},session=sessionId){return new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout ${method}`))},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(session?{sessionId:session}:{})}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);return r.result.value}
async function waitFor(expression){for(let i=0;i<250;i++){if(await evaluate(`Boolean(${expression})`))return;await pause(100)}throw Error(`UI timeout ${expression}; ${(await evaluate('document.body.innerText')).slice(-2500)}`)}
async function go(hash,text){await evaluate(`location.hash=${JSON.stringify(hash)}`);await waitFor(`document.querySelector('main')?.innerText.includes(${JSON.stringify(text)}) && !document.querySelector('.loading-state')`);await pause(180)}
async function click(text,scope='document'){await waitFor(`[...${scope}.querySelectorAll('button,a')].some(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled)`);await evaluate(`[...${scope}.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(text)} && !e.disabled).click()`);await pause(100)}
async function setValue(selector,value){await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const proto=e.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(e,${JSON.stringify(value)});e.dispatchEvent(new Event(e.tagName==='SELECT'?'change':'input',{bubbles:true}));})()`);await pause(100)}
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
 await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset}/overview`})
 await waitFor(`document.querySelector('main')?.innerText.includes('Thông tin chung') && !document.querySelector('.loading-state')`)
 assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Tháng 01/2026') && document.querySelector('main').innerText.includes('Tháng 02/2026')`))
 assert.equal(await evaluate(`[...document.querySelectorAll('main button')].some(e=>['Tải phiên bản mới','Chạy kiểm tra'].includes(e.textContent.trim()))`),false)
 await screenshot('dataset-overview');checks.push('Dataset overview prioritizes common information, named batches and creation, without generic run/upload')
 await go(`/datasets/${qa.dataset}/versions`,'Lịch sử phiên bản · tất cả đợt');assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Tháng 01/2026')`));await screenshot('legacy-versions')
 await go(`/datasets/${qa.dataset}/rules`,'Quy tắc mẫu của bộ dữ liệu');assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Chỉ sao chép khi tạo đợt mới')`));checks.push('Legacy versions/rules URLs retained with history/template scope labels')
 await go(`/datasets/${qa.dataset}/batches/${qa.jan}`,'Phiên bản trong đợt')
 assert.equal(await evaluate(`document.querySelector('#batch-rules').open`),false)
 assert.ok(await evaluate(`Boolean(document.querySelector('#batch-versions').compareDocumentPosition(document.querySelector('#batch-rules')) & Node.DOCUMENT_POSITION_FOLLOWING)`))
 await waitFor(`document.querySelector('.batch-current').innerText.includes('11 quy tắc đang bật')`)
 await screenshot('batch-first-screen');checks.push('Current v3 and next action at top; version list before collapsed rules, active rule count visible')
 await click('Xem dữ liệu');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Tháng 01/2026')`);await screenshot('version-preview');await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);checks.push('Version preview explicitly identifies dataset and batch')
 await click('Xem quy tắc');await waitFor(`document.querySelector('#batch-rules').open && document.querySelector('#batch-rules table')`);await screenshot('batch-rules-expanded')
 await evaluate(`document.querySelector('#batch-rules > summary').click()`);await waitFor(`!document.querySelector('#batch-rules').open`);checks.push('Rules can be expanded/collapsed without obstructing versions')
 await go('/dashboard','Chọn đợt cần theo dõi')
 await field('Tìm đợt dữ liệu','Tháng 01');await selectBatchCheckbox('Tháng 01/2026')
 await waitFor(`document.querySelectorAll('main tbody tr').length===1 && document.querySelector('main').innerText.includes('Chưa kiểm tra') && !document.querySelector('.loading-state')`)
 assert.deepEqual(await evaluate(`[...document.querySelectorAll('.result-stat strong')].map(e=>e.textContent)`),['0','0','0','Chưa có kết quả'])
 await field('Tìm đợt dữ liệu','Tháng 02');assert.ok(await evaluate(`document.querySelector('.batch-chips').innerText.includes('Tháng 01')`));await selectBatchCheckbox('Tháng 02/2026')
 await waitFor(`document.querySelectorAll('main tbody tr').length===2 && document.querySelector('.result-stat strong')?.textContent==='12' && !document.querySelector('.loading-state')`)
 assert.ok(await evaluate(`document.querySelector('main').innerText.includes('12 bản ghi · 9 dòng lỗi · 16 lượt vi phạm')`))
 await screenshot('dashboard-checkboxes');await click('Xóa lựa chọn');await waitFor(`document.querySelectorAll('main tbody tr').length===${qa.total_batches} && !document.querySelector('.loading-state')`)
 await click('Tất cả đợt');assert.equal(await evaluate(`document.querySelectorAll('.batch-options input:checked').length`),0);checks.push('Search/checkbox/chips retain visible selections without Ctrl, clear/all explicit; labeled 12/9/16 result')
 await go(`/datasets/${qa.dataset}/compare?a=${qa.raw_run}&b=${qa.feb_run}`,'Kết quả đối chiếu')
 await waitFor(`document.querySelector('.comparison-picks').innerText.includes('Tháng 02/2026')`)
 assert.equal(await evaluate(`document.querySelector('.filter-bar select').value`),'all')
 assert.ok(await evaluate(`document.querySelector('.comparison-picks').innerText.includes('Tháng 01/2026') && document.querySelector('main').innerText.includes('Không áp dụng')`))
 await screenshot('comparison-cross-batch')
 await field('Đợt dữ liệu',String(qa.jan));await waitFor(`document.querySelector('.comparison-picks').innerText.match(/Chưa chọn/g)?.length===2`)
 assert.equal(await evaluate(`location.hash.includes('?')`),false)
 await evaluate(`[...document.querySelectorAll('button')].find(e=>e.getAttribute('aria-label')==='Chọn lần ${qa.raw_run} cho A').click()`)
 await evaluate(`[...document.querySelectorAll('button')].find(e=>e.getAttribute('aria-label')==='Chọn lần ${qa.fixed_run} cho B').click()`)
 await click('Đối chiếu');await waitFor(`document.querySelector('main').innerText.includes('Cùng điều kiện') && document.querySelector('main').innerText.includes('16,67%')`)
 assert.equal(await evaluate(`document.querySelector('main').innerText.includes('16.6667%')`),false)
 await screenshot('comparison-same-batch');checks.push('Cross-batch URL shows A/B named batches and all scope; filter change clears picks/query; two-decimal rates')
 await go(`/datasets/${qa.dataset}/history`,'Lịch sử kiểm tra · tất cả đợt');await screenshot('legacy-history')
 await go('/history','Lịch sử kiểm tra · tất cả bộ dữ liệu và đợt')
 await click('Chạy kiểm tra');await waitFor(`document.querySelector('dialog[open]')`)
 await field('Bộ dữ liệu',String(qa.single_dataset),'document.querySelector("dialog[open]")')
 await waitFor(`document.querySelector('dialog[open] select') && !document.querySelector('.loading-state')`)
 const choices=await evaluate(`[...document.querySelectorAll('dialog[open] select')].map(e=>e.value)`)
 assert.equal(choices[1],'0');assert.ok(await evaluate(`[...document.querySelectorAll('dialog[open] button')].find(e=>e.textContent.trim()==='Bắt đầu kiểm tra').disabled`))
 await screenshot('no-implicit-batch');await click('Hủy');checks.push('Run dialog does not silently select the only batch of a dataset')
 await go(`/datasets/${qa.dataset}/batches/${qa.jan}`,'Phiên bản trong đợt');await click('Tải bản đã sửa');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Tháng 01/2026')`)
 const root=await send('DOM.getDocument'),node=await send('DOM.querySelector',{nodeId:root.root.nodeId,selector:'dialog[open] input[type=file]'})
 await send('DOM.setFileInputFiles',{nodeId:node.nodeId,files:[qa.fixed_file]});await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Xác nhận lưu phiên bản')`)
 await click('Xác nhận lưu phiên bản');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Đã lưu phiên bản 4')`)
 await click('Chạy kiểm tra');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Chạy kiểm tra dữ liệu') && !document.querySelector('.loading-state')`)
 assert.ok(await evaluate(`document.querySelector('dialog[open]').innerText.includes('Tháng 01/2026')`))
 const selection=await evaluate(`[...document.querySelectorAll('dialog[open] select')].map(e=>e.value)`)
 assert.equal(selection[1],String(qa.jan));const newVersion=Number(selection[2]);assert.ok(newVersion>qa.v3)
 await screenshot('new-version-run-review');await click('Bắt đầu kiểm tra');await waitFor(`document.querySelector('h1')?.textContent==='Kết quả kiểm tra' && document.querySelector('.result-stat') && !document.querySelector('.loading-state')`)
 const finalRun=await evaluate(`Number(location.hash.split('/')[4])`)
 const result=await evaluate(`fetch('/api/datasets/${qa.dataset}/runs/${finalRun}').then(r=>r.json())`)
 assert.equal(result.version_id,newVersion);assert.deepEqual([result.total_rows,result.error_row_count,result.violation_count,result.error_row_rate],[12,2,2,'16.6667'])
 assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Tháng 01/2026') && document.querySelector('main').innerText.includes('83,33%')`))
 await screenshot('full-flow-result');checks.push('Real upload creates Jan v4; Continue opens exact v4; real POST run gives 12/2/2, stored rate 16.6667 unchanged')
 await go(`/datasets/${qa.dataset}/batches/${qa.empty}`,'Tải CSV đầu tiên');await screenshot('empty-batch')
 await go(`/datasets/${qa.dataset}/batches/${qa.no_rules}`,'Cần thiết lập quy tắc');await click('Thiết lập quy tắc');await waitFor(`document.querySelector('#batch-rules').open`)
 await screenshot('missing-rules');checks.push('Empty/missing-rule batches provide correct next actions and never show passed')
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true})
 await go(`/datasets/${qa.dataset}/batches/${qa.jan}`,'Phiên bản trong đợt');await screenshot('mobile-batch')
 await go('/dashboard','Chọn đợt cần theo dõi');await screenshot('mobile-filter')
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'dark'}]});await screenshot('mobile-dark-filter')
 assert.equal(errors.length,0,errors.join('\n'))
 assert.deepEqual(writes,[{method:'POST',path:`/api/datasets/${qa.dataset}/batches/${qa.jan}/versions/import`},{method:'POST',path:`/api/datasets/${qa.dataset}/versions/${newVersion}/runs`}])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,disposableDatabaseOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);await vite.close();try{fs.rmSync(profile,{recursive:true,force:true})}catch{}}
