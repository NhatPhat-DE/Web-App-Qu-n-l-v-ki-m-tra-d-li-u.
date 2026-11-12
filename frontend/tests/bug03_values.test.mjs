import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
import Papa from 'papaparse'
const asURL = source => `data:text/javascript;base64,${Buffer.from(stripTypeScriptTypes(source)).toString('base64')}`
const cellURL = asURL(fs.readFileSync('src/workspace/cellPresentation.ts','utf8'))
const {describeCell,isWhitespaceOnly} = await import(cellURL)
const csvSource = fs.readFileSync('src/workspace/csv.ts','utf8').replace("import Papa from 'papaparse'",'const Papa = globalThis.__bug03Papa').replace("'./cellPresentation'",JSON.stringify(cellURL))
globalThis.__bug03Papa = Papa
const {csvBlob,parseCSVText} = await import(asURL(csvSource))
delete globalThis.__bug03Papa

test('BUG-03 distinguishes null/empty from whitespace and keeps zero and literal tokens',()=>{
  for(const value of [null,undefined,'']) assert.equal(describeCell(value).text,'Trống')
  for(const value of [0,'0','NULL','NaN','N/A']) assert.equal(describeCell(value).text,String(value))
  const spaces='   ';assert.equal(describeCell(spaces).text,'Chỉ có khoảng trắng')
  assert.ok(describeCell(spaces).title.includes('\\u0020\\u0020\\u0020'))
  assert.ok(describeCell(spaces).title.includes('3 ký tự'));assert.equal(spaces,'   ')
})
test('BUG-03 whitespace follows Python engine policy, including controls and Unicode',()=>{
  const points=[9,10,11,12,13,28,29,30,31,32,133,160,5760,...Array.from({length:11},(_,i)=>8192+i),8232,8233,8239,8287,12288]
  for(const point of points) assert.equal(isWhitespaceOnly(String.fromCodePoint(point)),true,point.toString(16))
  for(const value of ['','\ufeff','\u200b',' 0 ','\tNULL']) assert.equal(isWhitespaceOnly(value),false)
  assert.equal(describeCell('\t\u00a0').text,'Chỉ có khoảng trắng')
})
test('BUG-03 CSV keeps original whitespace and zero without presentation labels; formula protection remains',async()=>{
  const values=['','   ','\t','\r','\u0085','\u00a0','\u2003','\ufeff','0',0,'NULL','NaN','N/A']
  const text=await csvBlob([['id','value'],...values.map((v,i)=>[i,v])]).text()
  const parsed=Papa.parse(text).data.slice(1).map(row=>row[1])
  assert.deepEqual(parsed,values.map(String));assert.ok(!text.includes('Chỉ có khoảng trắng'));assert.ok(!text.includes('Trống'))
  const formulas=Papa.parse(await csvBlob([['=1+1','\t=1+1','@SUM(A1)']]).text()).data[0]
  assert.deepEqual(formulas,["'=1+1","'\t=1+1","'@SUM(A1)"])
  const preview=parseCSVText('id,value\n1,"   "\n2,"\t"\n3,0\n')
  assert.deepEqual(preview.rows,[['1','   '],['2','\t'],['3','0']])
})
