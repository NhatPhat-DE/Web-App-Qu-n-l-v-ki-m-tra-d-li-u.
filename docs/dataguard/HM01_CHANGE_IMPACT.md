# HM-01: Phân tích Tác động Thay đổi (Change Impact Analysis)

**Dự án:** DataGuard SME  
**Phạm vi:** Tách biệt Tạo Dataset khỏi Upload CSV  
**Ngày lập:** Tháng 11/2026  

---

## 1. Ma trận Tác động Tổng thể (Impact Matrix)

| Thành phần | Mức độ tác động | Khả năng phá vỡ (Breaking) | Mô tả chi tiết |
| :--- | :---: | :---: | :--- |
| **Database Schema** | **Không** | Không | Schema Alembic `0008` (head) đã hỗ trợ bảng `datasets` độc lập; không cần migration mới. |
| **Dữ liệu hiện hữu** | **Không** | Không | Toàn bộ 21+ datasets, 50+ versions, 57+ runs sẵn có trong DB không bị thay đổi hay ảnh hưởng. |
| **Quality Engine v5** | **Không** | Không | Không chỉnh sửa `quality_engine.py`, worker RE2 hay các quy tắc kiểm tra. |
| **Rule Snapshot** | **Không** | Không | Snapshot chỉ sinh ra khi gọi run cho một version cụ thể; logic snapshot bảo toàn 100%. |
| **Run Comparison** | **Không** | Không | Logic đối chiếu giữa 2 completed runs giữ nguyên. |
| **Endpoint cũ `/datasets/import`** | **Không** | Không | Giữ nguyên 100% cho các script kiểm thử tự động và client cũ. |
| **Endpoint `/versions/import`** | **Thấp (Mở rộng)** | Không | Bổ sung nhánh xử lý khi dataset chưa có cột: tự động khởi tạo `dataset_columns` và sinh $v1$. |
| **Backend Services & Router** | **Trung bình** | Không | Thêm route `POST /api/datasets` và hàm `create_dataset()`. |
| **Frontend UI/API Client** | **Trung bình** | Không | Bổ sung hàm API `createDataset()`, tách form tạo danh mục trên giao diện. |

---

## 2. Danh sách Chi tiết Thay đổi theo từng File (File-by-File Changes)

### 2.1. Backend

#### 1. `backend/app/services/dataset_metadata.py`
* **Vị trí thay đổi:** Thêm hàm mới `create_dataset(metadata: dict) -> dict`.
* **Trách nhiệm:** Mở transaction, thực thi `INSERT INTO datasets (name, description, source, owner) VALUES (...) RETURNING *`, trả về dictionary thông tin dataset vừa tạo.
* **Nguyên tắc an toàn:** Sử dụng `rule_connection()` đảm bảo timeout và cô lập transaction.

#### 2. `backend/app/routers/datasets.py`
* **Vị trí thay đổi:**
  * Bổ sung Pydantic model `DatasetCreate`:
    ```python
    class DatasetCreate(BaseModel):
        model_config = ConfigDict(extra="forbid")
        name: StrictStr
        description: StrictStr | None = None
        source: StrictStr | None = None
        owner: StrictStr | None = None
    ```
  * Bổ sung endpoint:
    ```python
    @router.post("/datasets", status_code=201)
    def create_new_dataset(body: DatasetCreate):
        changes, error = metadata_changes(body)
        return error if error is not None else catalog_response(dataset_metadata.create_dataset, changes)
    ```
* **Bảo vệ:** Tự động kế thừa bảo mật `require_business_access` (cookie HttpOnly + CSRF + Origin) được khai báo tại `app/main.py:45`.

#### 3. `backend/app/services/dataset_import.py`
* **Vị trí thay đổi:** Hàm `import_version(dataset_id: int, parsed: ParsedCSV, filename: str)` (khoảng dòng 13–30).
* **Logic điều chỉnh:**
  * Trước đây: Đọc `header = select(DatasetColumn.name)`. Nếu `parsed.header != header` thì ném lỗi `CSV_SCHEMA_MISMATCH`. (Khiến dataset rỗng không thể nạp file).
  * Điều chỉnh:
    * Kiểm tra: Nếu `existing_columns` rỗng $\rightarrow$ Đây là lần nạp file đầu tiên cho dataset độc lập:
      * Lưu `parsed.header` vào `dataset_columns` với `position` tăng dần từ 1.
      * Đặt `version_number = 1`.
    * Nếu `existing_columns` đã có $\rightarrow$ Giữ nguyên logic so khớp schema hiện tại, đặt `version_number = max + 1`.

