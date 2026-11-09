"""Independent offline cross-check of the saved text, source and event evidence."""
import ast
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q


def main():
    W=R/'.tools/qualification405-20261109'
    plan=json.loads((R/'scripts/qualification405/plan.json').read_bytes())
    for name,digest in plan['input_SHA256'].items():q.require_sha(R/name,digest)
    check=json.loads((W/'checks.json').read_bytes());root=Path(plan['candidate_source']);base=Path(plan['base_source'])
    watched=[p for p in W.rglob('*') if p.is_file() and p.suffix in ('.json','.xml','.log')]
    before={str(p):q.sha(p) for p in watched}
    git=lambda *a:subprocess.check_output(['git','-C',str(root),*a])
    assert git('diff','--name-only',plan['base_commit'],plan['candidate_commit']).decode().splitlines()==['src/solar_simulator/inspection.py']
    assert not git('status','--porcelain')
    # Parse independently of the presentation whitelist, then neutralize exactly
    # the one expected constant. Every other AST node must match.
    trees=[ast.parse((path/'src/solar_simulator/inspection.py').read_bytes()) for path in (base,root)]
    values=[]
    for tree in trees:
        nodes=[x for x in tree.body if isinstance(x,ast.Assign) and len(x.targets)==1
               and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='TWO_Q2_EXPERIMENTAL_WARNING']
        assert len(nodes)==1 and isinstance(nodes[0].value,ast.Constant)
        values.append(nodes[0].value.value);nodes[0].value=ast.Constant(value='audited405')
    assert values[1]==values[0].replace(plan['old_sentence'],plan['new_sentence'])
    assert ast.dump(trees[0],include_attributes=False)==ast.dump(trees[1],include_attributes=False)
    for name,digest in check['source']['working_SHA256_after'].items():q.require_sha(root/name,digest)
    for name,digest in check['source']['working_SHA256_before'].items():q.require_sha(base/name,digest)
    profile=W/'new-actual-environment.json';assert q.sha(profile)==check['actual_source_fingerprint']!=plan['base_fingerprint']
    fp=json.loads(profile.read_bytes());oldfp=json.loads((R/'.tools/qualification404-20261108/new-actual-environment.json').read_bytes())
    assert {k:v for k,v in fp.items() if k!='package_files'}=={k:v for k,v in oldfp.items() if k!='package_files'}
    assert {k for k in fp['package_files'].keys()|oldfp['package_files'].keys() if fp['package_files'].get(k)!=oldfp['package_files'].get(k)}=={'inspection.py'}
    assert check['orbits']==check['evolution_calls']==0 and not check['background_errors']
    owners={}
    for event in check['callbacks']:
        key=(event['interpreter'],event['after_id'])
        if event['event']=='schedule':owners[key]=event['owner']
        else:assert event['event']=='cancel' and owners[key]==event['owner']
    assert check['destroy'] and all(not x['after'] for x in check['destroy'])
    variants=[]
    for name in ('zero','one','two','arbitrary_loaded_two'):
        row=json.loads((W/(name+'-verified.json')).read_bytes());v=row['variant']
        assert v['id']==name and v['warning_present']==(v['figures']==2)
        assert not v['current_trajectory_certified'] and v['global_error_bound'] is None
        assert row['source_commit']==plan['candidate_commit'];variants.append(v)
    q.require_sha(W/'arbitrary-two.json',check['checkpoint_SHA256'])
    tests=ET.parse(W/'scope-tests.xml').getroot().find('testsuite').attrib
    assert tests['tests']=='13' and tests['failures']==tests['errors']==tests['skipped']=='0'
    prior=json.loads((R/'docs/q2-gui-lifecycle-fix-404.json').read_bytes())
    assert len(prior['cases'])==18 and all(x['status']=='PASS' and x['bgerrors']==0 for x in prior['cases'])
    assert len(prior['baseline_error_commands'])==10 and prior['post_exact_reproducer']['background_errors']==0
    for row in prior['cases']:
        complete=R/'.tools/qualification404-20261108/cases'/row['id']/'complete.json'
        q.require_sha(complete,row['complete_SHA256']);data=q.read_envelope(complete)
        for name,meta in data['files'].items():q.require_sha(complete.parent/name,meta['sha256'])
    assert before=={str(p):q.sha(p) for p in watched}
    q.atomic_json(W/'final-audit.json',dict(status='PASS_INDEPENDENT_TEXT_RAW_SOURCE_AUDIT',candidate=plan['candidate_commit'],
        actual_source_fingerprint=q.sha(profile),checks_SHA256=q.sha(W/'checks.json'),source_audit_SHA256=q.sha(W/'source-audit.json'),
        variants=variants,scope_tests=tests,prior404_cases=18,prior404_errors_before=10,prior404_errors_after=0,
        callbacks_checked=len(check['callbacks']),all_inputs_unchanged=True,science_receipt_transfer=False,
        meaning='Delta-only technical text qualification, not a new orbit or universal physical/numerical certification.'))
    print('PASS independent AST/file SHA/actual profile/raw callbacks/4snapshots/13tests/404historicalreceipts; no input mutation',flush=True)


if __name__=='__main__':main()
