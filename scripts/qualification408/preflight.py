"""Exact408 environment, all Git blobs, frozen inputs and collection; no pytest execution."""
import hashlib,importlib.metadata as md,inspect,json,os,subprocess,sys,sysconfig,time,zipfile
from pathlib import Path
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar408-20261111');P=json.loads((W/'plan.json').read_bytes());S=Path(P['candidate_source']);sys.path.insert(0,str(S));sys.path.insert(0,str(S/'tests'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(S),*args])
assert not git('status','--porcelain');assert git('rev-parse','HEAD').decode().strip()==P['candidate_commit'];assert git('rev-parse','HEAD^{tree}').decode().strip()==P['candidate_tree']
index=git('ls-files','--stage','-z').decode().split('\0');names=[];blobs=[]
for row in filter(None,index):
    before,name=row.split('\t',1);mode,blob,stage=before.split();assert stage=='0';names.append(name);blobs.append(blob)
hashed=subprocess.check_output(['git','-C',str(S),'hash-object','--stdin-paths'],input=('\n'.join(names)+'\n').encode()).decode().splitlines();assert hashed==blobs
from solar_simulator.recipe import runtime_fingerprint
from scripts.native_audit import require_native
import solar_simulator,solar_native,numpy,scipy,matplotlib
require_native();native=Path(getattr(solar_native,'solar_native',solar_native).__file__).resolve()
assert Path(sys.executable).resolve()==Path(P['test_python']).resolve() and Path(sys.prefix).resolve()==Path(P['environment']['prefix']).resolve()
assert Path(solar_simulator.__file__).resolve().is_relative_to(S/'src');assert native.is_relative_to(Path(sys.prefix));assert sha(native)==P['native_SHA256']
assert {n:md.version(n) for n in ('solar-simulator','solar-native','numpy','scipy','matplotlib')}=={'solar-simulator':'0.4.0','solar-native':'0.4.0','numpy':'2.5.1','scipy':'1.18.1','matplotlib':'3.11.0'}
assert sys.version_info[:3]==(3,14,2) and sysconfig.get_config_var('Py_GIL_DISABLED')==1
fp=runtime_fingerprint('rust');raw=(json.dumps(fp,indent=2)+'\n').encode();assert hashlib.sha256(raw).hexdigest()==P['source_fingerprint'];(W/'actual-environment.json').write_bytes(raw)
wheel=Path(P['required_external_inputs'][-1]['source']);assert sha(wheel)==P['environment']['native_wheel_SHA256']
with zipfile.ZipFile(wheel) as z:
    assert z.testzip() is None;binary=z.read(next(n for n in z.namelist() if n.endswith('.pyd')));assert hashlib.sha256(binary).hexdigest()==P['native_SHA256']
    assert 'Version: 0.4.0' in z.read('solar_native-0.4.0.dist-info/METADATA').decode();assert 'Tag: cp314-cp314t-win_amd64' in z.read('solar_native-0.4.0.dist-info/WHEEL').decode()
bundle=Path(P['required_external_inputs'][0]['source']);assert bundle.stat().st_size==706900 and sha(bundle)==P['required_external_inputs'][0]['SHA256'];os.environ['SOLAR_HISTORICAL376_BUNDLE']=str(bundle)
fixture=S/'tests/fixtures/metadata033-828c798.zip';assert fixture.stat().st_size==3922 and sha(fixture)=='a1fe4cbdf213a6d97652a7d8e2108f584a1c0066ab8fcc5adb96bbc951b5c970'
from historical033_fixture407v import restore033
restore033(W/'preflight-history033')
from historical376_fixture407 import checkout
checkout(S,W/'preflight-history376')
from scripts.prepare_test_inputs import restore
inputs=restore();assert inputs['verified']==7
from scripts.build_portable import candidate_versions
assert candidate_versions(S)[0]=='0.4.0'
cargo=Path.home()/'.cargo/bin/cargo.exe';rustc=cargo.with_name('rustc.exe');rustver=subprocess.check_output([str(rustc),'-vV'],text=True);assert 'rustc 1.99.0' in rustver and 'x86_64-pc-windows-gnu' in rustver
for crate in ('solar_core','solar_native'):
    text=subprocess.check_output([str(cargo),'metadata','--format-version','1','--locked','--offline','--manifest-path',str(S/f'rust/{crate}/Cargo.toml')],text=True)
    doc=json.loads(text);packages={p['name']:p['version'] for p in doc['packages']};assert packages['solar_core']=='0.4.0'
    if crate=='solar_native':assert packages['solar_native']=='0.4.0' and packages['pyo3']=='0.29.3'
    (W/f'{crate}-metadata.json').write_text(json.dumps(doc,indent=2)+'\n')
