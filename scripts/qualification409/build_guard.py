"""Stage409B cumulative budget, unique attempts and missing-receipt fail-closed."""
import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111')
p=json.loads((W/'plan.json').read_bytes());name=sys.argv[1];forecast=tuple(map(float,sys.argv[2:4]))
for launch in W.glob('launch-*.json'):
    if not (W/(launch.stem.removeprefix('launch-')+'-resources.json')).is_file():
        raise RuntimeError('Unaccounted previous attempt; recover resource evidence before resume: '+str(launch))
rows=[json.loads(x.read_bytes()) for x in W.glob('*-resources.json')]
cpu=sum(x['charged_CPU_seconds'] for x in rows);wall=sum(x['charged_active_wall_seconds'] for x in rows)
limits=dict(p['early']);limits['disk_bytes']-=128*1024**2
assert cpu+forecast[0]+p['CPU_final_reserve']<limits['cpu_seconds'] and wall+forecast[1]+p['wall_final_reserve']<limits['wall_seconds'],'NO-GO insufficient unchanged cumulative budget'
old=R/'.tools/qualification385/offline_monitor.py'
assert hashlib.sha256(old.read_bytes()).hexdigest()=='fe0f4e83a5b1473a23404e813f3f98693fac8099181d936ca5980e3e1f80a508'
if os.environ.get('SOLAR407_NEW_MONITOR')=='1':raise RuntimeError('Prototype NO-GO after real Windows race; retain old monitor')
monitor=old
spec=importlib.util.spec_from_file_location('m407',monitor);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for key in ('PYTHONPATH','PYTHONHOME','PYTHONHASHSEED','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','PYTEST_ADDOPTS','PYTEST_PLUGINS'):os.environ.pop(key,None)
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',LOCALAPPDATA=str(W/'user-data'),MPLCONFIGDIR=str(W/'matplotlib'),TEMP=str(W/'temp'),TMP=str(W/'temp'))
(W/'temp').mkdir(exist_ok=True)
command=sys.argv[4:]
m.save(W/('launch-'+name+'.json'),dict(command=command,forecast=forecast,priorCPU=cpu,priorWall=wall,monitor_SHA256=hashlib.sha256(monitor.read_bytes()).hexdigest(),plan_SHA256=hashlib.sha256((W/'plan.json').read_bytes()).hexdigest(),external_source_reserve=128*1024**2))
import psutil
parent=psutil.Process();start=time.perf_counter()
def hook(sample):
    if parent.memory_info().vms+sample['private_tree']>limits['private_bytes']:raise MemoryError('Combined private limit')
record=m.monitor(command,W/('guard-'+name),W,limits,used_cpu=cpu+time.process_time(),stage_start=start-wall,hook=hook)
charge=record['worker_CPU_seconds']+time.process_time()+.25;elapsed=time.perf_counter()-start+.25
m.save(W/(name+'-resources.json'),dict(record=record,charged_CPU_seconds=charge,charged_active_wall_seconds=elapsed,total_CPU=cpu+charge,total_wall=wall+elapsed,tail_allowances=.25,execution_completed=record['exit_code'] is not None and record['limit_reason'] is None))
print(json.dumps(dict(name=name,exit_code=record['exit_code'],reason=record['limit_reason'],charged_CPU=charge,total_CPU=cpu+charge,total_wall=wall+elapsed)),flush=True)
raise SystemExit(0 if record['complete'] else 1)
