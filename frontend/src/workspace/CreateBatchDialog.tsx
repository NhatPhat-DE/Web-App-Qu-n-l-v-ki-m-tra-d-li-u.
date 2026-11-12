import { useRef, useState } from 'react'
import { Calendar, Database, FolderPlus, LoaderCircle } from 'lucide-react'
import { createBatch } from '../api/datasets'
import { SupplierFields } from './Suppliers'
import { Button, Dialog, Field, Notice, useFormGuard } from './ui'

export default function CreateBatchDialog({
  datasetId,
  datasetName,
  onClose,
  onCreated,
}: {
  datasetId: number
  datasetName: string
  onClose: () => void
  onCreated: (batchId: number) => void
}) {
  const [metadata, setMetadata] = useState({ name: '', period_label: '', description: '' })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [apiError, setApiError] = useState('')
  const [copyTemplate, setCopyTemplate] = useState(true)
  const [saving, setSaving] = useState(false)
  const [store,setStore]=useState('')
  const saveLock = useRef(false)

  const dirty = Object.values(metadata).some(val => val.length > 0) || !copyTemplate || !!store
  const guard = useFormGuard(dirty, saving, onClose)

  function validate(): boolean {
    const errors: Record<string, string> = {}
    if(!store)errors.store='Chọn cửa hàng cung cấp.'
    const trimmedName = metadata.name.trim()

    if (!trimmedName) {
      errors.name = 'Tên đợt dữ liệu không được để trống hoặc chỉ chứa khoảng trắng.'
    } else if (metadata.name.length > 200) {
      errors.name = 'Tên đợt dữ liệu tối đa 200 ký tự.'
    }

    if (metadata.period_label && metadata.period_label.length > 100) {
      errors.period_label = 'Kỳ dữ liệu tối đa 100 ký tự.'
    }
    if (metadata.description && metadata.description.length > 2000) {
      errors.description = 'Mô tả tối đa 2000 ký tự.'
    }

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (saveLock.current || saving) return
    if (!validate()) return

    saveLock.current = true
    setSaving(true)
    setApiError('')

    try {
      const created = await createBatch(datasetId, {
        store_id:Number(store),
        name: metadata.name.trim(),
        copy_template_rules: copyTemplate,
        period_label: metadata.period_label.trim() || undefined,
        description: metadata.description.trim() || undefined,
      })
      guard.markSaved()
      onClose()
      onCreated(created.id)
    } catch (cause) {
      setApiError(cause instanceof Error ? cause.message : 'Không thể tạo đợt dữ liệu. Vui lòng thử lại.')
    } finally {
      saveLock.current = false
      setSaving(false)
    }
  }

  return (
    <Dialog
      title="Tạo đợt dữ liệu mới"
      description={`Khởi tạo đợt dữ liệu (Data Batch) trong bộ dữ liệu "${datasetName}". Mỗi đợt có chu kỳ phiên bản bắt đầu từ v1 riêng biệt.`}
      onClose={guard.close}
      busy={saving}
    >
      <form onSubmit={handleSubmit} className="form-stack">
        {apiError && <Notice kind="error">{apiError}</Notice>}
        <SupplierFields value={store} change={setStore} disabled={saving}/>

        <Field
          label="Tên đợt dữ liệu"
          required
          error={fieldErrors.name}
          hint="Ví dụ: Khách hàng tháng 10/2026, Đợt đối soát Q4 (tối đa 200 ký tự)"
        >
          <input
            required
            autoFocus
            maxLength={200}
            value={metadata.name}
            onChange={e => {
              setMetadata({ ...metadata, name: e.target.value })
              if (fieldErrors.name) setFieldErrors({ ...fieldErrors, name: '' })
            }}
            placeholder="Nhập tên đợt dữ liệu..."
          />
        </Field>

        <Field
          label="Kỳ dữ liệu"
          error={fieldErrors.period_label}
          hint="Thời gian hoặc kỳ áp dụng, ví dụ: 10/2026, Q4/2026, Tuần 42 (tối đa 100 ký tự)"
        >
          <input
            maxLength={100}
            value={metadata.period_label}
            onChange={e => {
              setMetadata({ ...metadata, period_label: e.target.value })
              if (fieldErrors.period_label) setFieldErrors({ ...fieldErrors, period_label: '' })
            }}
            placeholder="Ví dụ: 10/2026"
          />
        </Field>

        <Field
          label="Mô tả đợt dữ liệu"
          error={fieldErrors.description}
          hint="Ghi chú nguồn gốc, thời điểm nhận file hoặc người gửi (tối đa 2000 ký tự)"
        >
          <textarea
            rows={3}
            maxLength={2000}
            value={metadata.description}
            onChange={e => {
              setMetadata({ ...metadata, description: e.target.value })
              if (fieldErrors.description) setFieldErrors({ ...fieldErrors, description: '' })
            }}
            placeholder="Ghi chú thêm về đợt dữ liệu này..."
          />
        </Field>

        <label className="check-line"><input type="checkbox" checked={copyTemplate} onChange={e => setCopyTemplate(e.target.checked)} />Sao chép quy tắc mẫu thành bộ quy tắc độc lập của đợt. Bỏ chọn để cấu hình riêng.</label><div className="dialog-actions">
          <Button tone="ghost" onClick={guard.close} disabled={saving}>
            Hủy
          </Button>
          <Button tone="primary" type="submit" disabled={saving}>
            {saving ? (
              <>
                <LoaderCircle className="spin" size={16} />
                Đang tạo...
              </>
            ) : (
              <>
                <FolderPlus size={16} />
                Tạo đợt dữ liệu
              </>
            )}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

