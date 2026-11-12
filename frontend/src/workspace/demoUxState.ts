import type {Workflow} from './IssueWorkflow'

// Evidence belongs to this run; zero violation links says nothing about activation.
export function runWorkflowMessage(runId:number,violations:number,linkCount:number,workflow:Workflow):string {
  const recon=workflow.reconciliations.find(r=>r.run_id===runId)
  const empty=violations===0?'Lần kiểm tra này không có vi phạm để liên kết. ':''
  if(recon)return empty+(recon.result==='HISTORICAL'
    ?`Đã ghi nhận đối soát lịch sử #${recon.id}; không cập nhật trạng thái xử lý từ lần lịch sử này.`
    :recon.eligible?`Đã đối soát #${recon.id} cho lần kiểm tra này.`
    :`Đã ghi nhận đối soát #${recon.id}, nhưng chưa đủ điều kiện xác minh khóa. Xem lý do trong Xử lý lỗi.`)
  if(!workflow.enabled)return empty+'Đợt chưa bật quản lý xử lý lỗi.'
  if(linkCount)return ''
  return empty+'Chưa thấy bằng chứng đối soát của lần kiểm tra này trong dữ liệu đã tải. Mở Xử lý lỗi để kiểm tra; không suy ra trạng thái từ số liên kết.'
}

export function canSuggestCorrection(quality:string,closed:boolean,canComplete:boolean) {
  return !closed&&!canComplete&&quality==='HAS_ERRORS'
}

export function errorRowDelta(comparable:boolean,delta:number|null|undefined) {
  return comparable&&delta!==null&&delta!==undefined?`${delta>0?'+':''}${delta.toLocaleString('vi-VN')} dòng`:'Không áp dụng'
}

export function correctionHref(dataset:number,batch:number,currentHash:string) {
  const path=`#/datasets/${dataset}/batches/${batch}`
  const query=currentHash.split('?')[0]===path?new URLSearchParams(currentHash.split('?')[1]):new URLSearchParams({from:currentHash})
  query.set('tab','issues');query.set('upload','1')
  return `${path}?${query}`
}
