from fastapi import APIRouter, File, Form, UploadFile, Query, Request, Depends
from app.access import require_business_access
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictStr, StrictBool, Field
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.services.csv_reader import CSVValidationError, MAX_FILE_BYTES, parse_csv
from app.services.dataset_import import import_dataset, import_version
from app.services import dataset_catalog
from app.services import dataset_metadata
from app.services import data_batches

router = APIRouter(tags=["datasets"])


class DatasetCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: StrictStr
    description: StrictStr | None = None
    source: StrictStr | None = None
    owner: StrictStr | None = None


class DatasetPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: StrictStr | None = None
    description: StrictStr | None = None
    source: StrictStr | None = None
    owner: StrictStr | None = None


class ColumnPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    description: StrictStr | None = None


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: StrictStr
    description: StrictStr | None = None
    period_label: StrictStr | None = None
    copy_template_rules: StrictBool = True
    store_id: int = Field(gt=0,strict=True)


class BatchPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: StrictStr | None = None
    description: StrictStr | None = None
    period_label: StrictStr | None = None
    store_id: int | None = Field(None,gt=0,strict=True)


def metadata_changes(body):
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return None, error_response(422, 'EMPTY_PATCH', 'Cần gửi ít nhất một trường metadata để sửa.')
    if 'name' in changes and (changes['name'] is None or not changes['name'].strip()):
        return None, error_response(422, 'INVALID_NAME', 'Tên bộ dữ liệu không được null, rỗng hoặc chỉ có khoảng trắng.')
    if any(isinstance(value, str) and '\x00' in value for value in changes.values()):
        return None, error_response(422, 'INVALID_METADATA', 'Metadata không được chứa ký tự NUL.')
    return changes, None


def validate_dataset_create(body: DatasetCreate):
    data = body.model_dump()
    name = data.get('name')
    if name is None or not name.strip():
        return None, error_response(422, 'INVALID_NAME', 'Tên bộ dữ liệu không được null, rỗng hoặc chỉ có khoảng trắng.')
    if len(name) > 200:
        return None, error_response(422, 'INVALID_NAME', 'Tên bộ dữ liệu tối đa 200 ký tự.')
    if '\x00' in name:
        return None, error_response(422, 'INVALID_METADATA', 'Metadata không được chứa ký tự NUL.')
    for field in ('description', 'source', 'owner'):
        val = data.get(field)
        if val is not None:
            if len(val) > 200:
                return None, error_response(422, 'INVALID_METADATA', f'Trường {field} tối đa 200 ký tự.')
            if '\x00' in val:
                return None, error_response(422, 'INVALID_METADATA', 'Metadata không được chứa ký tự NUL.')
    return data, None


@router.post('/datasets', status_code=201)
def create_dataset(body: DatasetCreate):
    data, error = validate_dataset_create(body)
    return error if error is not None else catalog_response(dataset_metadata.create_dataset, data)


@router.patch('/datasets/{dataset_id}')
def update_dataset(dataset_id: int, body: DatasetPatch):
    changes, error = metadata_changes(body)
    return error if error is not None else catalog_response(dataset_metadata.patch_dataset, dataset_id, changes)


@router.patch('/datasets/{dataset_id}/columns/{column_id}')
def update_column(dataset_id: int, column_id: int, body: ColumnPatch):
    changes, error = metadata_changes(body)
    return error if error is not None else catalog_response(dataset_metadata.patch_column, dataset_id, column_id, changes)


def error_response(status: int, code: str, message: str, row_number=None):
    return JSONResponse(status_code=status, content={"error": {
        "code": code, "message": message, "row_number": row_number,
    }})


@router.post("/datasets/import", status_code=201)
def upload_dataset(
    file: UploadFile = File(...), name: str = Form(...),
    description: str | None = Form(None), source: str | None = Form(None),
    owner: str | None = Form(None),
):
    try:
        metadata = {"name": name, "description": description, "source": source, "owner": owner}
        if not name.strip() or any(value is not None and "\x00" in value for value in metadata.values()):
            return error_response(422, "INVALID_METADATA", "Tên không được chỉ có khoảng trắng; metadata không được chứa NUL.")
        filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
        if not filename.lower().endswith(".csv") or "\x00" in filename:
            return error_response(422, "INVALID_FILENAME", "Tên file phải có phần mở rộng .csv và không chứa NUL.")
        content = file.file.read(MAX_FILE_BYTES + 1)
        try:
            parsed = parse_csv(content)
        except CSVValidationError as error:
            return error_response(413 if error.code == "FILE_TOO_LARGE" else 422,
                                  error.code, error.message, error.row_number)
        try:
            result = import_dataset(parsed, filename, metadata)
        except ConnectionError:
            return error_response(503, "DATABASE_UNAVAILABLE", "Không thể kết nối cơ sở dữ liệu.")
        except DBAPIError as error:
            sqlstate = getattr(error.orig, "sqlstate", None)
            unavailable = error.connection_invalidated or sqlstate is None or sqlstate.startswith("08") or sqlstate in {"57P01", "57P02", "57P03"}
            return error_response(503 if unavailable else 500,
                                  "DATABASE_UNAVAILABLE" if unavailable else "DATABASE_ERROR",
                                  "Không thể kết nối cơ sở dữ liệu." if unavailable else "Không thể lưu bộ dữ liệu.")
        except SQLAlchemyError:
            return error_response(500, "DATABASE_ERROR", "Không thể lưu bộ dữ liệu.")
        return JSONResponse(status_code=201, content=result)
    finally:
        file.file.close()


