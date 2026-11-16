"""Independent read-only audit of410 admission, not a substitute for full acceptance."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
import psutil
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar410-20261116');P=json.loads((W/'execution-plan.json').read_bytes());B=P['bindings']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
archive=Path(B['archive']['archive']);assert sha(archive)==B['archive']['archive_SHA256']
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and len(z.namelist())==6005
 native=[n for n in z.namelist() if '/solar_native/' in n and n.endswith('.pyd')]
 assert len(native)==1 and hashlib.sha256(z.read(native[0])).hexdigest()==B['native_SHA256']
assert sha(B['acceptance_tool']['path'])==B['acceptance_tool']['SHA256']
assert sha(B['monitor']['path'])==B['monitor']['SHA256']
primary=json.loads((W/'monitor-contract.json').read_bytes());raw=json.loads((W/'monitor-root-exit/supervisor.json').read_bytes())
assert raw['exit_code']==0 and raw['complete'] is True and primary['descendant_alive_after_monitor_return'] is True
owner=primary['descendant'];seen=[x for x in raw['processes'] if x['pid']==owner['pid'] and x['creation_time']==owner['creation_time']];assert len(seen)==1
assert raw['wall_seconds']<5 and 'time.perf_counter()+5' in (W/'finite_child.py').read_text()
source=Path(B['monitor']['path']).read_text();assert 'while child.poll() is None:' in source and 'if child.poll() is None:' in source
for p in raw['processes']:
 try:
  actual=psutil.Process(p['pid']);assert actual.create_time()!=p['creation_time'] or not actual.is_running(),'Known fixture still active'
 except psutil.NoSuchProcess:pass
assert not Path(P['relocated_parent']).exists(),'Unexpected relocated execution output'
T=Path('C:/Users/Admin/Desktop/Solar-packaging-040-4095');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
for root,expected in [(T,B['packaging_commit']),(S,B['source_commit'])]:
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==expected
 assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'])
result=dict(status='CONFIRMED_MONITOR_ADMISSION_FAIL',exact_ZIP_CRC_native_SHA='PASS',monitor_hash_unchanged=True,acceptance_tool_hash_unchanged=True,root_exit_code=raw['exit_code'],root_complete_flag=raw['complete'],known_descendant_live_after_return=True,known_PID_creation_time_correlated=True,fixture_processes_now_gone=True,source_logic='Guard polls only root; finally kills tree only if root is still alive. A root that has already exited skips descendant termination.',executed_harness_SHA256=sha(W/'monitor_contract_executed.py'),test_cleanup_limitation=json.loads((W/'post-cleanup-audit.json').read_bytes()),production_runtime_defect_proven=False,full410_executed=False,year_or_continuous_propagations=0,remaining_mandatory_checks='All relocated runtime/GUI/recovery/legacy/replay/fresh-year/continuous stages NOT_RUN',decision='STOP; separate monitor/tooling impact review and qualification required before full410')
with (W/'independent-audit.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
print('Independent raw/lifecycle/code/ZIP audit confirms monitor FAIL; no production propagation')
