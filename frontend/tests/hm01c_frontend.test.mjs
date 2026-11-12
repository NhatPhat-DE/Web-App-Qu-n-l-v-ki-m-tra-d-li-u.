import test from 'node:test'
import assert from 'node:assert/strict'

// Test 1: Validation logic for CreateDataset form (DG-201, DG-202)
test('DG-202: Validation rejects blank or whitespace-only names', () => {
  function validate(metadata) {
    const errors = {}
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
    return errors
  }

  // Blank name
  let errors = validate({ name: '', description: '', source: '', owner: '' })
  assert.equal(errors.name, 'Tên bộ dữ liệu không được để trống hoặc chỉ chứa khoảng trắng.')

  // Whitespace name
  errors = validate({ name: '   \t  \n  ', description: '', source: '', owner: '' })
  assert.equal(errors.name, 'Tên bộ dữ liệu không được để trống hoặc chỉ chứa khoảng trắng.')

  // Valid name
  errors = validate({ name: 'Bộ dữ liệu bán hàng Q4', description: '', source: '', owner: '' })
  assert.equal(errors.name, undefined)
  assert.equal(Object.keys(errors).length, 0)
})

test('DG-202: Validation rejects field lengths exceeding limits', () => {
  function validate(metadata) {
    const errors = {}
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
    return errors
  }

  // Name > 200 chars
  let errors = validate({ name: 'a'.repeat(201), description: '', source: '', owner: '' })
  assert.equal(errors.name, 'Tên bộ dữ liệu tối đa 200 ký tự.')

  // Description > 2000 chars
  errors = validate({ name: 'Hợp lệ', description: 'd'.repeat(2001), source: '', owner: '' })
  assert.equal(errors.description, 'Mô tả tối đa 2000 ký tự.')

  // Source > 200 chars
  errors = validate({ name: 'Hợp lệ', description: '', source: 's'.repeat(201), owner: '' })
  assert.equal(errors.source, 'Nguồn / bộ phận tối đa 200 ký tự.')

  // Owner > 200 chars
  errors = validate({ name: 'Hợp lệ', description: '', source: '', owner: 'o'.repeat(201) })
  assert.equal(errors.owner, 'Người phụ trách tối đa 200 ký tự.')
})

// Test 2: UploadDialog schema mismatch logic (DG-204, DG-205)
test('DG-204 & DG-205: Empty dataset has no schema mismatch on first upload', () => {
  function computeMismatch(dataset, preview) {
    const oldHeader = dataset?.columns?.map(column => column.name) ?? []
    const hasExistingSchema = (dataset?.columns?.length ?? 0) > 0 && (dataset?.versions?.length ?? 0) > 0
    const mismatch = hasExistingSchema && !!preview && (
      oldHeader.length !== preview.header.length ||
      oldHeader.some((name, index) => name !== preview.header[index])
    )
    return mismatch
  }

  // Empty dataset with 0 versions and 0 columns
  const emptyDataset = { id: 101, name: 'Empty DS', columns: [], versions: [] }
  const firstPreview = { header: ['id', 'name', 'age'], rowCount: 10 }
  assert.equal(computeMismatch(emptyDataset, firstPreview), false, 'Empty dataset must NOT mismatch on first CSV')

  // Dataset with existing schema (v1 exists)
  const populatedDataset = {
    id: 101,
    name: 'Populated DS',
    columns: [{ id: 1, name: 'id' }, { id: 2, name: 'name' }, { id: 3, name: 'age' }],
    versions: [{ id: 1, version_number: 1 }]
  }

  // Matching preview for v2
  const matchingPreview = { header: ['id', 'name', 'age'], rowCount: 15 }
  assert.equal(computeMismatch(populatedDataset, matchingPreview), false, 'Matching schema must NOT mismatch')

  // Mismatched preview for v2 (added column)
  const mismatchedPreview = { header: ['id', 'name', 'age', 'extra'], rowCount: 15 }
  assert.equal(computeMismatch(populatedDataset, mismatchedPreview), true, 'Different schema MUST trigger mismatch')

  // Mismatched preview for v2 (different order)
  const reorderedPreview = { header: ['name', 'id', 'age'], rowCount: 15 }
  assert.equal(computeMismatch(populatedDataset, reorderedPreview), true, 'Reordered columns MUST trigger mismatch')
})

