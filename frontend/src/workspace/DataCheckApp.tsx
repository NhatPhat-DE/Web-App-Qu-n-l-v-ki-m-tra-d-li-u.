import { runBatch, batchHref, queryBatch, comparisonScope } from './scopeNavigation'
import { lazy, Suspense, useEffect, useState } from 'react'
import {
  BookOpen,
  ChevronRight,
  Database,
  FolderClosed,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  RefreshCw,
  Users,
  X,
} from 'lucide-react'
import type { AuthUser } from '../api/auth'
import { loadCatalog } from './api'
import type { CatalogEntry } from './api'
import { Button, Empty, LoadState, Notice, confirmLeave, useLoad } from './ui'
const Dashboard=lazy(()=>import('./BatchDashboard'))
import { boards } from './workModel'
const OperationalScreens=lazy(()=>import('./OperationalScreens'))
import CatalogDictionary from './CatalogDictionary'
import type { OperationalView } from './OperationalScreens'
import { CatalogPage, DatasetPage, RulesPage } from './CatalogPages'
import type { DatasetActions } from './CatalogPages'
import { HistoryPage } from './HistoryPage'
import Guide from './Guide'
import Results from './Results'
import BatchDetailPage from './BatchDetailPage'
import CreateDatasetDialog from './CreateDatasetDialog'
import UploadDialog from './UploadDialog'
import RunDialog from './RunDialog'
import Accounts from './Accounts'
import SystemStatus from './SystemStatus'
import { ThemeSwitcher } from './ThemeSwitcher'

export interface NavItem {
  id: string
  label: string
  path: string
  Icon: typeof LayoutDashboard
  code?:string
  adminOnly?: boolean
  badgeCount?: (datasets: CatalogEntry[]) => number | null
}

export const MAIN_NAVIGATION: NavItem[] = [
  {id:'dashboard',label:'Dashboard',code:'M9',path:'#/dashboard',Icon:LayoutDashboard},
  {id:'datasets',label:'Danh mục & Từ điển',code:'M2·M3',path:'#/datasets',Icon:FolderClosed},
  {id:'rules',label:'Quy tắc kiểm tra',code:'M4',path:'#/rules',Icon:ListChecks},
  {id:'submit',label:'Nộp & Kiểm tra',code:'M5·M6',path:'#/submit',Icon:Database},
  {id:'issues',label:'Quản lý lỗi',code:'M7',path:'#/issues',Icon:ListChecks},
  {id:'compare',label:'Đối soát phiên bản',code:'M8',path:'#/compare',Icon:ListChecks},
  {id:'reporting',label:'Báo cáo',code:'BC',path:'#/reporting',Icon:BookOpen},
  {id:'accounts',label:'Quản trị hệ thống',code:'M1',path:'#/accounts',Icon:Users,adminOnly:true},
  {id:'guide',label:'Trợ giúp',code:'?',path:'#/guide',Icon:BookOpen},
]
const legacyWorkView:Record<string,OperationalView>={intake:'submit',quality:'submit',setup:'rules',resolution:'issues',acceptance:'issues',reports:'reports'}

