"""Stock408 driver with reporting-only environment; frozen candidate untouched."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar408-20261111');P=json.loads((W/'plan.json').read_bytes());S=Path(P['candidate_source']);sys.path.insert(0,str(S))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not subprocess.check_output(['git','-C',str(S),'status','--porcelain'])
assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==P['candidate_commit']
pre=json.loads((W/'preflight.json').read_bytes());assert pre['status']=='PASS_EXACT_BINDINGS_COLLECTION'
from solar_simulator.recipe import runtime_fingerprint
assert hashlib.sha256((json.dumps(runtime_fingerprint('rust'),indent=2)+'\n').encode()).hexdigest()==P['source_fingerprint']
cargo=Path.home()/'.cargo/bin/cargo.exe';rustc=cargo.with_name('rustc.exe');sysroot=Path(subprocess.check_output([str(rustc),'--print','sysroot'],text=True).strip());env=os.environ.copy()
env['PATH']=str(cargo.parent)+os.pathsep+str(sysroot/'lib/rustlib/x86_64-pc-windows-gnu/bin/self-contained')+os.pathsep+str(R/'.tools/msys2/mingw64/bin')+os.pathsep+env['PATH']
env.update(CARGO_TARGET_DIR=str(W/'cargo-target'),CARGO_NET_OFFLINE='true',PYO3_PYTHON=sys.executable,SOLAR_HISTORICAL376_BUNDLE=P['required_external_inputs'][0]['source'])
phase=sys.argv[1]
if phase=='full_stock':
    (W/'results').mkdir(exist_ok=False);env['PYTEST_ADDOPTS']=P['reporting']['PYTEST_ADDOPTS'];commands=[[sys.executable,'-X','utf8','-B',str(S/'scripts/check_project.py'),'--require-native']]
elif phase=='rust_completion':
    commands=[[str(cargo),'fmt','--manifest-path',str(S/f'rust/{crate}/Cargo.toml'),'--check'] for crate in ('solar_core','solar_native')]
    commands+=[[str(cargo),'test','--locked','--offline','--manifest-path',str(S/'rust/solar_core/Cargo.toml')]]
else:raise ValueError(phase)
rows=[]
for command in commands:
    start=time.time();print('COMMAND408',json.dumps(command),flush=True);result=subprocess.run(command,cwd=S,env=env);rows.append(dict(command=command,exit_code=result.returncode,start_timestamp=start,end_timestamp=time.time()))
    if result.returncode:break
record=dict(phase=phase,execution_finished=True,commands=rows,candidate=P['candidate_commit'],tree=P['candidate_tree'],source_fingerprint=P['source_fingerprint'],native_SHA256=P['native_SHA256'],native_rebuilt=False,plan_SHA256=sha(W/'plan.json'),preflight_SHA256=sha(W/'preflight.json'),junit_SHA256=sha(W/'results/python.xml') if (W/'results/python.xml').exists() else None,reporting_environment={k:env[k] for k in ['PYTEST_ADDOPTS','TEMP','TMP','CARGO_TARGET_DIR','CARGO_NET_OFFLINE','PYO3_PYTHON','SOLAR_HISTORICAL376_BUNDLE'] if k in env})
raw=(json.dumps(record,indent=2)+'\n').encode();output=W/(phase+'-completion.json')
with output.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
print('EXECUTION_FINISHED408',phase,'exit',rows[-1]['exit_code'],'receiptSHA',hashlib.sha256(raw).hexdigest(),flush=True);raise SystemExit(rows[-1]['exit_code'])
