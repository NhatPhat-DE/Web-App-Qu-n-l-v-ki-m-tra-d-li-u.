import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
const asURL=source=>`data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString('base64')}`
const business=asURL(fs.readFileSync('src/api/business.ts','utf8'))
const {validateCreate,roleLabel,createUser}=await import(asURL(fs.readFileSync('src/api/admin.ts','utf8').replace("'./business'",JSON.stringify(business))))
test('NV-02 Owner role is accepted explicitly by admin UI/API client',async()=>{
 const user={username:'nv02_owner',password:'ephemeral owner test password',role:'data_owner'}
 assert.equal(validateCreate(user,user.password),'');assert.equal(roleLabel(user.role),'Data Owner')
 const original=globalThis.fetch;let sent
 globalThis.fetch=async(url,options)=>{sent={url,body:JSON.parse(options.body)};return new Response(JSON.stringify({id:9,...user,is_active:true}),{status:201})}
 try{await createUser(user,user.password);assert.equal(sent.url,'/api/admin/users');assert.equal(sent.body.role,'data_owner')}
 finally{globalThis.fetch=original}
})
