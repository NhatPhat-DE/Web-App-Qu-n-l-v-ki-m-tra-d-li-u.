import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const url=source=>'data:text/javascript;base64,'+Buffer.from(stripTypeScriptTypes(source)).toString('base64')
const model=url(fs.readFileSync('src/workspace/workModel.ts','utf8'))
const {qualityBucket,qualityCounts,trackedIssues}=await import(url(fs.readFileSync('src/workspace/demoDashboardModel.ts','utf8').replaceAll("'./workModel'",JSON.stringify(model))))
const {operationalItems,scopeHref}=await import(url(fs.readFileSync('src/workspace/operationalModel.ts','utf8').replaceAll("'./workModel'",JSON.stringify(model))))
const base={batch_id:39,dataset_id:58,dataset_name:'QA UAT',batch_name:'Tháng 11',period_label:'11/2026',business_state:'COMPLETED',active_rule_count:2,rules_revision:1,status:'PASSED',rules_changed:false,current_version:{id:88,version_number:2,row_count:3},run:{id:84,total_rows:3,error_row_count:0,violation_count:0},workflow:{enabled:true,unprocessed_count:0,uncertain_count:0,ignored_count:0,completion_blockers:[]}}

test('Demo heatmap uses real quality states; never labels an old/running/failed result clean',()=>{
 const items=[base,{...base,status:'STALE',rules_changed:true},{...base,status:'RUNNING'},{...base,status:'FAILED'},{...base,run:null,status:'UNCHECKED'},{...base,current_version:null,run:null,status:'NO_FILE'},{...base,status:'HAS_ERRORS',run:{...base.run,error_row_count:2,violation_count:3}}]
 assert.deepEqual(items.map(qualityBucket),['PASSED','STALE','WAITING','WAITING','WAITING','WAITING','HAS_ERRORS'])
 assert.equal(qualityCounts(items).reduce((n,g)=>n+g.count,0),items.length)
 assert.deepEqual(qualityCounts(items).map(g=>g.count),[1,1,1,4])
})
test('Issue KPI counts tracked records only; unknown is a subset, not another violation total',()=>{
 const items=[base,{...base,workflow:{...base.workflow,unprocessed_count:3,uncertain_count:3,ignored_count:1}},{...base,workflow:{...base.workflow,enabled:false,unprocessed_count:99,uncertain_count:99}}]
 assert.deepEqual(trackedIssues(items),{tracked:2,unprocessed:3,uncertain:3,ignored:1})
})
test('Source, period, historical batch filters and waiting cohorts preserve exact URL scope',()=>{
 const items=[base,{...base,batch_id:40,dataset_id:59,period_label:'10/2026',status:'STALE'},{...base,batch_id:41,dataset_id:59,status:'UNCHECKED',run:null}]
 const datasets=[{id:58,source:'Nguồn A'},{id:59,source:'Nguồn B'}]
 assert.deepEqual(operationalItems(items,datasets,new URLSearchParams('source=Nguồn A&period=11%2F2026')), [base])
 assert.deepEqual(operationalItems(items,datasets,new URLSearchParams('quality=WAITING')).map(i=>i.batch_id),[41])
 assert.deepEqual(operationalItems(items,datasets,new URLSearchParams('batch_id=39&batch_id=40')).map(i=>i.batch_id),[39,40])
 assert.equal(operationalItems(items,datasets,new URLSearchParams('source=missing')).length,0)
 const href=scopeHref('submit',new URLSearchParams('source=Nguồn A&period=11%2F2026&dataset_id=58'),{batch_id:'39'})
 const query=new URLSearchParams(href.split('?')[1]);assert.equal(query.get('source'),'Nguồn A');assert.equal(query.get('period'),'11/2026');assert.equal(query.get('batch_id'),'39')
})
