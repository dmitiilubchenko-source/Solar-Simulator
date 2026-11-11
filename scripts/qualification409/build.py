"""One bounded409build with native compilation fenced off."""
import hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar409-build-20261111');P=json.loads((W/'plan.json').read_bytes());T=Path(P['packaging_root']);A=Path('C:/Users/Admin/Documents/Codex/Solar409-20261111');assert json.loads((A/'cloud-final-closure.json').read_bytes())['status']=='CLOUD408_CLOSURE_VERIFIED'
pre=json.loads((W/'build-preflight.json').read_bytes());assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain']);commit=subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip();assert all(hashlib.sha256((T/n).read_bytes()).hexdigest()==v for n,v in pre['runtime_files'].items())
spec=importlib.util.spec_from_file_location('portable409',T/'scripts/build_portable.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);original=subprocess.run;calls=[]
def fenced(command,*a,**kw):
 text=' '.join(map(str,command)).lower()
 if any(x in text for x in ('build_native.py','maturin','cargo')):raise AssertionError('409native compilation forbidden')
 calls.append(dict(command=list(map(str,command)),cwd=str(kw.get('cwd','')),start=time.time()));result=original(command,*a,**kw);calls[-1].update(end=time.time(),exit_code=result.returncode);return result
m.subprocess.run=fenced;os.environ['PIP_NO_INDEX']='1';os.environ['PIP_DISABLE_PIP_VERSION_CHECK']='1';os.environ['CARGO_NET_OFFLINE']='true';failure=None;output=None
try:
 output=m.build(native_wheel=Path(P['wheel']),wheel_sha256=P['wheel_SHA256'],native_sha256=P['native_SHA256'],output_root=W/'output',verification_root=Path(pre['historical_root']),verification_manifest_sha256=pre['historical_manifest_SHA256'])
except BaseException as exc:
 failure=dict(type=type(exc).__name__,message=str(exc));raise
finally:
 record=dict(source_candidate=P['base_runtime_commit'],packaging_commit=commit,tooling_SHA256=hashlib.sha256((T/'scripts/build_portable.py').read_bytes()).hexdigest(),native_rebuilt=False,native_wheel_SHA256=P['wheel_SHA256'],native_SHA256=P['native_SHA256'],calls=calls,output=str(output) if output else None,failure=failure,build_finished=output is not None)
 with (W/'build-completion.json').open('x',encoding='utf8') as f:json.dump(record,f,indent=2)
