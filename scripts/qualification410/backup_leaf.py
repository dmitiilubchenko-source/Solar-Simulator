"""Backup-only bounded direct interpreter with no site or subprocess use in worker.

This does not qualify the pinned monitor for full410. Explicit post-return PID
checks refuse any unexpected descendant. The Solar fixture admission remains FAIL.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,sys,time
import psutil
R=Path(__file__).resolve().parents[2];C=Path('C:/Users/Admin/Documents/Codex/Solar410-backup-20261116')
p=json.loads((C/'plan.json').read_bytes());ref=json.load(sys.stdin);label=ref['label'];rows=[json.loads(f.read_bytes()) for f in C.glob('*-resources.json') if f.name!='connector-resources.json'];used=sum(x['charged_CPU_seconds'] for x in rows);wall=sum(x['charged_active_wall_seconds'] for x in rows)
connector=C/'connector-resources.json'
if connector.exists():wall+=json.loads(connector.read_bytes())['wall_seconds']
assert used+3+p['CPU_final_reserve']<60 and wall+60+p['wall_final_reserve']<300
source=R/'scripts/qualification409/monitor200.py';assert hashlib.sha256(source.read_bytes()).hexdigest()=='6ec4c2ac55ff1a56e0a4b229760ae594fa61c00ca864f5b54ac62bf3aca6642b'
spec=importlib.util.spec_from_file_location('leaf_monitor',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.environ['SOLAR409_REF']=json.dumps(ref);command=[sys._base_executable,'-I','-S','-X','utf8','-B',str(C/'read_object.py')]
m.save(C/('launch-'+label+'.json'),dict(command=command,scope='Direct single-process stdlib downloader, no venv launcher/site/subprocesses; NOT full410',expected_SHA256=ref['expected']['sha256'],cloud_id=ref['expected']['id']))
start=time.perf_counter();limits=dict(p['hard']);limits['wall_seconds']=min(300,wall+60)
record=m.monitor(command,C/('guard-'+label),C,limits,used_cpu=used+time.process_time(),stage_start=start-wall)
unexpected=[]
for item in record['processes']:
 try:
  q=psutil.Process(item['pid'])
  if q.create_time()==item['creation_time'] and q.is_running():unexpected.append(item);q.kill();q.wait(timeout=5)
 except psutil.NoSuchProcess:pass
ok=record['complete'] and not unexpected and len(record['processes'])<=1
out=dict(record=record,post_return_live_processes=unexpected,direct_leaf_scope_only=True,charged_CPU_seconds=record['worker_CPU_seconds']+time.process_time()+.25,charged_active_wall_seconds=time.perf_counter()-start+.25,verified_leaf_completion=ok)
m.save(C/(label+'-resources.json'),out);print(json.dumps(dict(label=label,leaf_complete=ok)))
raise SystemExit(0 if ok else 1)
