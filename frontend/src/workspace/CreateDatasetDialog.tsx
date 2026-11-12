import { useRef, useState } from 'react'
import { Check, Database, LoaderCircle } from 'lucide-react'
import { createDataset } from '../api/datasets'
import { Button, Dialog, Field, Notice, useFormGuard } from './ui'

export default function CreateDatasetDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (id: number) => void
}) {
  const [metadata, setMetadata] = useState({ name: '', description: '', source: '', owner: '' })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [apiError, setApiError] = useState('')
  const [saving, setSaving] = useState(false)
  const saveLock = useRef(false)

  const dirty = Object.values(metadata).some(val => val.length > 0)

  const guard = useFormGuard(dirty, saving, onClose)

  function validate(): boolean {
    const errors: Record<string, string> = {}
    const trimmedName = metadata.name.trim()

    if (!trimmedName) {
      errors.name = 'Tên bộ dữ liệu không được để trống hoặc chỉ chứa khoảng trắng.'
    } else if (metadata.name.length > 200) {
      errors.name = 'Tên bộ dữ liệu tối đa 200 ký tự.'
    }

    if (metadata.description && metadata.description.length > 2000) {
      errors.description = 'Mô tả tối đa 2000 ký tự.'
    }
    if (metadata.source && metadata.source.length > 200) {
      errors.source = 'Nguồn / bộ phận tối đa 200 ký tự.'
    }
    if (metadata.owner && metadata.owner.length > 200) {
      errors.owner = 'Người phụ trách tối đa 200 ký tự.'
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
      const created = await createDataset({
        name: metadata.name.trim(),
        description: metadata.description.trim() || undefined,
        source: metadata.source.trim() || undefined,
        owner: metadata.owner.trim() || undefined,
      })
      guard.markSaved()
      onClose()
      onCreated(created.id)
    } catch (cause) {
      setApiError(cause instanceof Error ? cause.message : 'Không thể tạo bộ dữ liệu. Vui lòng thử lại.')
    } finally {
      saveLock.current = false
      setSaving(false)
    }
  }

  return (
    <Dialog
      title="Tạo bộ dữ liệu mới"
      description="Khởi tạo danh mục dữ liệu chỉ bằng thông tin metadata. Bạn có thể tải file CSV sau tại trang chi tiết."
      onClose={guard.close}
      busy={saving}
    >
      <form onSubmit={handleSubmit} className="form-stack">
        {apiError && <Notice kind="error">{apiError}</Notice>}

        <Field
          label="Tên bộ dữ liệu"
          required
          error={fieldErrors.name}
          hint="Ví dụ: Danh sách khách hàng SME (tối đa 200 ký tự)"
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
            placeholder="Nhập tên bộ dữ liệu..."
          />
        </Field>

        <div className="form-grid">
          <Field
            label="Người phụ trách"
            error={fieldErrors.owner}
            hint="Tên cá nhân hoặc bộ phận chịu trách nhiệm nội dung (tùy chọn)"
          >
            <input
              maxLength={200}
              value={metadata.owner}
              onChange={e => {
                setMetadata({ ...metadata, owner: e.target.value })
                if (fieldErrors.owner) setFieldErrors({ ...fieldErrors, owner: '' })
              }}
              placeholder="Ví dụ: Nguyễn Văn A"
            />
          </Field>

          <Field
            label="Nguồn / bộ phận"
            error={fieldErrors.source}
            hint="Bộ phận hoặc hệ thống nguồn phát sinh dữ liệu (tùy chọn)"
          >
            <input
              maxLength={200}
              value={metadata.source}
              onChange={e => {
                setMetadata({ ...metadata, source: e.target.value })
                if (fieldErrors.source) setFieldErrors({ ...fieldErrors, source: '' })
              }}
              placeholder="Ví dụ: Phòng Kinh doanh"
            />
          </Field>
        </div>

        <Field
          label="Mô tả"
          error={fieldErrors.description}
          hint="Mô tả mục đích sử dụng và nội dung chính của bộ dữ liệu (tùy chọn)"
        >
          <textarea
            rows={3}
            maxLength={2000}
            value={metadata.description}
            onChange={e => {
              setMetadata({ ...metadata, description: e.target.value })
              if (fieldErrors.description) setFieldErrors({ ...fieldErrors, description: '' })
            }}
            placeholder="Bộ dữ liệu này dùng để làm gì và chứa những thông tin gì?"
          />
        </Field>

        <Notice>
          Bộ dữ liệu sẽ được tạo ngay khi bạn xác nhận. Bạn không cần tải file CSV ở bước này và có thể tải lên bất kỳ lúc nào sau đó.
        </Notice>

        <div className="dialog-footer">
          <Button
            type="button"
            disabled={saving}
            onClick={guard.close}
          >
            Hủy
          </Button>
          <Button tone="primary" type="submit" disabled={saving}>
            {saving ? <LoaderCircle className="spin" size={17} /> : <Check size={17} />}
            {saving ? 'Đang tạo bộ dữ liệu…' : 'Tạo bộ dữ liệu'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

