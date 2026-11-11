"""Pre-use409A2 monitor faults; exact385logic with only200mscadence delta."""
from pathlib import Path
import hashlib,importlib.util,json,sys,time
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-20261111');P=json.loads((W/'cloud-continuation-a2.json').read_bytes());module=R/P['monitor_path'];assert hashlib.sha256(module.read_bytes()).hexdigest()==P['monitor_SHA256'];spec=importlib.util.spec_from_file_location('m200',module);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=(R/'.tools/qualification385/offline_monitor.py').read_text();expected=base.replace('sleep(.05)','sleep(.2)').replace('poll_seconds=.05','poll_seconds=.2').replace('50 ms sampling is retained from pilot.monitor.','409A2 uses200ms requested sampling for bounded network readback; all other385logic retained.').replace('50ms cap overshoot possible','200ms cap overshoot possible');assert module.read_text()==expected
started=time.perf_counter();cpustart=time.process_time();out=W/'faults';out.mkdir(exist_ok=False);rows=[]
for name,code,change in [('wall','import time;time.sleep(3)',dict(wall_seconds=.25)),('CPU','while True: pass',dict(cpu_seconds=.15)),('RAM','import time;a=bytearray(10_000_000);time.sleep(3)',dict(private_bytes=1024)),('disk',"from pathlib import Path;import time;Path(r'"+str(out/'large.txt')+"').write_bytes(b'x'*4096);time.sleep(3)",dict(disk_bytes=1024)),('interrupt','import time;time.sleep(3)',{})]:
 limit=dict(cpu_seconds=10,wall_seconds=6,private_bytes=128*1024**2,disk_bytes=1024**2);limit.update(change)
 def hook(sample):
  if name=='interrupt':raise KeyboardInterrupt('Synthetic409fault')
 r=m.monitor([sys.executable,'-X','utf8','-B','-c',code],out/name,out,limit,hook=hook)
 assert r['exit_code'] is not None and not r['complete'] and r['limit_reason'] is not None and (out/name/'supervisor.json').is_file();rows.append(dict(name=name,reason=r['limit_reason'],CPU=r['worker_CPU_seconds']+r['parent_supervision_CPU_seconds'],record=r))
charge=sum(x['CPU'] for x in rows)+time.process_time()-cpustart+.25;wall=time.perf_counter()-started+.25
m.save(W/'faults-resources.json',dict(charged_CPU_seconds=charge,charged_active_wall_seconds=wall,kind='Small synthetic fault costs include child+supervisor; parent time conservatively doublecharges nestedmonitorCPU',results=rows));m.save(W/'faults-result.json',dict(monitor_SHA256=P['monitor_SHA256'],source_delta='Only documented .05->.2 sleep/poll literal and docstrings, all385logic byte-equal',faults=[dict(name=x['name'],reason=x['reason']) for x in rows],status='PASS_SYNTHETIC_MONITOR_FAULTS_NOT_PHYSICS'))
print('FAULTS_PASS',[(x['name'],x['reason']) for x in rows],'CPU',charge,'wall',wall)
