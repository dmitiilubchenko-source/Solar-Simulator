"""Exact409 inputs and scope audit before any409.5 implementation."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116')
p=json.loads((W/'plan.json').read_bytes());S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='bf03956fcfd15ff457f3cb9e90af9b8e72d11e93'
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'])
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==p['base_runtime_commit']
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD^{tree}'],text=True).strip()==p['base_runtime_tree']
assert sha(p['wheel'])==p['wheel_SHA256']
from solar_simulator.recipe import runtime_fingerprint
import solar_native,solar_simulator
fp=runtime_fingerprint('rust');assert hashlib.sha256((json.dumps(fp,indent=2)+'\n').encode()).hexdigest()==p['source_fingerprint']
assert sha(getattr(solar_native,'solar_native',solar_native).__file__)==p['native_SHA256']
assert Path(solar_simulator.__file__).resolve().is_relative_to(S/'src')
old=json.loads((R/'scripts/qualification409/zip-members.json').read_bytes());archive=Path(old['archive'])
assert archive.stat().st_size==old['archive_size'] and sha(archive)==old['archive_SHA256']
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None and len(z.namelist())==6001
 for row in old['members']:
  name=old['root']+'/'+row['path'];b=z.read(name)
  assert hashlib.sha256(b).hexdigest()==row.get('SHA256',row.get('sha256'))
protected=json.loads((Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111')/'build-preflight.json').read_bytes())['runtime_files']
assert all(sha(S/n)==v for n,v in protected.items())
result=dict(status='PASS_EXACT409_INPUTS',runtime_commit=p['base_runtime_commit'],runtime_tree=p['base_runtime_tree'],native_SHA256=p['native_SHA256'],wheel_SHA256=p['wheel_SHA256'],source_fingerprint=p['source_fingerprint'],old_ZIP_SHA256=old['archive_SHA256'],old_ZIP_size=old['archive_size'],old_members=6001,numerical_source_files=len(protected),impact=['New opt-in versioned verifier outside immutable historical bundle','Exact manifest for every package/dependency/interpreter file and all historical inputs','No source/native/IC/settings/model/threshold changes','Narrow backup approval only after full authenticated asset closure and security controls','No full410 or fresh-year/continuous propagation; resource forecast remains separate'],historical_paths_unchanged=True)
(W/'preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
