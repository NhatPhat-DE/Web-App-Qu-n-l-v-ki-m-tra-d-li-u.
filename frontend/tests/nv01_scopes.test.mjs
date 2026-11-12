import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
const dataURL=s=>`data:text/javascript;base64,${Buffer.from(s).toString('base64')}`
const business=dataURL(stripTypeScriptTypes(fs.readFileSync('src/api/business.ts','utf8')))
const ruleErrors=dataURL(stripTypeScriptTypes(fs.readFileSync('src/api/ruleErrors.ts','utf8')))
const rules=await import(dataURL(stripTypeScriptTypes(fs.readFileSync('src/api/rules.ts','utf8')).replace("'./business'",JSON.stringify(business)).replace("'./ruleErrors'",JSON.stringify(ruleErrors))))
const runs=await import(dataURL(stripTypeScriptTypes(fs.readFileSync('src/api/runs.ts','utf8')).replace("'./business'",JSON.stringify(business))))
test('NV-01 actual rule API client isolates templates and batch POST/PATCH',async()=>{
 const original=globalThis.fetch,calls=[]
 globalThis.fetch=async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify({id:1}),{status:200})}
 try{
  const rule={name:'Required',rule_type:'required',columns:['code'],config:{},is_active:true}
  await rules.createRule(5,rule,undefined,9)
  await rules.patchRule(5,1,{is_active:false},undefined,10)
  await rules.createRule(5,rule)
  assert.deepEqual(calls.map(c=>c.url),['/api/datasets/5/batches/9/rules','/api/datasets/5/batches/10/rules/1','/api/datasets/5/rules'])
  assert.equal(calls[0].options.method,'POST');assert.equal(calls[1].options.method,'PATCH')
 }finally{globalThis.fetch=original}
})
test('NV-01 comparison client accepts explicit cross-batch/revision reasons with no delta',async()=>{
 const original=globalThis.fetch
 const side={run_id:1,version:{id:2,version_number:1,original_filename:'x.csv',batch_id:3},status:'completed',started_at:'2026-01-01T00:00:00Z',finished_at:'2026-01-01T00:00:01Z',engine_version:'quality-v6',rule_set_fingerprint:'rules-v1:example',total_rows:1,error_row_count:0,violation_count:0,error_row_rate:'0.0000',pass_rate:'100.0000',rule_snapshot:[]}
 const body={dataset_id:5,a:side,b:{...side,run_id:2},same_run:false,comparable:false,non_comparable_reasons:['BATCH_DIFFERENT','RULE_REVISION_DIFFERENT'],delta:null}
 globalThis.fetch=async()=>new Response(JSON.stringify(body),{status:200})
 try{const result=await runs.fetchRunComparison(5,1,2,new AbortController().signal);assert.equal(result.delta,null);assert.equal(result.comparable,false)}finally{globalThis.fetch=original}
})
