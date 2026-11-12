import { Badge, Button, Dialog, LoadState, Notice, useLoad } from './ui'
import { request } from './api'

interface HealthStatus { status: string; database?: string }

export default function SystemStatus({ close }: { close: () => void }) {
  const state = useLoad(async signal => {
    const controller = new AbortController()
    const abort = () => controller.abort()
    signal.addEventListener('abort', abort, { once: true })
    if (signal.aborted) controller.abort()
    const timeout = window.setTimeout(abort, 5000)
    try {
      const results = await Promise.allSettled([
        request<HealthStatus>('/api/health', controller.signal),
        request<HealthStatus>('/api/health/db', controller.signal),
      ])
      if (signal.aborted) throw new DOMException('Request cancelled', 'AbortError')
      return results.map((result, index) => ({
        label: index === 0 ? 'Dịch vụ ứng dụng' : 'Cơ sở dữ liệu',
        ok: result.status === 'fulfilled' && result.value.status === 'ok' && (index === 0 || result.value.database === 'ok'),
      }))
    } finally { window.clearTimeout(timeout); signal.removeEventListener('abort', abort) }
  }, [])
  return <Dialog title="Kiểm tra kết nối hệ thống" description="Đọc trạng thái trực tiếp từ máy chủ, không thay đổi dữ liệu." onClose={close}><div className="form-stack"><LoadState loading={state.loading} error={state.error} retry={state.reload} />{state.data && <><dl className="info-list">{state.data.map(item => <div key={item.label}><dt>{item.label}</dt><dd><Badge tone={item.ok ? 'success' : 'danger'}>{item.ok ? 'Kết nối thành công' : 'Không kết nối được'}</Badge></dd></div>)}</dl>{state.data.some(item => !item.ok) && <Notice kind="error">Không xác nhận được kết nối trong 5 giây. Kiểm tra dịch vụ đang chạy rồi thử lại. Trạng thái kết nối không thay thế kiểm tra phiên hoặc quyền truy cập.</Notice>}</>}<Button disabled={state.loading} onClick={state.reload}>Kiểm tra lại kết nối</Button></div></Dialog>
}
