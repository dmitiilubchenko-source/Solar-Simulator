from pathlib import Path
import subprocess,sys,json,importlib.metadata as md,sysconfig,os
W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v');cargo=Path.home()/'.cargo/bin/cargo.exe'
rec=dict(python=sys.version,prefix=sys.prefix,ABI=sysconfig.get_config_var('SOABI'),tools={n:md.version(n) for n in ['maturin','setuptools','wheel','pip']},rust=subprocess.check_output([str(cargo.with_name('rustc.exe')),'-vV'],text=True))
for crate in ('solar_core','solar_native'):
    out=subprocess.check_output([str(cargo),'metadata','--manifest-path',str(S/f'rust/{crate}/Cargo.toml'),'--format-version','1','--locked','--offline'],text=True)
    p=json.loads(out);rec[crate]=dict(packages=[dict(name=x['name'],version=x['version'],source=x['source']) for x in p['packages']],target_directory=p['target_directory'])
(W/'toolchain-preflight.json').write_text(json.dumps(rec,indent=2)+'\n')
print('PREFLIGHT offline locked OK',rec['ABI'],rec['tools'])
