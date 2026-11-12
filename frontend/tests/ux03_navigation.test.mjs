import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const source=stripTypeScriptTypes(fs.readFileSync('src/workspace/scopeNavigation.ts','utf8'))
const {queryBatch,runBatch,historyHref,globalHistoryHref,comparisonHref,comparisonScope}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const dataset={runs:[{run_id:59,version_id:1,batch_id:27},{run_id:60,version_id:2,batch_id:27},{run_id:57,version_id:3,batch_id:26},{run_id:58,version_id:4}],versions:[{id:1,batch_id:27},{id:2,batch_id:27},{id:3,batch_id:26},{id:4,batch_id:25}]}

test('UX-03 explicit scope URLs survive direct entry; old all-batch URLs stay unchanged',()=>{
 assert.equal(historyHref(52,27),'#/datasets/52/history?batch_id=27')
 assert.equal(historyHref(52),'#/datasets/52/history')
 assert.equal(comparisonHref(52,'27'),'#/datasets/52/compare?batch_id=27')
 assert.equal(comparisonHref(52,'all'),'#/datasets/52/compare?batch_id=all')
 assert.equal(comparisonHref(52,'27','2',59,60),'#/datasets/52/compare?batch_id=27&version_id=2&a=59&b=60')
})
test('UX-03 URL pairs define scope even when an incoming filter contradicts them',()=>{
 assert.equal(comparisonScope(dataset,new URLSearchParams('a=59&b=60&batch_id=26')),'27')
 assert.equal(comparisonScope(dataset,new URLSearchParams('a=59&b=57&batch_id=27')),'all')
 assert.equal(comparisonScope(dataset,new URLSearchParams('batch_id=27')),'27')
 assert.equal(comparisonScope(dataset,new URLSearchParams()),'')
 assert.equal(runBatch(dataset,58),25);assert.equal(runBatch(dataset,999),undefined)
})
test('UX-03 invalid batch IDs never silently become an all-batch scope',()=>{
 for(const raw of ['-1','0','abc','27.5','9007199254740992'])assert.equal(queryBatch(new URLSearchParams({batch_id:raw})),'invalid')
 assert.equal(queryBatch(new URLSearchParams('batch_id=all')),'all')
})
test('UX-03 global history keeps selected dataset and batch in shareable URLs',()=>{
 assert.equal(globalHistoryHref('52','27'),'#/history?dataset_id=52&batch_id=27')
 assert.equal(globalHistoryHref('52'),'#/history?dataset_id=52')
 assert.equal(globalHistoryHref(),'#/history')
 assert.equal(globalHistoryHref('','27'),'#/history')
})
