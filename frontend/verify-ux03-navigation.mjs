// Real browser + API checks. Called only by verify-ux03-navigation.py against a disposable DB.
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
const out=path.resolve('test-artifacts/ux03-navigation');fs.mkdirSync(out,{recursive:true})
const vite=await createServer({server:{host:'127.0.0.1',port:Number(new URL(origin).port),strictPort:true,proxy:{'/api':backendOrigin}}});await vite.listen()
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


 const activeRequests=new Set();let lastActivity=Date.now()
 socket.addEventListener('message',event=>{const m=JSON.parse(String(event.data));if(m.method==='Network.requestWillBeSent'&&m.params.request.url.startsWith(origin+'/api/')){activeRequests.add(m.params.requestId);lastActivity=Date.now()}else if(['Network.loadingFinished','Network.loadingFailed'].includes(m.method)&&activeRequests.delete(m.params.requestId))lastActivity=Date.now()})
 const batchPath=`#/datasets/${qa.dataset}/batches/${qa.jan}`
 const historyPath=`#/datasets/${qa.dataset}/history?batch_id=${qa.jan}`
 async function loaded(){for(let i=0;i<250;i++){if(!activeRequests.size&&Date.now()-lastActivity>=300&&await evaluate(`Boolean(document.querySelector('main h1') && !document.querySelector('.loading-state'))`))return;await pause(100)}throw Error('API/UI did not settle')}
 async function reload(){await evaluate('window.__ux03Reload=true');await send('Page.reload',{ignoreCache:true});await waitFor('!window.__ux03Reload');await loaded()}
 async function back(){await evaluate('history.back()');await pause(180);await loaded()}
 const filterValue=label=>evaluate(`[...document.querySelectorAll('main label')].find(e=>e.querySelector('span')?.textContent.trim()===${JSON.stringify(label)})?.querySelector('select')?.value`)
 const historyBatchLinks=()=>evaluate(`[...document.querySelectorAll('main tbody tr')].map(tr=>tr.cells[1]?.querySelector('a')?.getAttribute('href'))`)
 await send('Page.navigate',{url:origin+`/#/datasets/${qa.dataset}/overview`});await loaded()
 for(const width of [1280,1024,768]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await pause(150)
  assert.ok(await evaluate(`(()=>{const nav=document.querySelector('.workspace-tab-groups');const box=nav.getBoundingClientRect();return nav.scrollWidth<=nav.clientWidth+1&&[...nav.querySelectorAll('a')].length===8&&[...nav.querySelectorAll('a')].every(a=>{const r=a.getBoundingClientRect();return r.width>0&&r.left>=box.left-1&&r.right<=box.right+1})})()`),`All tabs accessible at ${width}`)
  assert.ok(await evaluate(`(()=>{const b=[...document.querySelectorAll('main button')].find(e=>e.textContent.trim()==='Tạo đợt dữ liệu');const r=b.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight&&b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))})()`),`Primary action visible at ${width}`)
  await screenshot(`dataset-tabs-${width}`)
 }
 checks.push('All eight dataset navigation tabs wrap visibly, primary create action stays exposed and page has no horizontal overflow at 1280/1024/768')
 await go(`/datasets/${qa.dataset}/runs/${qa.raw_run}`,'Kết quả kiểm tra');await loaded()
 for(const width of [1280,1024,768]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await pause(120)
  assert.ok(await evaluate(`[...document.querySelectorAll('.breadcrumb a')].some(a=>a.getAttribute('href')===${JSON.stringify(batchPath)}&&a.textContent.includes('Tháng 01/2026'))`))
  assert.ok(await evaluate(`(()=>{const a=[...document.querySelectorAll('.breadcrumb a')].find(a=>a.getAttribute('href')===${JSON.stringify(batchPath)});const r=a.getBoundingClientRect(),header=a.closest('header')?.getBoundingClientRect()??document.querySelector('.topbar').getBoundingClientRect();return r.width>=32&&r.bottom<=header.bottom+1})()`),`Batch breadcrumb visible at ${width}`)
  await screenshot(`historical-result-${width}`)
 }
 assert.ok(await evaluate(`document.querySelector('.result-context').innerText.includes('v1 · Bản lịch sử')`))
 await reload();assert.ok(await evaluate(`[...document.querySelectorAll('.breadcrumb a')].some(a=>a.getAttribute('href')===${JSON.stringify(batchPath)})`))
 await click('Về đợt dữ liệu');await waitFor(`document.querySelector('.batch-current')?.innerText.includes('v3')`)
 await screenshot('historical-result-to-current-batch');await back()
 assert.ok(await evaluate(`location.hash.endsWith('/runs/${qa.raw_run}') && document.querySelector('.result-context').innerText.includes('v1 · Bản lịch sử')`))
 await go(`/datasets/${qa.dataset}/runs/${qa.fixed_run}`,'Kết quả kiểm tra');await loaded();await click('Về đợt dữ liệu');await waitFor(`document.querySelector('.batch-current')?.innerText.includes('v3')`);await back()
 assert.ok(await evaluate(`document.querySelector('.result-context').innerText.includes('v2 · Bản lịch sử')`))
 checks.push('Historical v1/v2 results have named batch breadcrumb and explicit return; returning shows current v3, reload preserves context, browser Back returns to the historical result')
 await click('Tải lên bản đã sửa');await waitFor(`document.querySelector('dialog[open]')`)
 assert.ok(await evaluate(`document.querySelector('dialog[open]').innerText.includes('Tháng 01/2026') && document.querySelector('dialog[open]').innerText.includes('v4')`))
 await screenshot('historical-upload-keeps-batch');await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`)
 await click('Lịch sử kiểm tra của đợt');await waitFor(`document.querySelector('main h2')?.innerText.includes('Lịch sử kiểm tra') && !document.querySelector('.loading-state')`)
 assert.equal(await evaluate('location.hash'),historyPath);assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan))
 assert.ok(await evaluate(`[...document.querySelectorAll('.workspace-tab-items a')].some(a=>a.textContent==='Lịch sử kiểm tra của đợt'&&a.getAttribute('href')===${JSON.stringify(historyPath)}) && [...document.querySelectorAll('.workspace-tab-items a')].some(a=>a.textContent==='Đối chiếu trong đợt'&&a.getAttribute('href')==='#/datasets/${qa.dataset}/compare?batch_id=${qa.jan}')`))
 assert.deepEqual(await historyBatchLinks(),Array(10).fill(batchPath))
 const options=await evaluate(`[...document.querySelectorAll('main label')].find(e=>e.querySelector('span')?.textContent==='Phiên bản').querySelector('select').options.length`);assert.equal(options,4)
 await evaluate(`document.querySelector('button[aria-label="Trang sau"]').click()`);await waitFor(`document.querySelector('.pagination')?.innerText.includes('Trang 2') && !document.querySelector('.loading-state')`)
 assert.deepEqual(await historyBatchLinks(),Array(2).fill(batchPath));await screenshot('batch-history-page-two')
 await field('Tìm lần kiểm tra',`#${qa.raw_run}`);await pause(450);await loaded();assert.ok((await historyBatchLinks()).every(h=>h===batchPath));await screenshot('batch-history-search')
 await reload();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan));assert.deepEqual(await historyBatchLinks(),Array(10).fill(batchPath))
 await click('Đối chiếu hai lần');await waitFor(`document.querySelector('.comparison-picks') && !document.querySelector('.loading-state')`);assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan));await screenshot('history-to-scoped-comparison')
 await back();assert.equal(await evaluate('location.hash'),historyPath);assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan))
 await click('Lịch sử tất cả đợt');await waitFor(`document.querySelector('main h2')?.innerText.includes('tất cả đợt') && !document.querySelector('.loading-state')`);assert.equal(await filterValue('Đợt dữ liệu'),'');assert.ok((await historyBatchLinks()).some(h=>h.endsWith(`/batches/${qa.feb}`)))
 await back();assert.equal(await evaluate('location.hash'),historyPath);assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan))
 await field('Đợt dữ liệu',String(qa.feb));await loaded();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.feb));await reload();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.feb));assert.deepEqual(await historyBatchLinks(),[`#/datasets/${qa.dataset}/batches/${qa.feb}`]);await back();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan))
 checks.push('Batch history filters API, version choices, pagination and client search; reload/direct URLs preserve batch; comparison link inherits scope; explicit all-batch link and Back restore correct filters')
 await go(`/datasets/${qa.dataset}/compare?a=${qa.raw_run}&b=${qa.fixed_run}`,'Kết quả đối chiếu');await loaded();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan))
 await click('Về đợt dữ liệu');await waitFor(`document.querySelector('.batch-current')?.innerText.includes('v3')`);await back();await reload();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan));await screenshot('same-batch-comparison')
 await go(`/datasets/${qa.dataset}/compare?a=${qa.raw_run}&b=${qa.feb_run}&batch_id=${qa.jan}`,'Kết quả đối chiếu');await loaded();assert.equal(await filterValue('Đợt dữ liệu'),'all')
 for(const [side,id] of [['A',qa.jan],['B',qa.feb]])assert.ok(await evaluate(`[...document.querySelectorAll('.comparison-picks a')].some(a=>a.textContent.startsWith('Về đợt ${side}')&&a.getAttribute('href')==='#/datasets/${qa.dataset}/batches/${id}')`))
 assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Hai đợt khác nhau.') && document.querySelector('main').innerText.includes('Không áp dụng')`));await screenshot('cross-batch-comparison-links')
 await go(`/datasets/${qa.dataset}/compare?a=${qa.raw_run}&b=${qa.revision_run}`,'Kết quả đối chiếu');await loaded();assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Bộ quy tắc đã thay đổi.') && document.querySelector('main').innerText.includes('Không áp dụng')`));await screenshot('revision-warning-preserved')
 await field('Đợt dữ liệu',String(qa.feb));await loaded();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.feb));assert.equal(await evaluate(`new URLSearchParams(location.hash.split('?')[1]).has('a')`),false);assert.equal(await evaluate(`document.querySelector('.comparison-picks').innerText.match(/Chưa chọn/g)?.length`),2)
 await reload();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.feb));await back();assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan));assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Kết quả đối chiếu')`))
 await go(`/datasets/${qa.dataset}/compare?batch_id=${qa.jan}`,'Đối chiếu hai lần kiểm tra');await loaded();await field('Phiên bản',String(qa.v2));await loaded();await reload();assert.equal(await filterValue('Phiên bản'),String(qa.v2));assert.equal(await filterValue('Đợt dữ liệu'),String(qa.jan));await back();assert.equal(await filterValue('Phiên bản'),'')
 checks.push('Old A/B URLs infer same/cross batch correctly; common and separate A/B return links work; batch/revision warnings remain; filter changes clear picks, persist in URL and Back restores pairs/version scope')
 await go(`/datasets/${qa.dataset}/batches/${qa.jan}`,'Phiên bản trong đợt');await click('Xem dữ liệu');await waitFor(`document.querySelector('dialog[open] tbody tr')`)
 assert.ok(await evaluate(`document.querySelector('dialog[open]').innerText.includes('Tháng 01/2026') && document.querySelector('dialog[open]').innerText.includes('Bản hiện hành')`));await screenshot('preview-retains-batch');await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);assert.equal(await evaluate('location.hash'),batchPath)
 await go(`/datasets/${qa.dataset}/history?batch_id=99999999`,'Đợt trong URL');assert.ok(await evaluate(`document.querySelector('[role="alert"]').innerText.includes('không hợp lệ') && !document.querySelector('main tbody tr')`));await screenshot('invalid-history-scope')
 for(const [path,text] of [['versions','Lịch sử phiên bản'],['rules','Quy tắc mẫu'],['history','Lịch sử kiểm tra']])await go(`/datasets/${qa.dataset}/${path}`,text)
 checks.push('Preview retains batch/current label and closes in place; legacy versions/rules/history routes remain; invalid batch scope displays an error instead of all-batch results')
 await go('/history','Lịch sử kiểm tra · tất cả bộ dữ liệu và đợt');await loaded();await field('Bộ dữ liệu',String(qa.dataset));await loaded();await field('Đợt dữ liệu',String(qa.feb));await loaded()
 assert.equal(await evaluate('location.hash'),`#/history?dataset_id=${qa.dataset}&batch_id=${qa.feb}`);await reload();assert.equal(await filterValue('Bộ dữ liệu'),String(qa.dataset));assert.equal(await filterValue('Đợt dữ liệu'),String(qa.feb));assert.ok(await evaluate(`document.querySelectorAll('main tbody tr').length===1`));await screenshot('global-history-scope-url')
 await back();assert.equal(await filterValue('Bộ dữ liệu'),String(qa.dataset));assert.equal(await filterValue('Đợt dữ liệu'),'')
 checks.push('Global history dataset/batch filters also survive direct URL/reload; Back restores the previous dataset scope')
 assert.equal(errors.length,0,errors.join('\n'));assert.deepEqual(writes,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,disposableDatabaseOnly:true},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);await vite.close();try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('ux03-navigation-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
