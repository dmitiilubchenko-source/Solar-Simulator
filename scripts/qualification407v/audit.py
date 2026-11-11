"""Independent read-only407V audit of Git objects, artifacts and saved values.
No acquisition or scientific integration. Static document export writes only W.
"""
from pathlib import Path
import ast,hashlib,importlib.metadata as md,json,shutil,subprocess,sys,tomllib,xml.etree.ElementTree as ET,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111');S=Path('C:/Users/Admin/Desktop/Solar-candidate-040-version-407v');OLD=Path('C:/Users/Admin/Desktop/Solar-candidate-033-blockers-407');BASE='828c79805f7db4576b474206923285ce0b4541c4';sys.path.insert(0,str(S));sys.path.insert(0,str(S/'tests'))
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(S),*a])
assert not git('status','--porcelain')
head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip();assert git('merge-base',BASE,head).decode().strip()==BASE
allowed={'docs/project-inventory.json','docs/project-map.md','docs/releases/v0.4.0.md','pyproject.toml','rust/solar_core/Cargo.lock','rust/solar_core/Cargo.toml','rust/solar_native/Cargo.lock','rust/solar_native/Cargo.toml','rust/solar_native/pyproject.toml','scripts/build_native.py','src/solar_simulator/inspection.py','tests/test_historical_sources407.py','tests/test_qualification383.py','tests/fixtures/metadata033-828c798.zip','tests/historical033_fixture407v.py','tests/test_version407v.py'}
changed=git('diff','--name-only',BASE,head).decode().splitlines();assert set(changed)==allowed
numerical={};raw_changes=[]
for n in git('ls-tree','-r','--name-only',BASE,'--','src','rust').decode().splitlines():
    before=git('show',BASE+':'+n);now=git('show',head+':'+n)
    if n.endswith(('Cargo.toml','Cargo.lock','pyproject.toml')):continue
    if n=='src/solar_simulator/inspection.py':
        expected=before.replace('Release0.3.3 — NO-GO.'.encode(),'Solar-Simulator 0.4.0 — кандидат, выпуск не разрешён.'.encode());assert now==expected
        def normalized(b):
            t=ast.parse(b)
            for node in ast.walk(t):
                if isinstance(node,ast.Constant) and isinstance(node.value,str):node.value=node.value.replace('Release0.3.3 — NO-GO.','STATUS').replace('Solar-Simulator 0.4.0 — кандидат, выпуск не разрешён.','STATUS')
            return ast.dump(t)
        assert normalized(before)==normalized(now)
    else:
        assert before==now,n
        assert (OLD/n).read_bytes()==(S/n).read_bytes(),n
        numerical[n]=dict(git_blob=git('rev-parse',head+':'+n).decode().strip(),raw_SHA256=sha((S/n).read_bytes()))
from test_historical_sources407 import assert_version
from scripts.prepare_qualification383 import METADATA
assert_version(S,'0.4.0')
for n in METADATA:
    a=tomllib.loads((OLD/n).read_text());b=tomllib.loads((S/n).read_text())
    if n.endswith('.lock'):
        for p in a['package']:
            if p['name'] in ('solar_core','solar_native'):p['version']='0.4.0'
    else:a['project' if n.endswith('pyproject.toml') else 'package']['version']='0.4.0'
    assert a==b
from historical033_fixture407v import ARCHIVE,MEMBERS,SHA
assert sha(ARCHIVE.read_bytes())==SHA
with zipfile.ZipFile(ARCHIVE) as z:
    assert z.testzip() is None and set(z.namelist())==set(METADATA)
    for n in METADATA:
        b=z.read(n);assert sha(b)==MEMBERS[n] and b==(OLD/n).read_bytes();assert b.replace(b'\r\n',b'\n')==git('show',BASE+':'+n).replace(b'\r\n',b'\n')
# Exact historical reports, archives, helpers and all other base files unchanged by Git.
for n in ('scripts/release_history.py','scripts/historical_sources407.py','scripts/prepare_qualification383.py','tests/historical376_fixture407.py'):
    assert git('rev-parse',BASE+':'+n)==git('rev-parse',head+':'+n)
