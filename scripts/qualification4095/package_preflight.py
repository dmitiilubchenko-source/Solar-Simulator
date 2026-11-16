"""Refresh only unsealed new verification assets; preflight, never propagation."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');T=Path('C:/Users/Admin/Desktop/Solar-packaging-040-4095');F=W/'SolarSimulator-0.4.0-4095'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
current=F/'verification-current040';manifest=current/'manifest-v1.json'
archive=W/'initial-verification-assets';archive.mkdir(exist_ok=False)
for f in current.iterdir():shutil.copyfile(f,archive/f.name)
shutil.copyfile(F/'Physics Verification.cmd',archive/'Physics Verification.cmd')
shutil.copyfile(T/'scripts/recompute_current040_v1.py',current/'recompute_current040_v1.py')
m=json.loads(manifest.read_bytes());m['verifier_SHA256']=sha(current/'recompute_current040_v1.py');m['packaging_commit']=subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip();manifest.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8',newline='\n');pin=sha(manifest)
cmd=(F/'Physics Verification.cmd').read_text();cmd=cmd.replace(json.loads((F/'CURRENT-040-VERIFICATION.json').read_bytes())['manifest_SHA256'],pin);(F/'Physics Verification.cmd').write_text(cmd,encoding='ascii',newline='')
(F/'CURRENT-040-VERIFICATION.json').write_text(json.dumps(dict(manifest_SHA256=pin,kind=m['kind'],packaging_commit=m['packaging_commit'],full410_executed=False,physics_unchanged=True),indent=2)+'\n',encoding='utf8')
command=[str(F/'runtime/python.exe'),'-I','-X','utf8','-B',str(current/'recompute_current040_v1.py'),str(F),'--manifest-sha256',pin]
p=subprocess.run(command,cwd=F,capture_output=True,timeout=45);(W/'current-preflight.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode('utf8')
historical=[str(F/'runtime/python.exe'),'-I','-X','utf8','-B','-c',"import importlib.util,pathlib;root=pathlib.Path.cwd();s=importlib.util.spec_from_file_location('historical',root/'verification/recompute_jpl.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.recompute(root/'verification')"]
p=subprocess.run(historical,cwd=F,capture_output=True,timeout=45);(W/'historical-refusal.log').write_bytes(p.stdout+p.stderr);assert p.returncode!=0 and b'Runtime scientific source changed' in p.stderr
(W/'current-preflight.json').write_text(json.dumps(dict(status='PREFLIGHT_PASS_NOT_SCIENTIFIC',folder=str(F),manifest_SHA256=pin,packaging_commit=m['packaging_commit'],historical_guard_refused=True,scientific_integrations=0),indent=2)+'\n')
print('Current packaged preflight PASS; historical source guard still refuses; no integrations')
