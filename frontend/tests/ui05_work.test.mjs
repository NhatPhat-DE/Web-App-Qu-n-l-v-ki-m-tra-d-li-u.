import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const code=stripTypeScriptTypes(fs.readFileSync('src/workspace/workModel.ts','utf8'))
const {boards,qualityOf,primaryStep,needs,missingWork,filterWork,readWorkFilter,workHref,detailHref,requestedTab}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'))
const clean={batch_id:36,dataset_id:57,dataset_name:'QA dữ liệu',batch_name:'Kỳ thử',period_label:'11/2026',business_state:'PROCESSING',active_rule_count:2,rules_revision:1,status:'PASSED',rules_changed:false,current_version:{id:1,version_number:2,row_count:3},run:{id:73,total_rows:3,error_row_count:0,violation_count:0,batch_rules_revision:1},workflow:{enabled:true,unprocessed_count:3,uncertain_count:3,ignored_count:0,completion_blockers:['IDENTITY_MISSING','CURRENT_RECONCILIATION_REQUIRED']}}

test('UI-05 clean file with unbound issues remains work; each batch has exactly one priority',()=>{
 assert.equal(qualityOf(clean),'PASSED');assert.equal(primaryStep(clean),'resolution')
 assert.equal(needs(clean).resolution,true);assert.equal(needs(clean).intake,false)
 assert.ok(missingWork(clean).includes('3 issue chưa xử lý'))
 const items=[clean,{...clean,batch_id:39,business_state:'COMPLETED'},{...clean,batch_id:40,current_version:null,run:null},{...clean,batch_id:41,active_rule_count:0},{...clean,batch_id:42,status:'UNCHECKED',run:null}]
 const buckets=items.map(primaryStep)
 assert.deepEqual(buckets,['resolution','completed','intake','setup','quality'])
 assert.equal(buckets.length,items.length);assert.equal(needs(items[1]).intake,false);assert.equal(needs(items[1]).resolution,false)
 const waived={...clean,status:'HAS_ERRORS',run:{...clean.run,error_row_count:2,violation_count:3},workflow:{enabled:true,unprocessed_count:0,uncertain_count:0,ignored_count:3,completion_blockers:[]}}
 assert.equal(primaryStep(waived),'acceptance');assert.equal(needs(waived).intake,false);assert.equal(needs(waived).resolution,false)
 assert.equal(qualityOf(waived),'HAS_ERRORS')
})
test('UI-05 historical/configuration-old result is never a current pass; unfinished is explicit',()=>{
 assert.equal(qualityOf({...clean,status:'STALE',rules_changed:true}),'STALE')
 for(const status of ['FAILED','RUNNING'])assert.equal(qualityOf({...clean,status}),status)
 assert.equal(qualityOf({...clean,run:null,status:'NEEDS_RULES'}),'UNCHECKED')
 assert.equal(qualityOf({...clean,current_version:null}),'NO_FILE')
 assert.equal(primaryStep({...clean,workflow:undefined}),'unknown')
 assert.ok(missingWork({...clean,workflow:undefined}).includes('Chưa có thông tin xử lý lỗi'))
})
test('UI-05 task areas have their own routes, retain scope and allow overlap without duplicating the chart',()=>{
 assert.deepEqual(boards.map(b=>b.label),['Tiếp nhận','Thiết lập kiểm tra','Kiểm tra chất lượng','Xử lý & kiểm tra lại','Nghiệm thu','Báo cáo'])
 const q=new URLSearchParams('dataset_id=57&batch_id=36&batch_id=38&q=Kỳ&business=PROCESSING')
 const href=workHref('resolution',q,{primary:'resolution'})
 const parsed=readWorkFilter(new URLSearchParams(href.split('?')[1]))
 assert.deepEqual(parsed.batchIds,[36,38]);assert.deepEqual(filterWork([clean],parsed),[clean])
 assert.deepEqual(filterWork([clean],readWorkFilter(new URLSearchParams('batch_id=invalid'))),[])
 assert.deepEqual(filterWork([clean],readWorkFilter(new URLSearchParams('quality=STALE'))),[])
 const detail=detailHref(clean,'issues',href),params=new URLSearchParams(detail.split('?')[1])
 assert.equal(params.get('from'),href);assert.equal(params.get('tab'),'issues')
 assert.equal(new URLSearchParams(detailHref(clean,'issues','https://example.org').split('?')[1]).has('from'),false)
})
test('UI-05 old batch deep links resolve to the correct new tab',()=>{
 assert.equal(requestedTab(new URLSearchParams('rules=1')),'rules')
 assert.equal(requestedTab(new URLSearchParams('issues=1')),'issues')
 assert.equal(requestedTab(new URLSearchParams('issue=15')),'issues')
 assert.equal(requestedTab(new URLSearchParams('tab=acceptance&issues=1')),'acceptance')
 assert.equal(requestedTab(new URLSearchParams('tab=invalid')),undefined)
})
