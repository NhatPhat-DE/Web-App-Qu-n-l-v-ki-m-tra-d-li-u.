import { useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Database,
  FileCheck2,
  FileSpreadsheet,
  FolderClosed,
  HelpCircle,
  ListChecks,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  Upload,
} from 'lucide-react'
import { latestRun, namedRuns } from './api'
import type { CatalogEntry, NamedRun } from './api'
import type { DatasetActions } from './CatalogPages'
import type { DatasetVersion } from '../api/datasets'
import type { RunSummary } from '../api/runs'
import {
  Badge,
  Button,
  DatasetMark,
  Empty,
  Notice,
  PageTitle,
  QualityBadge,
  date,
  number,
} from './ui'

export type DatasetAttentionStatus =
  | 'NO_FILE' // Chưa có file CSV
  | 'HAS_ERRORS' // Lần kiểm tra gần nhất phát hiện dòng lỗi
  | 'TECHNICAL_FAILED' // Lần kiểm tra thất bại kỹ thuật
  | 'NEEDS_RUN' // Đã có file nhưng chưa từng kiểm tra hoặc phiên bản mới chưa kiểm tra
  | 'PASSED' // Lần kiểm tra gần nhất đạt quy tắc

export interface DatasetItemSummary {
  dataset: CatalogEntry
  status: DatasetAttentionStatus
  statusLabel: string
  statusTone: 'neutral' | 'warning' | 'danger' | 'success' | 'primary'
  description: string
  actionLabel: string
  actionTone: 'primary' | 'secondary' | 'ghost'
  onAction: () => void
  actionHref?: string
  latestRun?: RunSummary
  latestVersion?: DatasetVersion
}

export function classifyDataset(
  dataset: CatalogEntry,
  actions: DatasetActions
): DatasetItemSummary {
  const latestVersion = dataset.versions[0]
  if (!latestVersion) {
    return {
      dataset,
      status: 'NO_FILE',
      statusLabel: 'Chưa có file dữ liệu',
      statusTone: 'neutral',
      description: 'Bộ dữ liệu chưa có file nào. Hãy tải file CSV đầu tiên để bắt đầu quản lý.',
      actionLabel: 'Tải file CSV',
      actionTone: 'primary',
      onAction: () => actions.upload(dataset),
    }
  }

  // Lấy lần kiểm tra mới nhất của phiên bản hiện tại
  const versionRun = latestRun(dataset, latestVersion.id)

  if (!versionRun) {
    return {
      dataset,
      status: 'NEEDS_RUN',
      statusLabel: 'Chưa kiểm tra',
      statusTone: 'neutral',
      description: `Phiên bản v${latestVersion.version_number} (${latestVersion.original_filename}) chưa được kiểm tra chất lượng.`,
      actionLabel: 'Chạy kiểm tra',
      actionTone: 'primary',
      onAction: () => actions.run(dataset, latestVersion.id),
      latestVersion,
    }
  }

  if (versionRun.status === 'running') {
    return {
      dataset,
      status: 'NEEDS_RUN',
      statusLabel: 'Đang kiểm tra',
      statusTone: 'primary',
      description: `Đang thực thi lần kiểm tra #${versionRun.run_id} cho phiên bản v${latestVersion.version_number}.`,
      actionLabel: 'Xem tiến độ',
      actionTone: 'secondary',
      onAction: () => {
        location.hash = `/datasets/${dataset.id}/runs/${versionRun.run_id}`
      },
      actionHref: `#/datasets/${dataset.id}/runs/${versionRun.run_id}`,
      latestRun: versionRun,
      latestVersion,
    }
  }

  if (versionRun.status === 'failed') {
    return {
      dataset,
      status: 'TECHNICAL_FAILED',
      statusLabel: 'Thực thi thất bại',
      statusTone: 'danger',
      description: `Lần kiểm tra #${versionRun.run_id} gặp sự cố kỹ thuật. Kiểm tra lại cấu hình hoặc bấm Thử lại.`,
      actionLabel: 'Thử lại',
      actionTone: 'secondary',
      onAction: () => actions.run(dataset, latestVersion.id),
      latestRun: versionRun,
      latestVersion,
    }
  }

  if ((versionRun.error_row_count ?? 0) > 0) {
    return {
      dataset,
      status: 'HAS_ERRORS',
      statusLabel: `${number(versionRun.error_row_count)} dòng lỗi`,
      statusTone: 'warning',
      description: `Phiên bản v${latestVersion.version_number} phát hiện ${number(versionRun.error_row_count)} dòng vi phạm quy tắc.`,
      actionLabel: 'Xem lỗi',
      actionTone: 'primary',
      onAction: () => {
        location.hash = `/datasets/${dataset.id}/runs/${versionRun.run_id}`
      },
      actionHref: `#/datasets/${dataset.id}/runs/${versionRun.run_id}`,
      latestRun: versionRun,
      latestVersion,
    }
  }

  return {
    dataset,
    status: 'PASSED',
    statusLabel: 'Đạt quy tắc',
    statusTone: 'success',
    description: `Phiên bản v${latestVersion.version_number} (${number(latestVersion.row_count)} dòng) đã vượt qua các quy tắc kiểm tra.`,
    actionLabel: 'Xem kết quả',
    actionTone: 'secondary',
    onAction: () => {
      location.hash = `/datasets/${dataset.id}/runs/${versionRun.run_id}`
    },
    actionHref: `#/datasets/${dataset.id}/runs/${versionRun.run_id}`,
    latestRun: versionRun,
    latestVersion,
  }
}

