import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
const source=stripTypeScriptTypes(fs.readFileSync('src/workspace/presentation.ts','utf8'))
const {percent,amount,resultText,batchText,initialComparisonBatch}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
test('UX-02 formats rates with at most two decimals without changing saved decimal strings',()=>{
 const original='16.6667'
 assert.equal(percent(original),'16,67%');assert.equal(original,'16.6667')
 assert.equal(percent('75.0000'),'75%');assert.equal(percent('0.0000'),'0%')
 assert.equal(percent(null),'Chưa có kết quả');assert.equal(amount('-58.3333'),'-58,33')
 assert.equal(resultText(12,9,16),'12 bản ghi · 9 dòng lỗi · 16 lượt vi phạm')
})
test('UX-02 batch names show business periods and avoid duplicate period text',()=>{
 assert.equal(batchText({name:'Tháng 01/2026',period_label:'01/2026'}),'Tháng 01/2026')
 assert.equal(batchText({name:'Khách hàng',period_label:'01/2026'}),'Khách hàng · 01/2026')
})
test('UX-02 comparison scope follows both URL selections and never guesses a batch',()=>{
 const dataset={runs:[{run_id:55,version_id:58,batch_id:25},{run_id:56,version_id:59,batch_id:25},{run_id:57,version_id:61,batch_id:26}],versions:[{id:58,batch_id:25},{id:59,batch_id:25},{id:61,batch_id:26}]}
 assert.equal(initialComparisonBatch(dataset,55,56),'25')
 assert.equal(initialComparisonBatch(dataset,55,57),'')
 assert.equal(initialComparisonBatch(dataset,0,0),'')
 assert.equal(initialComparisonBatch(dataset,55,999),'')
})
