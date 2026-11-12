import type { ReactNode } from 'react'
import type { CatalogEntry } from './api'
import { request } from './api'
import { Field, useLoad } from './ui'
import { filterWork, readWorkFilter, qualityOf, qualityLabels, businessLabels } from './workModel'
import type { BatchDashboardData, BatchMetric } from './workModel'

import {operationalItems,scopeHref} from './operationalModel'
export {operationalItems,scopeHref} from './operationalModel'
export function useOperationalScope(datasets:CatalogEntry[]) {
  const query=new URLSearchParams(location.hash.split('?')[1])
  const all=useLoad(signal=>request<BatchDashboardData>('/api/batch-dashboard',signal),[datasets])
  const items=operationalItems(all.data?.items??[],datasets,query)
  const subset=!!all.data&&items.length!==all.data.items.length
  const url=subset&&items.length>0&&items.length<=200?'/api/batch-dashboard?'+items.map(i=>'batch_id='+i.batch_id).join('&'):null
  const summary=useLoad(signal=>url?request<BatchDashboardData>(url,signal):Promise.resolve(null),[url])
  const matchingSummary=!!summary.data&&summary.data.selected_batch_ids.length===items.length&&items.every(i=>summary.data!.selected_batch_ids.includes(i.batch_id))
  const totalsLoading=all.loading||!!(subset&&url&&!summary.error&&(summary.loading||!matchingSummary))
  const totalsError=all.error||(subset?summary.error:'')
  const totals=subset?(matchingSummary&&!summary.loading?summary.data:null):all.data
  function update(patch:Record<string,string|null>,replace=false){const href=scopeHref(location.hash.slice(2).split('?')[0],query,patch);if(replace){history.replaceState(null,'',href);dispatchEvent(new HashChangeEvent('hashchange'))}else location.hash=href}
  const chosen=query.getAll('batch_id').length===1?query.get('batch_id'):null,batch=chosen?items.find(i=>String(i.batch_id)===chosen):undefined
  const dataset=datasets.find(d=>String(d.id)===query.get('dataset_id'))??(batch?datasets.find(d=>d.id===batch.dataset_id):undefined)
  return {all,items,query,summary,totals,totalsLoading,totalsError,update,batch,dataset,subset}
}
export type OperationalScope=ReturnType<typeof useOperationalScope>
export function ScopeFilters({scope,datasets,batch=false,children}:{scope:OperationalScope;datasets:CatalogEntry[];batch?:boolean;children?:ReactNode}) {
  const {query,update}=scope
  const supplierItems=(scope.all.data?.items??[]).flatMap(i=>i.supplier?[i.supplier]:[])
  const brands=[...new Map(supplierItems.map(s=>[s.brand_id,s])).values()]
  const stores=[...new Map(supplierItems.filter(s=>!query.get('brand_id')||String(s.brand_id)===query.get('brand_id')).map(s=>[s.store_id,s])).values()]
  const sources=[...new Set(datasets.map(d=>d.source||'__none__'))].sort()
  const periods=[...new Set((scope.all.data?.items??[]).map(i=>i.period_label||'__none__'))].sort()
  return <><section className="demo-scope" aria-label="Phạm vi dữ liệu"><Field label="Loại dữ liệu"><select value={query.get('dataset_id')??''} onChange={e=>update({dataset_id:e.target.value||null,batch_id:null,a:null,b:null})}><option value="">Tất cả loại dữ liệu</option>{datasets.map(d=><option value={d.id} key={d.id}>{d.name}</option>)}</select></Field><Field label="Kỳ dữ liệu"><select value={query.get('period')??''} onChange={e=>update({period:e.target.value||null,batch_id:null})}><option value="">Tất cả kỳ</option>{periods.map(p=><option key={p} value={p}>{p==='__none__'?'Chưa có kỳ':p}</option>)}</select></Field><Field label="Thương hiệu"><select value={query.get('brand_id')??''} onChange={e=>update({brand_id:e.target.value||null,store_id:null,batch_id:null})}><option value="">Tất cả thương hiệu</option>{brands.map(s=><option key={s.brand_id} value={s.brand_id}>{s.brand_code} · {s.brand_name}</option>)}</select></Field><Field label="Cửa hàng cung cấp"><select value={query.get('store_id')??''} onChange={e=>update({store_id:e.target.value||null,batch_id:null})}><option value="">Tất cả cửa hàng</option>{!query.get('brand_id')&&<option value="0">Chưa xác định cửa hàng</option>}{stores.map(s=><option key={s.store_id} value={s.store_id}>{s.store_code} · {s.store_name}</option>)}</select></Field><details><summary>Nguồn chữ tham khảo (cũ){query.get('source')?' · đang lọc':''}</summary><Field label="Nguồn chữ ở bộ dữ liệu"><select value={query.get('source')??''} onChange={e=>{const current=datasets.find(d=>String(d.id)===query.get('dataset_id'));update({source:e.target.value||null,batch_id:null,dataset_id:current&&e.target.value&&(current.source||'__none__')!==e.target.value?null:query.get('dataset_id')})}}><option value="">Tất cả nguồn</option>{sources.map(s=><option key={s} value={s}>{s==='__none__'?'Chưa khai báo nguồn':s}</option>)}</select></Field></details>{batch&&<Field label="Đợt dữ liệu"><select value={query.getAll('batch_id').length===1?query.get('batch_id')??'':''} onChange={e=>{const i=scope.items.find(i=>String(i.batch_id)===e.target.value);update({batch_id:e.target.value||null,dataset_id:i?String(i.dataset_id):query.get('dataset_id'),a:null,b:null})}}><option value="">Chọn đợt cần làm việc</option>{scope.items.map(i=><option value={i.batch_id} key={i.batch_id}>{i.batch_name} · {i.supplier?.store_code??'Chưa xác định cửa hàng'} · {i.period_label||'Chưa có kỳ'}</option>)}</select></Field>}{children}<a className="demo-reset" href={'#/'+location.hash.slice(2).split('?')[0]}>Xóa phạm vi lọc</a></section><div className="demo-active-scope">{query.get('quality')&&<span>Chất lượng: {qualityLabels[query.get('quality')!]??'Chưa có kết quả hợp lệ'} <a href={scopeHref(location.hash.slice(2).split('?')[0],query,{quality:null})}>×</a></span>}{query.get('business')&&<span>Đợt: {businessLabels[query.get('business')!]??query.get('business')} <a href={scopeHref(location.hash.slice(2).split('?')[0],query,{business:null})}>×</a></span>}{query.get('q')&&<span>Từ khóa: {query.get('q')} <a href={scopeHref(location.hash.slice(2).split('?')[0],query,{q:null})}>×</a></span>}{query.get('primary')&&<span>Phạm vi bước cũ: {query.get('primary')} <a href={scopeHref(location.hash.slice(2).split('?')[0],query,{primary:null})}>×</a></span>}{query.getAll('batch_id').length>1&&<span>{query.getAll('batch_id').length} đợt trong URL · chọn một đợt để thao tác <a href={scopeHref(location.hash.slice(2).split('?')[0],query,{batch_id:null})}>×</a></span>}</div></>
}
