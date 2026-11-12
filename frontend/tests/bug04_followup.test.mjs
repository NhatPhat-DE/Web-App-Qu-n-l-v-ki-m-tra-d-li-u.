import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const source=stripTypeScriptTypes(fs.readFileSync('src/workspace/comparisonMessages.ts','utf8'))
const {comparisonReasonMessages}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)

test('BUG-04 follow-up deduplicates user messages after technical reason mapping',()=>{
 const reasons=['RULE_REVISION_DIFFERENT','RULE_SET_FINGERPRINT_DIFFERENT']
 assert.deepEqual(comparisonReasonMessages(reasons),['Bộ quy tắc đã thay đổi.'])
 assert.deepEqual(reasons,['RULE_REVISION_DIFFERENT','RULE_SET_FINGERPRINT_DIFFERENT'])
})
test('BUG-04 follow-up keeps distinct causes and first occurrence order',()=>{
 assert.deepEqual(comparisonReasonMessages(['BATCH_DIFFERENT','RULE_REVISION_DIFFERENT','ENGINE_VERSION_DIFFERENT','RULE_SET_FINGERPRINT_DIFFERENT','BATCH_DIFFERENT']),['Hai đợt khác nhau.','Bộ quy tắc đã thay đổi.','Cách kiểm tra đã thay đổi.'])
 assert.deepEqual(comparisonReasonMessages([]),[])
 assert.equal(comparisonReasonMessages(['FUTURE_A','FUTURE_B']).length,2)
})
