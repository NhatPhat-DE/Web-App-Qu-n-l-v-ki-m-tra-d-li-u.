from nv01_fixtures import saved_run_fields
from nv01_fixtures import batch_rule_path
"""Written answer: three failing rows, five violations, 75%; fixed version 0%."""
from authenticated_client import TestClient
from app.main import app
from test_dataset_import import isolated_database


def test_full_demo_flow(isolated_database):
    with TestClient(app) as client:
        response=client.post(batch_rule_path(client, '/api/datasets/import'),data={'name':'integration-only'},files={'file':('bad.csv',b'code,amount\n,101\ndup,-1\ndup,10\nok,50\n')})
        assert response.status_code==201
        imported=response.json();dataset=imported['dataset_id'];v1=imported['version_id']
        rules=[]
        for name,kind,columns,config in [('Code required','required',['code'],{}),('Code unique','unique',['code'],{}),('Amount range','numeric_range',['amount'],{'min':'0','max':'100'})]:
            response=client.post(batch_rule_path(client, f'/api/datasets/{dataset}/rules'),json={'name':name,'rule_type':kind,'columns':columns,'config':config})
            assert response.status_code==201
            rules.append(response.json())
        response=client.post(batch_rule_path(client, f'/api/datasets/{dataset}/versions/{v1}/runs'))
        assert response.status_code==201
        run1=response.json()['run_id']
        base=f'/api/datasets/{dataset}/runs/{run1}'
        old=client.get(batch_rule_path(client, base)).json()
        assert (old['total_rows'],old['error_row_count'],old['violation_count'],old['error_row_rate'])==(4,3,5,'75.0000')
        expected=[
            (1,rules[0]['id'],'required',['code'],[''],'REQUIRED_MISSING','Giá trị bắt buộc đang thiếu.'),
            (1,rules[2]['id'],'numeric_range',['amount'],['101'],'NUMERIC_OUT_OF_RANGE','Giá trị nằm ngoài khoảng đóng cho phép.'),
            (2,rules[1]['id'],'unique',['code'],['dup'],'UNIQUE_DUPLICATE','Giá trị hoặc tổ hợp giá trị bị trùng.'),
            (2,rules[2]['id'],'numeric_range',['amount'],['-1'],'NUMERIC_OUT_OF_RANGE','Giá trị nằm ngoài khoảng đóng cho phép.'),
            (3,rules[1]['id'],'unique',['code'],['dup'],'UNIQUE_DUPLICATE','Giá trị hoặc tổ hợp giá trị bị trùng.')]
        errors=client.get(batch_rule_path(client, base+'/violations')).json()
        assert [(e['row_number'],e['rule_id_snapshot'],e['rule_type'],e['columns'],e['values'],e['error_code'],e['message']) for e in errors['items']]==expected
        assert client.get(batch_rule_path(client, base+'/violations'),params={'row_number':2,'rule_id_snapshot':rules[2]['id']}).json()['total']==1
        fixed=client.post(batch_rule_path(client, f'/api/datasets/{dataset}/versions/import'),files={'file':('fixed.csv',b'code,amount\nc1,100\nc2,0\nc3,10\nok,50\n')})
        assert fixed.status_code==201 and fixed.json()['version_number']==2
        response=client.post(batch_rule_path(client, f'/api/datasets/{dataset}/versions/{fixed.json()["version_id"]}/runs'))
        assert response.status_code==201
        new=response.json();assert (new['error_row_count'],new['violation_count'],new['error_row_rate'])==(0,0,'0.0000')
        assert saved_run_fields(client.get(batch_rule_path(client, base)).json()) == saved_run_fields(old)
        assert client.get(batch_rule_path(client, base+'/violations')).json()==errors
        assert client.get(batch_rule_path(client, f'/api/datasets/{dataset}/runs')).json()['total']==2
        assert client.patch(batch_rule_path(client, f'/api/datasets/{dataset}/rules/{rules[2]["id"]}'),json={'name':'Changed range','config':{'min':'0','max':'1000'}}).status_code==200
        assert saved_run_fields(client.get(batch_rule_path(client, base)).json()) == saved_run_fields(old)
        before=client.get(batch_rule_path(client, f'/api/datasets/{dataset}')).json()
        response=client.post(batch_rule_path(client, f'/api/datasets/{dataset}/versions/import'),files={'file':('schema.csv',b'amount,code\n1,c1')})
        assert response.status_code==422 and response.json()['error']['code']=='CSV_SCHEMA_MISMATCH'
        assert client.get(batch_rule_path(client, f'/api/datasets/{dataset}')).json()==before