from solar_simulator.recipe import runtime_fingerprint
from scripts.native_audit import require_native
import solar_simulator,solar_native
require_native();native=Path(getattr(solar_native,'solar_native',solar_native).__file__).resolve();source=Path(solar_simulator.__file__).resolve()
installation=json.loads((W/'actual-environment.json').read_bytes());fp=runtime_fingerprint('rust');assert fp==installation['fingerprint'];fpbytes=(json.dumps(fp,indent=2)+'\n').encode();assert (W/'actual-fingerprint.json').read_bytes()==fpbytes
expected_native='a2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b';assert sha(native.read_bytes())==expected_native==installation['native_SHA256'];assert source.is_relative_to(S/'src') and native.is_relative_to(W/'env') and Path(sys.prefix)==W/'env'
assert md.version('solar-simulator')==md.version('solar-native')=='0.4.0'
url=json.loads(md.distribution('solar-simulator').read_text('direct_url.json'));assert url['dir_info']['editable'] and url['url']==S.as_uri()
wheel=next((W/'wheels').glob('*.whl'))
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None
    n=next(n for n in z.namelist() if n.endswith('.pyd'));assert z.read(n)==native.read_bytes()
    assert 'Version: 0.4.0' in z.read('solar_native-0.4.0.dist-info/METADATA').decode()
    assert 'Tag: cp314-cp314t-win_amd64' in z.read('solar_native-0.4.0.dist-info/WHEEL').decode()
# Gates exercised on isolated corrupted copies, never qualified source/artifacts.
from scripts.ias15_process import verify_files
neg=[];bad=W/'audit-negative3';bad.mkdir(exist_ok=False)
oldnative=next(Path('C:/Users/Admin/Documents/Codex/Solar407-20261110/env/Lib/site-packages/solar_native').glob('*.pyd'));assert sha(oldnative.read_bytes())=='651e3466d67b94601c56eaf1bd622f178748c8439ade7e6725fd52682e13e091'
def must_reject(name,call):
    try:call()
    except (ValueError,AssertionError,FileNotFoundError):neg.append(name);return
    raise AssertionError('Gate accepted '+name)
for label,raw,expected in [('old_native',oldnative.read_bytes(),expected_native),('native_mutated',native.read_bytes()+b'x',expected_native),('physical_source_changed',(S/'src/solar_simulator/accuracy.py').read_bytes()+b'\n',sha((S/'src/solar_simulator/accuracy.py').read_bytes()))]:
    p=bad/label;p.write_bytes(raw);must_reject(label,lambda:verify_files({label:expected},root=bad))
from scripts.build_portable import candidate_versions,prepare_documents
from scripts.check_portable import check_document_links
from scripts.historical_sources407 import restore_metadata032
from historical033_fixture407v import restore033
for version,restore in [('0.3.2',lambda p:restore_metadata032(S,p)),('0.3.3',restore033)]:
    root=bad/version;restore(root);must_reject(version+'_as_current',lambda:assert_version(root,'0.4.0'));must_reject('current_as_'+version,lambda:assert_version(S,version))
root=bad/'mixed';restore033(root);p=root/'pyproject.toml';p.write_bytes(p.read_bytes().replace(b'0.3.3',b'0.4.0'));must_reject('Cargo_Python_mismatch',lambda:candidate_versions(root))
from historical376_fixture407 import checkout
import os
bundle=Path('C:/Users/Admin/Documents/Codex/Solar407-20261110/historical376-inputs.zip');assert sha(bundle.read_bytes())=='2326775712ab071ec6354b01f529ba2749c22bbee773e5f26948c11408cc38d5'
os.environ['SOLAR_HISTORICAL376_BUNDLE']=str(bad/'missing.zip');must_reject('missing376bundle',lambda:checkout(S,bad/'376'));os.environ['SOLAR_HISTORICAL376_BUNDLE']=str(bundle)
# Real closure verifies the external bundle plus source/member hashes without executing old binaries.
checkout(S,bad/'verified376')
# Recorded bindings are compared to actual imports, never made true by metadata alone.
def bound(r):
    if r['application_version']!='0.4.0' or r['native_version']!='0.4.0' or r['source']!=str(source) or r['native_SHA256']!=expected_native:raise ValueError('Runtime/source/native binding mismatch')
