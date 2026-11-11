"""409 packaging-only negative controls, no compile/integration/408repeat."""
import ast,hashlib,importlib.util,json,shutil,sys,zipfile
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111');P=json.loads((W/'plan.json').read_bytes());T=Path(P['packaging_root']);spec=importlib.util.spec_from_file_location('builder409',T/'scripts/build_portable.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);out=W/'negative-controls';out.mkdir(exist_ok=False);wheel=Path(P['wheel']);gold=P['wheel_SHA256'];native=P['native_SHA256'];rows=[]
def bad(name,call):
 try:call()
 except (ValueError,FileNotFoundError,AssertionError) as e:rows.append(dict(name=name,rejected=True,type=type(e).__name__,message=str(e)));return
 raise AssertionError('Accepted negative '+name)
valid=m.checked_native_wheel(wheel,'0.4.0',gold,native);assert valid==wheel
bad('missingwheel',lambda:m.checked_native_wheel(out/'absent.whl','0.4.0',gold,native))
for name,newname in [('wrongversion','solar_native-0.3.3-cp314-cp314t-win_amd64.whl'),('wrongABI','solar_native-0.4.0-cp313-cp313-win_amd64.whl')]:
 p=out/newname;shutil.copyfile(wheel,p);bad(name,lambda:m.checked_native_wheel(p,'0.4.0',gold,native))
bad('wrongwheelSHA',lambda:m.checked_native_wheel(wheel,'0.4.0','0'*64,native))
bad('wrongcompiledSHA',lambda:m.checked_native_wheel(wheel,'0.4.0',gold,'0'*64))
folder=out/'ambiguous';folder.mkdir();shutil.copyfile(wheel,folder/wheel.name);shutil.copyfile(wheel,folder/'solar_native-0.4.0-1-cp314-cp314t-win_amd64.whl');bad('ambiguouswheels',lambda:m.checked_native_wheel(folder,'0.4.0',gold,native))
with patch.object(m.subprocess,'run',side_effect=AssertionError('Unexpected native compilation')):
 assert m.native_artifact('0.4.0',wheel,gold,native)==wheel
rows.append(dict(name='reuse_path_forbids_compiler_subprocess',passed=True))
legacy=out/'legacy';(legacy/'.tools/wheels').mkdir(parents=True);shutil.copyfile(wheel,legacy/'.tools/wheels'/wheel.name);calls=[]
with patch.object(m,'ROOT',legacy),patch.object(m.subprocess,'run',side_effect=lambda command,**kw:calls.append(command)):
 assert m.native_artifact('0.4.0').name==wheel.name
assert len(calls)==1 and calls[0][-1]=='--wheel' and calls[0][-2].endswith('build_native.py');rows.append(dict(name='legacy_default_retains_native_build_command',passed=True,command=calls[0]))
H=W/'historical-export';binding=json.loads((W/'build-preflight.json').read_bytes())['historical_manifest_SHA256'];assert m.checked_verification_root(H,binding)==H
bad('wrong_archival_manifest_SHA',lambda:m.checked_verification_root(H,'0'*64))
p=H/'src/solar_simulator/experiment.py';saved=p.read_bytes()
try:
 p.write_bytes(saved+b'\n');bad('archival_source_corruption',lambda:m.checked_verification_root(H,binding))
finally:p.write_bytes(saved)
assert hashlib.sha256(p.read_bytes()).hexdigest()==P['historic_source_substitutions']['src/solar_simulator/experiment.py']['SHA256']
# Actual builder must delegate compilation only to native_artifact and retain stock smokes/export.
tree=ast.parse((T/'scripts/build_portable.py').read_bytes());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build');assert not any(isinstance(n,ast.Constant) and isinstance(n.value,str) and 'build_native.py' in n.value for n in ast.walk(fn));assert any(isinstance(n,ast.Name) and n.id=='run_build_smokes' for n in ast.walk(fn))
(W/'negative-controls.json').write_text(json.dumps(dict(status='PASS_TOOLING_NEGATIVE_CONTROLS',controls=rows,remaining_control='Actual outsideportableimport negative after real build',native_compilation_executed=False),indent=2)+'\n')
print('NEGATIVES_PASS',len(rows),'no actualnativecompile/integration')
