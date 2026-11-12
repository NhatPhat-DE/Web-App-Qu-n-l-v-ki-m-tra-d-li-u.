import secrets
from datetime import timedelta
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, StrictStr, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.models import User
from app.auth_config import get_auth_settings, AuthConfigurationError
from app.services import accounts, csrf, auth_sessions
from app.services.quality_rules import rule_connection
from app.services.login_limit import login_limiter, LoginLimited

router = APIRouter(prefix='/auth', tags=['auth'])
SESSION = 'datalens_session'
PREAUTH = 'datalens_preauth'
DUMMY_HASH = accounts.hash_password(secrets.token_urlsafe(32))


class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: StrictStr = Field(max_length=128)
    password: StrictStr = Field(min_length=12,max_length=128)


def error(status,code,message,**headers):
    return JSONResponse(status_code=status,content={'error':{'code':code,'message':message}},headers={'Cache-Control':'no-store',**headers})


def safe(operation):
    try: return operation()
    except AuthConfigurationError: return error(503,'AUTH_CONFIGURATION_ERROR','Cấu hình đăng nhập chưa sẵn sàng.')
    except csrf.CSRFError: return error(403,'CSRF_REJECTED','Yêu cầu không hợp lệ. Tải lại thông tin đăng nhập và thử lại.')
    except LoginLimited as exc: return error(429,'LOGIN_RATE_LIMITED','Thử đăng nhập quá nhiều lần. Vui lòng chờ.',**{'Retry-After':str(exc.retry_after)})
    except (SQLAlchemyError,ConnectionError): return error(503,'DATABASE_UNAVAILABLE','Không thể kết nối cơ sở dữ liệu.')
    except Exception: return error(500,'AUTH_ERROR','Không thể xử lý đăng nhập.')


def cookie_options(settings,path):
    return dict(path=path,httponly=True,samesite='lax',secure=settings.cookie_secure)


def check_origin(request,optional=False):
    origins=request.headers.getlist('origin')
    if optional and not origins:return
    if len(origins)!=1:raise csrf.CSRFError('Origin không hợp lệ.')
    csrf.validate_origin(origins[0])


def find(connection,request,now):
    try: return auth_sessions.find_session(connection,request.cookies.get(SESSION),now)
    except auth_sessions.SessionError: return None


def payload(session,token):
    return {'user':{'id':session['user_id'],'username':session['username'],'role':session['role']},
            'expires_at':session['expires_at'],'csrf_token':csrf.session_csrf_token(token)}


@router.get('/me')
def me(request: Request):
    def operation():
        settings=get_auth_settings(); now=auth_sessions.utc_now()
        check_origin(request,optional=True)
        with rule_connection() as c: session=find(c,request,now)
        if session:
            return JSONResponse(jsonable_encoder(payload(session,request.cookies[SESSION])),headers={'Cache-Control':'no-store'})
        challenge=request.cookies.get(PREAUTH)
        try: token=csrf.preauth_csrf_token(challenge,now)
        except csrf.CSRFError:
            challenge=csrf.create_challenge(now); token=csrf.preauth_csrf_token(challenge,now)
        response=JSONResponse(status_code=401,content={'error':{'code':'UNAUTHENTICATED','message':'Chưa đăng nhập hoặc phiên không còn hiệu lực.'},'csrf_token':token},headers={'Cache-Control':'no-store'})
        remaining=max(0,int(challenge.split('.')[2])-int(now.timestamp()))
        response.set_cookie(PREAUTH,challenge,max_age=remaining,expires=now+timedelta(seconds=remaining),**cookie_options(settings,'/api/auth'))
        response.delete_cookie(SESSION,**cookie_options(settings,'/api'))
        return response
    return safe(operation)


@router.post('/login')
def login(request: Request, body: LoginInput):
    def operation():
        settings=get_auth_settings(); check_origin(request); now=auth_sessions.utc_now()
        with rule_connection() as c:
            previous=find(c,request,now)
            if previous: csrf.validate_session_csrf(request.cookies[SESSION],request.headers.get('x-csrf-token'))
            else: csrf.validate_preauth_csrf(request.cookies.get(PREAUTH),request.headers.get('x-csrf-token'),now)
        try: username=accounts.normalize_username(body.username)
        except accounts.AccountError: username=None
        login_limiter.reserve(request.client.host if request.client else 'unknown',username or '<invalid>')
        with rule_connection() as c:
            user=c.execute(select(User).where(User.username==username)).mappings().first() if username else None
        verified=accounts.verify_password(user['password_hash'] if user else DUMMY_HASH,body.password)
        if not user or not verified or not user['is_active']:
            return error(401,'INVALID_CREDENTIALS','Tên đăng nhập hoặc mật khẩu không đúng.')
        with rule_connection() as c:
            current=c.execute(select(User).where(User.id==user['id']).with_for_update()).mappings().one()
            if not current['is_active'] or current['password_hash']!=user['password_hash']:
                return error(401,'INVALID_CREDENTIALS','Tên đăng nhập hoặc mật khẩu không đúng.')
            session=auth_sessions.create_session(c,current['id'],now)
            if previous: auth_sessions.revoke_session(c,request.cookies[SESSION],now)
            data={'user':{'id':current['id'],'username':current['username'],'role':current['role']},'expires_at':session['expires_at'],'csrf_token':csrf.session_csrf_token(session['token'])}
        response=JSONResponse(jsonable_encoder(data),headers={'Cache-Control':'no-store'})
        response.set_cookie(SESSION,session['token'],max_age=28800,expires=session['expires_at'],**cookie_options(settings,'/api'))
        response.delete_cookie(PREAUTH,**cookie_options(settings,'/api/auth'))
        return response
    return safe(operation)


@router.post('/logout',status_code=204)
def logout(request: Request):
    def operation():
        settings=get_auth_settings(); check_origin(request); now=auth_sessions.utc_now()
        with rule_connection() as c:
            session=find(c,request,now)
            if session:
                csrf.validate_session_csrf(request.cookies[SESSION],request.headers.get('x-csrf-token'))
                auth_sessions.revoke_session(c,request.cookies[SESSION],now)
            else: csrf.validate_preauth_csrf(request.cookies.get(PREAUTH),request.headers.get('x-csrf-token'),now)
        response=Response(status_code=204,headers={'Cache-Control':'no-store'})
        response.delete_cookie(SESSION,**cookie_options(settings,'/api'))
        response.delete_cookie(PREAUTH,**cookie_options(settings,'/api/auth'))
        return response
    return safe(operation)