def catalog_response(operation, *args):
    from app.services.quality_execution import RunError
    try:
        return operation(*args)
    except RunError as error:
        return error_response(error.status,error.code,error.message)
    except dataset_catalog.InvalidSearchQuery:
        return error_response(422, 'INVALID_SEARCH_QUERY', 'Chuỗi tìm kiếm phải hợp lệ, không chứa NUL và tối đa 200 ký tự Unicode.')
    except dataset_catalog.CatalogNotFound:
        return error_response(404, "NOT_FOUND", "Không tìm thấy bộ dữ liệu hoặc phiên bản phù hợp.")
    except ConnectionError:
        return error_response(503, "DATABASE_UNAVAILABLE", "Không thể kết nối cơ sở dữ liệu.")
    except DBAPIError as error:
        sqlstate = getattr(error.orig, "sqlstate", None)
        unavailable = error.connection_invalidated or sqlstate is None or sqlstate.startswith("08") or sqlstate in {"57P01", "57P02", "57P03"}
        return error_response(503 if unavailable else 500,
                              "DATABASE_UNAVAILABLE" if unavailable else "DATABASE_ERROR",
                              "Không thể kết nối cơ sở dữ liệu." if unavailable else "Không thể đọc dữ liệu.")
    except ValueError as error:
        return error_response(422, "INVALID_METADATA", str(error))
    except SQLAlchemyError:
        return error_response(500, "DATABASE_ERROR", "Không thể đọc dữ liệu.")


@router.post('/datasets/{dataset_id}/versions/import', status_code=201)
def upload_version(dataset_id: int, file: UploadFile = File(...)):
    try:
        filename = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
        if not filename.lower().endswith('.csv') or '\x00' in filename:
            return error_response(422, 'INVALID_FILENAME', 'Tên file phải có phần mở rộng .csv và không chứa NUL.')
        try:
            parsed = parse_csv(file.file.read(MAX_FILE_BYTES + 1))
        except CSVValidationError as error:
            return error_response(413 if error.code == 'FILE_TOO_LARGE' else 422, error.code, error.message, error.row_number)
        def save():
            try:
                return import_version(dataset_id, parsed, filename)
            except CSVValidationError as error:
                return error_response(422, error.code, error.message, error.row_number)
        result = catalog_response(save)
        return result if isinstance(result, JSONResponse) else JSONResponse(status_code=201, content=result)
    finally:
        file.file.close()


@router.get("/datasets")
def get_datasets(request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                 q: str | None = Query(None)):
    if len(request.query_params.getlist('q')) > 1:
        return error_response(422, 'INVALID_SEARCH_QUERY', 'Chỉ được gửi một tham số q.')
    return catalog_response(dataset_catalog.list_datasets, page, page_size, q)


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: int):
    return catalog_response(dataset_catalog.dataset_detail, dataset_id)


@router.get("/datasets/{dataset_id}/versions/{version_id}/rows")
def get_version_rows(dataset_id: int, version_id: int,
                     page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return catalog_response(dataset_catalog.version_rows, dataset_id, version_id, page, page_size)


@router.post('/datasets/{dataset_id}/batches', status_code=201)
def create_batch_endpoint(dataset_id: int, body: BatchCreate, actor=Depends(require_business_access)):
    data = body.model_dump()
    def save():
        res = data_batches.create_batch(dataset_id, data, actor)
        return JSONResponse(status_code=201, content=res)
    return catalog_response(save)


@router.get('/datasets/{dataset_id}/batches')
def list_batches_endpoint(dataset_id: int, request: Request, page: int = Query(1, ge=1),
                          page_size: int = Query(20, ge=1, le=100), q: str | None = Query(None)):
    if len(request.query_params.getlist('q')) > 1:
        return error_response(422, 'INVALID_SEARCH_QUERY', 'Chỉ được gửi một tham số q.')
    return catalog_response(data_batches.list_batches, dataset_id, page, page_size, q)


@router.get('/datasets/{dataset_id}/batches/{batch_id}')
def get_batch_endpoint(dataset_id: int, batch_id: int):
    return catalog_response(data_batches.get_batch, dataset_id, batch_id)


@router.patch('/datasets/{dataset_id}/batches/{batch_id}')
def update_batch_endpoint(dataset_id: int, batch_id: int, body: BatchPatch, actor=Depends(require_business_access)):
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return error_response(422, 'EMPTY_PATCH', 'Cần gửi ít nhất một trường để sửa.')
    return catalog_response(data_batches.patch_batch, dataset_id, batch_id, changes, actor)


@router.get('/datasets/{dataset_id}/batches/{batch_id}/versions')
def get_batch_versions_endpoint(dataset_id: int, batch_id: int):
    return catalog_response(data_batches.list_batch_versions, dataset_id, batch_id)


@router.post('/datasets/{dataset_id}/batches/{batch_id}/versions/import', status_code=201)
def upload_batch_version_endpoint(dataset_id: int, batch_id: int, file: UploadFile = File(...)):
    try:
        filename = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
        if not filename.lower().endswith('.csv') or '\x00' in filename:
            return error_response(422, 'INVALID_FILENAME', 'Tên file phải có phần mở rộng .csv và không chứa NUL.')
        try:
            parsed = parse_csv(file.file.read(MAX_FILE_BYTES + 1))
        except CSVValidationError as error:
            return error_response(413 if error.code == 'FILE_TOO_LARGE' else 422, error.code, error.message, error.row_number)
        def save():
            try:
                return import_version(dataset_id, parsed, filename, batch_id=batch_id)
            except CSVValidationError as error:
                return error_response(422, error.code, error.message, error.row_number)
        result = catalog_response(save)
        return result if isinstance(result, JSONResponse) else JSONResponse(status_code=201, content=result)
    finally:
        file.file.close()
