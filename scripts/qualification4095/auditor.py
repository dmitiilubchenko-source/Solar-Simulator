"""Read-only independent409.5 audit from artifact bytes and raw refusals, no year."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar4095-20261116');F=W/'SolarSimulator-0.4.0-4095';T=Path('C:/Users/Admin/Desktop/Solar-packaging-040-4095');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=json.loads((W/'new-package.json').read_bytes());old=json.loads((R/'scripts/qualification409/zip-members.json').read_bytes());oldmap={i['path']:i['SHA256'] for i in old['members']}
with zipfile.ZipFile(a['archive']) as z:
    assert z.testzip() is None and sha(a['archive'])==a['archive_SHA256']
    actual={str(Path(*Path(i.filename).parts[1:])).replace('\\','/'):hashlib.sha256(z.read(i)).hexdigest() for i in z.infolist()}
assert [n for n in oldmap if actual[n]!=oldmap[n]]==['Physics Verification.cmd']
assert all(actual[n]==h for n,h in oldmap.items() if n.startswith(('runtime/','verification/')))
assert sha(old['archive'])==old['archive_SHA256']
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'])
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()=='237f73612c3c159acf92b32a15cf0289958fd921'
assert not subprocess.check_output(['git','-C',str(T),'diff','02ca1cf1b0e327481713bfa7d9b0fa328991c0ef','--','src','rust','pyproject.toml'])
changed=subprocess.check_output(['git','-C',str(T),'diff','--name-only','02ca1cf1b0e327481713bfa7d9b0fa328991c0ef','HEAD'],text=True).splitlines()
assert set(changed)=={'scripts/check_portable.py','scripts/prepare_current040_v1.py','scripts/recompute_current040_v1.py'}
refusal=(W/'historical-refusal.log').read_bytes();assert b'Runtime scientific source changed' in refusal
neg=json.loads((W/'verifier-negatives.json').read_bytes())
for row in neg['controls']:
    if row['case']=='raw-failure-preserved-before-propagation':continue
    raw=(W/('negative-'+row['case']+'.log')).read_bytes()
    assert raw and (not row['expected_message'] or row['expected_message'].encode() in raw)
raw=json.loads((W/'failure-raw/result.json').read_bytes());assert raw['status']=='FAILED' and raw['solver_executed'] is False
code="import sys,pathlib,tkinter,solar_simulator,solar_native;from importlib.metadata import version;from solar_simulator.experiment import advance,preset;r=pathlib.Path(sys.prefix).resolve();assert pathlib.Path(solar_simulator.__file__).resolve().is_relative_to(r);assert pathlib.Path(solar_native.__file__).resolve().is_relative_to(r);assert version('solar-native')==version('solar-simulator')=='0.4.0';w=tkinter.Tk();w.withdraw();w.destroy();s=advance(preset('spheres',backend='rust'),2000);assert len(s.events)==2;print('Packaged Tk/native shortsmoke PASS, no annual calculation')"
p=subprocess.run([str(F/'runtime/python.exe'),'-I','-X','utf8','-B','-c',code],cwd=F,capture_output=True,timeout=25);(W/'final-smoke.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode()
report=dict(independent_ZIP_SHA_CRC='PASS',member_count=len(actual),old_runtime_and_historical_bundle_byte_identity='PASS',source237_and_native_unchanged=True,tooling_diff=changed,raw_verifier_refusals_checked=len(neg['controls']),short_packaged_Tk_native_smoke='PASS',full410_executed=False,fresh_year_and_continuous_resource_forecast='UNRESOLVED: no exact040 full-duration measurement in409/409.5; no automatic admission or new410plan',scientific_PASS_not_claimed=True)
(W/'independent-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
