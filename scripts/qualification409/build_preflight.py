"""409B preflight and exact archival export fixture, no native/physics build."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111');P=json.loads((W/'plan.json').read_bytes());S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v');T=Path(P['packaging_root']);H=W/'historical-export';H.mkdir(exist_ok=False);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain']);assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==P['base_runtime_commit']
from solar_simulator.recipe import runtime_fingerprint
raw=(json.dumps(runtime_fingerprint('rust'),indent=2)+'\n').encode();assert hashlib.sha256(raw).hexdigest()==P['source_fingerprint'];assert Path(sys.prefix).resolve()==Path(P['qualified_prefix']).resolve()
import solar_native,solar_simulator
assert sha(getattr(solar_native,'solar_native',solar_native).__file__)==P['native_SHA256'] and sha(P['wheel'])==P['wheel_SHA256']
tracked=subprocess.check_output(['git','-C',str(S),'ls-files'],text=True).splitlines();protected={n:sha(S/n) for n in tracked if n.startswith(('src/','rust/')) or n=='pyproject.toml'};assert all(sha(T/n)==digest for n,digest in protected.items())
# Exactly the existing exporter scripts. Historical src files below H/src are
# source-evidence data only: qualifiedPython.pth keeps liveimports at S/src.
shutil.copytree(T/'scripts',H/'scripts',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
needed={'docs/dense-jpl-validation.json','docs/strict-profile-validation.json','docs/qualification-grid-reference.json','docs/qualification-grid-validation.json','docs/solar-sandbox-strict-checkpoint.json','src/solar_simulator/data/solar-system-moon-20261008.json'}
receipts=[json.loads((T/'docs'/name).read_bytes()) for name in ['dense-jpl-validation.json','strict-profile-validation.json','qualification-grid-reference.json']]
for receipt in receipts:needed.update(receipt.get('source_sha256',{}));needed.update(receipt.get('input_sha256',{}))
for n in needed:
    p=H/n;p.parent.mkdir(parents=True,exist_ok=True)
    source=T/n if (T/n).is_file() else R/n
    shutil.copyfile(source,p)
restored={}
for n,row in P['historic_source_substitutions'].items():
    archive=T/row['archive'];assert sha(archive)==row['archive_SHA256']
    with zipfile.ZipFile(archive) as z:b=z.read(n)
    assert hashlib.sha256(b).hexdigest()==row['SHA256'];(H/n).write_bytes(b);restored[n]=row
cache=R/'.tools/qualification138/production139.npz';strict=receipts[1];assert sha(cache)==strict['cache_sha256'];(H/'.tools/qualification138').mkdir(parents=True,exist_ok=True);shutil.copyfile(cache,H/'.tools/qualification138/production139.npz')
ref=receipts[2];raws=[]
for body in ref['bodies']:
    offset=0
    for request in body['requests']:
        name=f"horizons-{body['id']}-{offset:03d}.json";source=R/'.tools/qualification144/jpl-batches'/name;assert sha(source)==request['response_sha256'];dest=H/'.tools/qualification144/jpl-batches'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);raws.append(name);offset+=len(request['epochs_jd_tdb'])
files={p.relative_to(H).as_posix():sha(p) for p in H.rglob('*') if p.is_file()};binding=dict(kind='historical-saved-replay-export-only',current_runtime_not_qualified_by_old_receipts=True,source_data_restored=restored,physical_integration_forbidden=True,files=files)
(H/'VERIFICATION-SOURCE.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf8',newline='\n')
# Reproduce original strict guard refusal, without creating build/output.
code="import sys;sys.path.insert(0,"+repr(str(T))+");import scripts.export_jpl_bundle as e;e.export("+repr(str(W/'must-not-exist-current-export'))+")"
p=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=T,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(W/'original-export-failure.log').write_bytes(p.stdout+p.stderr);assert p.returncode!=0 and b'Source changed: src/solar_simulator/experiment.py' in p.stderr
# Original exporter/guards execute unchanged over authenticated historical
# source-evidence bytes; no old src is imported or executed as current runtime.
code="import sys,json,pathlib;sys.path.insert(0,"+repr(str(H))+");import solar_simulator,solar_simulator.experiment as ex;assert pathlib.Path(solar_simulator.__file__).is_relative_to(pathlib.Path("+repr(str(S/'src'))+"));\ndef forbidden(*a,**k):raise AssertionError('No integration allowed in archivalexport')\nex.advance=forbidden;import scripts.export_jpl_bundle as e;r=e.export("+repr(str(W/'verification-preflight'))+");assert r['checks_passed'];assert all(not str(getattr(m,'__file__','')).startswith("+repr(str(H/'src'))+") for n,m in sys.modules.items() if n.startswith('solar_simulator'));print(json.dumps(r))"
p=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=H,stdout=subprocess.PIPE,stderr=subprocess.PIPE);(W/'historical-export-preflight.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr.decode('utf8')
(W/'build-preflight.json').write_text(json.dumps(dict(source_commit=P['base_runtime_commit'],native_SHA256=P['native_SHA256'],wheel_SHA256=P['wheel_SHA256'],current_fingerprint=P['source_fingerprint'],runtime_files=protected,historical_root=str(H),historical_manifest_SHA256=sha(H/'VERIFICATION-SOURCE.json'),historical_export_pass=True,original_export_refused=True,old_source_not_imported=True,new_integration_forbidden=True,raw_JPL_count=len(raws),source_inputs_size=sum((H/n).stat().st_size for n in files),free_disk_bytes=shutil.disk_usage(W).free),indent=2)+'\n')
print('B_PREFLIGHT archivalexport/authenticatedoldsource/live040origins PASS; no nativebuild')
