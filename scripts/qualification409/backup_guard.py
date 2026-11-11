"""409C cumulative bound, existing tested200ms monitor; connector wall in separate rows."""
import hashlib, importlib.util, json, os, sys, time
from pathlib import Path
import psutil
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-backup-20261111')
p=json.loads((W/'plan.json').read_bytes());name=sys.argv[1]
rows=[json.loads(f.read_bytes()) for f in W.glob('*-resources.json')]
cpu=sum(x['charged_CPU_seconds'] for x in rows);wall=sum(x['charged_active_wall_seconds'] for x in rows)
for f in W.glob('launch-*.json'):
 if not (W/(f.stem.removeprefix('launch-')+'-resources.json')).exists():raise RuntimeError('Missing previous receipt')
assert cpu+float(sys.argv[2])+p['CPU_final_reserve']<p['early']['cpu_seconds']
assert wall+float(sys.argv[3])+p['wall_final_reserve']<p['early']['wall_seconds']
monitor=R/p['monitor_path'];assert hashlib.sha256(monitor.read_bytes()).hexdigest()==p['monitor_SHA256']
spec=importlib.util.spec_from_file_location('m409c',monitor);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
command=sys.argv[4:];ref=json.load(sys.stdin) if os.environ.get('SOLAR409C_READBACK')=='1' else None
if ref is not None:os.environ['SOLAR409_REF']=json.dumps(ref)
limits=dict(p['early']);limits['wall_seconds']=min(limits['wall_seconds'],wall+p['per_object_wall'])
m.save(W/('launch-'+name+'.json'),dict(command=command,plan_SHA256=hashlib.sha256((W/'plan.json').read_bytes()).hexdigest(),monitor_SHA256=p['monitor_SHA256'],prior_CPU=cpu,prior_active_wall=wall))
start=time.perf_counter();parent=psutil.Process()
def hook(sample):
 if parent.memory_info().private+sample['private_tree']>p['early']['private_bytes']:raise MemoryError('Combined private cap')
record=m.monitor(command,W/('guard-'+name),W,limits,used_cpu=cpu+time.process_time(),stage_start=start-wall,hook=hook)
charge=record['worker_CPU_seconds']+time.process_time()+.25;elapsed=time.perf_counter()-start+.25
if ref is not None and not (W/'downloads'/(ref['label']+'-completion.json')).exists():
 m.save(W/'downloads'/(ref['label']+'-completion.json'),dict(label=ref['label'],id=ref['expected']['id'],status='SUPERVISOR_STOP_PARTIAL_NOT_VERIFIED',record=record))
m.save(W/(name+'-resources.json'),dict(record=record,charged_CPU_seconds=charge,charged_active_wall_seconds=elapsed,total_CPU=cpu+charge,total_wall=wall+elapsed))
print(json.dumps(dict(name=name,pass_=record['complete'],total_CPU=cpu+charge,total_wall=wall+elapsed)))
raise SystemExit(0 if record['complete'] else 1)
