"""Read-only exact410 admission inputs; does not extract or integrate an orbit."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar410-20261116');P=json.loads((W/'execution-plan.json').read_bytes());B=P['bindings']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
for k in ['PYTHONPATH','PYTHONHOME','PYTHONHASHSEED']:os.environ.pop(k,None)
T=Path('C:/Users/Admin/Desktop/Solar-packaging-040-4095');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,timeout=10).strip()
assert git(R,'rev-parse','HEAD')==P['start_dev']
assert git(T,'rev-parse','HEAD')==B['packaging_commit'] and not git(T,'status','--porcelain')
assert git(S,'rev-parse','HEAD')==B['source_commit'] and git(S,'rev-parse','HEAD^{tree}')==B['source_tree'] and not git(S,'status','--porcelain')
assert sha(B['acceptance_tool']['path'])==B['acceptance_tool']['SHA256'] and sha(B['monitor']['path'])==B['monitor']['SHA256']
archive=Path(B['archive']['archive']);assert sha(archive)==B['archive']['archive_SHA256'] and archive.stat().st_size==B['archive']['archive_size']
contract=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116/asset-contract.json');assert sha(contract)==B['archive']['asset_contract_SHA256'];assets=json.loads(contract.read_bytes())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and len(z.namelist())==6005
 for item in z.infolist():
  parts=Path(item.filename).parts;assert not Path(item.filename).is_absolute() and '..' not in parts and not ((item.external_attr>>16)&0o170000)==0o120000
  name='/'.join(parts[1:]);b=z.read(item);row=assets['files'][name];assert hashlib.sha256(b).hexdigest()==row['sha256'] and len(b)==row['size']
 prefix=assets['root']+'/'
 for name,key in [('verification-current040/manifest-v1.json','current_manifest_SHA256'),('verification-current040/recompute_current040_v1.py','current_verifier_SHA256'),('verification/recompute_jpl.py','historical_verifier_SHA256')]:assert hashlib.sha256(z.read(prefix+name)).hexdigest()==B[key]
 native=[n for n in z.namelist() if '/solar_native/' in n and n.endswith('.pyd')];assert len(native)==1 and hashlib.sha256(z.read(native[0])).hexdigest()==B['native_SHA256']
wheel=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111/wheels/solar_native-0.4.0-cp314-cp314t-win_amd64.whl');assert sha(wheel)==B['wheel_SHA256']
from solar_simulator.recipe import runtime_fingerprint
assert hashlib.sha256((json.dumps(runtime_fingerprint('rust'),indent=2)+'\n').encode()).hexdigest()==B['source_environment_fingerprint']
import shutil
assert not (T/'.tools').exists(),'Unknown existing relocated outputs; preserve and stop'
assert shutil.disk_usage(W).free>4*1024**3
# Available CPU/RAM are checked by the psutil-equipped supervisory harness.
result=dict(stage=410,status='PASS_EXACT_INPUTS_NOT_PORTABLE_ACCEPTANCE',archive_SHA256=sha(archive),members=6005,source_commit=B['source_commit'],source_tree=B['source_tree'],native_SHA256=B['native_SHA256'],wheel_SHA256=B['wheel_SHA256'],source_fingerprint=B['source_environment_fingerprint'],acceptance_tool_SHA256=sha(B['acceptance_tool']['path']),monitor_SHA256=sha(B['monitor']['path']),full_acceptance_executed=False,scientific_propagations=0)
with (W/'preflight.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
print('Exact inputs PASS; full execution still gated on monitor applicability')
