"""Create separate, retained BUG-03 QA datasets; never edit existing QA rows."""
from pathlib import Path
import json
import sys
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine
from app.config import get_database_url
from nv01_migrate import snapshot
from app.services.csv_reader import parse_csv
from app.services.dataset_import import import_dataset, import_version
from app.services.data_batches import patch_batch
from app.services.quality_rules import create_rule
from app.services.quality_execution import execute_run


def main():
    out = ROOT / 'frontend/test-artifacts/bug03/local-qa.json'
    if out.exists():
        raise SystemExit('BUG-03 QA already seeded; inspect local-qa.json instead of duplicating it.')
    engine = create_engine(get_database_url(), hide_parameters=True)
    before = json.loads((ROOT / '.runtime/bug03-before.json').read_text(encoding='utf-8'))
    assert snapshot(engine, before) == before, 'Pre-existing rows changed; investigate before adding QA data.'
    fixture = Path('D:/User_File/ChatGPT/DACN/qa_test_data')
    raw = parse_csv((fixture / 'v1.0_raw.csv').read_bytes())
    stamp = datetime.now().strftime('%d-%m-%Y %H:%M')
    ds = import_dataset(raw, 'v1.0_raw.csv', dict(name=f'BUG-03 QA — Sinh viên v1-v3 — {stamp}', owner='QA', source='BUG-03 riêng', description='Dữ liệu thử mới; không thay đổi dataset 52 hoặc đợt 27.'))
    dataset, batch = ds['dataset_id'], ds['batch_id']
    patch_batch(dataset, batch, dict(name='BUG-03 QA — Luồng v1 → v3', period_label='11/2026'))
    rules = [dict(name=f'{c} bắt buộc', rule_type='required', columns=[c], config={}) for c in raw.header]
    rules += [
        dict(name='Mã duy nhất', rule_type='unique', columns=['ma_sinh_vien'], config={}),
        dict(name='Email trường', rule_type='pattern', columns=['email'], config={'dialect':'re2-v1','pattern':r'[A-Za-z0-9._%+-]+@hcmut\.edu\.vn'}),
        dict(name='Điện thoại', rule_type='pattern', columns=['so_dien_thoai'], config={'dialect':'re2-v1','pattern':r'0[0-9]{9}'}),
        dict(name='Ngày sinh', rule_type='date_format', columns=['ngay_sinh'], config={'format':'YYYY-MM-DD','min':'1900-01-01','max':'2026-11-08'}),
        dict(name='Điểm', rule_type='numeric_range', columns=['diem_tong_ket'], config={'min':'0','max':'10'}),
    ]
    for rule in rules:
        create_rule(dataset, dict(**rule, is_active=True))
        create_rule(dataset, dict(**rule, is_active=True), batch)
    runs = [execute_run(dataset, ds['version_id'])]
    for filename in ('v1.1_fixed.csv', 'v1.2_clean.csv'):
        version = import_version(dataset, parse_csv((fixture / filename).read_bytes()), filename, batch)
        runs.append(execute_run(dataset, version['version_id']))
    assert [(r['error_row_count'], r['violation_count']) for r in runs] == [(9,16),(2,2),(0,0)]
    white_file = ROOT / 'frontend/test-artifacts/bug03/whitespace.csv'
    white = import_dataset(parse_csv(white_file.read_bytes()), white_file.name, dict(name=f'BUG-03 QA — Khoảng trắng — {stamp}', owner='QA', source='BUG-03 riêng', description='Phân biệt chuỗi rỗng, space/tab/Unicode, 0 và literal NULL/NaN/N/A.'))
    patch_batch(white['dataset_id'], white['batch_id'], dict(name='BUG-03 QA — Hiển thị khoảng trắng', period_label='11/2026'))
    for rule in [dict(name='Bắt buộc',rule_type='required',columns=['value'],config={}),dict(name='Chỉ nhận OK',rule_type='pattern',columns=['value'],config={'dialect':'re2-v1','pattern':'OK'})]:
        create_rule(white['dataset_id'], dict(**rule,is_active=True), white['batch_id'])
    white_run = execute_run(white['dataset_id'], white['version_id'])
    unchanged = snapshot(engine, before) == before
    engine.dispose()
    proof = dict(original_rows_unchanged=unchanged, students=dict(dataset_id=dataset,batch_id=batch,runs=[dict(id=r['run_id'],error_rows=r['error_row_count'],violations=r['violation_count']) for r in runs]),whitespace=dict(dataset_id=white['dataset_id'],batch_id=white['batch_id'],run_id=white_run['run_id']),fixture_file=str(white_file.relative_to(ROOT)))
    out.write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
    assert unchanged, 'Pre-existing QA row checksum changed.'
    print(json.dumps(proof,ensure_ascii=False))


if __name__ == '__main__':
    main()
