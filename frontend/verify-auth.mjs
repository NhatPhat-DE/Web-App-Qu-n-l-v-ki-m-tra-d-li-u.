import fs from 'node:fs'
import assert from 'node:assert/strict'
import { stripTypeScriptTypes } from 'node:module'
const source = stripTypeScriptTypes(fs.readFileSync('src/api/auth.ts','utf8'))
const {fetchMe,login,logout,AuthError} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`)
const signal=new AbortController().signal
const nativeFetch=globalThis.fetch
let calls=[]
globalThis.fetch=async (url,options) => {
  calls.push([url,options]);assert.equal(options.credentials,'same-origin')
  return new Response(JSON.stringify({error:{code:'UNAUTHENTICATED'},csrf_token:'challenge'}),{status:401})
}
assert.deepEqual(await fetchMe(signal),{authenticated:false,csrf_token:'challenge'})
await assert.rejects(login('admin','  password  ','challenge',signal),AuthError)
assert.equal(calls[1][1].body,JSON.stringify({username:'admin',password:'  password  '}))
assert.equal(calls[1][1].headers['X-CSRF-Token'],'challenge');assert.equal(calls.length,2)
globalThis.fetch=async () => new Response(JSON.stringify({user:{id:1,username:'admin',role:'admin'},expires_at:'2026-10-15T10:00:00Z',csrf_token:'session'}))
assert.equal((await login('admin','  password  ','challenge',signal)).authenticated,true)
globalThis.fetch=async () => new Response(null,{status:204});assert.equal(await logout('session',signal),null)
for(const status of [403,429,503]) {
  globalThis.fetch=async()=>new Response(JSON.stringify({error:{message:'safe error'}}),{status,headers:{'Retry-After':'120'}})
  await assert.rejects(login('admin','  password  ','challenge',signal),err=>err instanceof AuthError && err.status===status && err.retryAfter===120)
}
globalThis.fetch=async()=>{throw Error('network')};await assert.rejects(logout('session',signal),AuthError)
globalThis.fetch=(url,options)=>nativeFetch(`http://127.0.0.1:5173${url}`,options)
const live=await fetchMe(signal);assert.equal(live.authenticated,false);assert.equal(typeof live.csrf_token,'string')
globalThis.fetch=nativeFetch
console.log('PASS: me401 anonymous, login success/error, password exact, cookie same-origin, CSRF header, logout204,403/429/503/network no automatic retry; real proxy me401 challenge. Client/HTTP only, not browser UI.')
