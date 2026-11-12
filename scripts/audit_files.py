"""Read-only inventory and static reference audit. Does not import project code."""
from pathlib import Path
import ast
import hashlib
import json
import re
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'node_modules', '.venv', 'venv', '.git', '__pycache__', '.pytest_cache', 'dist'}
def rel(path): return path.relative_to(ROOT).as_posix()
files = [p for p in ROOT.rglob('*') if p.is_file()]
texts = {}
for p in files:
    if any(x in SKIP for x in p.relative_to(ROOT).parts) or p.name.startswith('.env'):
        continue
    if p.suffix in {'.py', '.ts', '.tsx', '.mjs', '.json', '.md', '.yaml', '.cmd', '.ps1', '.html', '.css', '.txt'}:
        texts[p] = p.read_text(encoding='utf-8-sig', errors='replace')

src = ROOT / 'frontend/src'
nodes = {p for p in texts if p.is_relative_to(src)}
graph = {p: set() for p in nodes}
unresolved = []
for p in nodes:
    for spec in re.findall(r'''(?:from\s*|import\s*\(\s*|import\s*)['"]([^'"]+)['"]''', texts[p]):
        if not spec.startswith('.'): continue
        base = p.parent / spec
        candidates = [base] + [Path(str(base) + ext) for ext in ('.ts', '.tsx', '.css', '.json')] + [base / 'index.ts', base / 'index.tsx']
        match = next((c.resolve() for c in candidates if c.is_file()), None)
        if match in nodes: graph[p].add(match)
        elif match is None: unresolved.append([rel(p), spec])
seen = set()
def visit(p):
    if p in seen: return
    seen.add(p)
    for dep in graph.get(p, ()): visit(dep)
visit(src / 'main.tsx')

orphans = []
for p in sorted(nodes - seen):
    if p.name.endswith('.d.ts'): continue
    refs = [rel(q) for q, content in texts.items() if q != p and '.backups' not in q.parts and (p.stem in content or rel(p) in content)]
    orphans.append({'file': rel(p), 'references': refs})

stale = []
for p in files:
    if '__pycache__' not in p.parts or any(x in {'.venv','venv','node_modules','.backups','.experiments'} for x in p.parts): continue
    if p.suffix == '.pyc':
        source = p.parent.parent / (p.name.split('.cpython-')[0] + '.py')
        if not source.exists(): stale.append(rel(p))

hashes = defaultdict(list)
for p in files:
    if any(x in SKIP or x in {'.backups','.experiments'} for x in p.relative_to(ROOT).parts): continue
    if p.stat().st_size: hashes[hashlib.sha256(p.read_bytes()).hexdigest()].append(rel(p))
duplicates = [v for v in hashes.values() if len(v)>1]
groups = {}
for label, pred in {
    'python_cache': lambda p: '__pycache__' in p.parts and not any(x in {'.venv','venv','.experiments','.backups'} for x in p.parts),
    'pytest_cache': lambda p: '.pytest_cache' in p.parts,
    'logs_outside_backups': lambda p: p.suffix == '.log' and not any(x in SKIP or x == '.backups' for x in p.relative_to(ROOT).parts),
}.items():
    selected = [p for p in files if pred(p)]
    groups[label] = {'files':len(selected),'bytes':sum(p.stat().st_size for p in selected), 'paths':[rel(p) for p in selected]}

app = ROOT / 'backend/app'
modules = {'.'.join(p.relative_to(ROOT / 'backend').with_suffix('').parts):p for p in texts if p.is_relative_to(app) and p.suffix == '.py'}
backend_edges = {m:set() for m in modules}
for m,p in modules.items():
    for n in ast.walk(ast.parse(texts[p])):
        targets = []
        if isinstance(n, ast.Import): targets = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            prefix = n.module or ''
            if n.level:
                package = m.split('.')[:-1]
                prefix = '.'.join(package[:len(package)-n.level+1] + ([prefix] if prefix else []))
            targets = [prefix] + [prefix + '.' + a.name for a in n.names]
        for target in targets:
            if target in modules: backend_edges[m].add(target)
backend_seen=set()
def backend_visit(m):
    if m in backend_seen:return
    backend_seen.add(m)
    for dep in backend_edges.get(m, ()):backend_visit(dep)
backend_visit('app.main')
backend_other = [rel(p) for m,p in modules.items() if m not in backend_seen and p.name != '__init__.py']
print(json.dumps({'frontend_total':len(nodes),'frontend_reachable':len(seen),'unreachable_frontend':orphans,'unresolved_imports':unresolved,'backend_modules':len(modules),'backend_reachable':len(backend_seen),'backend_outside_main_graph':backend_other,'orphan_pyc':stale,'groups':groups,'duplicates':duplicates},ensure_ascii=False,indent=2))
