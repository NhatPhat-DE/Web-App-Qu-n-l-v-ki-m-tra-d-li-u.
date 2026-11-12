import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const js=stripTypeScriptTypes(fs.readFileSync('src/workspace/demoUxState.ts','utf8'))
const {runWorkflowMessage,canSuggestCorrection,errorRowDelta,correctionHref}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))
const workflow={enabled:true,reconciliations:[{id:19,run_id:86,eligible:true,result:'RECHECK'}]}

test('clean run86 uses its reconciliation evidence even with no violation links',()=>{
 assert.equal(runWorkflowMessage(86,0,0,workflow),'Lần kiểm tra này không có vi phạm để liên kết. Đã đối soát #19 cho lần kiểm tra này.')
 assert.ok(!runWorkflowMessage(85,3,0,workflow).includes('#19'))
 assert.ok(runWorkflowMessage(85,3,0,workflow).includes('Chưa thấy bằng chứng'))
 assert.equal(runWorkflowMessage(85,3,3,workflow),'')
 assert.ok(runWorkflowMessage(86,0,0,{enabled:false,reconciliations:[]}).includes('Đợt chưa bật'))
})
test('ineligible and historical reconciliation are not presented as successful resolution',()=>{
 for(const [result,eligible,label] of [['RECHECK',false,'chưa đủ điều kiện'],['HISTORICAL',true,'đối soát lịch sử']]){
  assert.ok(runWorkflowMessage(86,0,0,{enabled:true,reconciliations:[{run_id:86,id:19,result,eligible}]}).includes(label))
 }
})
test('correction CTA requires current file errors, never just uncertain identity or config',()=>{
 assert.equal(canSuggestCorrection('HAS_ERRORS',false,false),true)
 for(const q of ['PASSED','STALE','UNCHECKED','RUNNING','FAILED','NO_FILE'])assert.equal(canSuggestCorrection(q,false,false),false)
 assert.equal(canSuggestCorrection('HAS_ERRORS',true,false),false)
 assert.equal(canSuggestCorrection('HAS_ERRORS',false,true),false)
})
test('Dashboard delta carries row units and respects API comparability',()=>{
 assert.equal(errorRowDelta(true,-2),'-2 dòng')
 assert.equal(errorRowDelta(true,2),'+2 dòng')
 assert.equal(errorRowDelta(true,0),'0 dòng')
 assert.equal(errorRowDelta(false,-2),'Không áp dụng')
 assert.equal(errorRowDelta(true,null),'Không áp dụng')
})
test('upload intent preserves issue filters and return scope on the same batch or a work list',()=>{
 const back='#/dashboard?dataset_id=57&batch_id=40'
 const same=correctionHref(57,40,'#/datasets/57/batches/40?tab=issues&issue_status=OPEN&from='+encodeURIComponent(back))
 const query=new URLSearchParams(same.split('?')[1])
 assert.equal(query.get('issue_status'),'OPEN');assert.equal(query.get('from'),back)
 assert.equal(query.get('tab'),'issues');assert.equal(query.get('upload'),'1')
 const list='#/issues?dataset_id=57&batch_id=40&issue_status=OPEN'
 assert.equal(new URLSearchParams(correctionHref(57,40,list).split('?')[1]).get('from'),list)
})
