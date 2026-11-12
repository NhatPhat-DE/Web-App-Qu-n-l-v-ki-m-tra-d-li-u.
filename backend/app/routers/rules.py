from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, StrictStr, StrictBool
from app.routers.datasets import catalog_response, error_response
from app.services import quality_rules
from app.services.quality_engine import QualityInputError

router = APIRouter(tags=["quality rules"])


class RuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: StrictStr
    rule_type: StrictStr
    columns: list[StrictStr]
    config: dict
    is_active: StrictBool = True


class RulePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: StrictStr | None = None
    rule_type: StrictStr | None = None
    columns: list[StrictStr] | None = None
    config: dict | None = None
    is_active: StrictBool | None = None


def execute(operation, *args):
    def validated():
        try:
            return operation(*args)
        except QualityInputError as error:
            return error_response(422, error.code, str(error))
    return catalog_response(validated)


@router.post("/datasets/{dataset_id}/rules", status_code=201)
def create(dataset_id: int, body: RuleCreate):
    return execute(quality_rules.create_rule, dataset_id, body.model_dump())


@router.get("/datasets/{dataset_id}/rules")
def listing(dataset_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return execute(quality_rules.list_rules, dataset_id, page, page_size)


@router.patch("/datasets/{dataset_id}/rules/{rule_id}")
def patch(dataset_id: int, rule_id: int, body: RulePatch):
    changes = body.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        return error_response(422, "INVALID_INPUT", "Không được đặt trường quy tắc thành null.")
    return execute(quality_rules.patch_rule, dataset_id, rule_id, changes)


@router.get('/datasets/{dataset_id}/batches/{batch_id}/rules')
def batch_listing(dataset_id: int, batch_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return execute(quality_rules.list_rules, dataset_id, page, page_size, batch_id)


@router.post('/datasets/{dataset_id}/batches/{batch_id}/rules', status_code=201)
def batch_create(dataset_id: int, batch_id: int, body: RuleCreate):
    return execute(quality_rules.create_rule, dataset_id, body.model_dump(), batch_id)


@router.patch('/datasets/{dataset_id}/batches/{batch_id}/rules/{rule_id}')
def batch_patch(dataset_id: int, batch_id: int, rule_id: int, body: RulePatch):
    changes = body.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        return error_response(422, 'INVALID_INPUT', 'Cần thay đổi hợp lệ, không null.')
    return execute(quality_rules.patch_rule, dataset_id, rule_id, changes, batch_id)
