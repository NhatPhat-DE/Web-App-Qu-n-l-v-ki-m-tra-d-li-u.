"""GET-only real-browser cleanup verification, using the existing CDP harness."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts')]
from sqlalchemy import create_engine, select, delete
from app.config import get_database_url
from app.models import User, Session
from app.services.auth_sessions import create_session
from app.services.quality_rules import rule_connection
from nv01_migrate import snapshot

source = (ROOT / 'frontend/verify-demo-ui-local.mjs').read_text(encoding='utf-8')
prefix = source[:source.index(" if(phase==='before')")]
suffix = source[source.index('}catch(error){'):]
body = r'''
 const get=async url=>evaluate(`fetch(${JSON.stringify(url)}).then(r=>{if(!r.ok)throw Error('GET '+r.status);return r.json()})`)
 await send('Page.navigate',{url:origin+'/#/dashboard'})
 await waitFor(`document.querySelector('.demo-tiles')&&!document.querySelector('.loading-state')`)
 const data=await get('/api/batch-dashboard')
 const removed=[17,22,23,28,29,30,36,37,38,41,42,43,44,45,46,47,48,49]
 assert.equal(data.items.length,21)
 assert.ok(data.items.every(i=>!removed.includes(i.dataset_id)))
 assert.deepEqual([data.total_rows,data.violated_rows_count,data.total_violations_count],[108,34,44])
 assert.equal(await evaluate(`document.querySelectorAll('.demo-tile').length`),data.items.length)
 assert.deepEqual(await evaluate(`[...document.querySelectorAll('.demo-kpi>strong')].slice(0,2).map(e=>e.textContent)`),['31,48%','44'])
 const links=await evaluate(`[...document.querySelectorAll('.demo-tile')].map(e=>e.getAttribute('href'))`)
 assert.equal(links.length,21)
 for(const item of data.items)assert.ok(links.some(h=>h.includes('/datasets/'+item.dataset_id+'/batches/'+item.batch_id)))
 await screenshot('dashboard-after-cleanup')
 checks.push('Dashboard: 21 retained batches; no deleted datasets; 108 records/34 error rows/44 violations; all batch links valid')
 for(const id of [35,39,40,50,51,52,53,54,55,56,57,58])assert.equal((await get('/api/datasets/'+id)).id,id)
 for(const [id,expected] of [[59,[12,9,16]],[60,[12,2,2]],[61,[12,0,0]],[66,[12,6,9]],[67,[12,6,8]],[83,[3,2,3]],[84,[3,0,0]]]){
  const ds=id<66?52:id<83?55:58,r=await get('/api/datasets/'+ds+'/runs/'+id)
  assert.deepEqual([r.total_rows,r.error_row_count,r.violation_count],expected)
 }
 assert.equal((await get('/api/datasets/58/batches/39')).business_state,'COMPLETED')
 await go('/datasets/58/batches/39','Khách hàng')
 await waitFor(`document.querySelector('.batch-tabs')&&!document.querySelector('.loading-state')`)
 await screenshot('qa58-batch39-after-cleanup')
 checks.push('All kept dataset APIs and QA runs59/60/61/66/67/83/84 unchanged; batch39 remains COMPLETED')
 assert.deepEqual(writes,[]);assert.deepEqual(errors,[])
 fs.writeFileSync(path.join(out,'verification.json'),JSON.stringify({checks,layouts,consoleErrors:errors,writes},null,2))
 console.log(JSON.stringify({passed:checks.length,checks}))
'''


def main():
    engine = create_engine(get_database_url(), hide_parameters=True)
    before = snapshot(engine)
    with rule_connection() as c:
        user = c.execute(select(User.id).where(User.username == 'admin', User.is_active.is_(True), User.role == 'admin')).scalar_one()
        session = create_session(c, user)
    try:
        config = dict(origin='http://127.0.0.1:5173', token=session['token'], phase='legacy-cleanup')
        subprocess.run(['node', '--input-type=module', '-e', prefix + body + suffix], cwd=ROOT / 'frontend', input=json.dumps(config), text=True, check=True)
    finally:
        with rule_connection() as c:
            c.execute(delete(Session).where(Session.id == session['id'], Session.user_id == user))
        after = snapshot(engine)
        output = ROOT / 'frontend/test-artifacts/demo-ui-legacy-cleanup'
        output.mkdir(parents=True, exist_ok=True)
        (output / 'preservation.json').write_text(json.dumps(dict(application_rows_unchanged=before == after, own_session_removed=True, before=before, after=after), indent=2), encoding='utf-8')
        assert before == after, 'Read-only verification changed data'
        engine.dispose()


if __name__ == '__main__':
    main()
