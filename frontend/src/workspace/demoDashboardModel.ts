import type {BatchMetric} from './workModel'
import {qualityOf} from './workModel'
export const qualityGroups=[{key:'PASSED',label:'Đạt quy tắc',tone:'good'},{key:'HAS_ERRORS',label:'Có dòng vi phạm',tone:'bad'},{key:'STALE',label:'Cấu hình cũ',tone:'warn'},{key:'WAITING',label:'Chưa có kết quả hợp lệ',tone:'neutral'}] as const
export function qualityBucket(item:BatchMetric){const q=qualityOf(item);return q==='PASSED'||q==='HAS_ERRORS'||q==='STALE'?q:'WAITING'}
export function qualityCounts(items:BatchMetric[]){return qualityGroups.map(g=>({...g,count:items.filter(i=>qualityBucket(i)===g.key).length}))}
export function trackedIssues(items:BatchMetric[]){const tracked=items.filter(i=>i.workflow?.enabled);return {tracked:tracked.length,unprocessed:tracked.reduce((n,i)=>n+i.workflow!.unprocessed_count,0),uncertain:tracked.reduce((n,i)=>n+(i.workflow!.uncertain_count??0),0),ignored:tracked.reduce((n,i)=>n+i.workflow!.ignored_count,0)}}
