"""Independent final acceptance evidence audit; preserves the original NO-GO."""
import hashlib
import importlib
import json
from pathlib import Path
import py_compile
import subprocess
import sys
import xml.etree.ElementTree as ET

R=Path(__file__).resolve().parents[2];W=R/'.tools/acceptance406-20261109'


def read(path):return json.loads(Path(path).read_bytes())
def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(path,value):
    with Path(path).open('x',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def envelope(path):
    x=read(path);raw=json.dumps(x['payload'],allow_nan=False,sort_keys=True,separators=(',',':')).encode()
    assert hashlib.sha256(raw).hexdigest()==x['sha256'];return x['payload']


def main():
    p=read(R/'scripts/qualification406/plan.json');source=Path(p['candidate_source'])
    assert Path(sys.prefix).resolve()==Path(p['test_environment']).resolve()
    for name,digest in p['input_SHA256'].items():assert sha(R/name)==digest,name
    for name,digest in p['source_contract_SHA256'].items():assert sha(source/name)==digest,name
    sys.path.insert(0,str(source))
    import solar_simulator,solar_native,numpy,scipy,matplotlib
    from solar_simulator import recipe,inspection
    assert Path(solar_simulator.__file__).resolve().is_relative_to(source/'src')
    for mod in (numpy,scipy,matplotlib,solar_native):assert Path(mod.__file__).resolve().is_relative_to(Path(sys.prefix))
    compiled=getattr(solar_native,'solar_native',solar_native)
    assert sha(compiled.__file__)==p['native_SHA256']
    fp=recipe.runtime_fingerprint('rust');raw=(json.dumps(fp,indent=2)+'\n').encode()
    assert hashlib.sha256(raw).hexdigest()==p['source_fingerprint'] and raw==(W/'actual-environment.json').read_bytes()
    post=W/'post-environment.json'
    if post.exists():assert post.read_bytes()==raw
    else:
        with post.open('xb') as f:f.write(raw)
    # Authenticate the complete frozen Git-blob SHA inventory from405, not the
    # developer tree or a new whitelist generated after seeing the failures.
    previous=read(R/'docs/q2-final-ui-marking-405.json');saved=R/'.tools/qualification405-20261109/source-audit.json'
    assert sha(saved)==previous['source_audit_SHA256'];prior=read(saved)
    expected=prior['Git_blob_SHA256_after']
    actual={name:sha(source/name) for name in expected}
    working_expected={name:prior['working_SHA256_after'].get(name,digest) for name,digest in expected.items()}
    assert actual==working_expected  # Exact prior raw hashes, no normalization.
    original=Path(p['original_source']);original_files={name:sha(original/name) for name in expected if (original/name).is_file()}
    assert all(working_expected[name]==digest for name,digest in original_files.items())
    git=lambda *a:subprocess.check_output(['git','-C',str(source),*a])
    assert git('rev-parse','HEAD').decode().strip()==p['candidate_commit']
    assert git('rev-parse','HEAD^{tree}').decode().strip()==p['candidate_tree']
    current_blobs={name.decode():meta.decode() for row in git('ls-tree','-r','-z','HEAD').split(b'\0') if row
                   for meta,name in [row.split(b'\t',1)]}
    assert current_blobs==prior['Git_blobs_after']
    assert not git('status','--porcelain')
    assert not git('diff','fe0f456f2c7ba3a077eac21fc8413937d6e84fac',p['candidate_commit'],'--','rust')
    accepted_diff=git('diff','--name-status',p['accepted032'],p['candidate_commit']).decode()
    save(W/'source-audit.json',dict(candidate=p['candidate_commit'],tree=p['candidate_tree'],
        accepted032=p['accepted032'],accepted032_diff=accepted_diff,all_frozen_Git_blob_SHA256=expected,
        exact_working_SHA256=actual,Git_blob_identity=current_blobs,
        materialization_differences={name:dict(Git_blob_SHA256=expected[name],qualified405_raw_SHA256=actual[name])
                                    for name in expected if expected[name]!=actual[name]},
        original_sparse_worktree_SHA256=original_files,compiled_native_SHA256=sha(compiled.__file__),
        native_Rust_source_equals_qualified384=True,code_modified=False))
    # Both source and copied dependency inputs remain byte-identical.
    copies=read(W/'dependency-copy.json');site=Path(sys.prefix)/'Lib/site-packages'
    for name,item in copies['files'].items():
        assert sha(site/name)==item['sha256'] and sha(Path(copies['qualified_source'])/name)==item['sha256'],name
    for name,digest in copies['rebound_expected_SHA256'].items():
        assert sha(source/'.tools/ias15165/dependency'/name)==digest
    compiled_files=[]
    for file in sorted((source/'src').rglob('*.py')):
        relative=file.relative_to(source/'src');target=W/'compile'/relative.with_suffix('.pyc')
        target.parent.mkdir(parents=True,exist_ok=True);py_compile.compile(str(file),cfile=str(target),doraise=True)
        compiled_files.append(relative.as_posix())
    imports={}
    for name in ('experiment','accuracy','error_control','nbody_rotation','rotation','storage','recipe','native_forces','rust_backend','app','inspection'):
        mod=importlib.import_module('solar_simulator.'+name);imports[name]=mod.__file__
        assert Path(mod.__file__).resolve().is_relative_to(source/'src')
    docs=subprocess.run([sys.executable,'-I','-X','utf8','-B','-c',
        'import sys;sys.path.insert(0,'+repr(str(source))+');from scripts.check_project import check_links;check_links()'],
        cwd=source,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (W/'results/doc-links.log').write_bytes(docs.stdout)
    xml=W/'results/python.xml';cases=list(ET.parse(xml).getroot().iter('testcase'))
    counts=dict(PASS=0,FAIL=0,ERROR=0,SKIP=0)
    for case in cases:
        status='ERROR' if case.find('error') is not None else 'FAIL' if case.find('failure') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS'
        counts[status]+=1
    inventory=read(W/'test-inventory.json');parsed=read(W/'python-results.json')
    assert len(cases)==inventory['node_count']==3045 and counts==parsed['counts']==dict(PASS=2972,FAIL=63,ERROR=10,SKIP=0)
    assert sha(xml)==parsed['junit_SHA256']
    groups=read(W/'diagnostics/failure-groups.json');assert sum(groups['counts'].values())==73
    rust=envelope(W/'rust_complete_if_stock_aborted-result.json');assert rust['tests_passed']
    rustlog=(W/'guard-rust_complete_if_stock_aborted/stdout.log').read_text(encoding='utf8')
    assert '19 passed; 0 failed; 0 ignored' in rustlog
    gui=read(W/'gui/result.json');assert gui['status']=='PASS_REAL_PACKET_GUI_RECOVERY'
    assert not gui['background_errors'] and not gui['foreign_cancellations']
    assert [x['time'] for x in gui['real_completed_packets']]==[1.,2.] and gui['compiled_native_calls']>0
    callback_owners={}
    for event in gui['callbacks']:
        key=(event['interpreter'],event['after_id'])
        if event['event']=='schedule':callback_owners[key]=event['owner']
        else:assert event['event']=='cancel' and callback_owners[key]==event['owner']
    assert all(not row['after'] for row in gui['destroy'] if row['status']=='CLOSED')
    for key,t in [('stopped',1.),('closed',2.)]:
        checkpoint=gui['checkpoints'][key];body=checkpoint['bodies'][0]
        assert checkpoint['time']==t
        assert max(abs(x-y) for x,y in zip(body['position'],[1+2*t,2-t,3+.5*t]))<=1e-12
    earlier=read(R/'docs/q2-gui-lifecycle-fix-404.json')
    for name in ('app.py','control_row.py'):
        assert fp['package_files'][name]==read(R/'.tools/qualification404-20261108/new-actual-environment.json')['package_files'][name]
    assert len(earlier['cases'])==18 and all(row['status']=='PASS' for row in earlier['cases'])
    warning=inspection.TWO_Q2_EXPERIMENTAL_WARNING
    assert '18/18 PASS' in warning and '0.244795' in warning and 'Release0.3.3 — NO-GO' in warning
    missing=[name for name in ('docs/q2-application-acceptance-402.md','docs/q2-gui-lifecycle-fix-404.md') if not (source/name).exists()]
    live_native_files=('test_native.py','test_numeric_native.py','test_native_collisions.py','test_native_forces.py',
        'test_rust_backend.py','test_rust_contacts.py','test_required_native.py','test_qualification383_native.py')
    live=[x for x in parsed['nodes'] if any(x['nodeid'].startswith('tests/'+name+'::') for name in live_native_files)]
    assert live and all(x['status']=='PASS' for x in live)
    out=dict(status='AUDIT_COMPLETE_WITH_CONFIRMED_TECHNICAL_NO_GO',candidate=p['candidate_commit'],
        source_profile_SHA256=p['source_fingerprint'],post_profile_SHA256=sha(W/'post-environment.json'),
        source_audit_SHA256=sha(W/'source-audit.json'),stock_tests=counts,inventory_nodes=3045,
        all_nodes_accounted=True,xfail_skip_waivers=False,compile_files=compiled_files,actual_imports=imports,
        document_links=dict(exit_code=docs.returncode,log_SHA256=sha(W/'results/doc-links.log')),
        missing_current_UI_reference_documents=missing,live_native_tests=dict(count=len(live),all_passed=True,files=live_native_files),
        rust_core_tests=19,fmt_core_native_passed=True,GUI_real_journey_passed=True,
        failures_remain_63_plus_10=True,full_suite_repeated=False,
        historical404technical_evidence='Code/dependency/profile equality plus current bounded realpacket journey; no automatic source-bound scientific receipt transfer.',
        source_verdict='NO-GO',application_D1='NO-GO_UNCHANGED',portable='NOT_BUILT_NO_GO',release='NO-GO')
    save(W/'final-audit.json',out)
    assert not git('status','--porcelain')
    print('AUDIT COMPLETE:3045/3045;63FAIL+10ERROR retained; source/native bytes unchanged; compilation/import/Rust/realGUI proof checked; overallNO-GO',flush=True)


if __name__=='__main__':main()
