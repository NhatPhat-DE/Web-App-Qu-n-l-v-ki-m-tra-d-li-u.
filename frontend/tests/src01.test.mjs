import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import {stripTypeScriptTypes} from 'node:module'
import Papa from 'papaparse'
const url=s=>'data:text/javascript;base64,'+Buffer.from(stripTypeScriptTypes(s)).toString('base64')
const model=url(fs.readFileSync('src/workspace/workModel.ts','utf8'))
const {operationalItems,scopeHref}=await import(url(fs.readFileSync('src/workspace/operationalModel.ts','utf8').replaceAll("'./workModel'",JSON.stringify(model))))
const {errorCSVRows}=await import(url(fs.readFileSync('src/workspace/errorExport.ts','utf8')))
globalThis.__srcPapa=Papa
const cell=url(fs.readFileSync('src/workspace/cellPresentation.ts','utf8'))
const {csvBlob}=await import(url(fs.readFileSync('src/workspace/csv.ts','utf8').replace("import Papa from 'papaparse'",'const Papa=globalThis.__srcPapa').replace("'./cellPresentation'",JSON.stringify(cell))))
const ack=url(fs.readFileSync('src/workspace/uploadAcknowledgement.ts','utf8'))
const {createBatch}=await import(url(fs.readFileSync('src/api/datasets.ts','utf8').replace("import { businessFetch } from './business'",'const businessFetch=(...args)=>globalThis.__srcFetch(...args)').replace("'../workspace/uploadAcknowledgement'",JSON.stringify(ack))))
const base={batch_id:1,dataset_id:1,dataset_name:'Same data type',batch_name:'Same period',period_label:'11/2026',current_version:{id:1},run:{error_row_count:1},status:'HAS_ERRORS',rules_changed:false}
test('SRC-01 batch adapter sends selected store ID and existing metadata together',async()=>{
 let payload
 globalThis.__srcFetch=async(url,init)=>{payload=JSON.parse(init.body);assert.equal(url,'/api/datasets/59/batches');return {ok:true,json:async()=>({id:42})}}
 await createBatch(59,{name:'November',store_id:17,period_label:'11/2026',copy_template_rules:true})
 assert.equal(payload.store_id,17);assert.equal(payload.period_label,'11/2026')
 delete globalThis.__srcFetch
})
test('SRC-01 suppliers are batch-specific; brand/store intersect and legacy text never assigns identity',()=>{
 const a={...base,supplier:{store_id:1,brand_id:1}},b={...base,batch_id:2,supplier:{store_id:2,brand_id:2}},legacy={...base,batch_id:3,supplier:null}
 const items=[a,b,legacy],datasets=[{id:1,source:'SHOP_1'}]
 assert.deepEqual(operationalItems(items,datasets,new URLSearchParams('store_id=1')),[a])
 assert.deepEqual(operationalItems(items,datasets,new URLSearchParams('brand_id=2')),[b])
 assert.deepEqual(operationalItems(items,datasets,new URLSearchParams('brand_id=1&store_id=2')),[])
 assert.deepEqual(operationalItems(items,datasets,new URLSearchParams('store_id=0')),[legacy])
 const href=scopeHref('reporting',new URLSearchParams('brand_id=1&store_id=1&period=11%2F2026'),{batch_id:'1'})
 assert.equal(new URLSearchParams(href.split('?')[1]).get('store_id'),'1')
})
test('SRC-01 CSV appends frozen supplier fields, preserves original columns/raw values, labels unknown',async()=>{
 const context={dataset:{id:1,name:'Dataset'},batch:{id:1,name:'Batch',period_label:'11/2026'},version:{id:1,number:1,filename:'raw.csv'},run_id:1,scope_source:'run_snapshot',identity:null,identity_status:'not_configured',identity_source:'run_snapshot',key_values_available:false,rows:[],supplier:{brand_code:'OLD',brand_name:'Old brand',store_code:'OLD_1',store_name:'=Old name'}}
 const error={id:1,row_number:1,columns:['name'],values:['  '],rule_name:'Required',message:'Missing'}
 const [header,row]=errorCSVRows(context,[error],()=> 'Required')
 assert.equal(row[header.indexOf('Cửa hàng cung cấp')],'=Old name')
 assert.equal(row[2],'  ');assert.equal(row[header.indexOf('Giá trị lỗi gốc (JSON)')],'["  "]')
 assert.deepEqual(header.slice(0,6),['Bản ghi','Trường','Giá trị','Loại lỗi','Quy tắc','Gợi ý'])
 const [,unknown]=errorCSVRows({...context,supplier:null},[error],()=> 'Required')
 assert.equal(unknown[header.indexOf('Nguồn cung cấp lịch sử')],'Chưa xác định cửa hàng')
 const parsed=Papa.parse(await csvBlob(errorCSVRows(context,[error],()=> 'Required')).text(),{header:true,skipEmptyLines:true}).data
 assert.equal(parsed[0]['Cửa hàng cung cấp'],"'=Old name")
 assert.equal(parsed[0]['Giá trị lỗi gốc (JSON)'],'["  "]')
})
