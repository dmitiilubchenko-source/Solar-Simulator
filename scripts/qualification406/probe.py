"""Actual imports/ABI/metadata/profile in the new -I test interpreter."""
import hashlib
import importlib.metadata as md
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tkinter as tk
import tomllib

R=Path(__file__).resolve().parents[2];W=R/'.tools/acceptance406-20261109'
p=json.loads((R/'scripts/qualification406/plan.json').read_bytes());source=Path(p['candidate_source']);prefix=Path(p['test_environment'])
assert sys.flags.isolated and Path(sys.prefix).resolve()==prefix.resolve()
sys.path.insert(0,str(source))
import solar_simulator,numpy,scipy,matplotlib,solar_native,rebound
from solar_simulator.recipe import runtime_fingerprint
from scripts.native_audit import require_native

assert Path(solar_simulator.__file__).resolve().is_relative_to(source/'src')
assert all(Path(x.__file__).resolve().is_relative_to(prefix) for x in (numpy,scipy,matplotlib,solar_native))
assert Path(rebound.__file__).resolve().is_relative_to(source/'.tools/ias15165/dependency')
for name,value in [('numpy','2.5.1'),('scipy','1.18.1'),('matplotlib','3.11.0'),('solar-simulator','0.3.3'),('solar-native','0.3.3')]:assert md.version(name)==value,(name,md.version(name))
assert sys.version_info[:3]==(3,14,2) and sysconfig.get_config_var('Py_GIL_DISABLED')
compiled=getattr(solar_native,'solar_native',solar_native)
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert sha(compiled.__file__)==p['native_SHA256']
assert rebound.__version__=='5.2.2'
native=require_native()
versions={}
for name,table in [('pyproject.toml','project'),('rust/solar_core/Cargo.toml','package'),('rust/solar_native/Cargo.toml','package'),('rust/solar_native/pyproject.toml','project')]:
    value=tomllib.loads((source/name).read_text(encoding='utf8'))[table]['version'];assert value=='0.3.3';versions[name]=value
window=tk.Tk();window.withdraw()
try:
    tk_versions=dict(Tcl=str(window.tk.call('info','patchlevel')),Tk=str(window.tk.call('set','tk_patchLevel')))
    assert set(tk_versions.values())=={'8.6.15'}
finally:window.destroy()
fp=runtime_fingerprint('rust');raw=(json.dumps(fp,indent=2)+'\n').encode()
assert hashlib.sha256(raw).hexdigest()==p['source_fingerprint'],'Actual profile mismatch: no heavy execution allowed'
with (W/'actual-environment.json').open('xb') as f:f.write(raw)
rustc=subprocess.check_output([str(Path.home()/'.cargo/bin/rustc.exe'),'--version','--verbose'],text=True)
cargo=subprocess.check_output([str(Path.home()/'.cargo/bin/cargo.exe'),'--version'],text=True)
binding=dict(candidate=p['candidate_commit'],tree=p['candidate_tree'],profile_SHA256=sha(W/'actual-environment.json'),
    interpreter=sys.executable,prefix=sys.prefix,isolated=sys.flags.isolated,source_import=solar_simulator.__file__,
    dependency_imports={name:module.__file__ for name,module in [('numpy',numpy),('scipy',scipy),('matplotlib',matplotlib),('solar_native',solar_native)]},
    native_SHA256=sha(compiled.__file__),native_probe=native,rebound_import=rebound.__file__,rebound_version=rebound.__version__,
    metadata=versions,Tcl_Tk=tk_versions,python=sys.version,SOABI=sysconfig.get_config_var('SOABI'),rustc=rustc,cargo=cargo,
    scope='Exact405 source, byte-identical dependency/native copies, explicit plainpth source activation. Not wheel/portable or hermetic image.')
with (W/'environment-binding.json').open('x',encoding='utf8') as f:json.dump(binding,f,ensure_ascii=False,indent=2);f.write('\n')
print('PASS actual -I candidate imports/prefix/metadata/compilednative/ABI/Tk/profile',flush=True)