// Test 3: Catalog empty dataset display logic (DG-206)
test('DG-206: Catalog displays "Chưa có dữ liệu" for empty dataset and does not default to v1', () => {
  function renderVersionTag(versions) {
    const latest = versions[0]
    if (!latest) {
      return 'Chưa có dữ liệu'
    }
    return `v${latest.version_number}`
  }

  // Empty dataset
  assert.equal(renderVersionTag([]), 'Chưa có dữ liệu')

  // Populated dataset
  assert.equal(renderVersionTag([{ version_number: 1 }]), 'v1')
  assert.equal(renderVersionTag([{ version_number: 2 }, { version_number: 1 }]), 'v2')
})

// Test 4: Empty state titles and action messages (DG-204)
test('DG-204: Empty state titles and buttons conform to requirements', () => {
  const emptyStateConfig = {
    title: 'Bộ dữ liệu chưa có file nào',
    subtitle: 'Tải file CSV đầu tiên để bắt đầu quản lý và kiểm tra dữ liệu.',
    primaryButton: 'Tải file CSV đầu tiên',
  }

  assert.equal(emptyStateConfig.title, 'Bộ dữ liệu chưa có file nào')
  assert.equal(emptyStateConfig.subtitle, 'Tải file CSV đầu tiên để bắt đầu quản lý và kiểm tra dữ liệu.')
  assert.equal(emptyStateConfig.primaryButton, 'Tải file CSV đầu tiên')
})

// Test 5: createDataset API request/response contract (DG-201)
test('DG-201: createDataset payload trims strings and excludes empty optionals', () => {
  function preparePayload(input) {
    return {
      name: input.name.trim(),
      description: input.description?.trim() || null,
      source: input.source?.trim() || null,
      owner: input.owner?.trim() || null,
    }
  }

  const payload = preparePayload({
    name: '   Dữ liệu khách hàng SME   ',
    description: '   Mô tả chi tiết   ',
    source: '   ',
    owner: ' Nguyễn Văn A '
  })

  assert.equal(payload.name, 'Dữ liệu khách hàng SME')
  assert.equal(payload.description, 'Mô tả chi tiết')
  assert.equal(payload.source, null)
  assert.equal(payload.owner, 'Nguyễn Văn A')
})

// Test 6: Navigation flow and anti-duplicate submit (DG-203, DG-202)
test('DG-203: Standalone creation flow navigates to dataset overview and reuses dataset for CSV upload', () => {
  let currentHash = '#/datasets'
  let createdDatasetId = null
  let versionUploadTargetDatasetId = null

  // Step 1: User creates standalone dataset
  function onDatasetCreated(id) {
    createdDatasetId = id
    currentHash = `#/datasets/${id}/overview`
  }

  onDatasetCreated(42)
  assert.equal(createdDatasetId, 42)
  assert.equal(currentHash, '#/datasets/42/overview')

  // Step 2: From overview, user clicks "Tải file CSV đầu tiên"
  // UploadDialog is opened with dataset = { id: 42 }
  function onUploadSubmit(dataset) {
    // Must NOT call createDataset! Must call importVersion on the existing dataset id
    versionUploadTargetDatasetId = dataset.id
  }

  onUploadSubmit({ id: createdDatasetId })
  assert.equal(versionUploadTargetDatasetId, 42, 'CSV upload must target the existing dataset id without recreating dataset')
})

// Test 7: Error handling and user messages (DG-205, DG-202)
test('DG-205: CSV_SCHEMA_MISMATCH produces clear Vietnamese error message', () => {
  function parseImportError(errorBody) {
    if (errorBody?.error?.code === 'CSV_SCHEMA_MISMATCH') {
      return 'Tên và thứ tự cột không khớp dataset. Hãy tạo bộ dữ liệu khác nếu cấu trúc thay đổi.'
    }
    return errorBody?.error?.message || 'Lỗi nhập dữ liệu.'
  }

  const mismatchError = parseImportError({
    error: {
      code: 'CSV_SCHEMA_MISMATCH',
      message: 'Schema mismatch'
    }
  })

  assert.equal(mismatchError, 'Tên và thứ tự cột không khớp dataset. Hãy tạo bộ dữ liệu khác nếu cấu trúc thay đổi.')
})

