import type {CatalogEntry} from './api'
import type {BatchMetric} from './workModel'
import {filterWork,readWorkFilter,qualityOf} from './workModel'
export function operationalItems(items:BatchMetric[],datasets:Pick<CatalogEntry,'id'|'source'>[],query:URLSearchParams) {
  const sources=new Map(datasets.map(d=>[d.id,d.source||'__none__']))
  const filter=readWorkFilter(query),waiting=filter.quality==='WAITING'
  return filterWork(items,waiting?{...filter,quality:''}:filter).filter(i=>(!waiting||!['PASSED','HAS_ERRORS','STALE'].includes(qualityOf(i)))&&(!query.get('brand_id')||String(i.supplier?.brand_id??'')===query.get('brand_id'))&&(!query.get('store_id')||(query.get('store_id')==='0'?!i.supplier:String(i.supplier?.store_id??'')===query.get('store_id')))&&(!query.get('source')||sources.get(i.dataset_id)===query.get('source'))&&(!query.get('period')||(i.period_label||'__none__')===query.get('period')))
}
export function scopeHref(path:string,query:URLSearchParams,patch:Record<string,string|null>={}) {
  const next=new URLSearchParams(query)
  for(const [key,value] of Object.entries(patch)){if(value)next.set(key,value);else next.delete(key)}
  return '#/'+path+(next.size?'?'+next:'')
}
