"""Prepare byte-identical isolated test dependencies, never modify a candidate."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv

R=Path(__file__).resolve().parents[2]
W=R/'.tools/acceptance406-20261109'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(path,value):
    with Path(path).open('x',encoding='utf8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def main():
    p=json.loads((R/'scripts/qualification406/plan.json').read_bytes());source=Path(p['candidate_source'])
    git=lambda *args:subprocess.check_output(['git','-C',str(source),*args])
    assert git('rev-parse','HEAD').decode().strip()==p['candidate_commit']
    assert git('rev-parse','HEAD^{tree}').decode().strip()==p['candidate_tree']
    assert not git('status','--porcelain')
    assert not git('diff','fe0f456f2c7ba3a077eac21fc8413937d6e84fac',p['candidate_commit'],'--','rust')
    for name,digest in p['input_SHA256'].items():assert sha(R/name)==digest,name
    for name,digest in p['source_contract_SHA256'].items():assert sha(source/name)==digest,name
    original=Path(p['qualified_environment'])/'Lib/site-packages'
    target=Path(p['test_environment']);assert not target.exists()
    venv.EnvBuilder(with_pip=False,symlinks=False).create(target)
    site=target/'Lib/site-packages'
    shutil.copytree(original,site,dirs_exist_ok=True,
        ignore=lambda directory,names:[x for x in names if x=='__pycache__' or (Path(directory)==original and x=='solar_simulator')])
    copied={}
    for directory,dirs,files in os.walk(original):
        dirs[:]=[x for x in dirs if x!='__pycache__' and not (Path(directory)==original and x=='solar_simulator')]
        for name in files:
            file=Path(directory)/name;relative=file.relative_to(original)
            digest=sha(file);assert sha(site/relative)==digest
            copied[relative.as_posix()]=dict(size=file.stat().st_size,sha256=digest)
    assert not (site/'solar_simulator').exists()
    # Optional, already archived research dependency used by mandatory tests.
    # Only exact published hashes are copied; no download/build/installation.
    history=json.loads((source/p['rebound_expected_manifest']).read_bytes())
    expected=history['library_files_sha256'];reb=source/'.tools/ias15165/dependency'
    for name,digest in expected.items():
        old=Path(p['rebound_source'])/name;assert sha(old)==digest,name
        new=reb/name;new.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,new)
        assert sha(new)==digest
    activation=site/'source-candidate406.pth'
    activation.write_text(str(source/'src')+'\n'+str(reb)+'\n',encoding='utf8')
    save(W/'dependency-copy.json',dict(qualified_source=str(original),test_prefix=str(target),
        files=copied,source_activation_pth_SHA256=sha(activation),source_activation=activation.read_text(encoding='utf8'),
        rebound_expected_SHA256=expected,policy='Copies only, original384environment unchanged; no pip and no binary rebuild.'))
    python=target/'Scripts/python.exe'
    subprocess.run([str(python),'-I','-X','utf8','-B',str(R/'scripts/qualification406/probe.py')],cwd=source,check=True)
    # Collection only: freeze exact nodeIDs before any test execution.
    command=[str(python),'-X','utf8','-B','-m','pytest','--collect-only','-q','-p','no:cacheprovider','-p','scripts.native_audit']
    env=os.environ.copy();env.pop('PYTEST_ADDOPTS',None)
    output=subprocess.run(command,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (W/'collection.log').write_bytes(output.stdout)
    if output.returncode:raise RuntimeError('Collection failed; full tests not allowed')
    nodes=[line.strip() for line in output.stdout.decode('utf8').splitlines() if line.startswith('tests/') and '::' in line]
    assert nodes and len(nodes)==len(set(nodes))
    save(W/'test-inventory.json',dict(candidate=p['candidate_commit'],plan_SHA256=sha(R/'scripts/qualification406/plan.json'),
        test_files=p['test_file_inventory'],nodes=nodes,node_count=len(nodes),
        node_list_SHA256=hashlib.sha256(('\n'.join(nodes)+'\n').encode()).hexdigest(),command=command,
        expected_main_skips=0,expected_main_xfails=0,selection='Full stock testpaths; no deselect/markers/filter'))
    save(W/'preflight.json',dict(status='PASS_ATTESTED_ENVIRONMENT_AND_COLLECTION',candidate=p['candidate_commit'],
        tree=p['candidate_tree'],environment_SHA256=sha(W/'actual-environment.json'),inventory_SHA256=sha(W/'test-inventory.json'),
        dependency_copy_SHA256=sha(W/'dependency-copy.json'),original_environment_mutated=False,
        source_unmodified=not bool(git('status','--porcelain')),test_count=len(nodes)))
    print('PASS source/native/environment/profile and collection; immutable node inventory',len(nodes),flush=True)


if __name__=='__main__':main()