export interface DashboardProps {
  datasets: CatalogEntry[]
  actions: DatasetActions
  username: string
  loading?: boolean
  error?: string
  onRetry?: () => void
}

export default function Dashboard({
  datasets,
  actions,
  username,
  loading = false,
  error = '',
  onRetry,
}: DashboardProps) {
  const [attentionFilter, setAttentionFilter] = useState<'ALL' | 'ERRORS' | 'NEEDS_RUN' | 'NO_FILE' | 'PASSED'>('ALL')
  const [showGuide, setShowGuide] = useState(false)

  // Phân loại tất cả các bộ dữ liệu
  const classifiedItems = datasets.map(d => classifyDataset(d, actions))

  // Các danh sách con theo phân loại
  const itemsWithErrors = classifiedItems.filter(i => i.status === 'HAS_ERRORS')
  const itemsNeedsRun = classifiedItems.filter(i => i.status === 'NEEDS_RUN' || i.status === 'TECHNICAL_FAILED')
  const itemsNoFile = classifiedItems.filter(i => i.status === 'NO_FILE')
  const itemsPassed = classifiedItems.filter(i => i.status === 'PASSED')

  // Danh sách cần chú ý (những mục chưa đạt hoàn toàn)
  const itemsNeedingAttention = classifiedItems.filter(i => i.status !== 'PASSED')

  // Lọc danh sách hiển thị trong khối "Dữ liệu cần chú ý"
  const filteredAttentionList =
    attentionFilter === 'ALL'
      ? itemsNeedingAttention
      : attentionFilter === 'ERRORS'
      ? itemsWithErrors
      : attentionFilter === 'NEEDS_RUN'
      ? itemsNeedsRun
      : attentionFilter === 'NO_FILE'
      ? itemsNoFile
      : itemsPassed

  // Danh sách lượt kiểm tra gần đây
  const allRuns: NamedRun[] = namedRuns(datasets)
  const recentRuns = allRuns.slice(0, 5)

  // Tìm mục đầu tiên cần thao tác để gợi ý nút Quick Action
  const nextActionItem =
    itemsWithErrors[0] ||
    itemsNeedsRun[0] ||
    itemsNoFile[0]

  // KPI Calculations
  const totalDatasetsCount = datasets.length
  const datasetsWithoutFilesCount = itemsNoFile.length
  const datasetsNeedingReviewCount = itemsNeedingAttention.length
  const completedRunsCount = allRuns.filter(r => r.status === 'completed').length

  // Xử lý trạng thái tải (Loading Skeleton)
  if (loading && datasets.length === 0) {
    return (
      <div className="dashboard-workbench" aria-busy="true">
        <PageTitle
          eyebrow="BÀN LÀM VIỆC DỮ LIỆU"
          title="Bàn làm việc"
          description={`Xin chào ${username}, hệ thống đang tải dữ liệu không gian làm việc...`}
        />
        <div className="skeleton-grid">
          <div className="skeleton skeleton-card" style={{ height: 110 }} />
          <div className="skeleton skeleton-card" style={{ height: 110 }} />
          <div className="skeleton skeleton-card" style={{ height: 110 }} />
          <div className="skeleton skeleton-card" style={{ height: 110 }} />
        </div>
        <div className="skeleton skeleton-card" style={{ height: 320, marginTop: 24 }} />
      </div>
    )
  }

  // Xử lý trạng thái lỗi tải dữ liệu
  if (error && datasets.length === 0) {
    return (
      <div className="dashboard-workbench">
        <PageTitle
          eyebrow="BÀN LÀM VIỆC DỮ LIỆU"
          title="Bàn làm việc"
          description={`Xin chào ${username}`}
        />
        <Notice
          kind="error"
          action={
            onRetry && (
              <Button onClick={onRetry}>
                <RefreshCw size={14} /> Thử lại
              </Button>
            )
          }
        >
          {error}
        </Notice>
      </div>
    )
  }

  return (
    <div className="dashboard-workbench">
      {/* 1. Header & Quick Actions Bar */}
      <PageTitle
        eyebrow="BÀN LÀM VIỆC DỮ LIỆU"
        title="Bàn làm việc"
        description={`Xin chào ${username}, đây là trung tâm theo dõi chất lượng và giải quyết các tồn đọng dữ liệu hôm nay.`}
        action={
          <div className="button-row">
            <Button tone="secondary" onClick={() => actions.create()}>
              <Plus size={16} />
              Tạo bộ dữ liệu
            </Button>
            {totalDatasetsCount > 0 && (
              <Button tone="primary" onClick={() => actions.run()}>
                <Play size={16} />
                Chạy kiểm tra
              </Button>
            )}
          </div>
        }
      />

      {/* Quick Action Navigation Bar */}
      <div className="quick-actions-bar" role="region" aria-label="Thao tác nhanh">
        <div className="quick-actions-info">
          <h2>Thao tác nhanh</h2>
          <p>Bắt đầu công việc tiếp theo hoặc truy cập nhanh các phân hệ dữ liệu.</p>
        </div>
        <div className="quick-actions-buttons">
          <Button tone="primary" onClick={() => actions.create()}>
            <Plus size={16} />
            Tạo bộ dữ liệu mới
          </Button>

          <a href="#/datasets" className="button button-secondary">
            <FolderClosed size={16} />
            Xem danh mục ({totalDatasetsCount})
          </a>

          {nextActionItem ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={nextActionItem.onAction}
              title={`Tiếp tục xử lý: ${nextActionItem.dataset.name}`}
            >
              <Play size={15} />
              <span>
                Tiếp tục:{' '}
                <strong>
                  {nextActionItem.status === 'HAS_ERRORS'
                    ? `Sửa lỗi ${nextActionItem.dataset.name}`
                    : nextActionItem.status === 'NO_FILE'
                    ? `Tải file ${nextActionItem.dataset.name}`
                    : `Kiểm tra ${nextActionItem.dataset.name}`}
                </strong>
              </span>
            </button>
          ) : (
            <a href="#/history" className="button button-secondary">
              <ListChecks size={16} />
              Xem lịch sử kiểm tra
            </a>
          )}

          <Button
            tone="ghost"
            onClick={() => setShowGuide(prev => !prev)}
            aria-expanded={showGuide}
            title="Xem hướng dẫn nhanh cho người dùng mới"
          >
            <HelpCircle size={16} />
            {showGuide ? 'Ẩn hướng dẫn' : 'Hướng dẫn 3 bước'}
          </Button>
        </div>
      </div>

      {/* Onboarding Guide (Hiển thị khi người dùng bấm xem hoặc khi chưa có bộ dữ liệu nào) */}
      {(showGuide || totalDatasetsCount === 0) && (
        <div className="welcome-strip" role="region" aria-label="Quy trình làm việc 3 bước">
          <div className="welcome-copy">
            <span className="mini-label">
              <ShieldCheck size={15} />
              QUY TRÌNH 3 BƯỚC CHO DOANH NGHIỆP SME
            </span>
            <h2>Từ file CSV thô đến dữ liệu tin cậy</h2>
            <p>
              Tạo bộ dữ liệu độc lập, nạp phiên bản CSV, áp dụng các quy tắc kiểm tra và xuất danh sách dòng lỗi để sửa trên Excel.
            </p>
            <a href="#/guide">
              Xem sổ tay hướng dẫn chi tiết <ArrowRight size={14} />
            </a>
          </div>

          <div className="mini-workflow">
            <div className="mini-step">
              <button
                type="button"
                onClick={() => actions.create()}
                aria-label="Bước 1: Tạo bộ dữ liệu"
              >
                <Database size={22} />
              </button>
              <span>
                <b>01</b> Tạo bộ dữ liệu
              </span>
              <ArrowRight className="step-arrow" size={17} />
            </div>

            <div className="mini-step">
              <button
                type="button"
                onClick={() => {
                  if (datasets[0]) actions.upload(datasets[0])
                  else actions.create()
                }}
                aria-label="Bước 2: Tải file CSV"
              >
                <Upload size={22} />
              </button>
              <span>
                <b>02</b> Tải file CSV
              </span>
              <ArrowRight className="step-arrow" size={17} />
            </div>

            <div className="mini-step">
              <a href="#/rules" aria-label="Bước 3: Thiết lập & Kiểm tra">
                <ShieldCheck size={22} />
              </a>
              <span>
                <b>03</b> Kiểm tra dữ liệu
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 2. KPI Overview Cards */}
      <div className="metric-grid" role="region" aria-label="Chỉ số tổng quan">
        <div className="metric-card">
          <div className="metric-top">
            <span>Tổng bộ dữ liệu</span>
            <span className="metric-icon icon-indigo">
              <Database size={19} />
            </span>
          </div>
          <strong>{number(totalDatasetsCount)}</strong>
          <p>
            {totalDatasetsCount === 0
              ? 'Chưa có bộ dữ liệu nào'
              : `${number(totalDatasetsCount - datasetsWithoutFilesCount)} bộ đã nạp file CSV`}
          </p>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Chưa có file dữ liệu</span>
            <span className="metric-icon icon-blue">
              <FileSpreadsheet size={19} />
            </span>
          </div>
          <strong className={datasetsWithoutFilesCount > 0 ? 'text-amber' : ''}>
            {number(datasetsWithoutFilesCount)}
          </strong>
          <p>
            {datasetsWithoutFilesCount === 0
              ? 'Tất cả bộ dữ liệu đều đã có file'
              : 'Cần tải file CSV đầu tiên để quản lý'}
          </p>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Bộ dữ liệu cần xem xét</span>
            <span className="metric-icon icon-amber">
              <AlertCircle size={19} />
            </span>
          </div>
          <strong className={datasetsNeedingReviewCount > 0 ? 'text-amber' : ''}>
            {number(datasetsNeedingReviewCount)}
          </strong>
          <p>
            {datasetsNeedingReviewCount === 0
              ? 'Dữ liệu đang ở trạng thái tốt'
              : `${number(itemsWithErrors.length)} bộ có lỗi · ${number(itemsNeedsRun.length)} bộ chờ kiểm tra`}
          </p>
        </div>

        <div className="metric-card">
          <div className="metric-top">
            <span>Lượt kiểm tra hoàn tất</span>
            <span className="metric-icon icon-green">
              <ListChecks size={19} />
            </span>
          </div>
          <strong>{number(completedRunsCount)}</strong>
          <p>Trên tổng số {number(allRuns.length)} lượt chạy kiểm tra</p>
        </div>
      </div>

      {/* Khi chưa có bất kỳ bộ dữ liệu nào trong danh mục */}
      {totalDatasetsCount === 0 ? (
        <section className="panel">
          <Empty
            title="Chào mừng bạn đến với DataGuard SME"
            text="Hệ thống giúp bạn theo dõi danh mục dữ liệu, phiên bản CSV và tự động kiểm tra chất lượng. Bắt đầu bằng việc tạo bộ dữ liệu đầu tiên!"
            action={
              <Button tone="primary" onClick={() => actions.create()}>
                <Plus size={16} /> Tạo bộ dữ liệu đầu tiên
              </Button>
            }
          />
        </section>
      ) : (
        /* Grid chính: Dữ liệu cần chú ý & Lượt kiểm tra gần đây */
        <div className="dashboard-grid">
          {/* CỘT 1: DỮ LIỆU CẦN CHÚ Ý (ATTENTION LIST) */}
          <section className="panel attention-panel" aria-labelledby="attention-heading">
            <div className="panel-heading">
              <div>
                <h2 id="attention-heading">
                  Dữ liệu cần chú ý{' '}
                  <span className="count-pill count-amber">
                    {itemsNeedingAttention.length}
                  </span>
                </h2>
                <p>Bộ dữ liệu có lỗi, chưa có file hoặc chưa được kiểm tra chất lượng</p>
              </div>

              <a href="#/datasets" className="text-button">
                Xem toàn bộ danh mục <ArrowRight size={14} />
              </a>
            </div>

            {/* Thanh lọc trạng thái trong khối Chú ý */}
            <div className="attention-tabs" role="tablist" aria-label="Lọc dữ liệu cần chú ý">
              <button
                type="button"
                role="tab"
                aria-selected={attentionFilter === 'ALL'}
                className={`attention-tab-btn ${attentionFilter === 'ALL' ? 'active' : ''}`}
                onClick={() => setAttentionFilter('ALL')}
              >
                Tất cả cần chú ý ({itemsNeedingAttention.length})
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={attentionFilter === 'ERRORS'}
                className={`attention-tab-btn ${attentionFilter === 'ERRORS' ? 'active' : ''}`}
                onClick={() => setAttentionFilter('ERRORS')}
              >
                Có dòng lỗi ({itemsWithErrors.length})
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={attentionFilter === 'NEEDS_RUN'}
                className={`attention-tab-btn ${attentionFilter === 'NEEDS_RUN' ? 'active' : ''}`}
                onClick={() => setAttentionFilter('NEEDS_RUN')}
              >
                Chờ kiểm tra ({itemsNeedsRun.length})
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={attentionFilter === 'NO_FILE'}
                className={`attention-tab-btn ${attentionFilter === 'NO_FILE' ? 'active' : ''}`}
                onClick={() => setAttentionFilter('NO_FILE')}
              >
                Chưa có file ({itemsNoFile.length})
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={attentionFilter === 'PASSED'}
                className={`attention-tab-btn ${attentionFilter === 'PASSED' ? 'active' : ''}`}
                onClick={() => setAttentionFilter('PASSED')}
              >
                Đạt quy tắc ({itemsPassed.length})
              </button>
            </div>

            {/* Danh sách các mục sau khi lọc */}
            {filteredAttentionList.length > 0 ? (
              <div className="attention-item-list">
                {filteredAttentionList.map(item => (
                  <article key={item.dataset.id} className="attention-item">
                    <div className="attention-item-main">
                      <DatasetMark name={item.dataset.name} small />
                      <div className="attention-item-info">
                        <div className="attention-item-title">
                          <a
                            href={`#/datasets/${item.dataset.id}/overview`}
                            className="attention-dataset-title"
                          >
                            <strong>{item.dataset.name}</strong>
                          </a>
                          <Badge tone={item.statusTone}>{item.statusLabel}</Badge>
                          {item.dataset.owner && (
                            <small className="muted">
                              Phụ trách: {item.dataset.owner}
                            </small>
                          )}
                        </div>
                        <p className="attention-item-desc">{item.description}</p>
                      </div>
                    </div>

                    <div className="attention-item-action">
                      {item.actionHref ? (
                        <a
                          href={item.actionHref}
                          className={`button button-${item.actionTone}`}
                        >
                          {item.actionLabel}
                          <ArrowRight size={14} />
                        </a>
                      ) : (
                        <Button
                          tone={item.actionTone}
                          onClick={item.onAction}
                        >
                          {item.status === 'NO_FILE' && <Upload size={14} />}
                          {item.status === 'NEEDS_RUN' && <Play size={14} />}
                          {item.status === 'TECHNICAL_FAILED' && <RefreshCw size={14} />}
                          {item.actionLabel}
                        </Button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="panel-pad">
                <Empty
                  title={
                    attentionFilter === 'ALL'
                      ? 'Tuyệt vời! Không có dữ liệu nào cần chú ý'
                      : 'Không có dữ liệu trong mục này'
                  }
                  text={
                    attentionFilter === 'ALL'
                      ? 'Tất cả các bộ dữ liệu đã được kiểm tra và không phát hiện vi phạm quy tắc.'
                      : 'Hãy chọn nhóm phân loại khác để theo dõi các bộ dữ liệu của bạn.'
                  }
                  action={
                    attentionFilter !== 'ALL' ? (
                      <Button onClick={() => setAttentionFilter('ALL')}>
                        Xem tất cả cần chú ý
                      </Button>
                    ) : undefined
                  }
                />
              </div>
            )}
          </section>

          {/* CỘT 2: LƯỢT KIỂM TRA GẦN ĐÂY (RECENT RUNS) & MẸO LÀM VIỆC */}
          <div className="dashboard-sidebar-column">
            <section className="panel recent-runs" aria-labelledby="recent-runs-heading">
              <div className="panel-heading">
                <div>
                  <h2 id="recent-runs-heading">Lượt kiểm tra gần đây</h2>
                  <p>Kết quả từ các lần chạy kiểm tra chất lượng mới nhất</p>
                </div>
                <a href="#/history" className="text-button">
                  Xem tất cả <ArrowRight size={14} />
                </a>
              </div>

              {recentRuns.length > 0 ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Bộ dữ liệu</th>
                        <th>Bản</th>
                        <th>Kết quả</th>
                        <th>Dòng lỗi</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentRuns.map(run => (
                        <tr key={run.run_id}>
                          <td>
                            <a
                              className="dataset-link"
                              href={`#/datasets/${run.dataset.id}/runs/${run.run_id}`}
                            >
                              <DatasetMark name={run.dataset.name} small />
                              <div>
                                <strong>{run.dataset.name}</strong>
                                <small>{date(run.started_at)}</small>
                              </div>
                            </a>
                          </td>
                          <td>
                            <span className="version-tag">v{run.version_number}</span>
                          </td>
                          <td>
                            <QualityBadge run={run} />
                          </td>
                          <td className={run.error_row_count ? 'text-amber' : ''}>
                            {run.status === 'completed'
                              ? `${number(run.error_row_count)}`
                              : run.status === 'failed'
                              ? 'Lỗi'
                              : '—'}
                          </td>
                          <td>
                            <a
                              className="button button-ghost button-sm"
                              href={`#/datasets/${run.dataset.id}/runs/${run.run_id}`}
                              title={`Xem kết quả lần kiểm tra #${run.run_id}`}
                            >
                              Xem <ArrowRight size={13} />
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="panel-pad">
                  <Empty
                    title="Chưa có lượt kiểm tra nào"
                    text="Sau khi tải file CSV và cấu hình quy tắc, hãy bấm Chạy kiểm tra để xem kết quả tại đây."
                    action={
                      <Button onClick={() => actions.run()}>
                        <Play size={15} /> Chạy kiểm tra ngay
                      </Button>
                    }
                  />
                </div>
              )}
            </section>

            {/* Mẹo làm việc hữu ích cho SME */}
            <div className="next-card" role="complementary" aria-label="Mẹo làm việc cho SME">
              <div className="next-icon">
                <FileCheck2 size={24} />
              </div>
              <span className="eyebrow">MẸO LÀM VIỆC DỮ LIỆU</span>
              <h2>Sửa file nguồn, giữ nguyên lịch sử</h2>
              <p>
                Khi kiểm tra phát hiện lỗi dữ liệu, bạn xuất danh sách dòng vi phạm để đối chiếu, sửa file nguồn trên Excel, rồi tải lên phiên bản mới (v2, v3).
              </p>
              <div className="tip-points">
                <span>
                  <CheckCircle2 size={15} className="text-success" /> Không ghi đè hay làm mất file cũ
                </span>
                <span>
                  <CheckCircle2 size={15} className="text-success" /> Dễ dàng đối chiếu kết quả trước và sau khi sửa
                </span>
              </div>
              <a href="#/guide">
                Đọc sổ tay hướng dẫn xử lý lỗi <ArrowRight size={14} />
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
