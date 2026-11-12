import type { Violation } from '../api/runs'

export interface ErrorExportContext {
  supplier?:import('./Suppliers').Supplier|null
  dataset:{id:number;name:string|null}; batch:{id:number;name:string|null;period_label:string|null}
  version:{id:number;number:number;filename:string};run_id:number;scope_source:string
  identity:{id:number;revision:number;columns:string[]}|null
  identity_status:'configured'|'not_configured'|'unavailable';identity_source:string
  key_values_available:boolean;rows:{row_number:number;values:(string|null)[]}[]
}

export function errorCSVRows(context:ErrorExportContext,values:Violation[],errorType:(item:Violation)=>string):unknown[][] {
  const columns=context.identity?.columns??[],byRow=new Map(context.rows.map(row=>[row.row_number,row.values]))
  const status=context.identity_status==='not_configured'?'Chưa cấu hình khóa':context.identity_status==='unavailable'?'Chưa có snapshot khóa; không suy danh tính':!context.key_values_available?'Không đọc được khóa: thiếu snapshot cột':'Đã cấu hình khóa theo snapshot'
  const header=['Bản ghi','Trường','Giá trị','Loại lỗi','Quy tắc','Gợi ý',
    'Bộ dữ liệu','ID bộ dữ liệu','Đợt dữ liệu','ID đợt','Kỳ dữ liệu','Phiên bản','ID phiên bản','File nguồn','Run',
    'Nguồn phạm vi','Trạng thái khóa','Lần cấu hình khóa','Nguồn khóa',...columns.map(name=>'Khóa: '+name),'Giá trị lỗi gốc (JSON)','Khóa gốc (JSON)']
  header.push('Mã thương hiệu nguồn','Thương hiệu nguồn','Mã cửa hàng cung cấp','Cửa hàng cung cấp','Nguồn cung cấp lịch sử')
  const supplier=context.supplier
  return [header,...values.map(item=>{
    if(context.key_values_available&&!byRow.has(item.row_number))throw new Error(`Không tìm thấy dữ liệu khóa gốc của bản ghi ${item.row_number}; chưa xuất CSV.`)
    const keys=byRow.get(item.row_number)
    return [item.row_number,item.columns.join(' + '),item.values.map(value=>value??'').join(' | '),errorType(item),item.rule_name,item.message,
      context.dataset.name??`#${context.dataset.id}`,context.dataset.id,context.batch.name??`#${context.batch.id}`,context.batch.id,context.batch.period_label??'',
      'v'+context.version.number,context.version.id,context.version.filename,context.run_id,
      context.scope_source==='run_snapshot'?'Snapshot khi bắt đầu lần kiểm tra':'ID lịch sử; chưa có snapshot tên',status,context.identity?.revision??'',
      context.identity_source==='run_snapshot'?'Snapshot lần kiểm tra':context.identity_source==='first_reconciliation_snapshot'?'Snapshot đối soát đầu tiên của run':'Không có snapshot khóa',
      ...columns.map((_,index)=>keys?.[index]??''),JSON.stringify(item.values),keys?JSON.stringify(keys):'',supplier?.brand_code??'',supplier?.brand_name??'',supplier?.store_code??'',supplier?.store_name??'',supplier?'Snapshot khi bắt đầu lần kiểm tra':'Chưa xác định cửa hàng']
  })]
}