binding=dict(application_version=md.version('solar-simulator'),native_version=md.version('solar-native'),source=str(source),native_SHA256=sha(native.read_bytes()));bound(binding)
for label,key,value in [('old-native-metadata','native_version','0.3.3'),('package_source_mismatch','source',str(OLD/'src/solar_simulator/__init__.py')),('package_current_version_mismatch','application_version','0.3.3')]:
    r=dict(binding);r[key]=value;must_reject(label,lambda:bound(r))
# Document-only composition, not a portable binary build.
out=W/'document-composition3';out.mkdir(exist_ok=False);copied=prepare_documents(out)
license=out/'runtime/Lib/site-packages/solar_simulator/data/ERFA-LICENSE.txt';license.parent.mkdir(parents=True);shutil.copyfile(S/'src/solar_simulator/data/ERFA-LICENSE.txt',license)
def check_docs():
    required=out/f'docs/releases/v{candidate_versions(S)[0]}.md'
    if not required.is_file():raise FileNotFoundError('Required current release page')
    return check_document_links(out)
links=check_docs()
release=out/'docs/releases/v0.4.0.md';assert release.is_file();release.rename(release.with_suffix('.withheld'));must_reject('missing_release040_document',check_docs);release.with_suffix('.withheld').rename(release)
assert [p for p in (out/'runtime').rglob('*') if p.is_file()]==[license] and not list(out.rglob('*.pyd'))
for p in out.rglob('*'):
    if p.is_file():assert not any(x in p.parts for x in ('AGENTS.md','.tools','.venv','__pycache__'))
a=(W/'binary-old.json').read_bytes();b=(W/'binary-new.json').read_bytes();assert a==b
old=json.loads((W/'binary-old.json').read_bytes());new=json.loads((W/'binary-new.json').read_bytes());assert old==new
# Newton action/reaction independent scalar identity, not PASS flags.
from solar_simulator.simulation import G,sun_earth
bodies,_=sun_earth(.6);distance=bodies[0].position.distance_to(bodies[1].position)
expected=G*bodies[0].mass/distance**2;measured=abs(new['newton'][1][0]);assert abs(expected-measured)<=expected*3e-15
counts={}
for n in ('targeted.xml','compatibility-tests.xml','doc-fixed.xml'):
    root=ET.parse(W/n).getroot();assert not root.findall('.//failure') and not root.findall('.//error') and not root.findall('.//skipped');counts[n]=len(root.findall('.//testcase'))
inventory=json.loads((W/'inventory408.json').read_bytes());old=json.loads((R/'scripts/qualification407/inventory407.json').read_bytes());assert len(inventory['nodes'])==3083 and len(set(old['nodes'])&set(inventory['nodes']))==3073
for name,digest in inventory['test_sources'].items():assert sha((S/name).read_bytes())==digest
# Protected public refs and candidate407 stay exactly as supplied.
assert git('rev-parse','main').decode().strip()=='cf653c9ca4b60649e70658b002a5e70669411266'
assert subprocess.check_output(['git','-C',str(OLD),'rev-parse','HEAD']).decode().strip()==BASE
result=dict(candidate_commit=head,candidate_tree=tree,branch='codex/candidate-0.4.0-version-407v',changed_paths=changed,numerical_files=numerical,source_fingerprint_SHA256=sha(fpbytes),fingerprint_format='SHA256 of UTF8 json.dumps(runtime_fingerprint, indent=2) plus LF',native_SHA256=expected_native,wheel_SHA256=sha(wheel.read_bytes()),ABI='cp314-cp314t-win_amd64',binding=binding,tests=counts,inventory_count=3083,old_nodes_preserved=3073,new_nodes=10,negative_controls=neg,document_files=len([p for p in out.rglob('*') if p.is_file()]),document_links=links,document_closure=copied,short_numerical_contract_exact=True,historical376_verified=True,old_native_unchanged=True,source_only_not_scientific_qualification=True,limitations=['No runtime version symbol in existing native; version bound by wheel/Cargo/import/hash','Source/ABI/short tests do not transfer scientific receipts','Full408 and portable acceptance NOT RUN; D1 and release NO-GO'])
(W/'independent-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('AUDIT VERIFIED',head,tree,sha(fpbytes),len(neg),'negatives',counts)
