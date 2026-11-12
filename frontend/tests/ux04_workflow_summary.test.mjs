import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const js=stripTypeScriptTypes(fs.readFileSync('src/workspace/workflowSummary.ts','utf8'))
const {workflowBlockers}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))

test('UX-04 completion blockers use shared business messages and deduplicate after mapping',()=>{
 const labels=workflowBlockers(['IDENTITY_MISSING','RULE_ENGINE_OR_SCHEMA_CHANGED','IDENTITY_MISSING'])
 assert.deepEqual(labels,['Có bản ghi thiếu khóa','Quy tắc, cấu trúc hoặc cách kiểm tra đã thay đổi'])
 assert.deepEqual(workflowBlockers([]),[])
})
