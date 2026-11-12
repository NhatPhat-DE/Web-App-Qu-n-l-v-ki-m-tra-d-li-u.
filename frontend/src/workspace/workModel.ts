import type { WorkflowSummary } from './workflowSummary'

export interface BatchMetric {
  store_id?:number|null;supplier?:import('./Suppliers').Supplier|null
  business_state?:string;workflow?:Omit<WorkflowSummary,'uncertain_count'> & {uncertain_count?:number}
  batch_id:number;dataset_id:number;dataset_name:string;batch_name:string;period_label:string|null
  rules_revision:number;active_rule_count:number;status:string;rules_changed:boolean
  current_version:{id:number;version_number:number;row_count:number}|null
  run:{id:number;total_rows:number;error_row_count:number;violation_count:number;batch_rules_revision:number|null}|null
}
export interface BatchDashboardData {
  items:BatchMetric[];selected_batch_ids:number[];scope:string;assessed_batches:number
  total_rows:number;violated_rows_count:number;total_violations_count:number;violation_rate:string|null
}
export const businessLabels:Record<string,string>={RECEIVING:'Đang tiếp nhận',PROCESSING:'Đang xử lý',COMPLETED:'Đã hoàn tất',UNKNOWN:'Chưa có trạng thái'}
export const qualityLabels:Record<string,string>={NO_FILE:'Chưa có file',UNCHECKED:'Chưa kiểm tra',STALE:'Cấu hình đã đổi — cần kiểm tra lại',HAS_ERRORS:'Có dòng vi phạm',PASSED:'Đạt quy tắc hiện tại',RUNNING:'Đang kiểm tra',FAILED:'Lỗi kỹ thuật'}
export const boards=[
  {id:'intake',label:'Tiếp nhận',tab:'intake',hint:'File đầu tiên hoặc bản sửa cần tiếp nhận'},
  {id:'setup',label:'Thiết lập kiểm tra',tab:'rules',hint:'Quy tắc, khóa nhận diện và phạm vi xử lý'},
  {id:'quality',label:'Kiểm tra chất lượng',tab:'results',hint:'Chưa kiểm tra, cần chạy lại hoặc lỗi kỹ thuật'},
  {id:'resolution',label:'Xử lý & kiểm tra lại',tab:'issues',hint:'Vi phạm, issue tồn đọng và đối soát chưa xác định'},
  {id:'acceptance',label:'Nghiệm thu',tab:'acceptance',hint:'Điều kiện hoàn tất và các đợt đã được xác nhận'},
  {id:'reports',label:'Báo cáo',tab:'results',hint:'Kết quả bản hiện hành và đường dẫn lịch sử theo đợt'},
] as const
export type Board=typeof boards[number]['id']
export type BatchTab='intake'|'rules'|'results'|'issues'|'acceptance'
export const batchTabs:{id:BatchTab;label:string}[]=[{id:'intake',label:'Tiếp nhận & phiên bản'},{id:'rules',label:'Quy tắc'},{id:'results',label:'Kết quả'},{id:'issues',label:'Xử lý lỗi'},{id:'acceptance',label:'Nghiệm thu'}]
export function qualityOf(i:BatchMetric):string {
  if(!i.current_version)return 'NO_FILE'
  if(i.status==='RUNNING'||i.status==='FAILED')return i.status
  if(i.rules_changed||i.status==='STALE')return 'STALE'
  return i.run?(i.run.error_row_count?'HAS_ERRORS':'PASSED'):'UNCHECKED'
}
export function needs(i:BatchMetric):Record<Board,boolean> {
  const closed=i.business_state==='COMPLETED',q=qualityOf(i),w=i.workflow
  const exceptionsReady=!!w?.enabled&&w.unprocessed_count===0&&w.completion_blockers.length===0
  const fileNeedsCorrection=q==='HAS_ERRORS'&&!exceptionsReady
  return {
    intake:!closed&&(!i.current_version||fileNeedsCorrection),
    setup:!closed&&(!i.active_rule_count||!w?.enabled||!!w?.completion_blockers.includes('IDENTITY_NOT_CONFIGURED')),
    quality:!closed&&!!i.current_version&&['UNCHECKED','STALE','RUNNING','FAILED'].includes(q),
    resolution:!closed&&(fileNeedsCorrection||!!w?.unprocessed_count||!!w?.uncertain_count||!!w?.completion_blockers.some(r=>['CURRENT_RECONCILIATION_REQUIRED','IDENTITY_MISSING','IDENTITY_DUPLICATE','RULE_ENGINE_OR_SCHEMA_CHANGED'].includes(r))),
    acceptance:closed||!!i.current_version&&!!i.run&&!!w?.enabled,
    reports:true,
  }
}
export function primaryStep(i:BatchMetric):Board|'completed'|'unknown' {
  if(i.business_state==='COMPLETED')return 'completed'
  if(!i.current_version)return 'intake'
  if(!i.active_rule_count)return 'setup'
  if(needs(i).quality)return 'quality'
  if(!i.workflow)return 'unknown'
  if(!i.workflow.enabled||i.workflow.completion_blockers.includes('IDENTITY_NOT_CONFIGURED'))return 'setup'
  if(needs(i).resolution)return 'resolution'
  return 'acceptance'
}
export function missingWork(i:BatchMetric):string[] {
  if(i.business_state==='COMPLETED')return ['Đã xác nhận hoàn tất đợt']
  const result:string[]=[],q=qualityOf(i),w=i.workflow
  if(!i.current_version)result.push('Chưa nhận file CSV')
  if(!i.active_rule_count)result.push('Chưa có quy tắc đang bật')
  if(q==='UNCHECKED')result.push('Bản hiện hành chưa được kiểm tra')
  if(q==='STALE')result.push('Kết quả đang lưu dùng cấu hình cũ')
  if(q==='RUNNING')result.push('Chờ lần kiểm tra đang chạy')
  if(q==='FAILED')result.push('Lần kiểm tra mới nhất gặp lỗi kỹ thuật')
  if(q==='HAS_ERRORS')result.push(`${i.run!.error_row_count} dòng lỗi · ${i.run!.violation_count} lượt vi phạm`)
  if(!w)result.push('Chưa có thông tin xử lý lỗi')
  else if(!w.enabled)result.push('Chưa bật quản lý xử lý lỗi')
  else {
    if(w.unprocessed_count)result.push(`${w.unprocessed_count} issue chưa xử lý`)
    if(w.uncertain_count)result.push(`${w.uncertain_count} trong số đó chưa thể đối soát`)
    if(w.ignored_count)result.push(`${w.ignored_count} ngoại lệ cần đọc cùng bằng chứng`)
  }
  return result.length?result:['Chờ xác nhận điều kiện nghiệm thu']
}
export interface WorkFilter {dataset:string;business:string;quality:string;q:string;batchIds:number[];primary:string}
export function readWorkFilter(query:URLSearchParams):WorkFilter {
  return {dataset:query.get('dataset_id')??'',business:query.get('business')??'',quality:query.get('quality')??'',q:query.get('q')??'',
    batchIds:query.getAll('batch_id').map(Number),primary:query.get('primary')??''}
}
export function filterWork(items:BatchMetric[],f:WorkFilter):BatchMetric[] {
  return items.filter(i=>(!f.dataset||String(i.dataset_id)===f.dataset)&&(!f.business||(i.business_state??'UNKNOWN')===f.business)&&
    (!f.quality||qualityOf(i)===f.quality)&&(!f.primary||primaryStep(i)===f.primary)&&(!f.batchIds.length||f.batchIds.includes(i.batch_id))&&
    `${i.dataset_name} ${i.batch_name} ${i.period_label??''}`.toLocaleLowerCase('vi').includes(f.q.toLocaleLowerCase('vi')))
}
export function workHref(board:Board|'dashboard',query:URLSearchParams,patch:Record<string,string|null>={}):string {
  const next=new URLSearchParams(query)
  for(const [key,value] of Object.entries(patch)){if(value)next.set(key,value);else next.delete(key)}
  return `#/${board==='dashboard'?'dashboard':'work/'+board}${next.size?'?'+next:''}`
}
export function detailHref(i:BatchMetric,tab:BatchTab,back=location.hash):string {
  const params=new URLSearchParams({tab})
  if(/^#\/(dashboard|submit|rules|issues|compare|reporting|datasets|work\/[^?]+)(\?|$)/.test(back))params.set('from',back)
  return `#/datasets/${i.dataset_id}/batches/${i.batch_id}?${params}`
}
export function requestedTab(query:URLSearchParams):BatchTab|undefined {
  const tab=query.get('tab');if(batchTabs.some(t=>t.id===tab))return tab as BatchTab
  if(query.has('issue')||query.has('issues'))return 'issues'
  if(query.get('rules')==='1')return 'rules'
}