export function normalizeRoute(hash: string): string {
  const clean = hash.replace(/^#\/?/, '').split('?')[0].trim()
  if (!clean || clean === 'home') return 'dashboard'
  if (clean === 'reports') return 'history'
  if (clean === 'admin') return 'accounts'
  if (clean === 'help') return 'guide'

  const segments = clean.split('/')
  if (segments[0] === 'datasets' && segments[1] && !segments[2]) {
    return `datasets/${segments[1]}/overview`
  }
  return clean
}

type Modal =
  | { kind: 'create' }
  | { kind: 'upload'; dataset?: CatalogEntry }
  | { kind: 'run'; dataset?: CatalogEntry; version?: number }
  | { kind: 'system' }
  | null

export default function DataCheckApp({
  user,
  logoutBusy,
  logoutMessage,
  onLogout,
  onCheckSession,
}: {
  user: AuthUser
  logoutBusy: boolean
  logoutMessage: string
  onLogout: () => void
  onCheckSession: () => void
}) {
  const [route, setRoute] = useState(() => normalizeRoute(location.hash) + (location.hash.includes('?') ? '?' + location.hash.split('?')[1] : ''))
  const [menu, setMenu] = useState(false)
  const [modal, setModal] = useState<Modal>(null)
  const [success, setSuccess] = useState('')
  const catalog = useLoad(loadCatalog, [])

  useEffect(() => {
    let current = location.hash
    const change = () => {
      if (!confirmLeave()) {
        history.replaceState(null, '', current || '#/dashboard')
        return
      }
      current = location.hash
      const normalized = normalizeRoute(location.hash)
      if (
        location.hash.slice(2) !== normalized &&
        ['home', 'reports', 'admin', 'help'].includes(location.hash.slice(2))
      ) {
        history.replaceState(null, '', `#/${normalized}`)
      }
      setRoute(normalized + (location.hash.includes('?') ? '?' + location.hash.split('?')[1] : ''))
      setMenu(false)
      setSuccess('')
      window.scrollTo({ top: 0 })
      document.getElementById('main')?.focus()
    }
    window.addEventListener('hashchange', change)
    return () => window.removeEventListener('hashchange', change)
  }, [])

  const parts = route.split('?')[0].split('/')
  const datasets = catalog.data ?? []
  const dataset =
    parts[0] === 'datasets' && parts[1]
      ? datasets.find(item => item.id === Number(parts[1]))
      : undefined

  const actions: DatasetActions = {
    create: () => setModal({ kind: 'create' }),
    upload: (item?: CatalogEntry) => {
      if (!item) setModal({ kind: 'create' })
      else setModal({ kind: 'upload', dataset: item })
    },
    run: (item?: CatalogEntry, version?: number) => setModal({ kind: 'run', dataset: item, version }),
    changed: () => {
      setSuccess('Đã cập nhật dữ liệu.')
      catalog.reload()
    },
  }

  const isDetail = parts[0] === 'datasets' && !!parts[1]
  const operational=parts[0]==='work'?legacyWorkView[parts[1]]:({submit:'submit',rules:'rules',issues:'issues',compare:'compare',reporting:'reports'} as Record<string,OperationalView>)[parts[0]]
  const isAccounts = parts[0] === 'accounts'

  // Filter navigation items by role
  const visibleNav = MAIN_NAVIGATION.filter(item => !item.adminOnly || user.role === 'admin')

  // Render Topbar Breadcrumb according to current location hierarchy
  const renderBreadcrumb = () => {
    if (parts[0] === 'dashboard') {
      return (
        <div className="breadcrumb">
          <Button
            className="mobile-menu"
            tone="ghost"
            aria-label="Mở menu"
            aria-expanded={menu}
            onClick={() => setMenu(true)}
          >
            <Menu size={21} />
          </Button>
          <span className="breadcrumb-root">DataGuard SME</span>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <strong>Trang chủ</strong>
        </div>
      )
    }

    if (parts[0] === 'datasets') {
      if (!parts[1]) {
        return (
          <div className="breadcrumb">
            <Button
              className="mobile-menu"
              tone="ghost"
              aria-label="Mở menu"
              aria-expanded={menu}
              onClick={() => setMenu(true)}
            >
              <Menu size={21} />
            </Button>
            <a href="#/dashboard" className="breadcrumb-root">Trang chủ</a>
            <ChevronRight size={14} className="breadcrumb-separator" />
            <strong>Bộ dữ liệu</strong>
          </div>
        )
      }

      const tabLabels: Record<string, string> = {
        overview: 'Thông tin & Đợt dữ liệu',
        batches: 'Đợt dữ liệu',
        rules: 'Quy tắc mẫu',
        history: 'Lần kiểm tra · tất cả đợt',
        compare: 'Đối chiếu lần chạy',
        trend: 'Xu hướng chất lượng',
        fields: 'Cột & Kiểu dữ liệu',
        versions: 'Lịch sử phiên bản · tất cả đợt',
      }

      if (parts[2] === 'batches' && parts[3]) {
        return (
          <div className="breadcrumb">
            <Button
              className="mobile-menu"
              tone="ghost"
              aria-label="Mở menu"
              aria-expanded={menu}
              onClick={() => setMenu(true)}
            >
              <Menu size={21} />
            </Button>
            <a href="#/datasets" className="breadcrumb-root">Bộ dữ liệu</a>
            <ChevronRight size={14} className="breadcrumb-separator" />
            <a
              href={`#/datasets/${parts[1]}/overview`}
              className="breadcrumb-link"
              title={dataset?.name ?? 'Bộ dữ liệu'}
            >
              {dataset?.name ?? `Bộ dữ liệu #${parts[1]}`}
            </a>
            <ChevronRight size={14} className="breadcrumb-separator" />
            <a
              href={`#/datasets/${parts[1]}/batches`}
              className="breadcrumb-link"
            >
              Đợt dữ liệu
            </a>
            <ChevronRight size={14} className="breadcrumb-separator" />
            <strong>{dataset?.batch_summaries?.find(b=>b.batch_id===Number(parts[3]))?.batch_name??'Đợt dữ liệu'}</strong>
          </div>
        )
      }

      const scopedBatchId = parts[2] === 'runs' ? (dataset && runBatch(dataset, Number(parts[3]))) : Number(parts[2]==='compare'&&dataset?comparisonScope(dataset,new URLSearchParams(route.split('?')[1])):queryBatch(new URLSearchParams(route.split('?')[1]))) || undefined
      const scopedBatch = dataset?.batch_summaries?.find(b => b.batch_id === scopedBatchId)
      const currentTab = parts[2] || 'overview'
      const leafLabel =
        parts[2] === 'runs' && parts[3]
          ? `Lần kiểm tra #${parts[3]}`
          : currentTab === 'history' && scopedBatchId ? 'Lịch sử kiểm tra của đợt' : tabLabels[currentTab] || 'Tổng quan'

      return (
        <div className="breadcrumb">
          <Button
            className="mobile-menu"
            tone="ghost"
            aria-label="Mở menu"
            aria-expanded={menu}
            onClick={() => setMenu(true)}
          >
            <Menu size={21} />
          </Button>
          <a href="#/datasets" className="breadcrumb-root">Bộ dữ liệu</a>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <a
            href={`#/datasets/${parts[1]}/overview`}
            className="breadcrumb-link"
            title={dataset?.name ?? 'Bộ dữ liệu'}
          >
            {dataset?.name ?? `Bộ dữ liệu #${parts[1]}`}
          </a>
          <ChevronRight size={14} className="breadcrumb-separator" />
          {scopedBatchId && <><a href={batchHref(Number(parts[1]),scopedBatchId)} className="breadcrumb-link" title={scopedBatch?.batch_name ?? 'Đợt dữ liệu'}>{scopedBatch?.batch_name ?? 'Đợt dữ liệu'}</a><ChevronRight size={14} className="breadcrumb-separator" /></>}
          <strong>{leafLabel}</strong>
        </div>
      )
    }

    if (parts[0] === 'history') {
      return (
        <div className="breadcrumb">
          <Button
            className="mobile-menu"
            tone="ghost"
            aria-label="Mở menu"
            aria-expanded={menu}
            onClick={() => setMenu(true)}
          >
            <Menu size={21} />
          </Button>
          <a href="#/dashboard" className="breadcrumb-root">Trang chủ</a>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <strong>Lịch sử & Báo cáo</strong>
        </div>
      )
    }

    if (parts[0] === 'rules') {
      return (
        <div className="breadcrumb">
          <Button
            className="mobile-menu"
            tone="ghost"
            aria-label="Mở menu"
            aria-expanded={menu}
            onClick={() => setMenu(true)}
          >
            <Menu size={21} />
          </Button>
          <a href="#/dashboard" className="breadcrumb-root">Trang chủ</a>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <strong>Quy tắc mẫu</strong>
        </div>
      )
    }

    if (parts[0] === 'accounts') {
      return (
        <div className="breadcrumb">
          <Button
            className="mobile-menu"
            tone="ghost"
            aria-label="Mở menu"
            aria-expanded={menu}
            onClick={() => setMenu(true)}
          >
            <Menu size={21} />
          </Button>
          <a href="#/dashboard" className="breadcrumb-root">Trang chủ</a>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <strong>Quản trị</strong>
        </div>
      )
    }

    if (operational) {
      return <div className="breadcrumb"><Button className="mobile-menu" tone="ghost" aria-label="Mở menu" aria-expanded={menu} onClick={()=>setMenu(true)}><Menu size={21}/></Button><a href="#/dashboard" className="breadcrumb-root">Trang chủ</a><ChevronRight size={14}/><strong>{{submit:'Nộp & Kiểm tra',rules:'Quy tắc kiểm tra',issues:'Quản lý lỗi',compare:'Đối soát phiên bản',reports:'Báo cáo'}[operational]}</strong></div>
    }

    if (parts[0] === 'guide') {
      return (
        <div className="breadcrumb">
          <Button
            className="mobile-menu"
            tone="ghost"
            aria-label="Mở menu"
            aria-expanded={menu}
            onClick={() => setMenu(true)}
          >
            <Menu size={21} />
          </Button>
          <a href="#/dashboard" className="breadcrumb-root">Trang chủ</a>
          <ChevronRight size={14} className="breadcrumb-separator" />
          <strong>Trợ giúp</strong>
        </div>
      )
    }

    return (
      <div className="breadcrumb">
        <Button
          className="mobile-menu"
          tone="ghost"
          aria-label="Mở menu"
          aria-expanded={menu}
          onClick={() => setMenu(true)}
        >
          <Menu size={21} />
        </Button>
        <a href="#/dashboard" className="breadcrumb-root">Trang chủ</a>
        <ChevronRight size={14} className="breadcrumb-separator" />
        <strong>Trang không tồn tại</strong>
      </div>
    )
  }

  return (
    <div className={`app-shell demo-shell ${!isDetail?'demo-top-level':''}`}>
      <a
        className="skip-link"
        href="#main"
        onClick={event => {
          event.preventDefault()
          document.getElementById('main')?.focus()
        }}
      >
        Chuyển đến nội dung chính
      </a>

      {menu && <div className="sidebar-overlay" onClick={() => setMenu(false)} />}

      <aside className={`sidebar ${menu ? 'is-open' : ''}`} aria-label="Điều hướng chính">
        <a href="#/dashboard" className="brand" aria-label="DataGuard SME — Về trang chủ">
          <span>
            <Database size={23} />
          </span>
          <div>
            Chất lượng dữ liệu
            <small>Kiểm soát dữ liệu · F&B</small>
          </div>
        </a>

        <Button
          className="mobile-close"
          tone="ghost"
          aria-label="Đóng menu"
          onClick={() => {
            setMenu(false)
            document.querySelector<HTMLButtonElement>('[aria-label="Mở menu"]')?.focus()
          }}
        >
          <X size={20} />
        </Button>

        <div className="workspace-label">
          <span className="workspace-avatar">DG</span>
          <div>
            Không gian dữ liệu SME
            <small>Quản lý & kiểm tra tập trung</small>
          </div>
          <ChevronRight size={15} />
        </div>

        <p className="nav-section">CÔNG VIỆC DỮ LIỆU</p>
        <nav aria-label="Menu chức năng chính">
          {visibleNav.map(({ id, label, path, Icon, badgeCount,code }) => {
            const isActive = (parts[0]==='work'?(operational==='reports'?'reporting':operational):parts[0]) === id
            const count = badgeCount ? badgeCount(datasets) : null
            return (
              <a
                key={id}
                href={path}
                className={isActive ? 'nav-item active' : 'nav-item'}
                aria-current={isActive ? 'page' : undefined}
              >
                {code?<b className="nav-code">{code}</b>:<Icon size={19}/>}
                <span>{label}</span>
                {count !== null && catalog.data && <small>{count}</small>}
              </a>
            )
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-help">
            <span className="help-icon">
              <BookOpen size={19} />
            </span>
            <strong>Lần đầu dùng DataGuard?</strong>
            <p>Tạo bộ dữ liệu → tạo đợt → tải CSV và kiểm tra.</p>
            <a href="#/guide">
              Xem hướng dẫn <ChevronRight size={15} />
            </a>
          </div>
          <div className="sidebar-footer">
            <span className="status-dot" />
            DataGuard SME sẵn sàng
          </div>
        </div>
      </aside>

      <div className="app-body">
        <header className="topbar">
          {renderBreadcrumb()}

          <div className="topbar-actions">
            <ThemeSwitcher />

            <div className="account">
              <div className="avatar">{user.username.slice(0, 2).toUpperCase()}</div>
              <div className="account-name">
                <strong>{user.username}</strong>
                <small>{user.role === 'data_owner' ? 'Data Owner' : user.role === 'admin' ? 'Quản trị viên' : 'Người quản lý dữ liệu'}</small>
              </div>
              <Button
                tone="ghost"
                aria-label="Đăng xuất"
                title="Đăng xuất"
                disabled={logoutBusy}
                onClick={() => {
                  if (confirmLeave()) onLogout()
                }}
              >
                <LogOut size={18} />
              </Button>
            </div>
          </div>
        </header>

        <main id="main" tabIndex={-1} className="main-content">
          {logoutMessage && (
            <Notice
              kind="warning"
              action={
                <Button disabled={logoutBusy} onClick={onCheckSession}>
                  Kiểm tra lại phiên
                </Button>
              }
            >
              {logoutMessage}
            </Notice>
          )}

          {success && <Notice kind="success">{success}</Notice>}

          <LoadState
            loading={catalog.loading && !isAccounts}
            error={isAccounts ? '' : catalog.error}
            retry={catalog.reload}
          />

          {(catalog.data || isAccounts) && (
            <>
              {isAccounts ? (
                user.role === 'admin' ? (
                  <Accounts user={user} />
                ) : (
                  <Empty
                    title="Không có quyền truy cập"
                    text="Chức năng quản trị chỉ dành cho tài khoản quản trị viên."
                    action={
                      <a href="#/dashboard" className="button button-primary">
                        Về trang chủ
                      </a>
                    }
                  />
                )
              ) : isDetail ? (
                dataset ? (
                  parts[2] === 'runs' && /^\d+$/.test(parts[3] ?? '') ? (
                    <Results
                      key={`${dataset.id}:${parts[3]}`}
                      dataset={dataset}
                      runId={Number(parts[3])}
                      userRole={user.role}
                      upload={() => actions.upload(dataset)}
                      retry={version => actions.run(dataset, version)}
                      changed={catalog.reload}
                    />
                  ) : parts[2] === 'batches' && /^\d+$/.test(parts[3] ?? '') ? (
                    <BatchDetailPage
                      key={`${dataset.id}:batch:${parts[3]}`}
                      dataset={dataset}
                      batchId={Number(parts[3])}
                      userRole={user.role}
                      actions={actions}
                    />
                  ) : ['overview', 'batches', 'fields', 'versions', 'rules', 'history', 'compare', 'trend'].includes(
                      parts[2] || 'overview'
                    ) ? (
                    <DatasetPage
                      key={dataset.id}
                      dataset={dataset}
                      tab={parts[2] || 'overview'}
                      userRole={user.role}
                      actions={actions}
                    />
                  ) : (
                    <NotFound />
                  )
                ) : (
                  <Empty
                    title="Không tìm thấy bộ dữ liệu"
                    text="Bộ dữ liệu không tồn tại hoặc không thuộc phạm vi truy cập của bạn."
                    action={
                      <a href="#/datasets" className="button button-secondary">
                        Về danh mục
                      </a>
                    }
                  />
                )
              ) : parts[0] === 'dashboard' ? (
                <Suspense fallback={<div className="loading-state" role="status">Đang mở bảng công việc…</div>}><Dashboard
                  datasets={datasets}
                  actions={actions}
                  username={user.username}
                  loading={catalog.loading}
                  error={catalog.error}
                  onRetry={catalog.reload}
                /></Suspense>
              ) : operational ? (
                <Suspense fallback={<div className="loading-state" role="status">Đang mở màn hình…</div>}><OperationalScreens view={operational} datasets={datasets} actions={actions} userRole={user.role}/></Suspense>
              ) : parts[0] === 'datasets' ? (
                <CatalogDictionary datasets={datasets} actions={actions} userRole={user.role}/>
              ) : parts[0] === 'history' ? (
                <HistoryPage key={location.hash} datasets={datasets} run={() => actions.run()} />
              ) : parts[0] === 'guide' ? (
                <Guide create={() => actions.create()} />
              ) : (
                <NotFound />
              )}
            </>
          )}

          <footer className="main-footer">
            <span>DataGuard SME · Quản lý danh mục & chất lượng dữ liệu doanh nghiệp</span>
            <div className="button-row">
              <Button tone="ghost" disabled={!!modal} onClick={() => setModal({ kind: 'system' })}>
                Kết nối hệ thống
              </Button>
              <Button
                tone="ghost"
                disabled={catalog.loading || !!modal}
                onClick={catalog.reload}
              >
                <RefreshCw size={13} />
                Làm mới dữ liệu
              </Button>
            </div>
          </footer>
        </main>
      </div>

      {modal?.kind === 'create' && (
        <CreateDatasetDialog
          onClose={() => setModal(null)}
          onCreated={id => {
            setSuccess('Đã tạo bộ dữ liệu. Hãy tạo đợt dữ liệu rồi tải CSV đầu tiên.')
            catalog.reload()
            location.hash = `/datasets/${id}/overview`
          }}
        />
      )}

      {modal?.kind === 'upload' && (
        <UploadDialog
          dataset={modal.dataset}
          onClose={() => setModal(null)}
          onSaved={() => {
            setSuccess('Đã lưu phiên bản CSV.')
            catalog.reload()
          }}
          next={(id, tab, batchId, versionId) => {
            location.hash = `/datasets/${id}/batches/${batchId}`
            if (tab === 'run') {
              setModal({
                kind: 'run',
                version: versionId,
                dataset: datasets.find(item => item.id === id) ?? modal.dataset ?? ({ id } as CatalogEntry),
              })
            }
          }}
        />
      )}

      {modal?.kind === 'run' && (
        <RunDialog
          datasets={datasets}
          datasetId={modal.dataset?.id}
          versionId={modal.version}
          onClose={() => setModal(null)}
          started={(id, run) => {
            location.hash = `/datasets/${id}/runs/${run}`
            catalog.reload()
          }}
        />
      )}

      {modal?.kind === 'system' && <SystemStatus close={() => setModal(null)} />}
    </div>
  )
}

function NotFound() {
  return (
    <Empty
      title="Trang không tồn tại"
      text="Chọn một mục trong menu hoặc đường dẫn hợp lệ để tiếp tục."
      action={
        <a href="#/dashboard" className="button button-primary">
          Về trang chủ
        </a>
      }
    />
  )
}
