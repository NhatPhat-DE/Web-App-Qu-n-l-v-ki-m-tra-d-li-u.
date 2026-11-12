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
const out=path.resolve('test-artifacts/demo-ui-'+phase);fs.mkdirSync(out,{recursive:true})

const browserPath=['C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',path.join(process.env.LOCALAPPDATA??'','ms-playwright/chromium-1248/chrome-win64/chrome.exe')].find(fs.existsSync)
assert.ok(browserPath,'Installed Chromium required')
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'demo-ui-browser-'))
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
  const reference='file:///'+path.resolve('..','.runtime','demo-reference.html').replaceAll('\\','/')
  await send('Page.navigate',{url:reference});await pause(2000)
  await waitFor(`document.body.innerText.includes('Dashboard chất lượng dữ liệu vận hành')`)
  const layout=await send('Page.getLayoutMetrics');const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1366,height:Math.min(layout.cssContentSize.height,2200),scale:1}})
  fs.writeFileSync(path.join(out,'demo-reference.png'),Buffer.from(shot.data,'base64'))
  fs.writeFileSync(path.join(out,'demo-dom.txt'),await evaluate('document.body.innerText'))
  await send('Page.navigate',{url:origin+'/#/dashboard'});await waitFor(`document.querySelector('.work-metrics')&&!document.querySelector('.loading-state')`);await screenshot('product-before-dashboard')
  await go('/datasets/58/batches/39','Nghiệm thu');await screenshot('product-before-batch')
  console.log('Demo reference and current UI captured.')
 }
 if(phase==='preview'){
  await send('Page.navigate',{url:origin+'/#/dashboard'});await waitFor(`document.querySelector('.demo-tiles')&&!document.querySelector('.loading-state')`);await pause(300)
  const metrics=await send('Page.getLayoutMetrics');const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1366,height:Math.min(metrics.cssContentSize.height,2400),scale:1}});fs.writeFileSync(path.join(out,'dashboard-preview.png'),Buffer.from(shot.data,'base64'));console.log('Product preview captured.')
 }
 if(phase==='after'){
  let loads=0,acceptDialog=true;const dialogs=[]
  socket.addEventListener('message',async event=>{const m=JSON.parse(String(event.data));if(m.method==='Page.loadEventFired')loads++;if(m.method==='Page.javascriptDialogOpening'){dialogs.push(m.params.message);await send('Page.handleJavaScriptDialog',{accept:acceptDialog})}})
  async function reload(){const previous=loads;await send('Page.reload');for(let i=0;i<250&&loads===previous;i++)await pause(50);assert.ok(loads>previous)}
  const get=async url=>evaluate(`fetch(${JSON.stringify(url)}).then(r=>{if(!r.ok)throw Error('GET '+r.status);return r.json()})`)
  const ready=async selector=>waitFor(`${JSON.stringify(selector)}&&document.querySelector(${JSON.stringify(selector)})&&!document.querySelector('.loading-state')`)
  const viewport=async width=>{await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});await pause(120)}
  async function fullScreenshot(label){await pause(150);const layout=await send('Page.getLayoutMetrics'),size=await evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');assert.ok(size.scroll<=size.width+1,label+': page overflow');layouts.push({label,...size});const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:size.width,height:Math.min(layout.cssContentSize.height,2400),scale:1}});fs.writeFileSync(path.join(out,label+'.png'),Buffer.from(shot.data,'base64'))}
  async function key(value,virtual){for(const type of ['keyDown','keyUp'])await send('Input.dispatchKeyEvent',{type,key:value,windowsVirtualKeyCode:virtual});await pause(100)}
  await send('Page.navigate',{url:origin+'/#/dashboard'});await ready('.demo-tiles');await waitFor(`[...document.querySelectorAll('.demo-source-card strong')].every(e=>e.textContent!=='—')`)
  const data=await get('/api/batch-dashboard'),dataset58=await get('/api/datasets/58')
  const kpis=await evaluate(`[...document.querySelectorAll('.demo-kpi>strong')].map(e=>e.textContent)`)
  assert.equal(kpis[0],Number(data.violation_rate).toLocaleString('vi-VN',{maximumFractionDigits:2})+'%');assert.equal(kpis[1],String(data.total_violations_count))
  assert.equal(kpis[2],String(data.items.filter(i=>i.workflow?.enabled).reduce((n,i)=>n+i.workflow.unprocessed_count,0)))
  assert.equal(await evaluate(`document.querySelectorAll('.demo-tile').length`),data.items.length)
  const tokens=await evaluate(`(()=>{const sidebar=getComputedStyle(document.querySelector('.sidebar')),main=getComputedStyle(document.querySelector('.main-content'));return {sidebar:sidebar.width,bg:sidebar.backgroundColor,padding:main.paddingLeft,font:getComputedStyle(document.body).fontFamily,title:getComputedStyle(document.querySelector('main h1')).fontSize,page:getComputedStyle(document.documentElement).getPropertyValue('--bg-app').trim(),primary:getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()}})()`)
  assert.equal(tokens.sidebar,'232px');assert.equal(tokens.bg,'rgb(15, 39, 71)');assert.equal(tokens.padding,'28px');assert.equal(tokens.title,'22px');assert.ok(tokens.font.includes('Inter'));assert.equal(tokens.page.toUpperCase(),'#F4F6F9');assert.equal(tokens.primary.toUpperCase(),'#1D4ED8')
  const sum=await evaluate(`[...document.querySelectorAll('.demo-chart-answer tbody td')].reduce((n,e)=>n+Number(e.textContent),0)`);assert.equal(sum,data.items.length)
  await fullScreenshot('dashboard-1366')
  checks.push('Demo fidelity: 232px navy #0F2747 sidebar, #F4F6F9 background, blue #1D4ED8, bundled Inter, 22px title/28px gutter; KPI and heatmap counts match aggregate API with no demo numbers')
  await field('Loại dữ liệu','58');await ready('.demo-tiles');await field('Kỳ dữ liệu','11/2026');await ready('.demo-tiles');await field('Nguồn dữ liệu',dataset58.source||'__none__');await ready('.demo-tiles')
  assert.equal(await evaluate(`document.querySelectorAll('.demo-tile').length`),1);await waitFor(`document.querySelector('.demo-kpi>strong')?.textContent==='0%'`)
  const scopeHash=await evaluate('location.hash');await reload();await ready('.demo-tiles');assert.equal(await evaluate('location.hash'),scopeHash)
  await evaluate(`document.querySelector('.demo-tile').click()`);await ready('.batch-tabs');assert.ok(await evaluate(`document.querySelector('.batch-current').innerText.includes('Đã hoàn tất')`))
  assert.equal(await evaluate(`new URLSearchParams(location.hash.split('?')[1]).get('from')`),scopeHash)
  await evaluate('history.back()');await ready('.demo-tiles');assert.equal(await evaluate('location.hash'),scopeHash)
  checks.push('Dataset/source/period scope is real, survives reload/Back; tile opens exact batch39 and preserves return scope')
  const pages=[['/datasets','Danh mục & Từ điển dữ liệu','.catalog-content'],['/rules?dataset_id=58&batch_id=39','Quy tắc kiểm tra','.screen-rules'],['/submit','Nộp & Kiểm tra','.screen-submit table'],['/issues?dataset_id=57&batch_id=36','Quản lý lỗi','#batch-workflow'],['/compare?dataset_id=58&batch_id=39&a=83&b=84','Đối soát phiên bản','.comparison-picks'],['/reporting?dataset_id=58&batch_id=39&run_id=83','Báo cáo chất lượng dữ liệu','.screen-reports'],['/accounts','Quản trị','main table']]
  for(const [pathName,title,selector] of pages){await go(pathName,title);await ready(selector);for(const width of [1366,1024,768]){await viewport(width);await screenshot(pathName.split('?')[0].slice(1)+'-'+width)}await viewport(1366)}
  checks.push('Distinct Catalog, Rules, Submit, Issues, Compare, Reports and Admin screens render at 1366/1024/768 without page overflow, sharing reference typography/cards/tables')
  await go('/datasets?view=dictionary&dataset_id=58','Từ điển dữ liệu');await ready('.dictionary-content table');await field('Phiên bản xem suy luận','87');await ready('.dictionary-content table');await reload();await ready('.dictionary-content table')
  assert.equal(await evaluate(`[...document.querySelectorAll('label')].find(l=>l.textContent.includes('Phiên bản xem suy luận')).querySelector('select').value`),'87');await screenshot('dictionary-1366')
  await go('/datasets','Danh mục & Từ điển dữ liệu');await ready('.catalog-content');const search=await evaluate(`document.querySelector('.catalog-content input[type=search]').outerHTML`)
  await setValue('.catalog-content input[type=search]','QA UAT');await waitFor(`location.hash.includes('catalog_q=')&&!document.querySelector('.loading-state')`);await reload();await ready('.catalog-content');assert.equal(await evaluate(`document.querySelector('.catalog-content input[type=search]').value`),'QA UAT')
  await go('/rules?dataset_id=58&batch_id=39','Quy tắc kiểm tra');await ready('.screen-rules table');const rules=await get('/api/datasets/58/batches/39/rules?page=1&page_size=100');await field('Tìm quy tắc',rules.items[0].name);await waitFor(`location.hash.includes('rule_q=')&&!document.querySelector('.loading-state')`);await reload();await ready('.screen-rules table');assert.equal(await evaluate(`document.querySelector('input[type=search]').value`),rules.items[0].name)
  assert.ok(await evaluate(`[...document.querySelectorAll('.screen-rules button')].filter(b=>b.textContent.includes('Thêm quy tắc')).every(b=>b.disabled)`))
  checks.push('Catalog search, dictionary version and rule search persist in URL/reload; completed batch39 rule writes stay locked')
  await go('/submit?dataset_id=58','Nộp & Kiểm tra');await ready('.screen-submit table');assert.equal(await evaluate(`document.querySelectorAll('[data-batch-row="39"]').length`),1)
  await click('Tiếp nhận đợt mới');await ready('dialog[open]');await field('Nguồn trong danh mục',dataset58.source||'__none__','document.querySelector("dialog[open]")');await field('Loại dữ liệu có sẵn','58','document.querySelector("dialog[open]")');await field('Kỳ tiếp nhận','12/2026','document.querySelector("dialog[open]")');await screenshot('create-batch-one-step')
  acceptDialog=false;await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);await pause(100);assert.equal(await evaluate(`document.querySelector('dialog[open] input[placeholder="Ví dụ: 11/2026"]').value`),'12/2026')
  acceptDialog=true;await evaluate(`document.querySelector('dialog[open] button[aria-label="Đóng"]').click()`);await waitFor(`!document.querySelector('dialog[open]')`)
  await evaluate(`document.querySelector('[data-batch-row="39"] td:last-child a').click()`);await ready('.batch-tabs');assert.ok(await evaluate(`[...document.querySelectorAll('#batch-tab-panel button')].filter(b=>b.textContent.includes('Tải bản')||b.textContent.startsWith('Kiểm tra v')).every(b=>b.disabled)`))
  checks.push('Submit opens batch list directly; one-step source/catalog/period creation form keeps draft on Cancel and sends no write; upload/recheck remains locked on completed batch39')
  await go('/issues?dataset_id=57&batch_id=36','Quản lý lỗi');await ready('#batch-workflow');assert.ok(await evaluate(`document.querySelector('#batch-workflow').innerText.includes('Có bản ghi thiếu khóa')`));await field('Trạng thái issue','OPEN');await ready('#batch-workflow');await reload();await ready('#batch-workflow');assert.equal(await evaluate(`document.querySelector('#batch-workflow select').value`),'OPEN')
  await go('/compare?dataset_id=57&a=73&b=74','Đối soát phiên bản');await ready('.comparison-picks');assert.ok(await evaluate(`document.querySelector('main').innerText.includes('Không áp dụng')`))
  await go('/compare?dataset_id=58&batch_id=39&a=83&b=84','Đối soát phiên bản');await ready('.comparison-picks');const comparison=await get('/api/datasets/58/run-comparison?a_run_id=83&b_run_id=84');assert.equal(comparison.comparable,true)
  await go('/reporting?dataset_id=58&batch_id=39&run_id=83','Báo cáo chất lượng dữ liệu');await ready('.screen-reports');await field('Lần kiểm tra cần xuất','83');await reload();await ready('.screen-reports');assert.ok(await evaluate(`document.querySelector('.screen-reports').innerText.includes('3 bản ghi · 2 dòng lỗi · 3 lượt vi phạm')`))
  checks.push('Issue backlog/unknown and filters preserved; different-condition compare keeps Not applicable; same-condition 83→84 uses API delta; report selects historical run83 snapshot via URL')
  for(const url of ['/work/intake?dataset_id=58','/work/quality?dataset_id=58','/work/setup?dataset_id=58&batch_id=39','/work/resolution?dataset_id=58&batch_id=39','/work/acceptance?dataset_id=58&batch_id=39','/work/reports?dataset_id=58&batch_id=39']){await go(url,url.includes('intake')||url.includes('quality')?'Nộp & Kiểm tra':url.includes('setup')?'Quy tắc kiểm tra':url.includes('reports')?'Báo cáo chất lượng dữ liệu':'Quản lý lỗi');await waitFor(`document.querySelector('main h1')&&!document.querySelector('.loading-state')`)}
  for(const suffix of ['?rules=1','?issues=1']){await go('/datasets/58/batches/39'+suffix,'Khách hàng');await ready('.batch-tabs');assert.equal(await evaluate(`document.querySelector('.batch-tabs [aria-selected=true]').id`),suffix.includes('rules')?'batch-tab-rules':'batch-tab-issues')}
  const r83=await get('/api/datasets/58/runs/83'),r84=await get('/api/datasets/58/runs/84');assert.deepEqual([r83.total_rows,r83.error_row_count,r83.violation_count],[3,2,3]);assert.deepEqual([r84.total_rows,r84.error_row_count,r84.violation_count],[3,0,0]);assert.equal((await get('/api/datasets/58/batches/39')).business_state,'COMPLETED')
  checks.push('All legacy work routes and old batch deep links remain usable; QA39 completed, run83=3/2/3 and run84=3/0/0 unchanged')
  await go('/dashboard','Dashboard chất lượng dữ liệu vận hành');await ready('.demo-tiles');await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await key('End',35);await key('Enter',13);await waitFor(`!document.querySelector('.theme-popover')&&document.documentElement.getAttribute('data-theme-preference')==='soft'`)
  assert.equal(await evaluate(`document.activeElement===document.querySelector('.theme-trigger')`),true);await reload();await ready('.demo-tiles');assert.equal(await evaluate(`localStorage.getItem('dataguard-theme')`),'soft')
  await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await key('Escape',27);assert.equal(await evaluate(`document.querySelector('.theme-trigger').getAttribute('aria-expanded')`),'false')
  await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await evaluate(`[...document.querySelectorAll('.theme-popover button')].find(b=>b.textContent.includes('sáng rõ')).click()`);await waitFor(`!document.querySelector('.theme-popover')`)
  for(const width of [1366,1024,768]){await viewport(width);await fullScreenshot('dashboard-final-'+width);await evaluate(`document.querySelector('.theme-trigger').click()`);await waitFor(`document.querySelector('.theme-popover')`);await screenshot('theme-popover-'+width);await key('Escape',27)}
  await viewport(768);await evaluate(`document.querySelector('button[aria-label="Mở menu"]').click()`);await waitFor(`document.querySelector('.sidebar.is-open')`);await screenshot('navigation-768');await evaluate(`document.querySelector('button[aria-label="Đóng menu"]').click()`)
  checks.push('Theme popover retains preferences, keyboard End/Enter/Escape and focus; responsive menu and final Dashboard/graphs checked at 1366/1024/768')
  assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
  fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes,dialogs,tokens,qa:{run83:[3,2,3],run84:[3,0,0],batch39:'COMPLETED'},phase},null,2));console.log(JSON.stringify({passed:checks.length,screenshots:layouts.length,checks}))
 }

}catch(error){try{await screenshot('failure');fs.writeFileSync(path.join(out,'failure.txt'),String(error)+'\n'+await evaluate('document.body.innerText'))}catch{}throw error}
finally{for(const p of pending.values()){clearTimeout(p.timer);p.reject(Error('Browser closed'))}socket?.close();browser.kill();await Promise.race([once(browser,'exit').catch(()=>{}),pause(3000)]);try{const resolvedProfile=path.resolve(profile),tempRoot=path.resolve(os.tmpdir())+path.sep;assert.ok(resolvedProfile.startsWith(tempRoot)&&path.basename(resolvedProfile).startsWith('demo-ui-browser-'));fs.rmSync(resolvedProfile,{recursive:true,force:true})}catch{}}
