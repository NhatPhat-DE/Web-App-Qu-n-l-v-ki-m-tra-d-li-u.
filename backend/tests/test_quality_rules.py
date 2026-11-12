import pytest
from authenticated_client import TestClient
from app.main import app
from test_dataset_import import isolated_database


@pytest.fixture
def dataset(isolated_database):
    with TestClient(app) as client:
        response = client.post('/api/datasets/import', data={'name': 'rules test'}, files={'file': ('a.csv', b'a,b\n1,2')})
    assert response.status_code == 201
    return response.json()['dataset_id']


def payload(kind='required', config=None):
    return {'name': 'Rule', 'rule_type': kind, 'columns': ['a'], 'config': config or {}}


def test_create_list_patch(dataset):
    url = f'/api/datasets/{dataset}/rules'
    with TestClient(app) as client:
        assert client.get(url).json()['items'] == []
        ids = []
        for body in [payload(), payload('unique'), payload('numeric_range', {'min': '0.00000000000000000001', 'max': '100'})]:
            response = client.post(url, json=body)
            assert response.status_code == 201
            rule = response.json()
            assert rule['config'] == body['config'] and rule['is_active'] is True
            assert rule['dataset_id'] == dataset and rule['columns'] == ['a']
            ids.append(rule['id'])
        response = client.patch(url+f'/{ids[0]}', json={'is_active': False, 'name': 'Renamed'})
        assert response.status_code == 200 and response.json()['is_active'] is False
        assert response.json()['name'] == 'Renamed'
        assert client.patch(url+f'/{ids[0]}', json={'is_active': True}).json()['is_active'] is True
        assert client.patch(url+f'/{ids[1]}', json={'columns': ['b','a']}).json()['columns'] == ['b','a']
        assert client.patch(url+f'/{ids[2]}', json={'config': {'min':'0', 'max':'200'}}).json()['config'] == {'min':'0','max':'200'}
        first = client.get(url, params={'page_size':2}).json()
        second = client.get(url, params={'page':2,'page_size':2}).json()
        assert [item['id'] for item in first['items']+second['items']] == ids
        assert first['total'] == second['total'] == 3
        assert client.get(url,params={'page':99}).json()['items'] == []
        for params in [{'page':0},{'page_size':101}]:
            assert client.get(url,params=params).status_code == 422


@pytest.mark.parametrize('changes', [
    {'columns':['missing']}, {'columns':['a','a']}, {'rule_type':'invalid'}, {'name':'   '},
    {'config':{'extra':1}}, {'rule_type':'numeric_range','config':{'min':'2','max':'1'}},
    {'rule_type':'numeric_range','config':{'min':'NaN','max':'1'}},
    {'rule_type':'numeric_range','config':{'min':'0','max':'Infinity'}},
    {'rule_type':'numeric_range','config':{'min':0,'max':'1'}},
    {'rule_type':'numeric_range','config':{'min':'0','max':True}},
    {'rule_type':'numeric_range','config':{'min':'0','max':'1','extra':1}},
])
def test_bad_create_not_saved(dataset, changes):
    url=f'/api/datasets/{dataset}/rules'
    with TestClient(app) as client:
        response=client.post(url,json={**payload(),**changes})
        assert response.status_code==422
        assert client.get(url).json()['total']==0


def test_invalid_merged_patch_and_foreign_rule(dataset):
    url=f'/api/datasets/{dataset}/rules'
    with TestClient(app) as client:
        original=client.post(url,json=payload('numeric_range',{'min':'0','max':'1'})).json()
        for changes in [{'rule_type':'required'}, {'columns':['a','b']}, {'config':{'min':'0'}}, {'name':None}, {'is_active':None}]:
            assert client.patch(url+f"/{original['id']}",json=changes).status_code==422
            assert client.get(url).json()['items'][0]==original
        other=client.post('/api/datasets/import',data={'name':'other'},files={'file':('b.csv',b'a\n1')}).json()['dataset_id']
        assert client.patch(f"/api/datasets/{other}/rules/{original['id']}",json={'is_active':False}).status_code==404
        assert client.patch(url+'/999999',json={'name':'x'}).status_code==404
        assert client.get('/api/datasets/999999/rules').status_code==404
        assert client.post('/api/datasets/999999/rules',json=payload()).status_code==404


def test_database_offline(dataset, monkeypatch):
    monkeypatch.setenv('DATABASE_URL','postgresql+psycopg://test:example@127.0.0.1:65432/test')
    with TestClient(app) as client:
        url=f'/api/datasets/{dataset}/rules'
        for response in [client.get(url),client.post(url,json=payload()),client.patch(url+'/1',json={'name':'x'})]:
            assert response.status_code==503
            assert response.json()['error']['code']=='DATABASE_UNAVAILABLE'
            assert 'example' not in response.text
