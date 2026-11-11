"""New409A cumulative supervisor, exact385monitor, partial/timeout receipt closure."""
import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
import psutil
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-20261111');P=json.loads((W/'cloud-plan.json').read_bytes());label=sys.argv[1]
continuation=W/'cloud-continuation-a2.json'
if continuation.exists():P=json.loads(continuation.read_bytes())
forecast_cpu=float(sys.argv[2]);forecast_wall=float(sys.argv[3]);ref=json.load(sys.stdin)
for p in W.glob('launch-*.json'):
 if not (W/(p.stem.removeprefix('launch-')+'-resources.json')).exists():raise RuntimeError('Previous launch resource receipt missing; reconcile before resume')
rows=[json.loads(p.read_bytes()) for p in W.glob('*-resources.json')];usedcpu=sum(x['charged_CPU_seconds'] for x in rows);usedwall=sum(x['charged_active_wall_seconds'] for x in rows)
assert usedcpu+forecast_cpu+P['CPU_final_reserve']<P['early']['cpu_seconds'] and usedwall+forecast_wall+P['wall_final_reserve']<P['early']['wall_seconds'],'Insufficient unchanged409Aresourcebudget'
limits=dict(P['early']);phasewall=P['per_file_wall_limits']['control' if ref['index'] in (3,4) else 'part'];limits['wall_seconds']=min(limits['wall_seconds'],usedwall+phasewall)
monitor=R/P.get('monitor_path','.tools/qualification385/offline_monitor.py');assert hashlib.sha256(monitor.read_bytes()).hexdigest()==P['monitor_SHA256'];spec=importlib.util.spec_from_file_location('m409',monitor);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ref['label']=label;os.environ['SOLAR409_REF']=json.dumps(ref)
command=[sys.executable,'-X','utf8','-B',str(R/'scripts/qualification409/read_object.py')]
m.save(W/('launch-'+label+'.json'),dict(label=label,index=ref['index'],cloud_id=ref['expected']['id'],expected_size=ref['expected']['size'],expected_SHA256=ref['expected']['sha256'],command=command,plan_SHA256=hashlib.sha256((continuation if continuation.exists() else W/'cloud-plan.json').read_bytes()).hexdigest(),worker_SHA256=hashlib.sha256((R/'scripts/qualification409/read_object.py').read_bytes()).hexdigest(),supervisor_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),monitor_SHA256=P['monitor_SHA256'],phase_wall_cap=phasewall,prior_CPU=usedcpu,prior_active_wall=usedwall,forecast=[forecast_cpu,forecast_wall]))
start=time.perf_counter();parent=psutil.Process()
def hook(sample):
 if parent.memory_info().private+sample['private_tree']>P['early']['private_bytes']:raise MemoryError('Combined sampledprivate limit')
record=m.monitor(command,W/('guard-'+label),W,limits,used_cpu=usedcpu+time.process_time(),stage_start=start-usedwall,hook=hook)
charge=record['worker_CPU_seconds']+time.process_time()+.25;elapsed=time.perf_counter()-start+.25
if not (W/'downloads'/(label+'-completion.json')).exists():
 m.save(W/'downloads'/(label+'-completion.json'),dict(label=label,id=ref['expected']['id'],status='SUPERVISOR_STOP_PARTIAL_NOT_VERIFIED',exit_code=record['exit_code'],limit_reason=record['limit_reason'],actual_partial_bytes=(W/'downloads'/(label+'.partial')).stat().st_size if (W/'downloads'/(label+'.partial')).exists() else 0))
m.save(W/(label+'-resources.json'),dict(record=record,charged_CPU_seconds=charge,charged_active_wall_seconds=elapsed,total_CPU=usedcpu+charge,total_active_wall=usedwall+elapsed,tail_allowance=.25,completed_pass=record['complete']))
print(json.dumps(dict(label=label,exit_code=record['exit_code'],reason=record['limit_reason'],charged_CPU=charge,total_CPU=usedcpu+charge,total_active_wall=usedwall+elapsed)),flush=True);raise SystemExit(0 if record['complete'] else 1)
