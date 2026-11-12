import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const url=s=>'data:text/javascript;base64,'+Buffer.from(stripTypeScriptTypes(s)).toString('base64')
const ack=url(fs.readFileSync('src/workspace/uploadAcknowledgement.ts','utf8'))
const {UploadAcknowledgementError,pendingUploadKey,readPendingUpload}=await import(ack)
const source=fs.readFileSync('src/api/datasets.ts','utf8').replace("import { businessFetch } from './business'",'const businessFetch=(...args)=>globalThis.__ackFetch(...args)').replace("'../workspace/uploadAcknowledgement'",JSON.stringify(ack))
const {importVersion,importDataset}=await import(url(source))
const file=new File(['id,value\nA,one'],'ack.csv',{type:'text/csv'})

test('CORE-ACK transport, malformed/truncated success and server5xx are ambiguous; no implicit resend',async()=>{
 const ok={dataset_id:1,batch_id:2,version_id:3,version_number:2}
 for(const fetch of [async()=>{throw new TypeError('Connection closed')},async()=>new Response('{',{status:201}),async()=>new Response('{}',{status:201}),async()=>new Response(JSON.stringify({...ok,batch_id:99}),{status:201}),async()=>new Response('{"error":{"message":"server failed"}}',{status:500})]){
  let calls=0;globalThis.__ackFetch=async(...args)=>{calls++;return fetch(...args)}
  await assert.rejects(importVersion(1,file,2),UploadAcknowledgementError);assert.equal(calls,1)
 }
 globalThis.__ackFetch=async()=>new Response(JSON.stringify(ok),{status:201})
 assert.deepEqual(await importVersion(1,file,2),ok)
})
test('CORE-ACK definite validation rejection keeps ordinary retry behavior',async()=>{
 globalThis.__ackFetch=async()=>new Response('{"error":{"message":"Invalid CSV"}}',{status:422})
 await assert.rejects(importVersion(1,file,2),e=>e.message==='Invalid CSV'&&!(e instanceof UploadAcknowledgementError))
})
test('CORE-ACK old dataset import also preserves uncertain classification',async()=>{
 for(const fetch of [async()=>{throw Error('network')},async()=>new Response('bad json',{status:201}),async()=>new Response('{}',{status:201}),async()=>new Response('{}',{status:503})]){
  globalThis.__ackFetch=fetch;await assert.rejects(importDataset(new FormData()),UploadAcknowledgementError)
 }
})
test('CORE-ACK pending state is batch-scoped, survives a new reader, contains no raw CSV',()=>{
 const data=new Map(),storage={getItem:key=>data.get(key)??null},key=pendingUploadKey(1,2)
 const marker={filename:'ack.csv',size:20,rowCount:1,startedAt:'2026-11-12T00:00:00Z',beforeIds:[1]}
 data.set(key,JSON.stringify(marker));assert.deepEqual(readPendingUpload(storage,key),marker)
 assert.equal(readPendingUpload(storage,pendingUploadKey(1,3)),null)
 data.set(key,'broken');assert.equal(readPendingUpload(storage,key),null)
})
