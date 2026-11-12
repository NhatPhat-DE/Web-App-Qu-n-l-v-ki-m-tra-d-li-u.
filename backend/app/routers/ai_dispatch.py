import json
from fastapi import APIRouter,Depends,Request,HTTPException
from pydantic import BaseModel,ConfigDict,StrictInt,StrictStr,StrictBool,Field
from app.access import require_business_access
from app.services import ai_dispatch
from app.services.ai_preview import PreviewError,unique_object
from app.services.ai_suggestions import AIResponseError

router=APIRouter(tags=['AI suggestions'])

class SuggestionInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version_id: StrictInt=Field(gt=0)
    preview_token: StrictStr=Field(min_length=1,max_length=4096)
    confirmed: StrictBool


def reject(status,code,retry_after=None):
    raise HTTPException(status,detail={'code':code,'message':'Không thể lấy đề xuất AI. Hãy kiểm tra cấu hình, phiên hoặc tạo lại preview; hệ thống không tự gửi lại.'},
                        headers={'Retry-After':str(retry_after)} if retry_after else None)

@router.post('/datasets/{dataset_id}/ai-rule-suggestions')
async def suggestions(dataset_id:int,request:Request,session=Depends(require_business_access)):
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>8192: reject(413,'AI_INPUT_TOO_LARGE')
        raw.extend(chunk)
    try:
        body=SuggestionInput.model_validate(json.loads(bytes(raw).decode('utf-8'),object_pairs_hook=unique_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError())))
        if not body.confirmed: reject(422,'AI_CONFIRMATION_REQUIRED')
    except (ValueError,RecursionError): reject(422,'INVALID_AI_INPUT')
    try:
        result=await ai_dispatch.generate(dataset_id,body.version_id,body.preview_token,session['user_id'],request.cookies.get('datalens_session'))
        return {'request_id':request.state.ai_request_id,'dataset_id':dataset_id,'version_id':body.version_id,'suggestions':result}
    except (ai_dispatch.AIError,PreviewError) as exc: reject(exc.status,exc.code,exc.retry_after)
    except AIResponseError: reject(502,'AI_INVALID_RESPONSE')
