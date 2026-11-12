from fastapi import APIRouter, Depends, Request, Query, HTTPException
from pydantic import BaseModel, ConfigDict, StrictStr, StrictBool, Field
from typing import Literal
from sqlalchemy.exc import SQLAlchemyError
from app.access import require_business_access
from app.services.quality_rules import rule_connection
from app.services.auth_sessions import find_session, SessionError
from app.services import admin_users

router = APIRouter(prefix='/admin/users', tags=['admin users'])


class UserCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: StrictStr = Field(max_length=128)
    password: StrictStr = Field(min_length=12, max_length=128, repr=False)
    role: Literal['admin', 'data_steward', 'data_owner']


class UserPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['admin', 'data_steward', 'data_owner'] | None = None
    is_active: StrictBool | None = None


def admin_transaction(request: Request, session=Depends(require_business_access)):
    if session['role'] != 'admin':
        admin_users.reject(403, 'FORBIDDEN', 'Chỉ admin được quản lý tài khoản.')
    try:
        with rule_connection() as connection:
            admin_users.lock_accounts(connection)
            # Revalidate after waiting for another admin's transaction.
            current = find_session(connection, request.cookies.get('datalens_session'))
            if current['role'] != 'admin':
                admin_users.reject(403, 'FORBIDDEN', 'Chỉ admin được quản lý tài khoản.')
            yield connection, current['user_id']
    except SessionError:
        admin_users.reject(401, 'UNAUTHENTICATED', 'Phiên không còn hiệu lực.')
    except (SQLAlchemyError, ConnectionError):
        admin_users.reject(503, 'DATABASE_UNAVAILABLE', 'Không thể xử lý cơ sở dữ liệu.')


@router.post('', status_code=201)
def create(body: UserCreate, context=Depends(admin_transaction, scope='function')):
    connection, _ = context
    return admin_users.create_user(connection, body.model_dump())


@router.get('')
def listing(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
            context=Depends(admin_transaction, scope='function')):
    connection, _ = context
    return admin_users.list_users(connection, page, page_size)


@router.patch('/{user_id}')
def patch(user_id: int, body: UserPatch, context=Depends(admin_transaction, scope='function')):
    connection, actor_id = context
    return admin_users.patch_user(connection, actor_id, user_id, body.model_dump(exclude_unset=True))
