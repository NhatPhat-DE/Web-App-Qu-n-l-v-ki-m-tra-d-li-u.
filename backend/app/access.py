from fastapi import Request, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.services.auth_sessions import find_session, SessionError
from app.services.quality_rules import rule_connection
from app.services.csrf import validate_session_csrf, CSRFError
from app.routers.auth import check_origin
from app.auth_config import AuthConfigurationError


def require_business_access(request: Request):
    token=request.cookies.get('datalens_session')
    if not token: raise HTTPException(401,detail={'code':'UNAUTHENTICATED','message':'Vui lòng đăng nhập.'})
    try:
        with rule_connection() as connection: session=find_session(connection,token)
        if session['role'] not in {'admin','data_steward','data_owner'}:
            raise HTTPException(403,detail={'code':'FORBIDDEN','message':'Không có quyền thực hiện thao tác.'})
        if session['role']=='data_owner' and request.method not in {'GET','HEAD','OPTIONS'}:
            path=request.url.path
            allowed='/workflow/' in path or path.endswith('/versions/import') or (path.endswith('/runs') and '/versions/' in path)
            if not allowed:raise HTTPException(403,detail={'code':'FORBIDDEN','message':'Data Owner không được sửa cấu hình nghiệp vụ.'})
        if request.method not in {'GET','HEAD','OPTIONS'}:
            check_origin(request)
            validate_session_csrf(token,request.headers.get('x-csrf-token'))
        return session
    except SessionError: raise HTTPException(401,detail={'code':'UNAUTHENTICATED','message':'Phiên không còn hiệu lực.'}) from None
    except CSRFError: raise HTTPException(403,detail={'code':'CSRF_REJECTED','message':'CSRF không hợp lệ. Làm mới phiên rồi thử lại thủ công.'}) from None
    except AuthConfigurationError: raise HTTPException(503,detail={'code':'AUTH_CONFIGURATION_ERROR','message':'Cấu hình xác thực chưa sẵn sàng.'}) from None
    except (SQLAlchemyError,ConnectionError): raise HTTPException(503,detail={'code':'DATABASE_UNAVAILABLE','message':'Không thể kết nối cơ sở dữ liệu.'}) from None
