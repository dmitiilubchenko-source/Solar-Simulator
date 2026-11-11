"""407V isolated environment, exact metadata and fixture preparation."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,venv,zipfile,tomllib
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v');OLD=Path('C:/Users/Admin/Desktop/Solar-candidate-033-blockers-407')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
metadata=('pyproject.toml','rust/solar_core/Cargo.toml','rust/solar_native/Cargo.toml','rust/solar_native/pyproject.toml','rust/solar_core/Cargo.lock','rust/solar_native/Cargo.lock')
old={n:(S/n).read_bytes() for n in metadata}
for n,raw in old.items():
    if n.endswith('.lock'):
        for name in ('solar_core','solar_native'):
            raw=raw.replace(('name = "'+name+'"\nversion = "0.3.3"').encode(),('name = "'+name+'"\nversion = "0.4.0"').encode())
    else:
        assert raw.count(b'version = "0.3.3"')==1
        raw=raw.replace(b'version = "0.3.3"',b'version = "0.4.0"')
    assert raw!=old[n],n
    (S/n).write_bytes(raw)
    a=tomllib.loads(old[n].decode());b=tomllib.loads(raw.decode())
    if n.endswith('.lock'):
        for p in a['package']:
            if p['name'] in ('solar_core','solar_native'):p['version']='0.4.0'
    else:a['project' if n.endswith('pyproject.toml') else 'package']['version']='0.4.0'
    assert a==b,'non-version TOML delta '+n
p=S/'src/solar_simulator/inspection.py';raw=p.read_bytes();assert raw.count('Release0.3.3 — NO-GO.'.encode())==1
p.write_bytes(raw.replace('Release0.3.3 — NO-GO.'.encode(),'Solar-Simulator 0.4.0 — кандидат, выпуск не разрешён.'.encode()))
zpath=S/'tests/fixtures/metadata033-828c798.zip'
with zipfile.ZipFile(zpath,'x',zipfile.ZIP_DEFLATED) as z:
    for n,b in old.items():
        assert b==(OLD/n).read_bytes()
        info=zipfile.ZipInfo(n,date_time=(2026,11,10,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,b)
(S/'tests/historical033_fixture407v.py').write_text('''"""Immutable407metadata ONLY; never a live runtime overlay."""
from pathlib import Path
import hashlib
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'tests/fixtures/metadata033-828c798.zip'
SHA='''+repr(sha(zpath))+'''
MEMBERS='''+repr({n:hashlib.sha256(b).hexdigest() for n,b in old.items()})+'''
def restore033(destination):
    destination=Path(destination).resolve()
    if destination==ROOT:raise ValueError('No historical overlay into live source')
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()!=SHA:raise ValueError('Historical033 archive SHA')
    with ZipFile(ARCHIVE) as z:
        if set(z.namelist())!=set(MEMBERS) or len(z.namelist())!=len(MEMBERS):raise ValueError('Historical033 members')
        files={n:z.read(n) for n in MEMBERS}
    if any(hashlib.sha256(b).hexdigest()!=MEMBERS[n] for n,b in files.items()):raise ValueError('Historical033 member SHA')
    for n,b in files.items():
        p=destination/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
''',encoding='utf8',newline='\n')
p=S/'tests/test_historical_sources407.py';raw=p.read_bytes()
a=b"saved.restore_metadata032(ROOT,old);assert_version(old,'0.3.2');assert_version(ROOT,'0.3.3')";b=b"saved.restore_metadata032(ROOT,old);assert_version(old,'0.3.2')\r\n    from historical033_fixture407v import restore033\r\n    restore033(new)"
assert a in raw;raw=raw.replace(a,b)
a=b"dst=new/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)";assert a in raw
raw=raw.replace(a,b"assert (new/name).is_file()  # exact immutable033, independent of current version")
p.write_bytes(raw)
# Copy dependencies into NEW prefix, never modify qualified384/407.
venv.EnvBuilder(with_pip=False).create(W/'env')
source=Path(sys.prefix)/'Lib/site-packages';dest=W/'env/Lib/site-packages';copied={}
for p in source.iterdir():
    if p.name.startswith(('solar_native','solar_simulator','__editable__')) or p.suffix=='.pth' or p.name=='__pycache__':continue
    target=dest/p.name
    if p.is_dir():shutil.copytree(p,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    elif p.is_file():shutil.copyfile(p,target)
# Build tools are exact existing1.15.0 and offline wheels, not new dependencies.
for pattern in ('maturin*','pip*'):
    for p in (R/'.venv/Lib/site-packages').glob(pattern):
        if p.is_dir():shutil.copytree(p,dest/p.name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copyfile(R/'.venv/Scripts/maturin.exe',W/'env/Scripts/maturin.exe')
for pattern in ('setuptools*.whl','wheel*.whl'):
    p=next((R/'.tools/qualification383').glob(pattern))
    with zipfile.ZipFile(p) as z:z.extractall(dest)
(dest/'source040.pth').write_text(str(S/'src')+'\n'+str(OLD/'.tools/ias15165/dependency')+'\n',encoding='utf8')
# Initial source path is temporary during build. It will be replaced by standard editable install.
for p in dest.rglob('*'):
    if p.is_file():copied[p.relative_to(dest).as_posix()]=sha(p)
(W/'dependency-copy.json').write_text(json.dumps(dict(files=copied,source_prefix=sys.prefix,build_tools=str(R/'.venv')),indent=2)+'\n')
(W/'metadata-diff.json').write_text(json.dumps({n:dict(before=hashlib.sha256(b).hexdigest(),after=sha(S/n)) for n,b in old.items()},indent=2)+'\n')
print('prepared',len(copied),'files; fixture',sha(zpath),flush=True)
