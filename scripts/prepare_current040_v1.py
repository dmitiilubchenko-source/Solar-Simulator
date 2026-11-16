"""Derive a NEW verification-only package from authenticated409; no native build."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,sysconfig,zipfile
from importlib import metadata

OLD_SHA='74247a863bd1c445ecfa736e1a0df60db43ad541cb34d7df5de909410781f3bd'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prepare(old,output):
    old=Path(old);output=Path(output);tool=Path(__file__).resolve().parents[1]
    assert sha(old)==OLD_SHA and old.stat().st_size==112698889
    assert not output.exists()
    commit=subprocess.check_output(['git','-C',str(tool),'rev-parse','HEAD'],text=True).strip()
    assert not subprocess.check_output(['git','-C',str(tool),'status','--porcelain'])
    assert not subprocess.check_output(['git','-C',str(tool),'diff','02ca1cf1b0e327481713bfa7d9b0fa328991c0ef','--','src','rust','pyproject.toml'])
    output.mkdir(parents=True)
    with zipfile.ZipFile(old) as z:
        assert z.testzip() is None
        root=Path(z.namelist()[0]).parts[0]
        for i in z.infolist():
            parts=Path(i.filename).parts
            assert parts[0]==root and '..' not in parts and not Path(i.filename).is_absolute()
            assert (i.external_attr>>16)&0o170000!=0o120000
            rel=Path(*parts[1:]);p=output/rel
            p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(i))
    runtime=output/'runtime';package=runtime/'Lib/site-packages/solar_simulator'
    current=output/'verification-current040';current.mkdir()
    shutil.copyfile(tool/'scripts/recompute_current040_v1.py',current/'recompute_current040_v1.py')
    files={p.relative_to(runtime).as_posix():sha(p) for p in runtime.rglob('*') if p.is_file()}
    initial=json.loads((output/'verification/initial.json').read_bytes())
    ref=json.loads((output/'verification/reference.json').read_bytes())
    strict=json.loads((output/'verification/strict-report.json').read_bytes())
    from scripts.build_portable import dependency_closure
    dependencies={name:dist.version for name,dist in dependency_closure().items()}
    dependencies.update({'solar-native':'0.4.0','solar-simulator':'0.4.0'})
    m=dict(kind='current040-fresh-year-v1',scientific_execution_completed=False,
      source_commit='237f73612c3c159acf92b32a15cf0289958fd921',source_tree='5cf43fd9c5bb7d0d80a427d8a6d11ec8b81cb8e9',
      qualified_source_environment_fingerprint='f84294862fac710dedd03bdf854b537e541aa5c955f90938832e9b72840d2083',
      native_SHA256='a2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b',
      wheel_SHA256='5c2db314218484f5cb8b436de4479d5ecb069b56a5bd621eaa6e5cd5c70a5adb',
      original409_ZIP_SHA256=OLD_SHA,packaging_commit=commit,SOABI=sysconfig.get_config_var('SOABI'),
      free_threaded=bool(sysconfig.get_config_var('Py_GIL_DISABLED')),interpreter_SHA256=sha(runtime/'python.exe'),
      distributions=dependencies,runtime_files=files,
      historical_files={p.relative_to(output/'verification').as_posix():sha(p) for p in (output/'verification').rglob('*') if p.is_file()},
      verifier_SHA256=sha(current/'recompute_current040_v1.py'),initial_SHA256=sha(output/'verification/initial.json'),
      reference_SHA256=sha(output/'verification/reference.json'),settings=initial['settings'],origin=initial['origin'],units='SI',
      epochs_jd_tdb=ref['epochs_jd_tdb'],packet_steps=20,
      criteria=dict(body_position_m=10000,moon_relative_position_m=1000,stored_position_m=.1,stored_velocity_m_s=1e-5),
      historical_source_differences={n:dict(historical=h,current=sha(package/n.removeprefix('src/solar_simulator/'))) for n,h in strict['source_sha256'].items() if n.startswith('src/solar_simulator/') and sha(package/n.removeprefix('src/solar_simulator/'))!=h})
    (current/'manifest-v1.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8',newline='\n')
    pin=sha(current/'manifest-v1.json')
    (output/'Physics Verification.cmd').write_text('@echo off\r\ncd /d "%~dp0"\r\nset OMP_NUM_THREADS=1\r\nset OPENBLAS_NUM_THREADS=1\r\nset MKL_NUM_THREADS=1\r\n"runtime\\python.exe" -I -B "verification-current040\\recompute_current040_v1.py" . --manifest-sha256 '+pin+' %*\r\npause\r\n',encoding='ascii')
    (current/'README.md').write_text('Current040 v1: default preflight only. No scientific PASS.\nExplicit --run --output NEW_DIRECTORY_OUTSIDE_PACKAGE performs a real fresh year; separately authorize410 first.\nHistorical verification/ is immutable and independent. Original criteria apply, including stored reproduction FAIL.\n',encoding='utf8')
    (output/'CURRENT-040-VERIFICATION.json').write_text(json.dumps(dict(manifest_SHA256=pin,kind=m['kind'],packaging_commit=commit,physics_unchanged=True,full410_executed=False),indent=2)+'\n',encoding='utf8')
    return dict(folder=str(output),manifest_SHA256=pin,packaging_commit=commit)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('old');p.add_argument('output');a=p.parse_args()
    print(json.dumps(prepare(a.old,a.output)))
