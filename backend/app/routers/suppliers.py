from fastapi import APIRouter,Depends
from pydantic import BaseModel,ConfigDict,StrictStr,StrictBool,Field
from app.access import require_business_access
from app.services import suppliers
from app.routers.runs import read_history

router=APIRouter(tags=['supplier catalog'])


class BrandInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    code:StrictStr
    name:StrictStr
    is_active:StrictBool=True


class StoreInput(BrandInput):
    brand_id:int=Field(gt=0,strict=True)


class SourcePatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:StrictStr|None=None
    is_active:StrictBool|None=None


@router.get('/suppliers')
def catalog():return read_history(suppliers.catalog)


@router.get('/suppliers/history')
def history():return read_history(suppliers.history)


@router.post('/suppliers/brands',status_code=201)
def brand(body:BrandInput,actor=Depends(require_business_access)):
    return read_history(suppliers.save,'brand',body.model_dump(),actor)


@router.post('/suppliers/stores',status_code=201)
def store(body:StoreInput,actor=Depends(require_business_access)):
    return read_history(suppliers.save,'store',body.model_dump(),actor)


@router.patch('/suppliers/{kind}/{identifier}')
def patch(kind:str,identifier:int,body:SourcePatch,actor=Depends(require_business_access)):
    def save():
        if kind not in ('brands','stores'):suppliers.fail('SOURCE_NOT_FOUND','Không tìm thấy loại nguồn.',404)
        data=body.model_dump(exclude_unset=True)
        if not data or any(v is None for v in data.values()):suppliers.fail('INVALID_SOURCE_PATCH','Cần tên hoặc trạng thái hợp lệ.')
        return suppliers.save('brand' if kind=='brands' else 'store',data,actor,identifier)
    return read_history(save)
