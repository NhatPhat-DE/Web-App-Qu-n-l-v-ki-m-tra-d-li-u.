import {supplierLabel} from './Suppliers'
import { IdentityPanel } from './IssueWorkflow'
import { historyHref, comparisonHref, queryBatch, comparisonScope, isScopeId } from './scopeNavigation'
import CellValue from './CellValue'
import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Database,
  Eye,
  FileSpreadsheet,
  FolderOpen,
  FolderPlus,
  History,
  LoaderCircle,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  Search,
  Upload,
  UserRound,
  X,
} from 'lucide-react'
import type { DataBatchItem, DatasetColumn, DatasetVersion, RowsPage } from '../api/datasets'
import { listBatches } from '../api/datasets'
import { catalogSelection, latestRun, request, allPages } from './api'
import { batchText } from './presentation'
import type { CatalogEntry } from './api'
import type { RunSummary } from '../api/runs'
import { MetadataDialog } from './EditDialogs'
import CreateBatchDialog from './CreateBatchDialog'
import UploadDialog from './UploadDialog'
import {
  Badge,
  Button,
  DatasetMark,
  Dialog,
  Empty,
  Field,
  LoadState,
  Notice,
  PageTitle,
  Pager,
  QualityBadge,
  date,
  number,
  useDebounced,
  useLoad,
} from './ui'
import { HistoryPage } from './HistoryPage'
import RuleList from './RuleList'
import { Comparison, QualityTrend } from './QualityInsights'
import InferenceDetails from './InferenceDetails'

export interface DatasetActions {
  create: () => void
  upload: (dataset?: CatalogEntry) => void
  run: (dataset?: CatalogEntry, version?: number) => void
  changed: () => void
}

export type CatalogStatus =
  | 'NO_FILE'
  | 'NEEDS_RUN'
  | 'RUNNING'
  | 'TECHNICAL_FAILED'
  | 'HAS_ERRORS'
  | 'PASSED'

export interface CatalogStatusInfo {
  status: CatalogStatus
  label: string
  tone: 'neutral' | 'primary' | 'warning' | 'danger' | 'success'
  run?: RunSummary
  subtext: string
}

export function getCatalogStatus(item: CatalogEntry): CatalogStatusInfo {
  if (item.batch_summaries?.length) {
    const batches=item.batch_summaries
    if (batches.some(b=>b.status==='UNCHECKED'||b.status==='STALE'||b.status==='NEEDS_RULES'||b.status==='NO_FILE')) return {status:'NEEDS_RUN',label:'Đợt cần xử lý',tone:'warning',subtext:'Mở danh sách đợt để tải file, cấu hình quy tắc hoặc kiểm tra lại'}
    if (batches.some(b=>b.status==='RUNNING')) return {status:'RUNNING',label:'Có đợt đang chạy',tone:'primary',subtext:'Xem từng đợt'}
    if (batches.some(b=>b.status==='FAILED')) return {status:'TECHNICAL_FAILED',label:'Có đợt lỗi kỹ thuật',tone:'danger',subtext:'Xem từng đợt'}
    if (batches.some(b=>b.status==='HAS_ERRORS')) return {status:'HAS_ERRORS',label:'Có đợt vi phạm',tone:'warning',subtext:'Kết quả của bản hiện hành từng đợt'}
    return {status:'PASSED',label:'Đạt quy tắc',tone:'success',subtext:'Theo bản hiện hành từng đợt; không đồng nghĩa hoàn tất đợt'}
  }
  const latest = item.versions[0]
  if (!latest) {
    return {
      status: 'NO_FILE',
      label: 'Chưa có file',
      tone: 'neutral',
      subtext: 'Chưa tải file dữ liệu',
    }
  }
  const run = latestRun(item, latest.id)
  if (!run) {
    return {
      status: 'NEEDS_RUN',
      label: 'Chưa kiểm tra',
      tone: 'warning',
      subtext: `Phiên bản v${latest.version_number} chưa kiểm tra`,
    }
  }
  if (run.status === 'running') {
    return {
      status: 'RUNNING',
      label: 'Đang kiểm tra',
      tone: 'primary',
      run,
      subtext: `Đang thực thi lần #${run.run_id}`,
    }
  }
  if (run.status === 'failed') {
    return {
      status: 'TECHNICAL_FAILED',
      label: 'Lỗi kỹ thuật',
      tone: 'danger',
      run,
      subtext: `Lần #${run.run_id} · ${date(run.started_at)}`,
    }
  }
  if ((run.error_row_count ?? 0) > 0) {
    return {
      status: 'HAS_ERRORS',
      label: `Có lỗi (${number(run.error_row_count ?? 0)})`,
      tone: 'warning',
      run,
      subtext: `Lần #${run.run_id} · ${date(run.started_at)}`,
    }
  }
  return {
    status: 'PASSED',
    label: 'Đạt chuẩn',
    tone: 'success',
    run,
    subtext: `Lần #${run.run_id} · ${date(run.started_at)}`,
  }
}

