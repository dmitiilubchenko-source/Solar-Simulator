"""Bounded root-exit/descendant-lifetime contract test for exact frozen monitor.

Fixture processes have a five-second self-limit and external cleanup. No Solar
orbits, GUI or production code changes. Actual probe outcome is not predetermined.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,time
import psutil
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar410-20261116');P=json.loads((W/'execution-plan.json').read_bytes())
monitor=Path(P['bindings']['monitor']['path']);assert hashlib.sha256(monitor.read_bytes()).hexdigest()==P['bindings']['monitor']['SHA256']
spec=importlib.util.spec_from_file_location('sealed410monitor',monitor);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert len(psutil.Process().cpu_affinity())>=2 and psutil.virtual_memory().available>3*1024**3
start=time.perf_counter();pidfile=W/'fixture-child.json'
child=W/'finite_child.py';child.write_text('import time\nend=time.perf_counter()+5\ndata=bytearray(16*1024**2)\nwhile time.perf_counter()<end: sum(range(10000))\n',encoding='utf8')
root=W/'finite_parent.py';root.write_text("import subprocess,sys,time,json,os,psutil\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,'-B',"+repr(str(child))+"])\nPath("+repr(str(pidfile))+").write_text(json.dumps(dict(pid=p.pid,creation_time=psutil.Process(p.pid).create_time(),parent_pid=os.getpid())))\ntime.sleep(.8)\n",encoding='utf8')
limits=dict(cpu_seconds=15,wall_seconds=12,private_bytes=256*1024**2,disk_bytes=8*1024**2)
record=m.monitor([sys.executable,'-X','utf8','-B',str(root)],W/'monitor-root-exit',W,limits)
remaining=None;h=None;cleanup={};alive=False
try:
 data=json.loads(pidfile.read_bytes());p=psutil.Process(data['pid'])
 assert p.create_time()==data['creation_time'],'PID reused; do not touch unrelated process'
 alive=p.is_running() and p.status()!=psutil.STATUS_ZOMBIE
 if alive:
  h=m.process_handle(p.pid);remaining=dict(pid=p.pid,creation_time=p.create_time(),parent_after_monitor=p.ppid(),CPU_at_probe=sum(p.cpu_times()[:2]))
  # Cleanup belongs to the test harness, NOT to the monitor being qualified.
  p.kill();p.wait(timeout=5);cleanup=dict(external_harness_killed=True,final_CPU=m.windows_cpu(h),alive_after_cleanup=p.is_running())
except psutil.NoSuchProcess:cleanup=dict(already_exited=True)
finally:
 if h:m.close_handle(h)
observed_by_monitor=[x for x in record['processes'] if pidfile.exists() and x['pid']==json.loads(pidfile.read_bytes())['pid']]
contract_pass=not alive
result=dict(kind='exact-monitor-root-exit-cleanup-contract',status='PASS' if contract_pass else 'FAIL',monitor_SHA256=hashlib.sha256(monitor.read_bytes()).hexdigest(),root_exit_code=record['exit_code'],monitor_complete=record['complete'],descendant_alive_after_monitor_return=alive,descendant=remaining,observed_by_monitor=observed_by_monitor,cleanup=cleanup,fixture_self_limit_seconds=5,full410_admission=contract_pass,production_orbits_executed=0,meaning='A known owned live descendant must not continue after the guard reports completion; post-return CPU must be accounted or explicitly terminated.')
cpu_extra=max(0,cleanup.get('final_CPU',0)-sum(x['CPU_seconds'] for x in observed_by_monitor))
resource=dict(charged_CPU_seconds=record['worker_CPU_seconds']+time.process_time()+cpu_extra+.25,charged_active_wall_seconds=time.perf_counter()-start+.25,monitor_record=record,descendant_CPU_after_monitor_extra=cpu_extra,tail_allowance=.25)
m.save(W/'monitor-contract.json',result);m.save(W/'monitor-contract-resources.json',resource)
print(json.dumps(result))
raise SystemExit(0 if contract_pass else 1)
