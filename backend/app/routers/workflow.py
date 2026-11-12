from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, StrictStr, StrictBool, Field
from app.access import require_business_access
from app.services import issue_workflow as work
from app.services.quality_rules import rule_connection
from app.models import DatasetIdentity
from sqlalchemy import select

router=APIRouter(tags=['issue workflow'])


class IdentityInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    columns:list[StrictStr]=Field(min_length=1,max_length=100)


class Confirmation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    confirm:StrictBool
    note:StrictStr=Field(default='',max_length=2000)
    accept_ignored:StrictBool=False


class StatusInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status:StrictStr
    note:StrictStr=Field(default='',max_length=2000)
    expected_revision:int=Field(ge=1)


class RecheckInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    run_id:int=Field(ge=1)


def confirmed(body):
    if not body.confirm:work.reject(422,'CONFIRM_REQUIRED','Cần xác nhận rõ thao tác này.')


@router.get('/datasets/{dataset_id}/identity')
def get_identity(dataset_id:int):
    with rule_connection() as c:
        return {'current':work.identity(c,dataset_id),'history':[dict(r) for r in c.execute(select(DatasetIdentity).where(DatasetIdentity.dataset_id==dataset_id).order_by(DatasetIdentity.revision.desc())).mappings()]}


@router.put('/datasets/{dataset_id}/identity')
def put_identity(dataset_id:int,body:IdentityInput,actor=Depends(require_business_access)):
    return work.configure_identity(dataset_id,body.columns,actor)


@router.get('/datasets/{dataset_id}/batches/{batch_id}/workflow')
def get_workflow(dataset_id:int,batch_id:int):return work.state(dataset_id,batch_id)


@router.post('/datasets/{dataset_id}/batches/{batch_id}/workflow/activate')
def activate(dataset_id:int,batch_id:int,body:Confirmation,actor=Depends(require_business_access)):
    confirmed(body)
    return work.activate(dataset_id,batch_id,actor)


@router.post('/datasets/{dataset_id}/batches/{batch_id}/workflow/reconcile')
def reconcile(dataset_id:int,batch_id:int,body:RecheckInput,actor=Depends(require_business_access)):
    return work.reconcile(dataset_id,batch_id,body.run_id,actor)


@router.get('/datasets/{dataset_id}/batches/{batch_id}/workflow/issues')
def issues(dataset_id:int,batch_id:int,status:str|None=None,page:int=Query(1,ge=1)):
    return work.issue_list(dataset_id,batch_id,status,page)


@router.get('/datasets/{dataset_id}/batches/{batch_id}/workflow/issues/{issue_id}')
def issue(dataset_id:int,batch_id:int,issue_id:int):return work.issue_detail(dataset_id,batch_id,issue_id)


@router.patch('/datasets/{dataset_id}/batches/{batch_id}/workflow/issues/{issue_id}')
def change_issue(dataset_id:int,batch_id:int,issue_id:int,body:StatusInput,actor=Depends(require_business_access)):
    return work.change_issue(dataset_id,batch_id,issue_id,body.status,body.note,body.expected_revision,actor)


@router.post('/datasets/{dataset_id}/batches/{batch_id}/workflow/complete')
def complete(dataset_id:int,batch_id:int,body:Confirmation,actor=Depends(require_business_access)):
    confirmed(body)
    return work.finish(dataset_id,batch_id,body.note,body.accept_ignored,actor)


@router.post('/datasets/{dataset_id}/batches/{batch_id}/workflow/reopen')
def reopen(dataset_id:int,batch_id:int,body:Confirmation,actor=Depends(require_business_access)):
    confirmed(body)
    return work.reopen(dataset_id,batch_id,body.note,actor)


@router.get('/datasets/{dataset_id}/runs/{run_id}/issue-links')
def issue_links(dataset_id:int,run_id:int):return work.violation_links(dataset_id,run_id)
