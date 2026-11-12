import SupplierCatalog from './Suppliers'
import type {CatalogEntry} from './api'
import type {DatasetActions} from './CatalogPages'
import {CatalogPage,DatasetPage} from './CatalogPages'
import {Button,Field,PageTitle} from './ui'
import {scopeHref} from './OperationalScope'
export default function CatalogDictionary({datasets,actions,userRole}:{datasets:CatalogEntry[];actions:DatasetActions;userRole:string}) {
  const query=new URLSearchParams(location.hash.split('?')[1]),supplierView=query.get('view')==='suppliers',dictionary=query.get('view')==='dictionary',selected=datasets.find(d=>String(d.id)===query.get('dataset_id'))
  return <div className="demo-page"><PageTitle title="Danh mục & Từ điển dữ liệu" description="Khai báo một lần, dùng lại cho nhiều kỳ tiếp nhận và các đợt kiểm tra." action={!supplierView&&<Button tone="primary" onClick={actions.create}>Thêm loại dữ liệu</Button>}/><nav className="demo-segments" aria-label="Danh mục và từ điển"><a className={!dictionary&&!supplierView?'active':''} href={scopeHref('datasets',query,{view:null})}>Danh mục dữ liệu</a><a className={dictionary?'active':''} href={scopeHref('datasets',query,{view:'dictionary'})}>Từ điển dữ liệu</a><a className={supplierView?'active':''} href={scopeHref('datasets',query,{view:'suppliers'})}>Thương hiệu & Cửa hàng</a></nav>{supplierView?<SupplierCatalog role={userRole} changed={actions.changed}/>:!dictionary?<div className="catalog-content"><CatalogPage datasets={datasets} actions={actions}/></div>:<><section className="demo-scope"><Field label="Loại dữ liệu cần tra cứu"><select value={selected?.id??''} onChange={e=>{location.hash=scopeHref('datasets',query,{dataset_id:e.target.value||null})}}><option value="">Chọn loại dữ liệu</option>{datasets.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select></Field></section>{selected?<div className="dictionary-content"><DatasetPage key={selected.id} dataset={selected} tab="fields" userRole={userRole} actions={actions}/></div>:<section className="panel panel-pad"><h2>Từ điển trường dữ liệu</h2><p>Chọn loại dữ liệu để xem cấu trúc, mô tả và kiểu suy luận theo phiên bản đã lưu.</p></section>}</>}</div>
}