---

### 2.2. Frontend

#### 1. `frontend/src/api/datasets.ts`
* **Vị trí thay đổi:** Thêm hàm `createDataset`:
  ```typescript
  export interface DatasetInput {
    name: string
    description?: string
    source?: string
    owner?: string
  }
  export async function createDataset(data: DatasetInput): Promise<CatalogEntry> {
    const response = await businessFetch('/api/datasets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(body?.error?.message || 'Không thể tạo bộ dữ liệu.')
    }
    return response.json()
  }
  ```

#### 2. `frontend/src/workspace/UploadDialog.tsx` & `CatalogPages.tsx`
* **Hiện trạng:** Bấm "Tạo bộ dữ liệu" mở wizard 4 bước (`UploadDialog`) bắt buộc phải chọn file CSV ở bước 2 mới cho lưu.
* **Cải tiến:**
  * Tách biệt rõ ràng:
    * Thao tác **"Tạo bộ dữ liệu"** (tại trang Danh mục): Mở Dialog nhập Metadata (`name`, `source`, `owner`, `description`) $\rightarrow$ Bấm "Lưu bộ dữ liệu" $\rightarrow$ Gọi `createDataset()` $\rightarrow$ Tạo xong chuyển hướng ngay đến trang Chi tiết bộ dữ liệu rỗng.
    * Thao tác **"Tải CSV phiên bản đầu tiên"** hoặc **"Tải phiên bản mới"**: Mở Dialog chọn file CSV (`UploadDialog` với `dataset` đã có sẵn) $\rightarrow$ Xem trước 10 dòng $\rightarrow$ Gọi `importVersion()` $\rightarrow$ Sinh phiên bản $v1$ (nếu rỗng) hoặc $v2, v3$ (nếu đã có).

---

## 3. Đánh giá Tác động Dữ liệu Hiện có (Data Migration & Compatibility)

* **Số lượng bộ dữ liệu hiện tại trong DB:** 21 datasets.
* **Số lượng phiên bản hiện tại:** 50+ versions.
* **Rủi ro hồi quy dữ liệu:** **Bằng 0**.
  * Các bản ghi `datasets`, `dataset_columns`, `dataset_versions`, `dataset_rows` đã lưu từ trước vẫn giữ nguyên cấu trúc và khóa ngoại.
  * Việc thêm một bản ghi vào `datasets` mà chưa có bản ghi con không vi phạm bất kỳ chỉ mục hay tính toàn vẹn nào của PostgreSQL.
  * Các câu truy vấn `JOIN DatasetVersion` hiện tại đều dùng INNER JOIN hoặc correlate subquery `select count()` nên khi `version_count = 0` hệ thống vẫn trả về số liệu chính xác mà không gặp lỗi `NullPointerException` hay `ZeroDivisionError`.

---

## 4. Tác động tới Hệ thống Kiểm thử Tự động (Test Suites Impact)

1. **Backend Pytest (`backend/tests/`):**
   * Các file `test_dataset_import.py`, `test_quality_engine.py`, `test_access_control.py`, `test_admin_users.py` sử dụng fixture tạo dataset qua `import_dataset` hoặc tạo trực tiếp qua SQLAlchemy. Tất cả các test này **tiếp tục PASS 100%**.
   * Cần bổ sung test case mới: `test_create_dataset_metadata_only` và `test_import_first_version_to_empty_dataset` trong `backend/tests/test_dataset_import.py`.
2. **Frontend Scripts (`frontend/verify-*.mjs` & `verify-redesign.py`):**
   * Các kịch bản chạy thử nghiệm thu vẫn sử dụng các API hợp đồng hiện hữu. Việc giữ nguyên `POST /api/datasets/import` đảm bảo `verify-redesign.py` và `verify-auth.mjs` không bị ảnh hưởng.

