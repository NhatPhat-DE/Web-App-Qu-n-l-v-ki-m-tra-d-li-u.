from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException
from app.access import require_business_access
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler, http_exception_handler
from fastapi.responses import JSONResponse
from app.routers.auth import router as auth_router

from app.routers.health import router as health_router
from app.routers.datasets import router as datasets_router
from app.routers.rules import router as rules_router
from app.routers.runs import router as runs_router

app = FastAPI(title="Data Catalog API")
app.include_router(auth_router,prefix='/api')


@app.exception_handler(HTTPException)
async def access_error(request,exc):
    if isinstance(exc.detail,dict) and 'code' in exc.detail:
        body={'error':exc.detail}
        if '/ai-rule-suggestions' in request.url.path: body['request_id']=request.state.ai_request_id
        return JSONResponse(status_code=exc.status_code,content=body,headers=exc.headers)
    return await http_exception_handler(request,exc)


@app.middleware('http')
async def auth_no_store(request,call_next):
    if '/ai-rule-suggestions' in request.url.path: request.state.ai_request_id=uuid4().hex
    response=await call_next(request)
    if '/ai-rule-suggestions' in request.url.path: response.headers['X-Request-ID']=request.state.ai_request_id
    if request.url.path.startswith(('/api/auth/', '/api/admin/')) or '/ai-rule-suggestions' in request.url.path:
        response.headers['Cache-Control']='no-store'
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    if '/ai-rule-suggestions' in request.url.path:
        return JSONResponse(status_code=422,content={'error':{'code':'INVALID_AI_INPUT','message':'Thông tin AI không hợp lệ.'},'request_id':request.state.ai_request_id},headers={'Cache-Control':'no-store'})
    if request.url.path.startswith(('/api/auth/', '/api/admin/')) or '/ai-rule-suggestions' in request.url.path:
        return JSONResponse(status_code=422,content={'error':{'code':'INVALID_AUTH_INPUT','message':'Thông tin đăng nhập thiếu hoặc không hợp lệ.'}},headers={'Cache-Control':'no-store'})
    return await request_validation_exception_handler(request,exc)
app.include_router(health_router, prefix="/api")
app.include_router(datasets_router, prefix="/api", dependencies=[Depends(require_business_access)])
app.include_router(rules_router, prefix="/api", dependencies=[Depends(require_business_access)])
app.include_router(runs_router, prefix="/api", dependencies=[Depends(require_business_access)])

from app.routers.workflow import router as workflow_router
app.include_router(workflow_router,prefix='/api',dependencies=[Depends(require_business_access)])
from app.routers.suppliers import router as suppliers_router
app.include_router(suppliers_router,prefix='/api',dependencies=[Depends(require_business_access)])

from app.routers.admin_users import router as admin_users_router
app.include_router(admin_users_router, prefix='/api')

from app.routers.ai_preview import router as ai_preview_router
app.include_router(ai_preview_router,prefix='/api')

from app.routers.ai_dispatch import router as ai_dispatch_router
app.include_router(ai_dispatch_router,prefix='/api')
