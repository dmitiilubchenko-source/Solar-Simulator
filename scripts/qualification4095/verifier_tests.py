"""Real isolated packaged negative controls on a separate complete fixture."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess,sys
W=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');F=W/'SolarSimulator-0.4.0-4095';Q=W/'verifier fixture';shutil.copytree(F,Q)
manifest=Q/'verification-current040/manifest-v1.json';original=manifest.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();rows=[]
script=Q/'verification-current040/recompute_current040_v1.py'
def probe(label,path=None,transform=None,message=None,external=False,extra=()):
    old=path.read_bytes() if path else None
    try:
        if path:path.write_bytes(transform(old))
        pin=sha(manifest.read_bytes())
        command=[sys.executable if external else str(Q/'runtime/python.exe'),'-I','-B','-X','utf8',str(script),str(Q),'--manifest-sha256',pin,*extra]
        p=subprocess.run(command,cwd=Q,capture_output=True,timeout=25)
        (W/('negative-'+label+'.log')).write_bytes(p.stdout+p.stderr)
        assert p.returncode!=0 and (message is None or message.encode() in p.stderr),(label,p.stderr.decode())
        rows.append(dict(case=label,rejected=True,expected_message=message))
    finally:
        if path:path.write_bytes(old)
def altered(b):return b+b'\n'
for name in ['experiment.py','native_forces.py','nbody_rotation.py','accuracy.py']:
    probe('source-'+name,Q/'runtime/Lib/site-packages/solar_simulator'/name,altered,'Bound file mismatch')
for name in ['initial.json','reference.json']:
    probe('input-'+name,Q/'verification'/name,altered,'Bound file mismatch')
def change(key,value):
    def f(b):
        d=json.loads(b);d[key]=value;return (json.dumps(d)+'\n').encode()
    return f
probe('ABI',manifest,change('SOABI','not-qualified-ABI'),'Wrong Python ABI')
probe('native-version',manifest,change('native_SHA256','0'*64),'Wrong native lineage')
probe('historical-presented-current',manifest,lambda b:(Q/'verification/manifest.json').read_bytes(),'Not a current preflight manifest')
d=json.loads(original);settings=dict(d['settings']);settings['dt']=7200
probe('settings',manifest,change('settings',settings),'Settings/frame mismatch')
probe('epochs',manifest,change('epochs_jd_tdb',d['epochs_jd_tdb'][:-1]),'Units/epochs mismatch')
probe('units',manifest,change('units','KM-S'),'Units/epochs mismatch')
origin=dict(d['origin']);origin['frame']='ICRF'
probe('frame',manifest,change('origin',origin),'Settings/frame mismatch')
probe('external-python',external=True,message='Packaged isolated Python required')
probe('cached-trajectory-option',extra=('--cached-trajectory',str(Q/'verification/trajectories.json')),message='unrecognized arguments')
native=next((Q/'runtime/Lib/site-packages/solar_native').glob('*.pyd'))
probe('changed-native',native,altered,'Bound file mismatch')
old_native=next(Path('C:/Users/Admin/Desktop/Solar-candidate-033-384/.venv/Lib/site-packages/solar_native').glob('*.pyd'))
probe('actual033-native',native,lambda b:old_native.read_bytes(),'Bound file mismatch')
meta=next((Q/'runtime/Lib/site-packages').glob('solar_native-*.dist-info/METADATA'))
probe('actual033-metadata',meta,lambda b:b.replace(b'Version: 0.4.0',b'Version: 0.3.3'),'Bound file mismatch')
# A fail-before-propagation --run must still preserve a real failure report.
p=subprocess.run([str(Q/'runtime/python.exe'),'-I','-B',str(script),str(Q),'--manifest-sha256','0'*64,'--run','--output',str(W/'failure-raw')],capture_output=True,timeout=25)
assert p.returncode!=0
failure=json.loads((W/'failure-raw/result.json').read_bytes());assert failure['status']=='FAILED' and not failure['solver_executed'] and not failure['scientific_PASS']
rows.append(dict(case='raw-failure-preserved-before-propagation',rejected=True))
# Acceptance command construction only; no annual or full portable execution.
tool=Path('C:/Users/Admin/Desktop/Solar-packaging-040-4095/scripts/check_portable.py');spec=importlib.util.spec_from_file_location('acceptance',tool);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
assert str(Q/'verification/recompute_jpl.py') in a.fresh_year_command(Q)
command=a.fresh_year_command(Q,sha(original));assert '--run' in command and not Path(command[-1]).is_relative_to(Q)
try:a.fresh_year_command(Q,'0'*64)
except ValueError:pass
else:raise AssertionError('Wrong acceptance pin admitted')
(W/'verifier-negatives.json').write_text(json.dumps(dict(controls=rows,acceptance_command_tests='PASS legacy/current/wrongpin',scientific_integrations=0,annual_results_not_claimed=True),indent=2)+'\n')
print('VERIFIER_NEGATIVES_PASS',len(rows),'no scientific integrations')
