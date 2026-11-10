"""Copy only existing qualified dependency bytes; activate the separate source."""
import hashlib,json,os,shutil,subprocess,sys,venv
from pathlib import Path
W=Path('C:/Users/Admin/Documents/Codex/Solar407-20261110');p=json.loads((W/'plan.json').read_bytes())
S=Path(p['candidate_source']);R=Path(__file__).resolve().parents[2];target=Path(p['test_environment'])
assert not target.exists()
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==p['base']
venv.EnvBuilder(with_pip=False).create(target);old=Path(p['qualified_environment'])/'Lib/site-packages';site=target/'Lib/site-packages'
shutil.copytree(old,site,dirs_exist_ok=True,ignore=lambda directory,names:[x for x in names if x=='__pycache__' or (Path(directory)==old and x=='solar_simulator')])
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();files={}
for root,dirs,names in os.walk(old):
    dirs[:]=[x for x in dirs if x!='__pycache__' and not (Path(root)==old and x=='solar_simulator')]
    for name in names:
        a=Path(root)/name;rel=a.relative_to(old);digest=sha(a);assert sha(site/rel)==digest;files[rel.as_posix()]=digest
rebound=json.loads((S/'docs/ias15-restart-validation.json').read_bytes())['library_files_sha256'];reb=S/'.tools/ias15165/dependency'
for name,digest in rebound.items():
    src=R/'.tools/ias15165/dependency'/name;assert sha(src)==digest;dst=reb/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
(site/'source-candidate407.pth').write_text(str(S/'src')+'\n'+str(reb)+'\n')
with (W/'dependency-copy.json').open('x') as f:json.dump(dict(files=files,rebound=rebound,original_qualified_unchanged=True),f)
code='''import sys,json,hashlib;from pathlib import Path;import solar_simulator,solar_native,numpy,scipy,matplotlib;from solar_simulator.recipe import runtime_fingerprint;from scripts.native_audit import require_native
assert Path(solar_simulator.__file__).is_relative_to(Path(sys.argv[1])/'src');require_native();fp=runtime_fingerprint('rust');raw=(json.dumps(fp,indent=2)+'\\n').encode();Path(sys.argv[2]).write_bytes(raw);print(hashlib.sha256(raw).hexdigest())'''
subprocess.run([str(target/'Scripts/python.exe'),'-I','-X','utf8','-B','-c','import sys;sys.path.insert(0,sys.argv[1]);'+code,str(S),str(W/'baseline-environment.json')],cwd=S,check=True)
assert sha(W/'baseline-environment.json')=='f31aa35a6f4b1e504c1ce34b620a7ca7fe7e5ecf3ca5b4d5d8f2a86d0fe52091'
print('PASS isolated407source/dependencies/-I compilednative/exact405baselineprofile',flush=True)
