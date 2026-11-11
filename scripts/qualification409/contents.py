"""Independent allowed-content closure from CPython/distributions/two pinned wheels."""
from pathlib import Path
import fnmatch,hashlib,json,os,sys,zipfile
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111');P=json.loads((W/'plan.json').read_bytes());audit=json.loads((W/'package-audit.json').read_bytes());folder=Path(audit['directory']);runtime=folder/'runtime';base=Path(sys.base_prefix);expected={};roles={};sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(name,path,role):expected[name]=sha(path);roles[name]=role
exe=Path(sys._base_executable);source('python.exe',exe,'qualifiedCPython');source('pythonw.exe',exe.with_name(exe.name.replace('python','pythonw',1)),'qualifiedCPython');source('LICENSE.txt',base/'LICENSE.txt','CPythonlicense')
for p in base.glob('*.dll'):
 if '_d' not in p.stem:source(p.name,p,'qualifiedCPythonDLL')
patterns=('__pycache__','*.pyc','*.pdb','site-packages','test','tests','idlelib','turtledemo')
for root in ('Lib','DLLs','tcl'):
 for b,dirs,files in os.walk(base/root):
  dirs[:]=[d for d in dirs if not any(fnmatch.fnmatch(d,g) for g in patterns)]
  for n in files:
   if any(fnmatch.fnmatch(n,g) for g in patterns):continue
   p=Path(b)/n;source((Path(root)/p.relative_to(base/root)).as_posix(),p,'qualifiedCPythonStdlibTcl')
sys.path.insert(0,P['packaging_root']);from scripts.build_portable import dependency_closure,PUBLIC_DOCUMENT_ARCHIVES
for name,dist in dependency_closure().items():
 root=Path(dist.locate_file('')).resolve()
 for entry in dist.files or []:
  p=Path(dist.locate_file(entry)).resolve()
  if not p.is_relative_to(root) or not p.is_file() or '__pycache__' in p.parts or p.suffix=='.pyc':continue
  source((Path('Lib/site-packages')/p.relative_to(root)).as_posix(),p,'dependency:'+name)
project=next((Path(P['packaging_root'])/'.tools/distribution-wheels').glob('solar_simulator-0.4.0-*.whl'))
for path,role in [(project,'project040wheel'),(Path(P['wheel']),'pinnedNative040wheel')]:
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for n in z.namelist():
   if n.endswith('/'):continue
   key='Lib/site-packages/'+n;expected[key]=hashlib.sha256(z.read(n)).hexdigest();roles[key]=role
pth=json.loads((folder/'BUILD-INFO.json').read_bytes())['python_abi']+'._pth';assert (runtime/pth).read_text()=='.\nLib\nDLLs\nLib/site-packages\nimport site\n';source(pth,runtime/pth,'explicit_isolation_configuration')
actual={p.relative_to(runtime).as_posix():sha(p) for p in runtime.rglob('*') if p.is_file()};assert actual==expected,dict(missing=sorted(set(expected)-set(actual))[:10],unexpected=sorted(set(actual)-set(expected))[:10],changed=[n for n in actual.keys()&expected.keys() if actual[n]!=expected[n]][:10])
allowedtop={'runtime','docs','data','scripts','verification','scenarios'};unexpected=[]
for p in folder.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(folder)
 if rel.parts[0] in allowedtop:continue
 if rel.as_posix() in PUBLIC_DOCUMENT_ARCHIVES|{'src/solar_simulator/data/ERFA-LICENSE.txt'}:
  assert sha(p)==sha(Path(P['packaging_root'])/rel);continue
 if len(rel.parts)!=1 or p.suffix not in ('.cmd','.md','.json'):unexpected.append(rel.as_posix())
assert not unexpected
for name in ['pytest','maturin','setuptools','pip']:
 assert not (runtime/'Lib/site-packages'/name).exists(),'Undeclared devpackage '+name
licenses=[n for n in actual if any(x in n.lower() for x in ('license','copying','copyright'))]
result=dict(status='PASS_EXACT_RUNTIME_CLOSURE',runtime_file_count=len(actual),roles_count={role:list(roles.values()).count(role) for role in sorted(set(roles.values()))},all_runtime_files=expected,CPython_dependency_wheel_bytes_verified=True,undeclared_runtime_files=[],declared_source_license_copy='src/solar_simulator/data/ERFA-LICENSE.txt',initial_harness_failure='Narrow allowlist initially omitted explicitly declared ERFAlicense source-copy and publictests/data/jpl-verification.zip; exactexistingPUBLIC_DOCUMENT_ARCHIVES allowlist used with sourceSHA checks; rawFAIL preserved, no packagefiles changed',developer_packages_absent=['pytest','maturin','setuptools','pip'],license_files=licenses,source040wheel_SHA256=sha(project),native040wheel_SHA256=sha(P['wheel']),outsideRuntime_policy='Only declared docs/data/scriptsJSON/verification2replayPY/scenarios and rootcmd/md/json; no extraexecutables',note='Upstream CPython/dependency distributions keep their normal bundledfiles; not developer venv or Solar rawresearch')
(W/'runtime-content-audit.json').write_text(json.dumps(result,indent=2)+'\n');print('CONTENTCLOSURE_PASS',len(actual),'runtimefiles',len(licenses),'licensefiles')
