import type { QualityRule } from '../api/rules'
import type { CatalogEntry } from './api'
import { getRules } from './api'
import { RuleDialog } from './EditDialogs'
import { Button, Dialog, LoadState, useLoad } from './ui'

export type RuleEditorIntent = { mode: 'create' } | { mode: 'edit'; ruleId: number }
interface Props {
  dataset: CatalogEntry
  batchId?: number
  intent: RuleEditorIntent
  saved: () => void
  onClose: () => void
}

export default function RuleEditorDialog(props: Props) {
  const scope=`${props.dataset.id}:${props.batchId??'template'}`
  return props.intent.mode==='create'
    ? <RuleDialog key={`${scope}:create`} mode="create" dataset={props.dataset} batchId={props.batchId} saved={props.saved} onClose={props.onClose}/>
    : <ExistingRuleDialog key={`${scope}:edit:${props.intent.ruleId}`} {...props} ruleId={props.intent.ruleId}/>
}

function ExistingRuleDialog({dataset,batchId,ruleId,saved,onClose}:Props & {ruleId:number}) {
  const current=useLoad<QualityRule>(async signal=>{
    let rules:QualityRule[]
    try { rules=await getRules(dataset.id,signal,batchId) }
    catch(cause) {
      if(signal.aborted)throw cause
      throw new Error('Không thể tải quy tắc cần sửa. Hãy thử tải lại; chưa có thay đổi nào được gửi.')
    }
    const rule=rules.find(item=>item.id===ruleId)
    if(!rule||rule.dataset_id!==dataset.id||(batchId==null?rule.batch_id!=null:rule.batch_id!==batchId))
      throw new Error('Quy tắc không còn tồn tại trong phạm vi này. Đóng cửa sổ và tải lại danh sách để chọn lại.')
    return rule
  },[dataset.id,batchId,ruleId])

  if(!current.loading&&current.data?.id===ruleId&&current.data.dataset_id===dataset.id)
    return <RuleDialog key={`${dataset.id}:${batchId??'template'}:${ruleId}`} mode="edit" dataset={dataset} batchId={batchId} rule={current.data} saved={saved} onClose={onClose}/>

  return <Dialog title="Chỉnh sửa quy tắc" description={`${dataset.name} · ${batchId?'Quy tắc của đợt':'Quy tắc mẫu'}`} onClose={onClose}>
    <LoadState loading={current.loading} error={current.error} retry={current.reload}/>
    <div className="dialog-footer"><Button onClick={onClose}>Đóng</Button><Button tone="primary" disabled>Lưu quy tắc</Button></div>
  </Dialog>
}
