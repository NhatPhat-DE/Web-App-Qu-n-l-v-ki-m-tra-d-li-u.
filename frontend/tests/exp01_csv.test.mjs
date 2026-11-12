import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import Papa from 'papaparse'
import {stripTypeScriptTypes} from 'node:module'
const asURL=s=>'data:text/javascript;base64,'+Buffer.from(stripTypeScriptTypes(s)).toString('base64')
const {errorCSVRows}=await import(asURL(fs.readFileSync('src/workspace/errorExport.ts','utf8')))
const cell=asURL(fs.readFileSync('src/workspace/cellPresentation.ts','utf8'))
globalThis.__expPapa=Papa
const {csvBlob}=await import(asURL(fs.readFileSync('src/workspace/csv.ts','utf8').replace("import Papa from 'papaparse'",'const Papa=globalThis.__expPapa').replace("'./cellPresentation'",JSON.stringify(cell))))
delete globalThis.__expPapa
const ctx={dataset:{id:58,name:'Dataset cũ'},batch:{id:39,name:'Đợt cũ',period_label:'11/2026'},version:{id:87,number:1,filename:'v1.csv'},run_id:83,scope_source:'run_snapshot',identity:{id:2,revision:1,columns:['id','part']},identity_status:'configured',identity_source:'run_snapshot',key_values_available:true,rows:[{row_number:1,values:['001','X']},{row_number:3,values:['0','Y']}]}
const item={row_number:1,columns:['name'],values:['   '],rule_name:'Tên bắt buộc',message:'Giữ nguyên',error_code:'REQUIRED_MISSING'}

test('EXP-01 keeps existing error columns and adds each composite key from exact run row',()=>{
 const rows=errorCSVRows(ctx,[{...item,row_number:3},item],()=> 'Bắt buộc')
 assert.deepEqual(rows[0].slice(0,6),['Bản ghi','Trường','Giá trị','Loại lỗi','Quy tắc','Gợi ý'])
 const records=rows.slice(1).map(r=>Object.fromEntries(rows[0].map((k,i)=>[k,r[i]])))
 assert.deepEqual(records.map(r=>[r['Khóa: id'],r['Khóa: part']]),[['0','Y'],['001','X']])
 assert.equal(records[0]['Run'],83);assert.equal(records[0]['ID đợt'],39);assert.equal(records[0]['Giá trị'],'   ')
 assert.equal(records[0]['Giá trị lỗi gốc (JSON)'],'["   "]')
 assert.throws(()=>errorCSVRows(ctx,[{...item,row_number:2}],()=>''),/Không tìm thấy dữ liệu khóa gốc/)
})
test('EXP-01 CSV quoting and injection protection preserve exact values in safe JSON columns',async()=>{
 const attacks=['=1+1','+SUM(A1)','-2','@SUM(A1)','\t=2','\r=3','\n=4','   =5','\u00a0@SUM(A1)','\ufeff=6']
 for(const attack of attacks){
  const raw=[attack,'a,"b"\r\nline'];const context={...ctx,dataset:{id:58,name:attack},rows:[{row_number:1,values:raw}]}
  const table=Papa.parse(await csvBlob(errorCSVRows(context,[{...item,values:[attack,null,'','   ','0']}],()=>attack)).text()).data
  const r=Object.fromEntries(table[0].map((k,i)=>[k,table[1][i]]))
  for(const key of ['Bộ dữ liệu','Khóa: id','Loại lỗi','Giá trị'])assert.ok(r[key].startsWith("'"),key+': '+attack)
  assert.deepEqual(JSON.parse(r['Khóa gốc (JSON)']),raw)
  assert.deepEqual(JSON.parse(r['Giá trị lỗi gốc (JSON)']),[attack,null,'','   ','0'])
  assert.equal(r['Khóa: part'],raw[1])
 }
})
test('EXP-01 absent and legacy identity are explicit, never synthesized from row number',()=>{
 for(const status of ['not_configured','unavailable']){
  const rows=errorCSVRows({...ctx,identity:null,identity_status:status,key_values_available:false,rows:[]},[item],()=> '')
  assert.equal(rows[0].some(h=>h.startsWith('Khóa: ')),false)
  const record=Object.fromEntries(rows[0].map((k,i)=>[k,rows[1][i]]))
  assert.match(record['Trạng thái khóa'],status==='not_configured'?/Chưa cấu hình/:/Chưa có snapshot/)
  assert.equal(record['Khóa gốc (JSON)'],'')
 }
})
