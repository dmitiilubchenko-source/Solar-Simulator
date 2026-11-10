"""Read-only source/ABI/inventory audit; no scientific integrations."""
import ast,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[2];W=Path('C:/Users/Admin/Documents/Codex/Solar407-20261110');P=json.loads((W/'plan.json').read_bytes());S=Path(P['candidate_source']);sys.path.insert(0,str(S))
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(S),*args])
assert not git('status','--porcelain')
head=git('rev-parse','HEAD').decode().strip();tree=git('rev-parse','HEAD^{tree}').decode().strip()
assert git('merge-base',P['base'],head).decode().strip()==P['base']
paths=git('diff','--name-only',P['base'],head,'--','src','rust').decode().splitlines()
assert paths==['src/solar_simulator/control_row.py'],paths
name=paths[0];old=git('show',P['base']+':'+name);new=(S/name).read_bytes()
def protected(raw):
    t=ast.parse(raw);cls=next(x for x in t.body if isinstance(x,ast.ClassDef))
    cls.body=[x for x in cls.body if not isinstance(x,ast.FunctionDef) or x.name!='_layout']
    return ast.dump(t)
assert protected(old)==protected(new)
expected=old.replace(b'row_height+6; row_height',b'row_height+4; row_height').replace(b'y=y+3',b'y=y+2').replace(b'height=y+row_height+6',b'height=y+row_height+4')
assert new==expected,'Only the three declared vertical geometry constants may differ'
from solar_simulator.recipe import runtime_fingerprint
from scripts.native_audit import require_native
import solar_simulator,solar_native
assert Path(solar_simulator.__file__).resolve().is_relative_to(S/'src')
native=getattr(solar_native,'solar_native',solar_native);assert sha(Path(native.__file__).read_bytes())==P['native_SHA256'];require_native()
fp=runtime_fingerprint('rust');baseline=json.loads((W/'baseline-environment.json').read_bytes())
changed=[k for k in fp['package_files'] if fp['package_files'][k]!=baseline['package_files'][k]]
assert changed==['control_row.py'];a=dict(fp);b=dict(baseline);a.pop('package_files');b.pop('package_files');assert a==b
raw=(json.dumps(fp,indent=2)+'\n').encode();(W/'actual-environment-v2.json').write_bytes(raw)
for name,digest in P['inputs'].items():assert sha((R/name).read_bytes())==digest,name
oldreport=R/'docs/q2-release-source-acceptance-406.json';original=json.loads((W/'original73.json').read_bytes());assert sha(oldreport.read_bytes())==original['report_SHA256']
for name in git('ls-tree','-r','--name-only',P['base'],'--','src','rust').decode().splitlines():
    if name!=paths[0]:assert (S/name).read_bytes()==git('show',P['base']+':'+name),name
command=[sys.executable,'-X','utf8','-B','-m','pytest','--collect-only','-q','-p','no:cacheprovider','-p','scripts.native_audit']
out=subprocess.run(command,cwd=S,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(W/'collection-final-v2.log').write_bytes(out.stdout);assert out.returncode==0
nodes=[x.strip() for x in out.stdout.decode('utf8').splitlines() if x.startswith('tests/') and '::' in x]
oldnodes=json.loads((R/'.tools/acceptance406-20261109/test-inventory.json').read_bytes())['nodes']
assert len(nodes)==len(set(nodes)) and set(oldnodes)<=set(nodes) and len(oldnodes)==3045
inventory=dict(candidate=head,tree=tree,nodes=nodes,old3045_mapping={x:x for x in oldnodes},added=sorted(set(nodes)-set(oldnodes)),removed=[],selection='Collection only, full stock testpaths, no deselect/markers/skip waiver')
(W/'inventory-final-v2.json').write_text(json.dumps(inventory,indent=2)+'\n')
replay={}
for filename in ('targeted73-v2.xml','neighbors-final.xml','foreign-poll-fixed.xml'):
    for test in ET.parse(W/filename).iter('testcase'):
        node=test.attrib['classname'].replace('.','/')+'.py::'+test.attrib['name']
        status='ERROR' if test.find('error') is not None else 'FAIL' if test.find('failure') is not None else 'SKIP' if test.find('skipped') is not None else 'PASS'
        replay[node]=dict(status=status,receipt=filename,receipt_SHA256=sha((W/filename).read_bytes()),test_seconds=test.attrib.get('time'))
mapping=[dict(row,new=replay[row['nodeid']]) for row in original['nodes']]
assert len(mapping)==73 and all(x['new']['status']=='PASS' for x in mapping)
from scripts.project_inventory import check_inventory
from scripts.check_project import check_links
check_inventory(S);check_links()
commits=[]
for c in git('rev-list','--reverse',P['base']+'..'+head).decode().splitlines():
    diff=git('show','--format=fuller','--binary',c);folder=W/'commit-diffs';folder.mkdir(exist_ok=True);(folder/(c+'.patch')).write_bytes(diff)
    commits.append(dict(commit=c,subject=git('show','-s','--format=%s',c).decode().strip(),paths=git('diff-tree','--no-commit-id','--name-only','-r',c).decode().splitlines(),diff_SHA256=sha(diff)))
result=dict(status='TARGETED_GO_NOT_FULL_ACCEPTANCE',candidate=head,tree=tree,base=P['base'],source_fingerprint_SHA256=sha(raw),native_SHA256=P['native_SHA256'],actual_interpreter=sys.executable,prefix=sys.prefix,actual_import=solar_simulator.__file__,package_diff=changed,production_diff=paths,numerical_Rust_native_inputs_unchanged=True,other_controlrow_methods_AST_identical=True,old399_406_evidence_unchanged=True,original73=mapping,inventory_count=len(nodes),added_nodes=len(inventory['added']),inventory_SHA256=sha((W/'inventory-final-v2.json').read_bytes()),commits=commits,monitor='Original385 retained; optimized prototype NO-GO after real Windows race',source_scope='70 original cases PASS at phase metadata fixes; 66neighbor cases at032c36e supersede all3late blockers; final2pollcases at new frozen head verify ownership correction, tests-only delta. Unchanged numerical/replay implementation and inputs verified; final historical51 not reexecuted. Not a full-candidate acceptance or new scientific qualification.')
(W/'audit-final-v2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],candidate=head,tree=tree,source_fingerprint=result['source_fingerprint_SHA256'],old73='ALL_PASS_PHASED',nodes=len(nodes),added=len(inventory['added']))),flush=True)