monitor=R/'.tools/qualification385/offline_monitor.py';assert sha(monitor)==P['monitor']['SHA256']
inv=R/P['inventory'];assert sha(inv)==P['inventory_SHA256'];old=json.loads(inv.read_bytes());assert len(old['nodes'])==3083
# Collection subprocess does not execute any tests. Exact native audit plugin retained.
env=os.environ.copy();env['PYTEST_ADDOPTS']='';command=[sys.executable,'-X','utf8','-B','-m','pytest','--collect-only','-q','-p','no:cacheprovider','-p','scripts.native_audit'];result=subprocess.run(command,cwd=S,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(W/'collection.log').write_bytes(result.stdout)
nodes=[line.strip() for line in result.stdout.decode('utf8').splitlines() if line.startswith('tests/') and '::' in line]
missing=sorted(set(old['nodes'])-set(nodes));extra=sorted(set(nodes)-set(old['nodes']));(W/'collection-diff.json').write_text(json.dumps(dict(missing=missing,extra=extra,expected=len(old['nodes']),actual=len(nodes),same_order=nodes==old['nodes']),indent=2)+'\n')
assert result.returncode==0 and not missing and not extra and len(nodes)==len(set(nodes))==3083
(W/'test-inventory.json').write_text(json.dumps(dict(nodes=nodes,test_sources={n:sha(S/n) for n in names if n.startswith('tests/')},source_inventory_SHA256=sha(inv)),indent=2)+'\n')
# Pin candidate, developer evidence, all raw source files and optional compiled dependency.
source={n:dict(SHA256=sha(S/n),git_blob=blob) for n,blob in zip(names,blobs)}
(W/'source-bindings.json').write_text(json.dumps(source,indent=2)+'\n')
rebound=__import__('rebound');rebound_root=Path(rebound.__file__).parent;optional={str(p):sha(p) for p in rebound_root.rglob('*') if p.is_file() and p.suffix in ('.py','.pyd')}
core=S/'rust/solar_core/target/release/solar_core.exe';oldcore=Path('C:/Users/Admin/Documents/Codex/Solar407V-20261111/target-native/release/solar_core.exe');assert core.read_bytes()==oldcore.read_bytes()
report=dict(status='PASS_EXACT_BINDINGS_COLLECTION',candidate=P['candidate_commit'],tree=P['candidate_tree'],prefix=sys.prefix,python=sys.executable,actual_source=solar_simulator.__file__,native=str(native),native_SHA256=sha(native),wheel=str(wheel),wheel_SHA256=sha(wheel),source_fingerprint=hashlib.sha256(raw).hexdigest(),source_binding_SHA256=sha(W/'source-bindings.json'),inventory_count=len(nodes),inventory_SHA256=sha(W/'test-inventory.json'),original_inventory_SHA256=sha(inv),external376_SHA256=sha(bundle),historical033_SHA256=sha(fixture),public_research_inputs=inputs,source_files=len(source),versions={n:md.version(n) for n in ('solar-simulator','solar-native','numpy','scipy','matplotlib','psutil','pytest')},rustc=rustver,standalone_core_SHA256=sha(core),optional_rebound_version=rebound.__version__,optional_dependency=optional,native_rebuild=False,timestamp=time.time())
(W/'preflight.json').write_text(json.dumps(report,indent=2)+'\n');print('PREFLIGHT exactcandidate/native/fingerprint/inputs/3083collection PASS',flush=True)
