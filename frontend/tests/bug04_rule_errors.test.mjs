import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const dataURL=source=>`data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString('base64')}`
const errorsURL=dataURL(fs.readFileSync('src/api/ruleErrors.ts','utf8'))
const {RuleAPIError,ruleFeedback}=await import(errorsURL)
const businessURL=dataURL(fs.readFileSync('src/api/business.ts','utf8'))
const rulesURL=dataURL(fs.readFileSync('src/api/rules.ts','utf8').replace("'./business'",JSON.stringify(businessURL)).replace("'./ruleErrors'",JSON.stringify(errorsURL)))
const {createRule,fetchRules}=await import(rulesURL)

test('BUG-04 incomplete character class has Vietnamese field feedback and separate technical detail',()=>{
 const result=ruleFeedback(new RuleAPIError('INVALID_CONFIG',422,'Empty or unclosed character class.'),'pattern')
 assert.equal(result.field,'pattern');assert.match(result.message,/dấu \[/);assert.ok(!result.message.includes('Empty or unclosed'))
 assert.ok(result.detail.includes('Empty or unclosed character class.'))
})
test('BUG-04 remaining pattern dialect errors never become raw primary messages',()=>{
 for(const detail of ['Unsupported escape.','Unclosed group.','Unexpected closing group.','Range endpoints must be ordered literal code points.','Future parser diagnostic']){
  const result=ruleFeedback(new RuleAPIError('INVALID_CONFIG',422,detail),'pattern')
  assert.equal(result.field,'pattern');assert.ok(!result.message.includes(detail));assert.ok(result.detail.includes(detail))
 }
})
test('BUG-04 configuration errors consistently target relevant fields',()=>{
 for(const [kind,field] of [['numeric_range','range'],['date_format','dates'],['allowed_values','values'],['integer','kind']]){
  const result=ruleFeedback(new RuleAPIError('INVALID_CONFIG',422,'Library raw diagnostic'),kind)
  assert.equal(result.field,field);assert.ok(!result.message.includes('Library'))
 }
 assert.equal(ruleFeedback(new RuleAPIError('INVALID_NAME',422),'required').field,'name')
 assert.equal(ruleFeedback(new RuleAPIError('INVALID_COLUMNS',422),'unique').field,'columns')
})
test('BUG-04 network/server errors preserve uncertainty and hide unknown raw errors',()=>{
 assert.match(ruleFeedback(new RuleAPIError('NETWORK_ERROR',0),'pattern').message,/Máy chủ có thể đã lưu/)
 const result=ruleFeedback(new RuleAPIError('UNEXPECTED',500,'Database traceback'),'pattern')
 assert.ok(!result.message.includes('traceback'));assert.ok(result.detail.includes('Database traceback'))
 assert.match(result.message,/kiểm tra danh sách trước khi gửi lại/)
 assert.ok(!ruleFeedback(new Error('Library raw diagnostic'),'pattern').message.includes('Library'))
})
test('BUG-04 actual rule API client retains code/status/details and does not mutate submitted pattern',async()=>{
 const original=globalThis.fetch,calls=[]
 globalThis.fetch=async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify({error:{code:'INVALID_CONFIG',message:'Empty or unclosed character class.'}}),{status:422})}
 try{
  const body={name:'Mẫu tùy chỉnh',rule_type:'pattern',columns:['value'],config:{pattern:'[',dialect:'re2-v1'},is_active:true}
  await assert.rejects(createRule(7,body,undefined,9),error=>error instanceof RuleAPIError&&error.code==='INVALID_CONFIG'&&error.status===422&&error.technicalDetail==='Empty or unclosed character class.'&&!error.message.includes('Empty'))
  assert.equal(body.config.pattern,'[');assert.equal(JSON.parse(calls[0].options.body).config.pattern,'[');assert.equal(calls[0].url,'/api/datasets/7/batches/9/rules')
 }finally{globalThis.fetch=original}
})
test('BUG-04 read failure differs from uncertain writes and abort remains an abort',async()=>{
 const original=globalThis.fetch
 globalThis.fetch=async()=>{throw new TypeError('Network offline')}
 try{
  await assert.rejects(fetchRules(7,1,new AbortController().signal),error=>error instanceof RuleAPIError&&error.code==='NETWORK_READ_ERROR'&&!error.message.includes('có thể đã lưu'))
  const controller=new AbortController();controller.abort()
  globalThis.fetch=async()=>{throw new DOMException('Aborted','AbortError')}
  await assert.rejects(fetchRules(7,1,controller.signal),error=>error.name==='AbortError')
 }finally{globalThis.fetch=original}
})
