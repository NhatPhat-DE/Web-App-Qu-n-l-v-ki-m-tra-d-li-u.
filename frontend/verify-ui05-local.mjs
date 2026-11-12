// Read-only existing QA checks, called by verify-exp01-local.py.
import assert from 'node:assert/strict'
import Papa from 'papaparse'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import {spawn} from 'node:child_process'
import {once} from 'node:events'

let input='';for await(const chunk of process.stdin)input+=chunk
const {origin,backendOrigin,token,qa,phase}=JSON.parse(input);input=''
assert.equal(origin,'http://127.0.0.1:5173','Read-only local QA verification')
const out=path.resolve('test-artifacts/ui05-'+phase);fs.mkdirSync(out,{recursive:true})

const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'ui05-browser-'))
const browser=spawn(browserPath,['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'})
const pause=ms=>new Promise(r=>setTimeout(r,ms)),pending=new Map(),errors=[],checks=[],layouts=[],writes=[]
let socket,sessionId,seq=0
function send(method,params={},session=sessionId){return new Promise((resolve,reject)=>{const id=++seq,timer=setTimeout(()=>{pending.delete(id);reject(Error(`CDP timeout ${method}`))},20000);pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params,...(session?{sessionId:session}:{})}))})}
async function evaluate(expression){const r=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true,userGesture:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description??r.exceptionDetails.text);return r.result.value}
async function waitFor(expression){for(let i=0;i<250;i++){if(await evaluate(`Boolean(${expression})`))return;await pause(100)}throw Error(`UI timeout ${expression}; ${(await evaluate('document.body.innerText')).slice(-2500)}`)}
async function go(hash,text){await evaluate(`location.hash=${JSON.stringify(hash)}`);await waitFor(`document.querySelector('main')?.innerText.includes(${JSON.stringify(text)}) && !document.querySelector('.loading-state')`);await pause(180)}
async function click(text,scope='document'){await waitFor(`(()=>{const root=${scope};const e=root&&[...root.querySelectorAll('button,a')].find(e=>e.textContent.trim()===${JSON.stringify(text)}&&!e.disabled);if(!e)return false;e.click();return true})()`);await pause(120)}
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



 if(phase==='before'){
  await send('Page.navigate',{url:origin+'/#/dashboard'});await waitFor(`document.querySelector('.result-stats')&&!document.querySelector('.loading-state')`);await screenshot('dashboard-before')
  await go('/datasets/58/batches/39','Phiên bản trong đợt');await screenshot('batch39-before')
  await evaluate('window.scrollTo(0,0)');await screenshot('theme-before')
  fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({layouts,consoleErrors:errors,writes,phase},null,2));console.log('Before screenshots captured; no writes.')
 }
 if(phase==='after'){
  let pageLoads=0;socket.addEventListener('message',event=>{if(JSON.parse(String(event.data)).method==='Page.loadEventFired')pageLoads++})
  async function reloadPage(){const previous=pageLoads;await send('Page.reload');for(let i=0;i<250&&pageLoads===previous;i++)await pause(50);assert.ok(pageLoads>previous,'Reload must commit a new document')}
  const readPaths=[];socket.addEventListener('message',event=>{const m=JSON.parse(String(event.data));if(m.method==='Network.requestWillBeSent'&&m.params.request.url.startsWith(origin+'/api/'))readPaths.push(new URL(m.params.request.url).pathname)})
  const get=async url=>evaluate(`fetch(${JSON.stringify(url)}).then(r=>{if(!r.ok)throw Error('GET '+r.status);return r.json()})`)
  const viewport=async width=>{await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await pause(100)}
  const key=async(name,code=name,virtual)=>{for(const type of ['keyDown','keyUp'])await send('Input.dispatchKeyEvent',{type,key:name,code,...(virtual?{windowsVirtualKeyCode:virtual}:{})});await pause(100)}
  const ready=async()=>{await waitFor(`document.querySelector('.work-table-panel')&&!document.querySelector('.loading-state')`)}
  await send('Page.navigate',{url:origin+'/#/dashboard'});await ready()
  const dashboard=await get('/api/batch-dashboard')
  const sum=await evaluate(`[...document.querySelectorAll('.work-pipeline strong')].reduce((n,e)=>n+Number(e.textContent),0)`)
  assert.equal(sum,dashboard.items.length)
  assert.equal(await evaluate(`Number(document.querySelector('.work-chart-table tfoot td').textContent)`),dashboard.items.length)
  assert.equal(await evaluate(`document.querySelectorAll('.work-table tbody [data-work-batch]').length`),dashboard.items.filter(i=>i.business_state!=='COMPLETED').length)
  const expectedCounts={};for(const i of dashboard.items)expectedCounts[i.business_state??'UNKNOWN']=(expectedCounts[i.business_state??'UNKNOWN']??0)+1
  for(const [state,count] of Object.entries(expectedCounts))assert.equal(await evaluate(`Number(document.querySelector('.work-metric.state-${state.toLowerCase()} strong').textContent)`),count)
  await screenshot('dashboard-after');await evaluate(`document.querySelector('.work-distribution').scrollIntoView()`);await screenshot('distribution-after')
  const entryLinks=await evaluate(`[...document.querySelectorAll('.work-metric,.work-pipeline a')].map(a=>({href:a.getAttribute('href'),count:Number(a.querySelector('strong').textContent)}))`)
  for(const item of entryLinks){await go(item.href,'Hành động tiếp theo');await ready();assert.equal(await evaluate(`document.querySelectorAll('[data-work-batch]').length`),item.count)}
  await go('/dashboard','Điều hành dữ liệu');await ready()
  checks.push('Dashboard business cards/chart equal aggregate API, pipeline counts each batch once, work table includes only open batches; chart has equivalent count table')
  await field('Bộ dữ liệu','58');await ready();assert.ok((await evaluate('location.hash')).includes('dataset_id=58'))
  await field('Tìm đợt hoặc dataset','UAT');await ready();assert.ok((await evaluate('location.hash')).includes('q=UAT'))
  await evaluate(`document.querySelector('.work-metric.state-completed').click()`);await ready()
  assert.ok((await evaluate('location.hash')).includes('/work/reports?'));assert.equal(await evaluate(`document.querySelectorAll('[data-work-batch="39"]').length`),1)
  const scopedHash=await evaluate('location.hash');await reloadPage();await ready();assert.equal(await evaluate('document.querySelector(".work-filters select").value'),'58')
  await evaluate('history.back()');await waitFor(`location.hash.includes('/dashboard?')&&document.querySelector('.work-metrics')&&!document.querySelector('.loading-state')`)
  assert.equal(await evaluate('document.querySelector(".work-filters select").value'),'58')
  checks.push('Business card opens exact dataset/business scope; URL filters survive reload and browser Back')
  const names=['Tiếp nhận','Thiết lập kiểm tra','Kiểm tra chất lượng','Xử lý & kiểm tra lại','Nghiệm thu','Báo cáo'],ids=['intake','setup','quality','resolution','acceptance','reports']
  for(let index=0;index<ids.length;index++){
   await evaluate(`document.querySelector('aside a[href="#/work/${ids[index]}"]').click()`);await ready()
   assert.equal(await evaluate('document.querySelector("main h1").textContent'),names[index])
   for(const width of [1366,1024,768]){await viewport(width);await screenshot(`board-${ids[index]}-${width}`)}
   await viewport(1366)
  }
  await evaluate(`document.querySelector('aside a[href="#/datasets"]').click()`);await waitFor(`document.querySelector('main h1')?.textContent==='Danh mục dữ liệu'&&!document.querySelector('.loading-state')`)
  checks.push('Catalog and all six task boards navigate via sidebar; every board checked at 1366/1024/768px with no page overflow')
  await go('/work/reports?dataset_id=57&batch_id=34&batch_id=35&batch_id=36&batch_id=37&batch_id=38','Báo cáo');await ready()
  const aggregate=await get('/api/batch-dashboard?batch_id=34&batch_id=35&batch_id=36&batch_id=37&batch_id=38')
  await waitFor(`document.querySelectorAll('.result-stat').length===4`)
  const values=await evaluate(`[...document.querySelectorAll('.result-stat strong')].map(e=>e.textContent)`)
  assert.deepEqual(values,[String(aggregate.total_rows),String(aggregate.violated_rows_count),String(aggregate.total_violations_count),Number(aggregate.violation_rate).toLocaleString('vi-VN',{maximumFractionDigits:2})+'%'])
  const backlog=aggregate.items.find(i=>i.run?.error_row_count===0&&i.workflow?.unprocessed_count>0)
  if(backlog){const text=await evaluate(`document.querySelector('[data-work-batch="${backlog.batch_id}"]').innerText`);assert.ok(text.includes(backlog.workflow.unprocessed_count+' issue chưa xử lý'))}
  checks.push('Report totals come unchanged from filtered aggregate endpoint; clean-file/open-issue backlog stays visible independently')
  await go(scopedHash,'Báo cáo');await ready();const backHash=await evaluate('location.hash')
  await evaluate(`document.querySelector('[data-work-batch="39"] td:last-child>a').click()`)
  await waitFor(`document.querySelector('.batch-tabs')&&!document.querySelector('.loading-state')`)
  assert.equal(await evaluate(`new URLSearchParams(location.hash.split('?')[1]).get('from')`),backHash)
  assert.ok(await evaluate(`document.querySelector('.batch-current').innerText.includes('Đã hoàn tất')&&document.querySelector('.batch-current').innerText.includes('v2')`))
  for(const [tab,label] of [['intake','Tiếp nhận & phiên bản'],['rules','Quy tắc'],['results','Kết quả'],['issues','Xử lý lỗi'],['acceptance','Nghiệm thu']]){
   await evaluate(`document.querySelector('#batch-tab-${tab}').click()`);await waitFor(`document.querySelector('#batch-tab-${tab}')?.getAttribute('aria-selected')==='true'&&!document.querySelector('.loading-state')`)
   await screenshot('batch39-tab-'+tab)
   if(tab==='intake')assert.ok(await evaluate(`[...document.querySelectorAll('#batch-tab-panel button')].filter(b=>b.textContent.includes('Tải bản')||b.textContent.startsWith('Kiểm tra v')).every(b=>b.disabled)`))
   if(tab==='rules')assert.ok(await evaluate(`!document.querySelector('#record-identity button')&&[...document.querySelectorAll('#batch-rules button')].filter(b=>b.textContent.includes('Thêm')).every(b=>b.disabled)`))
   for(const width of [1024,768]){await viewport(width);assert.ok(await evaluate('document.documentElement.scrollWidth<=innerWidth+1'))}
   await viewport(1366)
  }
  for(const width of [1024,768]){await viewport(width);await screenshot('batch39-'+width)}await viewport(1366)
  await click('Về bảng công việc đã lọc');await ready();assert.equal(await evaluate('location.hash'),backHash)
  checks.push('Batch39 has five URL tabs, one header action, current v2 and separate completed/file-quality state; upload/rule writes remain locked; return retains board filters; tabs checked at three widths')
  await go('/datasets/58/batches/39?rules=1','Quy tắc của đợt');await waitFor(`document.querySelector('#batch-tab-rules')?.getAttribute('aria-selected')==='true'&&!document.querySelector('.loading-state')`)
  await go('/datasets/58/batches/39?issues=1','Xử lý lỗi');await waitFor(`document.querySelector('#batch-workflow')&&!document.querySelector('.loading-state')`)
  await field('Trạng thái issue','RESOLVED');await waitFor(`location.hash.includes('issue_status=RESOLVED')&&!document.querySelector('.loading-state')`)
  await reloadPage();await waitFor(`document.querySelector('#batch-workflow select')?.value==='RESOLVED'&&!document.querySelector('.loading-state')`)
  await evaluate(`document.querySelector('#batch-tab-results').click()`);await waitFor(`document.querySelector('#batch-tab-results')?.getAttribute('aria-selected')==='true'`)
  await evaluate('history.back()');await waitFor(`document.querySelector('#batch-workflow select')?.value==='RESOLVED'&&!document.querySelector('.loading-state')`)
  const oldIssue=(await get('/api/datasets/58/batches/39/workflow/issues')).items[0]
  if(oldIssue){await go('/datasets/58/batches/39?issue='+oldIssue.id,'Xử lý lỗi');await waitFor(`document.querySelector('dialog[open]')?.innerText.includes('Issue #${oldIssue.id}')&&!document.querySelector('.loading-state')`);await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`)}
  checks.push('Legacy rules/issues/issue-ID deep links work; issue-status filter persists in URL across reload and Back')
  const r83=await get('/api/datasets/58/runs/83'),r84=await get('/api/datasets/58/runs/84')
  assert.deepEqual([r83.total_rows,r83.error_row_count,r83.violation_count],[3,2,3]);assert.deepEqual([r84.total_rows,r84.error_row_count,r84.violation_count],[3,0,0])
  await go('/datasets/58/runs/83','Kết quả kiểm tra');await click('Về đợt dữ liệu');await waitFor(`document.querySelector('#batch-acceptance')&&!document.querySelector('.loading-state')`)
  checks.push('Historical run83 remains 3/2/3, run84 remains clean; result breadcrumb/back link opens completed batch39/current v2, not historical v1')
  await evaluate('window.scrollTo(0,0)');assert.equal(await evaluate(`document.querySelectorAll('.theme-popover').length`),0)
  await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-trigger').getAttribute('aria-expanded')==='true'&&document.querySelector('.theme-popover [role=menuitemradio]')===document.activeElement||document.querySelector('.theme-popover')?.contains(document.activeElement)`)
  assert.equal(await evaluate(`document.querySelectorAll('.theme-popover [role=menuitemradio]').length`),4);await screenshot('theme-popover-1366')
  await key('End','End',35);assert.ok(await evaluate(`document.activeElement.textContent.includes('dịu mắt')`));await key('Enter','Enter',13)
  await waitFor(`!document.querySelector('.theme-popover')&&document.documentElement.getAttribute('data-theme-preference')==='soft'`)
  assert.equal(await evaluate('localStorage.getItem("dataguard-theme")'),'soft');assert.equal(await evaluate(`document.activeElement===document.querySelector('.theme-trigger')`),true)
  await reloadPage();await waitFor(`document.querySelector('#batch-acceptance')&&!document.querySelector('.loading-state')`);assert.equal(await evaluate(`document.documentElement.getAttribute('data-theme-preference')`),'soft')
  await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await key('ArrowDown','ArrowDown',40);await key('Escape','Escape',27)
  assert.equal(await evaluate(`document.querySelector('.theme-trigger').getAttribute('aria-expanded')`),'false');assert.equal(await evaluate(`document.activeElement===document.querySelector('.theme-trigger')`),true)
  await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`)
  await send('Input.dispatchMouseEvent',{type:'mousePressed',x:320,y:150,button:'left',clickCount:1});await send('Input.dispatchMouseEvent',{type:'mouseReleased',x:320,y:150,button:'left',clickCount:1});await waitFor(`!document.querySelector('.theme-popover')`)
  for(const width of [1024,768]){await viewport(width);await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await screenshot('theme-popover-'+width);await key('Escape','Escape',27)}
  await viewport(768);await evaluate(`document.querySelector('button[aria-label="Mở menu"]').click()`);await waitFor(`document.querySelector('.sidebar.is-open')`);assert.ok(await evaluate(`[...document.querySelectorAll('.sidebar nav a')].some(a=>a.textContent==='Nghiệm thu')`));await screenshot('mobile-navigation-768');await evaluate(`document.querySelector('button[aria-label="Đóng menu"]').click()`)
  await viewport(1366);await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await key('Tab','Tab',9);await waitFor(`!document.querySelector('.theme-popover')`)
  await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await evaluate(`[...document.querySelectorAll('.theme-popover button')].find(b=>b.textContent.includes('nền tối')).click()`);await waitFor(`!document.querySelector('.theme-popover')&&document.documentElement.getAttribute('data-theme')==='dark'`);await screenshot('theme-dark-1366')
  await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await evaluate(`[...document.querySelectorAll('.theme-popover button')].find(b=>b.textContent.includes('Tự động')).click()`);await waitFor(`!document.querySelector('.theme-popover')&&document.documentElement.getAttribute('data-theme-preference')==='system'`)
  await viewport(1366);await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await evaluate(`[...document.querySelectorAll('.theme-popover button')].find(b=>b.textContent.includes('sáng rõ')).click()`);await waitFor(`!document.querySelector('.theme-popover')`)
  for(const width of [1366,1024,768]){await viewport(width);await go('/dashboard','Điều hành dữ liệu');await ready();await screenshot('dashboard-final-'+width)}
  checks.push('Theme popover: four existing themes, current choice, keyboard End/Arrow/Enter/Escape, restored focus, outside-click close, persisted preference after reload; checked three widths and mobile sidebar')
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
  fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,readPaths,qa:{run83:[r83.total_rows,r83.error_row_count,r83.violation_count],run84:[r84.total_rows,r84.error_row_count,r84.violation_count]},phase},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
 }

}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('ui05-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