export function CatalogPage({ datasets, actions }: { datasets: CatalogEntry[]; actions: DatasetActions }) {
  const cq=new URLSearchParams(location.hash.split('?')[1]),search=cq.get('catalog_q')??'',source=cq.get('catalog_source')??'',owner=cq.get('catalog_owner')??'',status=cq.get('catalog_status')??'',page=Math.max(1,Number(cq.get('catalog_page'))||1)
  function writeCatalog(patch:Record<string,string|null>,replace=false){const p=new URLSearchParams(location.hash.split('?')[1]);for(const [k,v] of Object.entries(patch)){if(v)p.set(k,v);else p.delete(k)}const href=location.hash.split('?')[0]+(p.size?'?'+p:'');if(replace){history.replaceState(null,'',href);dispatchEvent(new HashChangeEvent('hashchange'))}else if(href!==location.hash)location.hash=href}
  const setSearch=(v:string)=>writeCatalog({catalog_q:v||null,catalog_page:null},true),setSource=(v:string)=>writeCatalog({catalog_source:v||null,catalog_page:null}),setOwner=(v:string)=>writeCatalog({catalog_owner:v||null,catalog_page:null}),setStatus=(v:string)=>writeCatalog({catalog_status:v||null,catalog_page:null}),setPage=(v:number)=>writeCatalog({catalog_page:v>1?String(v):null})
  const [edit, setEdit] = useState<CatalogEntry | null>(null)
  const q = useDebounced(search)
  const localFilters = !!source || !!owner || !!status
  const list = useLoad(signal => catalogSelection(datasets, q, page, localFilters, signal), [datasets, q, page, localFilters])

  const filtered = (list.data?.items ?? []).filter(item => {
    const info = getCatalogStatus(item)
    const matchesSource = !source || item.source === source
    const matchesOwner = !owner || item.owner === owner
    const matchesStatus = !status || (
      (status === 'no_file' && info.status === 'NO_FILE') ||
      (status === 'needs_run' && info.status === 'NEEDS_RUN') ||
      (status === 'running' && info.status === 'RUNNING') ||
      (status === 'failed' && info.status === 'TECHNICAL_FAILED') ||
      (status === 'errors' && info.status === 'HAS_ERRORS') ||
      (status === 'passed' && info.status === 'PASSED')
    )
    return matchesSource && matchesOwner && matchesStatus
  })

  const visible = localFilters ? filtered.slice((page - 1) * 10, page * 10) : filtered
  const total = localFilters ? filtered.length : list.data?.total ?? 0



  const hasAnyFilter = Boolean(search || source || owner || status)
  function handleResetFilters() {writeCatalog({catalog_q:null,catalog_source:null,catalog_owner:null,catalog_status:null,catalog_page:null})
  }

  const distinctSources = [...new Set(datasets.map(item => item.source).filter(Boolean))].sort()
  const distinctOwners = [...new Set(datasets.map(item => item.owner).filter(Boolean))].sort()

  return (
    <>
      <PageTitle
        eyebrow="KHÔNG GIAN DỮ LIỆU"
        title="Danh mục dữ liệu"
        description="Tìm đúng dữ liệu, biết ai phụ trách và theo dõi từng phiên bản."
        action={
          <Button tone="primary" onClick={() => actions.create()}>
            <Plus size={18} />Tạo bộ dữ liệu
          </Button>
        }
      />
      <section className="panel">
        <div className="catalog-top">
          <div className="inline-title">
            <h2>Tất cả bộ dữ liệu</h2>
            <span className="count-pill">{number(datasets.length)}</span>
          </div>
          <span className="muted">Dữ liệu được lưu trên hệ thống</span>
        </div>

        <div className="filter-bar catalog-filter-bar">
          <Field label="Tìm kiếm">
            <div className="search-input">
              <Search size={17} />
              <input
                type="search"
                value={search}
                onChange={event => setSearch(event.target.value)}
                placeholder="Tìm theo tên, mô tả, nguồn hoặc người phụ trách…"
                maxLength={200}
              />
              {search && (
                <button
                  type="button"
                  className="search-clear-btn"
                  aria-label="Xóa từ khóa tìm kiếm"
                  onClick={() => setSearch('')}
                >
                  <X size={15} />
                </button>
              )}
            </div>
          </Field>
          <Field label="Nguồn / bộ phận">
            <select value={source} onChange={event => setSource(event.target.value)}>
              <option value="">Tất cả nguồn / bộ phận</option>
              {distinctSources.map(value => (
                <option key={value!} value={value!}>{value}</option>
              ))}
            </select>
          </Field>
          <Field label="Người phụ trách">
            <select value={owner} onChange={event => setOwner(event.target.value)}>
              <option value="">Tất cả người phụ trách</option>
              {distinctOwners.map(value => (
                <option key={value!} value={value!}>{value}</option>
              ))}
            </select>
          </Field>
          <Field label="Trạng thái kiểm tra">
            <select value={status} onChange={event => setStatus(event.target.value)}>
              <option value="">Tất cả trạng thái</option>
              <option value="no_file">Chưa có file CSV</option>
              <option value="needs_run">Chưa kiểm tra</option>
              <option value="running">Đang kiểm tra</option>
              <option value="errors">Có lỗi dữ liệu</option>
              <option value="passed">Đạt chuẩn</option>
              <option value="failed">Lỗi kỹ thuật</option>
            </select>
          </Field>
          {hasAnyFilter && (
            <div className="filter-reset-action">
              <Button tone="ghost" onClick={handleResetFilters} title="Xóa tất cả điều kiện lọc">
                <RotateCcw size={15} />Đặt lại bộ lọc
              </Button>
            </div>
          )}
        </div>

        {hasAnyFilter && (
          <div className="catalog-filter-summary">
            <span>
              Đang hiển thị <strong>{filtered.length}</strong> / {datasets.length} bộ dữ liệu
            </span>
            {search && <span className="catalog-filter-pill">Từ khóa: &ldquo;{search}&rdquo;</span>}
            {source && <span className="catalog-filter-pill">Nguồn: {source}</span>}
            {owner && <span className="catalog-filter-pill">Phụ trách: {owner}</span>}
            {status && (
              <span className="catalog-filter-pill">
                Trạng thái:{' '}
                {status === 'no_file'
                  ? 'Chưa có file'
                  : status === 'needs_run'
                  ? 'Chưa kiểm tra'
                  : status === 'running'
                  ? 'Đang kiểm tra'
                  : status === 'errors'
                  ? 'Có lỗi dữ liệu'
                  : status === 'passed'
                  ? 'Đạt chuẩn'
                  : 'Lỗi kỹ thuật'}
              </span>
            )}
          </div>
        )}

        {localFilters && (
          <p className="helper-text panel-pad catalog-filter-disclaimer">
            Tìm kiếm từ khóa được thực hiện trực tiếp trên máy chủ. Bộ lọc Nguồn, Người phụ trách và Trạng thái được áp dụng trên tập dữ liệu tải về do máy chủ chưa hỗ trợ lọc nhiều chiều kết hợp.
          </p>
        )}

        <LoadState loading={list.loading} error={list.error} retry={list.reload} />

        {list.data && (
          filtered.length ? (
            <>
              <div className="table-scroll">
                <table className="catalog-table">
                  <thead>
                    <tr>
                      <th scope="col">Bộ dữ liệu</th>
                      <th scope="col">Nguồn & Phụ trách</th>
                      <th scope="col">Phiên bản CSV</th>
                      <th scope="col">Trạng thái kiểm tra</th>
                      <th scope="col">Cập nhật</th>
                      <th scope="col" className="text-right">Thao tác tiếp theo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map(item => {
                      const latest = item.versions[0]
                      const statusInfo = getCatalogStatus(item)
                      const run = statusInfo.run
                      return (
                        <tr key={item.id}>
                          <td className="catalog-cell-main">
                            <a className="dataset-link" href={`#/datasets/${item.id}/overview`}>
                              <DatasetMark name={item.name} small />
                              <div className="dataset-link-text">
                                <strong className="dataset-name">{item.name}</strong>
                                <span className="dataset-desc">{item.description || 'Chưa có mô tả'}</span>
                              </div>
                            </a>
                          </td>
                          <td className="catalog-cell-meta">
                            <div className="meta-stack">
                              <span className="meta-source">{item.source || '—'}</span>
                              <span className="meta-owner muted">{item.owner || 'Chưa ghi nhận'}</span>
                            </div>
                          </td>
                          <td className="catalog-cell-version">
                            {latest ? (
                              <div className="version-stack">
                                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                                  <span className="version-tag">File mới nhập: v{latest.version_number} · Đợt #{latest.batch_id}</span>
                                  {typeof item.batch_count === 'number' && item.batch_count > 0 && (
                                    <span className="badge badge-subtle">{item.batch_count} đợt</span>
                                  )}
                                </div>
                                <small className="muted">{number(latest.row_count)} bản ghi</small>
                              </div>
                            ) : (
                              <div className="version-stack">
                                <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                                  <span className="badge badge-muted">Chưa có dữ liệu</span>
                                  {typeof item.batch_count === 'number' && item.batch_count > 0 && (
                                    <span className="badge badge-subtle">{item.batch_count} đợt</span>
                                  )}
                                </div>
                                <small className="muted">Chưa tải CSV</small>
                              </div>
                            )}
                          </td>
                          <td className="catalog-cell-quality">
                            <div className="quality-stack">
                              <Badge tone={statusInfo.tone}>{statusInfo.label}</Badge>
                              <small className="muted">{statusInfo.subtext}</small>
                            </div>
                          </td>
                          <td className="catalog-cell-date nowrap">
                            {date(item.updated_at, false)}
                          </td>
                          <td className="catalog-cell-action text-right">
                            <div className="catalog-action-group">
                              {item.batch_summaries?.length ? <a className="button button-primary" href={`#/datasets/${item.id}/batches`}>Mở các đợt</a> : <>
                              {statusInfo.status === 'NO_FILE' && (
                                <a className="button button-primary" href={`#/datasets/${item.id}/batches`}>Tạo hoặc chọn đợt</a>
                              )}
                              {statusInfo.status === 'NEEDS_RUN' && (
                                <Button tone="primary" onClick={() => actions.run(item, latest?.id)}>
                                  <Play size={14} />Chạy kiểm tra
                                </Button>
                              )}
                              {statusInfo.status === 'RUNNING' && (
                                <Button tone="ghost" disabled>
                                  <LoaderCircle className="spin" size={14} />Đang kiểm tra
                                </Button>
                              )}
                              {statusInfo.status === 'TECHNICAL_FAILED' && (
                                <Button tone="secondary" onClick={() => actions.run(item, latest?.id)}>
                                  <Play size={14} />Thử lại
                                </Button>
                              )}
                              {statusInfo.status === 'HAS_ERRORS' && run && (
                                <a className="button button-primary" href={`#/datasets/${item.id}/runs/${run.run_id}`}>
                                  <AlertCircle size={14} />Xem lỗi
                                </a>
                              )}
                              {statusInfo.status === 'PASSED' && run && (
                                <a className="button button-secondary" href={`#/datasets/${item.id}/runs/${run.run_id}`}>
                                  <Eye size={14} />Xem kết quả
                                </a>
                              )}
                              </>}
                              <Button
                                tone="ghost"
                                aria-label={`Chỉnh sửa ${item.name}`}
                                onClick={() => setEdit(item)}
                                title="Chỉnh sửa thông tin"
                              >
                                <Pencil size={15} />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <Pager page={page} total={total} change={setPage} />
            </>
          ) : (
            <Empty
              title={datasets.length ? 'Không tìm thấy bộ dữ liệu phù hợp' : 'Chưa có bộ dữ liệu nào'}
              text={
                datasets.length
                  ? 'Không có bộ dữ liệu nào khớp với điều kiện tìm kiếm hoặc bộ lọc hiện tại. Thử đổi từ khóa hoặc đặt lại bộ lọc.'
                  : 'Tạo bộ dữ liệu mới và bắt đầu quản lý thông tin tập trung cho doanh nghiệp.'
              }
              action={
                datasets.length ? (
                  <Button onClick={handleResetFilters}>
                    <RotateCcw size={15} />Đặt lại bộ lọc
                  </Button>
                ) : (
                  <Button tone="primary" onClick={() => actions.create()}>
                    <Plus size={17} />Tạo bộ dữ liệu
                  </Button>
                )
              }
            />
          )
        )}
      </section>
      {edit && <MetadataDialog dataset={edit} onClose={() => setEdit(null)} saved={actions.changed} />}
    </>
  )
}

export interface WorkspaceTabItem {
  id: string
  label: string
}

export interface WorkspaceTabGroup {
  id: string
  label: string
  tabs: WorkspaceTabItem[]
}

export const WORKSPACE_TAB_GROUPS: WorkspaceTabGroup[] = [
  {
    id: 'inspection',
    label: 'Bộ dữ liệu & Đợt',
    tabs: [
      { id: 'overview', label: 'Thông tin & Đợt dữ liệu' },
      { id: 'batches', label: 'Đợt dữ liệu' },
      { id: 'rules', label: 'Quy tắc mẫu' },
    ],
  },
  {
    id: 'history_improvement',
    label: 'Lịch sử & Cải thiện',
    tabs: [
      { id: 'history', label: 'Lần kiểm tra · tất cả đợt' },
      { id: 'versions', label: 'Phiên bản · tất cả đợt' },
      { id: 'compare', label: 'Đối chiếu lần chạy' },
      { id: 'trend', label: 'Xu hướng chất lượng' },
    ],
  },
  {
    id: 'structure_info',
    label: 'Cấu trúc & Thông tin',
    tabs: [
      { id: 'fields', label: 'Cột & Kiểu dữ liệu' },
    ],
  },
]

export function DatasetPage({ dataset, tab, actions, userRole }: { dataset: CatalogEntry; tab: string; actions: DatasetActions;userRole?:string }) {
  const [edit, setEdit] = useState(false)
  const [createBatchOpen, setCreateBatchOpen] = useState(false)
  const [uploadBatch, setUploadBatch] = useState<DataBatchItem | null>(null)
  const uploadSaved=useRef(false)
  const [column, setColumn] = useState<DatasetColumn | null>(null)
  const [preview, setPreview] = useState<DatasetVersion | null>(null)
  // The dataset workspace stays mounted across tabs. Back must dismiss its preview.
  useEffect(() => { setPreview(null) }, [tab])
  const fieldsVersion=new URLSearchParams(location.hash.split('?')[1]).get('fields_version')??''
  const setFieldsVersion=(value:string)=>{const p=new URLSearchParams(location.hash.split('?')[1]);p.set('fields_version',value);location.hash=location.hash.split('?')[0]+'?'+p}
  const scopeQuery=new URLSearchParams(location.hash.split('?')[1])
  const workspaceScope=tab==='compare'?comparisonScope(dataset,scopeQuery):queryBatch(scopeQuery)
  const scoped=isScopeId(workspaceScope)
  const tabHref=(id:string)=>scoped&&id==='history'?historyHref(dataset.id,workspaceScope):scoped&&id==='compare'?comparisonHref(dataset.id,workspaceScope):`#/datasets/${dataset.id}/${id}`
  const latest = dataset.versions[0]
  const inferenceVersion = dataset.versions.find(item => String(item.id) === fieldsVersion) ?? latest
  const batchNames=useLoad(signal=>allPages<DataBatchItem>(`/api/datasets/${dataset.id}/batches`,signal),[dataset.id])
  const batchName=(id?:number)=>batchText(batchNames.data?.find(b=>b.id===id))

  return (
    <>
      <a className="back-link" href="#/datasets">
        <ArrowLeft size={15} />Bộ dữ liệu <span>/</span> {dataset.name}
      </a>
      <div className="detail-title"><DatasetMark name={dataset.name}/><PageTitle title={dataset.name} description={dataset.description||'Thông tin chung và các kỳ tiếp nhận của loại dữ liệu này.'} action={<><Button onClick={()=>setEdit(true)}>Sửa thông tin chung</Button><Button tone="primary" onClick={()=>setCreateBatchOpen(true)}><FolderPlus size={16}/>Tạo đợt dữ liệu</Button></>}/></div>
      <div className="detail-meta">
        <span><UserRound size={15} />{dataset.owner || 'Chưa có người phụ trách'}</span>
        <span><Database size={15} />{dataset.source || 'Chưa ghi nguồn dữ liệu'}</span>
        <span><CalendarDays size={15} />Cập nhật {date(dataset.updated_at)}</span>
      </div>
      <Notice>Bộ dữ liệu quản lý lâu dài; kết quả thuộc từng đợt và phiên bản. <a href={`#/datasets/${dataset.id}/batches`}>Mở các đợt dữ liệu</a> để chọn bản hiện hành và quy tắc riêng. Quy tắc ở cấp bộ dữ liệu là mẫu cho đợt mới.</Notice>
      <div className="workspace-tab-groups" role="navigation" aria-label="Phân nhóm chức năng bộ dữ liệu">
        {WORKSPACE_TAB_GROUPS.map(group => {
          const isGroupActive = group.tabs.some(item => item.id === tab)
          return (
            <div key={group.id} className={`workspace-tab-group ${isGroupActive ? 'group-active' : ''}`}>
              <span className="workspace-tab-group-label">{group.label}</span>
              <div className="workspace-tab-items" role="tablist">
                {group.tabs.map(item => {
                  const isActive = tab === item.id
                  return (
                    <a
                      key={item.id}
                      href={tabHref(item.id)}
                      role="tab"
                      aria-selected={isActive}
                      className={`workspace-tab-btn ${isActive ? 'active' : ''}`}
                    >
                      <span>{scoped&&item.id==='history'?'Lịch sử kiểm tra của đợt':scoped&&item.id==='compare'?'Đối chiếu trong đợt':item.label}</span>
                      {item.id === 'batches' && typeof dataset.batch_count === 'number' && dataset.batch_count > 0 && (
                        <span className="tab-badge">{dataset.batch_count}</span>
                      )}
                      {item.id === 'versions' && dataset.versions.length > 0 && (
                        <span className="tab-badge">{dataset.versions.length}</span>
                      )}
                    </a>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
      {tab==='overview'&&<><section className="panel panel-pad"><h2>Thông tin chung</h2><p>{dataset.description||'Chưa có mô tả.'}</p><p>Chọn một đợt bên dưới để xem hoặc tải CSV, thiết lập quy tắc và chạy kiểm tra. Mỗi đợt giữ các phiên bản và lịch sử riêng.</p></section><IdentityPanel dataset={dataset} role={userRole}/><BatchesSection dataset={dataset} actions={actions} onOpenCreate={()=>setCreateBatchOpen(true)} onUploadBatch={setUploadBatch}/></>}
      {tab === 'batches' && (
        <BatchesSection
          dataset={dataset}
          actions={actions}
          onOpenCreate={() => setCreateBatchOpen(true)}
          onUploadBatch={b => setUploadBatch(b)}
        />
      )}
    {tab === 'fields' && <section className="panel"><div className="panel-heading"><div><h2>Giải thích các trường dữ liệu</h2><p>Kiểu dữ liệu là đề xuất từ phiên bản CSV đang chọn, cần người phụ trách xác nhận.</p></div></div>
      {!dataset.columns.length ? (
        <Empty
          title="Chưa có thông tin trường dữ liệu"
          text="Bộ dữ liệu chưa có file nào. Hãy tải file CSV đầu tiên để hệ thống tự động nhận diện các cột."
          action={<a className="button button-primary" href={`#/datasets/${dataset.id}/batches`}>Chọn đợt để tải CSV</a>}
        />
      ) : (
        <>
          <Notice>Tên hiển thị, kiểu dữ liệu đã xác nhận và ví dụ riêng chưa được hệ thống lưu. Bạn có thể ghi ý nghĩa và ví dụ trong phần mô tả trường.</Notice>
          <div className="filter-bar"><Field label="Phiên bản xem suy luận"><select value={inferenceVersion?.id ?? ''} onChange={event => setFieldsVersion(event.target.value)}>{dataset.versions.map(item => <option key={item.id} value={item.id}>{batchName(item.batch_id)} · v{item.version_number} · {item.original_filename}</option>)}</select></Field></div>
          <div className="table-scroll"><table><thead><tr><th>Tên cột</th><th>Kiểu được đề xuất</th><th>Ý nghĩa và ví dụ</th><th></th></tr></thead><tbody>{dataset.columns.map(item => <tr key={item.id}><td><code>{item.name}</code></td><td><InferenceDetails version={inferenceVersion} column={item.name} /></td><td className="wrap-cell">{item.description || <span className="muted">Chưa có mô tả</span>}</td><td><Button tone="ghost" onClick={() => setColumn(item)}><Pencil size={15} />Mô tả</Button></td></tr>)}</tbody></table></div>
        </>
      )}
    </section>}
    {tab==='versions'&&<section className="panel"><div className="panel-heading"><div><h2>Lịch sử phiên bản · tất cả đợt</h2><p>Tổng hợp các file đã nhập trong {dataset.name}. Số v1, v2… được tính riêng trong từng đợt.</p></div><a className="button button-secondary" href={`#/datasets/${dataset.id}/batches`}>Chọn đợt để tải CSV</a></div><LoadState loading={batchNames.loading} error={batchNames.error} retry={batchNames.reload}/>{!dataset.versions.length?<Empty title="Chưa có phiên bản" text="Tạo hoặc chọn đợt dữ liệu rồi tải CSV đầu tiên."/>:<div className="table-scroll"><table><thead><tr><th>Đợt dữ liệu</th><th>Phiên bản</th><th>File</th><th>Ngày tải</th><th>Bản ghi</th><th>Kết quả</th><th>Thao tác</th></tr></thead><tbody>{dataset.versions.map(v=><tr key={v.id}><td><a href={`#/datasets/${dataset.id}/batches/${v.batch_id}`}>{batchName(v.batch_id)}</a></td><td>v{v.version_number}<small>{v.is_current?'Hiện hành của đợt':'Lịch sử'}</small></td><td>{v.original_filename}</td><td>{date(v.imported_at)}</td><td>{number(v.row_count)}</td><td><QualityBadge run={latestRun(dataset,v.id)}/></td><td><Button onClick={()=>setPreview(v)}>Xem dữ liệu</Button><a className="button button-ghost" href={`#/datasets/${dataset.id}/batches/${v.batch_id}`}>Mở đợt</a></td></tr>)}</tbody></table></div>}</section>}
    {tab === 'rules' && <RulesPage datasets={[dataset]} embedded />}
    {tab === 'history' && <HistoryPage key={location.hash} datasets={[dataset]} embedded run={() => actions.run(dataset)} />}
    {tab === 'compare' && <Comparison key={location.hash} dataset={dataset} />}
    {tab === 'trend' && <QualityTrend dataset={dataset} />}
    {edit && <MetadataDialog dataset={dataset} onClose={() => setEdit(false)} saved={actions.changed} />}
    {column && <MetadataDialog dataset={dataset} column={column} onClose={() => setColumn(null)} saved={actions.changed} />}
    {preview && <PreviewDialog scopeName={batchName(preview.batch_id)} dataset={dataset} version={preview} onClose={() => setPreview(null)} />}
    {createBatchOpen && (
      <CreateBatchDialog
        datasetId={dataset.id}
        datasetName={dataset.name}
        onClose={() => setCreateBatchOpen(false)}
        onCreated={batchId => {
          actions.changed()
          location.hash = `#/datasets/${dataset.id}/batches/${batchId}`
        }}
      />
    )}
    {uploadBatch && (
      <UploadDialog
        dataset={dataset}
        batch={uploadBatch}
        onClose={() => {setUploadBatch(null);if(uploadSaved.current){uploadSaved.current=false;actions.changed()}}}
        onSaved={() => {uploadSaved.current=true}}
        next={(id,t,batchId,versionId)=>{setUploadBatch(null);location.hash=`#/datasets/${id}/batches/${batchId}${t==='rules'?'?rules=1':''}`;if(t==='run'&&versionId)actions.run(dataset,versionId)}}
      />
    )}
  </>
  )
}

export function BatchesSection({
  dataset,
  actions,
  onOpenCreate,
  onUploadBatch,
}: {
  dataset: CatalogEntry
  actions: DatasetActions
  onOpenCreate: () => void
  onUploadBatch: (batch: DataBatchItem) => void
}) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const q = useDebounced(search)
  const batches = useLoad(
    signal => listBatches(dataset.id, page, 10, q || undefined, signal),
    [dataset.id, page, q]
  )

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Các đợt dữ liệu (Data Batches)</h2>
          <p>Quản lý dữ liệu theo từng kỳ tiếp nhận (tháng, quý, đợt đối soát). Mỗi đợt có chu kỳ phiên bản độc lập (v1, v2...).</p>
        </div>
        <Button tone="primary" onClick={onOpenCreate}>
          <FolderPlus size={16} />Tạo đợt dữ liệu
        </Button>
      </div>

      <div className="panel-pad batch-search-bar" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <input
          type="search"
          placeholder="Tìm đợt dữ liệu theo tên, kỳ dữ liệu, mô tả..."
          value={search}
          onChange={e => {
            setSearch(e.target.value)
            setPage(1)
          }}
          style={{ maxWidth: 360 }}
        />
        {search && (
          <Button tone="ghost" onClick={() => { setSearch(''); setPage(1) }}>
            Xóa tìm kiếm
          </Button>
        )}
      </div>

      <LoadState loading={batches.loading} error={batches.error} retry={batches.reload} />

      {batches.data && (
        batches.data.items.length ? (
          <>
            <div className="table-scroll">
              <table className="batch-table">
                <thead>
                  <tr>
                    <th scope="col">Đợt dữ liệu</th>
                    <th scope="col">Kỳ dữ liệu</th>
                    <th scope="col">Mô tả</th>
                    <th scope="col">Phiên bản</th>
                    <th scope="col">Ngày tạo</th>
                    <th scope="col" className="text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {batches.data.items.map(batch => (
                    <tr key={batch.id}>
                      <td className="catalog-cell-main">
                        <a className="dataset-link" href={`#/datasets/${dataset.id}/batches/${batch.id}`}>
                          <FolderOpen size={20} className="icon-folder" />
                          <div className="dataset-link-text">
                            <strong className="dataset-name">{batch.name}</strong><small>{supplierLabel(batch.supplier)}</small>
                          </div>
                        </a>
                      </td>
                      <td>
                        {batch.period_label ? (
                          <span className="badge badge-subtle">{batch.period_label}</span>
                        ) : (
                          <span className="muted">—</span>
                        )}
                      </td>
                      <td className="wrap-cell text-muted" style={{ maxWidth: 300 }}>
                        {batch.description || <span className="muted">Chưa có mô tả</span>}
                      </td>
                      <td>
                        {batch.version_count === 0 ? (
                          <span className="badge badge-muted">Chưa có file (v0)</span>
                        ) : (
                          <div className="version-stack">
                            <span className="version-tag">v{batch.version_count}</span>
                            <small className="muted">{batch.version_count} phiên bản</small>
                          </div>
                        )}
                      </td>
                      <td className="nowrap muted">{date(batch.created_at, false)}</td>
                      <td className="text-right">
                        <div className="catalog-action-group" style={{ justifyContent: 'flex-end' }}>
                          <a
                            className="button button-ghost"
                            href={`#/datasets/${dataset.id}/batches/${batch.id}`}
                            title="Xem chi tiết đợt"
                          >
                            <Eye size={14} />Chi tiết
                          </a>
                          {batch.version_count === 0 ? (
                            <Button disabled={batch.business_state==='COMPLETED'} tone="primary" onClick={() => onUploadBatch(batch)}>
                              <Upload size={14} />Tải file v1
                            </Button>
                          ) : (
                            <Button disabled={batch.business_state==='COMPLETED'} tone="secondary" onClick={() => onUploadBatch(batch)}>
                              <Upload size={14} />Tải bản sửa
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pager page={page} total={batches.data.total} change={setPage} />
          </>
        ) : (
          <Empty
            title={search ? 'Không tìm thấy đợt dữ liệu nào phù hợp' : 'Chưa có đợt dữ liệu nào'}
            text={
              search
                ? 'Không tìm thấy đợt dữ liệu khớp với từ khóa. Thử đổi từ khóa tìm kiếm.'
                : 'Tạo đợt dữ liệu đầu tiên (ví dụ: Khách hàng tháng 10/2026) để bắt đầu chu trình tiếp nhận và kiểm tra.'
            }
            action={
              search ? (
                <Button onClick={() => { setSearch(''); setPage(1) }}>Đặt lại</Button>
              ) : (
                <Button tone="primary" onClick={onOpenCreate}>
                  <FolderPlus size={16} />Tạo đợt dữ liệu đầu tiên
                </Button>
              )
            }
          />
        )
      )}
    </section>
  )
}

function PreviewDialog({ dataset, version, onClose, scopeName }: { dataset: CatalogEntry; version: DatasetVersion; onClose: () => void; scopeName?: string }) {
  const [page, setPage] = useState(1)
  const rows = useLoad(signal => request<RowsPage>(`/api/datasets/${dataset.id}/versions/${version.id}/rows?page=${page}&page_size=10`, signal), [dataset.id, version.id, page])
  return <Dialog title={`Phiên bản ${version.version_number} · Xem trước`} description={`${dataset.name} / ${scopeName} · v${version.version_number} · ${version.is_current ? 'Bản hiện hành' : 'Bản lịch sử'} · ${version.original_filename}`} onClose={onClose} wide><LoadState loading={rows.loading} error={rows.error} retry={rows.reload} />{rows.data && <><div className="table-scroll"><table><thead><tr><th>Bản ghi</th>{rows.data.header.map(name => <th key={name}>{name}</th>)}</tr></thead><tbody>{rows.data.items.map(item => <tr key={item.row_number}><td>{item.row_number}</td>{item.values.map((value, index) => <td key={index}><CellValue value={value} /></td>)}</tr>)}</tbody></table></div><Pager page={page} total={rows.data.total} change={setPage} /><p className="helper-text">Bản ghi 1 bắt đầu sau dòng tiêu đề. Giá trị được giữ nguyên như file CSV.</p></>}</Dialog>
}

export function RulesPage({ datasets, embedded = false }: { datasets: CatalogEntry[]; embedded?: boolean }) {
  return <RuleList datasets={datasets} embedded={embedded} />
}
