from pathlib import Path
import json,subprocess,sys,hashlib,zipfile
W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
wheel=next((W/'wheels').glob('solar_native-0.4.0-*.whl'))
with zipfile.ZipFile(wheel) as z:
    assert 'Version: 0.4.0' in z.read('solar_native-0.4.0.dist-info/METADATA').decode()
    assert 'Tag: cp314-cp314t-win_amd64' in z.read('solar_native-0.4.0.dist-info/WHEEL').decode()
subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps',str(wheel)],check=True)
subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps','--no-build-isolation','-e',str(S)],check=True)
(W/'env/Lib/site-packages/source040.pth').unlink()
from solar_simulator.recipe import runtime_fingerprint
import solar_simulator,solar_native,importlib.metadata as md
native=Path(getattr(solar_native,'solar_native',solar_native).__file__)
r=dict(python=sys.version,prefix=sys.prefix,source=str(Path(solar_simulator.__file__).resolve()),native=str(native),native_SHA256=hashlib.sha256(native.read_bytes()).hexdigest(),wheel=wheel.name,wheel_SHA256=hashlib.sha256(wheel.read_bytes()).hexdigest(),versions={n:md.version(n) for n in ['solar-simulator','solar-native','numpy','scipy','matplotlib']},fingerprint=runtime_fingerprint('rust'))
(W/'actual-environment.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='fingerprint'}))
