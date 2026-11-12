import fs from 'node:fs'
import assert from 'node:assert/strict'
import {stripTypeScriptTypes} from 'node:module'
const source=stripTypeScriptTypes(fs.readFileSync('src/api/business.ts','utf8'))
const {businessFetch,configureBusiness,disconnectBusiness}=await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const nativeFetch=globalThis.fetch;const events=[]
configureBusiness('in-memory-csrf',event=>events.push(event))
globalThis.fetch=async(url,options)=>{
 assert.equal(options.credentials,'same-origin');assert.equal(options.headers.get('X-CSRF-Token'),'in-memory-csrf')
 assert.equal(options.headers.has('Content-Type'),false)
 return new Response('{}')
}
await businessFetch('/api/datasets/import',{method:'POST',body:new FormData()})
globalThis.fetch=async()=>new Response('{"error":{"code":"CSRF_REJECTED"}}',{status:403});await businessFetch('/api/datasets');assert.deepEqual(events,['csrf'])
globalThis.fetch=async()=>new Response('{}',{status:503});await businessFetch('/api/datasets');assert.deepEqual(events,['csrf'])
globalThis.fetch=async()=>new Response('{}',{status:401});await businessFetch('/api/datasets');assert.deepEqual(events,['csrf','expired'])
disconnectBusiness();globalThis.fetch=nativeFetch
console.log('PASS: in-memory CSRF/same-origin/FormData no Content-Type,403 CSRF refresh notification,503 retains session,401 clears requests/session notification. No browser UI test.')
