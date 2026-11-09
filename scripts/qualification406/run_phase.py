"""Run stock candidate commands with reporting-only options and immutable receipts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

R=Path(__file__).resolve().parents[2];W=R/'.tools/acceptance406-20261109'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,value):
    from scripts.q2_execution398 import atomic_json,envelope
    atomic_json(path,envelope(value))


def main():
    sys.path.insert(0,str(R))
    p=json.loads((R/'scripts/qualification406/plan.json').read_bytes());source=Path(p['candidate_source'])
    python=Path(p['test_environment'])/'Scripts/python.exe';cargo=Path.home()/'.cargo/bin/cargo.exe'
    assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==p['candidate_commit']
    pre=json.loads((W/'preflight.json').read_bytes())
    assert pre['status']=='PASS_ATTESTED_ENVIRONMENT_AND_COLLECTION'
    assert sha(W/'actual-environment.json')==p['source_fingerprint']==pre['environment_SHA256']
    assert sha(W/'test-inventory.json')==pre['inventory_SHA256']
    env=os.environ.copy();env.update(CARGO_TARGET_DIR=str(source/'rust/solar_core/target'),
        PYO3_PYTHON=str(python),TEMP=str(W/'temp'),TMP=str(W/'temp'))
    (W/'temp').mkdir(exist_ok=True);(W/'results').mkdir(exist_ok=True)
    phase=sys.argv[1];commands=[]
    if phase=='rust_prepare':
        commands=[[str(cargo),'build','--release','--locked','--offline','--manifest-path',str(source/'rust/solar_core/Cargo.toml')]]
    elif phase=='full_stock_check':
        # Do not set a shared --basetemp: nested pytest self-tests must retain
        # their own distinct default temp roots. The main JUnit is written last.
        env['PYTEST_ADDOPTS']='-vv -ra --junitxml='+str(W/'results/python.xml')
        commands=[[str(python),'-X','utf8','-B',str(source/'scripts/check_project.py'),'--require-native']]
    elif phase=='rust_complete_if_stock_aborted':
        commands=[[str(cargo),'fmt','--manifest-path',str(source/'rust'/crate/'Cargo.toml'),'--check'] for crate in ('solar_core','solar_native')]
        commands.append([str(cargo),'test','--manifest-path',str(source/'rust/solar_core/Cargo.toml')])
    elif phase=='compile_import':
        commands=[[str(python),'-I','-X','utf8','-B',str(R/'scripts/qualification406/compile_import.py')]]
    else:raise ValueError(phase)
    rows=[]
    for command in commands:
        print('COMMAND406',json.dumps(command),flush=True)
        result=subprocess.run(command,cwd=source,env=env)
        rows.append(dict(command=command,exit_code=result.returncode))
        if result.returncode:break
    files={}
    if phase=='rust_prepare' and rows[-1]['exit_code']==0:
        executable=source/'rust/solar_core/target/release/solar_core.exe'
        files['standalone_rust']=dict(path=str(executable),SHA256=sha(executable))
    if phase=='full_stock_check' and (W/'results/python.xml').is_file():
        files['python_junit']=dict(path=str(W/'results/python.xml'),SHA256=sha(W/'results/python.xml'))
    save(W/(phase+'-result.json'),dict(candidate=p['candidate_commit'],tree=p['candidate_tree'],
        environment_SHA256=sha(W/'actual-environment.json'),inventory_SHA256=sha(W/'test-inventory.json'),
        plan_SHA256=sha(R/'scripts/qualification406/plan.json'),commands=rows,execution_finished=True,
        tests_passed=all(x['exit_code']==0 for x in rows),files=files,
        reporting_environment={key:env.get(key) for key in ('PYTEST_ADDOPTS','TEMP','TMP','CARGO_TARGET_DIR','PYO3_PYTHON')},
        native_rebuilt_or_installed=False))
    raise SystemExit(0 if all(x['exit_code']==0 for x in rows) else 1)


if __name__=='__main__':main()
