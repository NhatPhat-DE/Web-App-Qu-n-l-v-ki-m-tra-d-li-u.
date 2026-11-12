from fastapi.testclient import TestClient as BaseClient

session_cookie = None
csrf_token = None


class TestClient(BaseClient):
    __test__ = False
    def __enter__(self):
        result=super().__enter__()
        self.cookies.set('datalens_session',session_cookie,path='/api')
        self.headers.update({'Origin':'http://127.0.0.1:5173','X-CSRF-Token':csrf_token})
        return result
