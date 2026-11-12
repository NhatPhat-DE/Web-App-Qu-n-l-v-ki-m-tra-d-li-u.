import json
from fastapi import APIRouter, Request, Depends, HTTPException
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, StrictStr, StrictBool, StrictInt, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.access import require_business_access
from app.services import ai_preview
from app.services.ai_payload import AIPayloadError
from app.services.dataset_catalog import CatalogNotFound

router=APIRouter(tags=['AI preview'])


class PreviewInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version_id: StrictInt = Field(gt=0)
    columns: list[StrictStr] = Field(min_length=1,max_length=30)
    include_descriptions: StrictBool = True
    include_statistics: StrictBool = True


def reject(status,code):
    raise HTTPException(status,detail={'code':code,'message':'Không thể xác nhận bản xem trước. Hãy kiểm tra cấu hình/lựa chọn và tạo preview mới.'})


@router.post('/datasets/{dataset_id}/ai-rule-suggestions/preview')
async def preview(dataset_id: int,request: Request,session=Depends(require_business_access)):
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>8192: reject(413,'AI_INPUT_TOO_LARGE')
        raw.extend(chunk)
    try:
        body=PreviewInput.model_validate(json.loads(bytes(raw).decode('utf-8'),object_pairs_hook=ai_preview.unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError())))
    except (ValueError,UnicodeError,RecursionError,ValidationError): reject(422,'INVALID_AI_INPUT')
    try:
        ai_preview.secret()
        ai_preview.preview_limiter.reserve(session['user_id'])
        return await run_in_threadpool(ai_preview.issue_preview,dataset_id,body.version_id,body.columns,
            body.include_descriptions,body.include_statistics,session['user_id'],request.cookies.get('datalens_session'))
    except ai_preview.PreviewError as exc:
        headers={'Retry-After':str(exc.retry_after)} if exc.retry_after else None
        raise HTTPException(exc.status,detail={'code':exc.code,'message':'Preview chưa sẵn sàng hoặc không còn hợp lệ. Hãy tạo preview mới; nếu bị giới hạn, chờ rồi thử thủ công.'},headers=headers) from None
    except CatalogNotFound: reject(404,'DATASET_VERSION_NOT_FOUND')
    except AIPayloadError as exc: reject(422,exc.code)
    except (SQLAlchemyError,ConnectionError): reject(503,'DATABASE_UNAVAILABLE')
