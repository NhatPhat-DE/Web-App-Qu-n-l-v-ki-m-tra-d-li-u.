"""Supply the newly required source for pre-SRC01 lifecycle regression tests.

Used explicitly by legacy tests; new contract/validation tests use raw clients.
All catalog rows live only in the isolated PostgreSQL fixture.
"""
from authenticated_client import TestClient as AuthenticatedClient


def batch_payload(client,body):
    if 'store_id' in body:return body
    catalog=client.get('/api/suppliers').json()
    stores=catalog['stores']
    if stores:identifier=stores[0]['store_id']
    else:
        brand=client.post('/api/suppliers/brands',json={'code':'LIFECYCLE_TEST','name':'Lifecycle test brand'})
        assert brand.status_code==201,brand.text
        store=client.post('/api/suppliers/stores',json={'code':'LIFECYCLE_TEST','name':'Lifecycle test source','brand_id':brand.json()['id']})
        assert store.status_code==201,store.text
        identifier=store.json()['id']
    return {**body,'store_id':identifier}


class SupplierTestClient(AuthenticatedClient):
    def post(self,url,**kwargs):
        if str(url).endswith('/batches') and isinstance(kwargs.get('json'),dict):
            kwargs['json']=batch_payload(self,kwargs['json'])
        return super().post(url,**kwargs)
