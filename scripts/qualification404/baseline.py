"""Confirm the existing minimal failing403reproducer on exacte9, before edits."""
import json,sys,subprocess,hashlib,importlib.metadata
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
W=R/'.tools/qualification404-20261108'
def main():
 p=json.loads((R/'scripts/qualification404/plan.json').read_bytes());root=Path(p['base_source']);sys.path.insert(0,str(root/'src'))
 import solar_simulator,solar_native,numpy,scipy
 from solar_simulator.recipe import runtime_fingerprint
 from scripts.q2_source_adapter396 import require_origins
 require_origins(solar_simulator.__file__,[numpy.__file__,scipy.__file__,solar_native.__file__],root,sys.prefix,Path(p['interpreter']).parents[1])
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==p['base_commit'] and not subprocess.check_output(['git','-C',str(root),'status','--porcelain'])
 fp=runtime_fingerprint('rust');raw=(json.dumps(fp,indent=2)+'\n').encode();assert hashlib.sha256(raw).hexdigest()==p['base_fingerprint']
 q.require_sha(getattr(solar_native,'solar_native',solar_native).__file__,p['native_SHA256'])
 with (W/'base-actual-environment.json').open('xb') as stream:stream.write(raw)
 repro=R/'scripts/qualification403/reproduce_close.py';q.require_sha(repro,p['reproducer_SHA256'])
 command=[sys.executable,'-X','utf8','-B',str(repro),'--source',str(root)]
 with (W/'baseline-reproducer.log').open('xb') as stream:r=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
 log=(W/'baseline-reproducer.log').read_text();assert r.returncode!=0 and 'AssertionError' in log
 assert all(x in log for x in ('invalid command name','_poll','_layout','idle_draw'))
 q.atomic_json(W/'baseline.json',dict(status='EXPECTED_FAIL_CONFIRMED',returncode=r.returncode,command=command,source=p['base_commit'],actual_source_fingerprint=p['base_fingerprint'],actual_import=solar_simulator.__file__,dependency_prefix=sys.prefix,native_SHA256=p['native_SHA256'],Matplotlib=importlib.metadata.version('matplotlib'),reproducer_SHA256=q.sha(repro),raw_log_SHA256=q.sha(W/'baseline-reproducer.log'),orbits=0,assertion='Original403 assert no background errors fails on exacte9; not xfail/skip or hidden PASS'))
 print('Confirmed original FAIL403 on exacte9 with actual source/dependency/native identity; no orbits',flush=True)
if __name__=='__main__':main()
