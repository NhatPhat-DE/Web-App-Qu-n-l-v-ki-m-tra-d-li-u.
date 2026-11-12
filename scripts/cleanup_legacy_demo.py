"""Explicitly reviewed legacy demo cleanup; dry-run unless --apply is supplied.

Never infer demo status from an ID range. Back up under DML locks, verify all
retained rows in the same transaction, and leave shared repository fixtures alone.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, inspect, text
from app.config import get_database_url
from app.services.batch_dashboard import dashboard

# Reviewed against persisted metadata, not selected by ID or a name regex.
EVIDENCE = {
    17: 'Demo CSV 07; description Demo import CSV; source samples/import_demo.csv',
    22: 'Demo CSV 10; source samples/import_demo.csv',
    23: 'Description explicitly says data serves quality testing and profiling',
    28: 'Demo Quality Errors 16; sample source and explicit expected test counts',
    29: 'Rules UI Test 17; source API client verification',
    30: 'Version UI Test 19B',
    36: 'Metadata API Test 21A updated',
    37: 'Metadata UI Test 21B updated AAAA',
    38: 'Type Inference Demo 22B; source 22B HTTP verification',
    41: 'Source explicitly says simulated data; description says import/quality tested',
    42: 'QT-01A Data Type Demo; sample source and expected test counts',
    43: 'Acceptance dataset data_type QT-01C; documented test milestone in docs/RULE_EXTENSION_PLAN.md',
    44: 'QT-02A Date Format Demo; sample source and expected test counts',
    45: 'QT-02C UI Test.',
    46: 'QT-03A Allowed Values Demo; source samples/allowed_values_qt03a.csv',
    47: 'QT-03C UI Test.',
    48: 'QT-04A Pattern RE2 Demo; source samples/pattern_qt04a.csv',
    49: 'QT-04C UI Test.',
}
UNCLEAR = {
    35: 'Personal name and ERP/POS source; no reliable demo provenance',
    39: 'Product name and ERP/POS source; no reliable demo provenance',
    40: 'Product name and ERP/POS source; no reliable demo provenance',
    50: 'Test name conflicts with business description of monthly VIP customer data',
    51: 'AAAAAA/AAAAA suggests a draft but is insufficient proof of origin',
}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def read_rows(c, tables):
    return {t: c.execute(text(f'SELECT row_to_json(r)::text FROM "{t}" r ORDER BY row_to_json(r)::text')).scalars().all() for t in tables}


def hashes(rows, deleted):
    result = {}
    for table, values in rows.items():
        kept = [r for r in values if json.loads(r).get('id') not in deleted.get(table, set())]
        result[table] = dict(count=len(kept), sha256=hashlib.sha256('\n'.join(kept).encode()).hexdigest())
    return result


def schema(c):
    return dict(
        columns=[list(r) for r in c.execute(text("SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position"))],
        constraints=[list(r) for r in c.execute(text("SELECT conrelid::regclass::text,conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE connamespace='public'::regnamespace ORDER BY 1,2"))],
        indexes=[list(r) for r in c.execute(text("SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY 1,2"))],
    )


def closure(records, fks, dataset_ids):
    deleted = {t: set() for t in records}
    deleted['datasets'] = set(dataset_ids)
    changed = True
    while changed:
        changed = False
        for child, constraints in fks.items():
            for fk in constraints:
                parent = fk['referred_table']
                keys = {tuple(r[col] for col in fk['referred_columns']) for r in records[parent] if r.get('id') in deleted[parent]}
                for row in records[child]:
                    key = tuple(row[col] for col in fk['constrained_columns'])
                    if all(v is not None for v in key) and key in keys and row['id'] not in deleted[child]:
                        deleted[child].add(row['id'])
                        changed = True
    # A cross-scope reference must never expand cleanup into a kept dataset.
    for table, values in records.items():
        for row in values:
            if row.get('id') in deleted[table] and 'dataset_id' in row:
                assert row['dataset_id'] in dataset_ids, f'Cross-dataset dependency in {table}; abort'
    assert not deleted['users'] and not deleted['user_sessions']
    return deleted


def orphan_counts(c, fks):
    result = {}
    for child, constraints in fks.items():
        for fk in constraints:
            present = ' AND '.join(f'c."{col}" IS NOT NULL' for col in fk['constrained_columns'])
            join = ' AND '.join(f'p."{p}"=c."{ch}"' for ch, p in zip(fk['constrained_columns'], fk['referred_columns']))
            count = c.execute(text(f'SELECT count(*) FROM "{child}" c WHERE {present} AND NOT EXISTS (SELECT 1 FROM "{fk["referred_table"]}" p WHERE {join})')).scalar_one()
            if count:
                result[f'{child}.{fk["name"]}'] = count
    return result


def main():
    apply = sys.argv[1:] == ['--apply']
    assert sys.argv[1:] in ([], ['--apply'])
    engine = create_engine(get_database_url(), hide_parameters=True)
    backup = None
    with engine.begin() as c:
        tables = sorted(inspect(c).get_table_names())
        assert all(t.replace('_', '').isalnum() for t in tables)
        c.execute(text("SET LOCAL lock_timeout='5s'"))
        c.execute(text('LOCK TABLE ' + ','.join(f'"{t}"' for t in tables) + ' IN SHARE ROW EXCLUSIVE MODE'))
        raw = read_rows(c, tables)
        records = {t: [json.loads(r) for r in rows] for t, rows in raw.items()}
        datasets = {r['id']: r for r in records['datasets']}
        assert set(EVIDENCE) <= datasets.keys(), 'Reviewed dataset missing; re-audit first'
        milestone = datasets[52]
        assert 'NV-01 QA' in milestone['name'] and 'Sinh viên' in milestone['name']
        for identifier in EVIDENCE:
            assert identifier < 52 and datasets[identifier]['created_at'] < milestone['created_at']
        fks = {t: inspect(c).get_foreign_keys(t) for t in tables}
        deleted = closure(records, fks, set(EVIDENCE))
        before = hashes(raw, deleted)
        schema_before = schema(c)
        assert not orphan_counts(c, fks), 'Pre-existing orphan references; abort for review'
        assert all(r['status'] in ('completed', 'failed') for r in records['quality_runs']), 'Run in progress; retry when idle'
        retained_batches = [r['id'] for r in records['data_batches'] if r['id'] not in deleted['data_batches']]
        dashboard_before = dashboard(retained_batches)
        per_dataset = {}
        for identifier in EVIDENCE:
            scoped = closure(records, fks, {identifier})
            per_dataset[identifier] = {t: len(ids) for t, ids in scoped.items() if ids}
        manifest = dict(
            created_at=datetime.now(timezone.utc).isoformat(), milestone=milestone,
            delete=[dict(**datasets[i], evidence=reason, dependent_counts=per_dataset[i]) for i, reason in EVIDENCE.items()],
            kept=[dict(**r, reason=UNCLEAR.get(i, 'Protected: dataset52 or later')) for i, r in datasets.items() if i not in EVIDENCE],
            delete_counts={t: len(ids) for t, ids in deleted.items()},
            delete_ids={t: sorted(ids) for t, ids in deleted.items()}, foreign_keys=fks,
            retained_before=before, schema_before=schema_before,
            physical_upload_files=[], files_deleted=[],
            storage_note='Upload bytes are parsed in memory into dataset_rows. Only original_filename/file_size_bytes metadata persists; no upload file path/storage columns or file-writing code. Repository CSV fixtures are kept, including shared sources.',
        )
        if not apply:
            write_json(ROOT / '.runtime' / 'legacy-cleanup-plan.json', manifest)
            print(json.dumps(dict(mode='dry-run', delete=list(EVIDENCE), keep=list(UNCLEAR), counts=manifest['delete_counts'])))
            return
        backup = ROOT / '.backups' / ('legacy-demo-cleanup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        backup.mkdir(parents=True, exist_ok=False)
        # Save the exact approved list before any destructive statement.
        write_json(backup / 'manifest.json', manifest)
        write_json(backup / 'deleted-rows.json', {t: [r for r in records[t] if r.get('id') in ids] for t, ids in deleted.items() if ids})
        dump = backup / 'database.dump'
        with dump.open('wb') as target:
            result = subprocess.run(['docker', 'exec', 'webb-postgres-1', 'sh', '-c', 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'], stdout=target, stderr=subprocess.PIPE)
        assert result.returncode == 0 and dump.stat().st_size > 100, 'Backup failed; no deletions applied'
        with dump.open('rb') as src:
            assert src.read(5) == b'PGDMP', 'Invalid dump header'
        with dump.open('rb') as src:
            listing = subprocess.run(['docker', 'exec', '-i', 'webb-postgres-1', 'pg_restore', '--list'], stdin=src, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert listing.returncode == 0 and b'TABLE DATA public datasets' in listing.stdout, 'Backup catalog verification failed'
        (backup / 'database-contents.txt').write_bytes(listing.stdout)
        with dump.open('rb') as src:
            decoded = subprocess.run(['docker', 'exec', '-i', 'webb-postgres-1', 'pg_restore', '--file=/dev/null'], stdin=src, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        assert decoded.returncode == 0, 'Backup payload verification failed; no deletions applied'
        # Archive matching source CSVs as supporting evidence; never remove repo assets.
        source_paths = {Path(r['source'].replace('\\', '/')).name for i, r in datasets.items() if i in EVIDENCE and r.get('source')}
        filenames = source_paths | {r['original_filename'] for r in records['dataset_versions'] if r['id'] in deleted['dataset_versions']}
        candidates = subprocess.run(['rg', '--files', '--hidden', '-g', '!.git', '-g', '!.backups', '-g', '!.venv', '-g', '!node_modules', '-g', '!test-artifacts', '-g', '!.runtime'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
        archived = []
        for relative in candidates:
            path = (ROOT / relative).resolve()
            assert path.is_relative_to(ROOT)
            if path.name in filenames and path.suffix.lower() == '.csv':
                dest = backup / 'source-files' / path.relative_to(ROOT)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                archived.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), action='backed up; original retained as repository fixture'))
        manifest['source_file_backups'] = archived
        manifest['database_dump_sha256'] = hashlib.sha256(dump.read_bytes()).hexdigest()
        write_json(backup / 'manifest.json', manifest)
        (backup / 'RESTORE.md').write_text('''# Khôi phục dữ liệu trước khi dọn

`database.dump` là bản sao PostgreSQL custom-format đầy đủ, gồm tài khoản,
phân quyền, snapshot và nội dung CSV đã lưu trong dataset_rows. manifest.json
ghi danh sách, lý do, từng ID phụ thuộc, số lượng và hash dữ liệu được giữ.
deleted-rows.json chỉ để kiểm tra, không thay thế dump. source-files chứa bản
sao CSV nguồn tìm được trong repo; bản gốc vẫn được giữ vì là fixture dùng chung.
Không có file upload vật lý riêng để xóa.

1. Dừng ghi vào ứng dụng trong thời gian phục hồi. Giữ bản sao database hiện tại.
2. Tạo database phục hồi RIÊNG, ví dụ legacy_demo_restore, bằng createdb với
   tài khoản PostgreSQL hiện có (không đưa mật khẩu vào lệnh hoặc log).
3. Chạy pg_restore --exit-on-error --single-transaction --no-owner
   --dbname=legacy_demo_restore database.dump. Nếu dùng Docker, truyền file
   bằng stdin nhị phân từ Python subprocess.run hoặc copy vào container.
   Không dùng PowerShell Get-Content dạng text cho file dump nhị phân.
4. Kiểm tra dataset và số lượng trong manifest.json trên database phục hồi.
   Khi cần phục hồi riêng các dataset đã dọn vào database đang dùng: lấy đúng
   ID trong manifest từ database phục hồi, nhập theo thứ tự cha trước/con sau,
   trong một transaction; kiểm tra xung đột ID và tham chiếu trước khi commit.
   Không ghi đè hoặc reset database production đang chạy.
5. Chỉ chuyển ứng dụng sang database phục hồi đầy đủ sau khi đã đối chiếu mọi
   thay đổi phát sinh sau thời điểm backup. Dữ liệu mới sau backup không nằm
   trong dump; không phục hồi đè để tránh mất dữ liệu.

Không schema/migration nào bị thay đổi bởi tác vụ dọn. Sequence ID giữ nguyên.
''', encoding='utf-8')
        # Child-first topological order derived from the actual FK graph.
        pending = {t for t, ids in deleted.items() if ids}
        order = []
        while pending:
            leaves = sorted(t for t in pending if not any(fk['referred_table'] == t for child in pending - {t} for fk in fks[child]))
            assert leaves, 'FK cycle; rollback and review'
            for table in leaves:
                result = c.execute(text(f'DELETE FROM "{table}" WHERE id=ANY(:ids)'), {'ids': sorted(deleted[table])})
                assert result.rowcount == len(deleted[table]), f'Unexpected deletion count: {table}'
                order.append(table)
                pending.remove(table)
        after_raw = read_rows(c, tables)
        after = hashes(after_raw, {})
        assert after == before, 'Retained data changed; transaction rolled back'
        assert schema(c) == schema_before, 'Schema changed; transaction rolled back'
        assert not orphan_counts(c, fks), 'Broken references; transaction rolled back'
        write_json(backup / 'transaction-verification.json', dict(retained_rows_unchanged=True, schema_unchanged=True, orphan_foreign_keys=0, deletion_order=order, retained_after=after))
    # No filesystem deletion is needed: there are no persisted upload files.
    # All future file removal, if storage changes, must happen only after commit.
    after_dashboard = dashboard()
    assert after_dashboard == dashboard_before, 'Dashboard differs from pre-cleanup retained scope'
    assert not (set(EVIDENCE) & {r['dataset_id'] for r in after_dashboard['items']})
    with engine.connect() as c:
        qa_runs = [dict(r) for r in c.execute(text('SELECT id,dataset_version_id,status,total_rows,error_row_count,violation_count FROM quality_runs WHERE id IN (59,60,61,66,67,83,84) ORDER BY id')).mappings()]
        completed = c.execute(text('SELECT business_state FROM data_batches WHERE id=39 AND dataset_id=58')).scalar_one()
        assert completed == 'COMPLETED'
        assert next(r for r in qa_runs if r['id'] == 83)['violation_count'] == 3
        assert next(r for r in qa_runs if r['id'] == 84)['violation_count'] == 0
    write_json(backup / 'verification.json', dict(committed=True, retained_rows_unchanged=True, schema_unchanged=True, foreign_key_orphans=0, dashboard_exactly_matches_retained_before=True, dashboard=after_dashboard, qa_runs=qa_runs, batch39_business_state=completed, physical_files_deleted=0))
    print(json.dumps(dict(committed=True, backup=str(backup), deleted=list(EVIDENCE), kept_unclear=list(UNCLEAR), counts=manifest['delete_counts'], dashboard_totals=after_dashboard['totals'] if 'totals' in after_dashboard else {k: v for k, v in after_dashboard.items() if k != 'items'}), default=str))
    engine.dispose()


if __name__ == '__main__':
    main()
