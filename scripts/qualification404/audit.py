"""Offline raw/source audit404. No solver or acceptance-case reexecution."""
import json,hashlib,subprocess,sys,importlib.metadata
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
from scripts.q2_lifecycle_delta404 import compare
W=R/'.tools/qualification404-20261108';PLAN=R/'scripts/qualification404/plan.json'
def read(path):return json.loads(Path(path).read_bytes())
def main():
 p=read(PLAN);binding=read(W/'candidate.json');root=Path(p['new_source']);base=Path(p['base_source'])
 def git(*a):return subprocess.check_output(['git','-C',str(root),*a])
 assert git('rev-parse','HEAD').decode().strip()==binding['commit'] and not git('status','--porcelain')
 assert git('rev-parse','HEAD^').decode().strip()==p['base_commit']
 paths=git('diff','--name-only',p['base_commit'],binding['commit']).decode().splitlines();assert paths==p['allowed_production_paths']
 old=[git('show',p['base_commit']+':'+x) for x in paths];new=[git('show',binding['commit']+':'+x) for x in paths]
 assert all((root/name).read_bytes()==raw for name,raw in zip(paths,new))
 delta=compare(old[0],new[0],old[1],new[1])
 def inventory(commit):return {name.decode():meta.decode() for row in git('ls-tree','-r','-z',commit).split(b'\0') if row for meta,name in [row.split(b'\t',1)]}
 a,b=inventory(p['base_commit']),inventory(binding['commit']);assert a.keys()==b.keys() and sorted(x for x in a if a[x]!=b[x])==paths
 # Strongly bind the input and recovery oracle to historical402/403 receipts.
 for name,digest in p['input_SHA256'].items():q.require_sha(R/name,digest)
 evidence402=read(R/'docs/q2-application-acceptance-402.json');evidence403=read(R/'docs/q2-ui-lifecycle-403.json')
 info=next(x for x in evidence402['jobs'] if x['job']['id']=='main__python__gui__cold');prior=R/'.tools/qualification402-20261108/jobs/main__python__gui__cold';q.require_sha(prior/'complete.json',info['complete_SHA256']);manifest=q.read_envelope(prior/'complete.json');q.require_sha(prior/'frame-100.json',manifest['files']['frame-100.json']['sha256']);saved=read(prior/'frame-100.json')
 prior403=R/'.tools/qualification403-20261108/lifecycle/active_close_recovery';q.require_sha(prior403/'result.json',evidence403['independent_audit']['raw_hashes']['active_close_recovery']['result']);oldrow=read(prior403/'result.json');expected_recovery_SHA256=oldrow['snapshots'][0]['recovery']['sha256'];q.require_sha(prior403/'recovery-original.json',expected_recovery_SHA256)
 results=[];before={str(f):q.sha(f) for f in (W/'cases').rglob('*') if f.is_file()}
 assert {x.name for x in (W/'cases').iterdir()}==set(p['post_cases'])
 for name in p['post_cases']:
  d=W/'cases'/name;complete=q.read_envelope(d/'complete.json');row=read(d/'result.json')
  assert complete['source']==row['source']==binding and complete['case']==name==row['id'] and complete['result_SHA256']==q.sha(d/'result.json')
  assert row['plan_SHA256']==q.sha(PLAN) and row['tools_SHA256']==q.sha(W/'tools-v2.json') and row['status']=='PASS' and not row['failure'] and not row['errors'] and not row['foreign_cancellations'] and row['evolution_calls']==0
  for file,meta in complete['files'].items():assert (d/file).stat().st_size==meta['size'] and q.sha(d/file)==meta['sha256']
  owners={}
  for event in row['callbacks']:
   key=(event['interpreter'],event['after_id'])
   if event['event']=='schedule':owners[key]=event['owner']
   else:assert event['event']=='cancel' and owners[key]==event['owner'],'Wrong-owner cancellation'
  for item in row['destroy']:
   if item['status']=='CLOSED':assert not item['after']
   else:assert name=='canvas_contract_and_foreign_owner' and item['status']=='REJECTED_BEFORE_DESTROY' and item['closed'] is False
  recovered=[]
  for file in d.glob('*recovery.json'):
   assert read(file)==saved and q.sha(file)==expected_recovery_SHA256;recovered.append(dict(file=file.name,sha256=q.sha(file)))
  if name=='user_save_load':assert read(d/'user.json')==saved
  results.append(dict(id=name,status='PASS',bgerrors=0,registered=[x for x in row['callbacks'] if x['event']=='schedule'],cancelled=[x for x in row['callbacks'] if x['event']=='cancel'],destroy=row['destroy'],result=row['result'],UI_messages=row['UI_messages'],recovery=recovered,complete_SHA256=q.sha(d/'complete.json')))
 assert before=={str(f):q.sha(f) for f in (W/'cases').rglob('*') if f.is_file()}
 # Fresh actual fingerprint belongs to the new source, not a copied old receipt.
 sys.path.insert(0,str(root/'src'))
 import solar_simulator,numpy,scipy,solar_native
 from solar_simulator.recipe import runtime_fingerprint
 from scripts.q2_source_adapter396 import require_origins
 require_origins(solar_simulator.__file__,[numpy.__file__,scipy.__file__,solar_native.__file__],root,sys.prefix,Path(p['interpreter']).parents[1])
 q.require_sha(getattr(solar_native,'solar_native',solar_native).__file__,p['native_SHA256'])
 fp=runtime_fingerprint('rust');original=read(W/'base-actual-environment.json');q.require_sha(W/'base-actual-environment.json',p['base_fingerprint'])
 assert {k:v for k,v in fp.items() if k!='package_files'}=={k:v for k,v in original.items() if k!='package_files'}
 assert {k for k in fp['package_files'].keys()|original['package_files'].keys() if fp['package_files'].get(k)!=original['package_files'].get(k)}=={'app.py','control_row.py'}
 raw=(json.dumps(fp,indent=2)+'\n').encode();digest=hashlib.sha256(raw).hexdigest();assert digest!=p['base_fingerprint']
 with (W/'new-actual-environment.json').open('xb') as stream:stream.write(raw)
 backend=Path(importlib.metadata.distribution('matplotlib').locate_file('matplotlib/backends/_backend_tk.py'))
 q.atomic_json(W/'audit.json',dict(status='PASS_RAW_SOURCE_AND_CALLBACK_AUDIT',source=binding,source_delta=delta,full_Git_inventory_before=a,full_Git_inventory_after=b,cases=results,actual_source_fingerprint=digest,base_fingerprint=p['base_fingerprint'],actual_import=solar_simulator.__file__,dependency_prefix=sys.prefix,native_SHA256=p['native_SHA256'],Matplotlib=importlib.metadata.version('matplotlib'),backend_source=str(backend),backend_SHA256=q.sha(backend),expected_recovery_SHA256=expected_recovery_SHA256,legacy_warning_literal_unchanged=True,old_scientific_evidence_unchanged=True,zero_orbits=True,interpretation='Lifecycle behavior changed; physical/dispatch/recovery bodies protected. Historical399/401/402 only in original fixedscope, no oldreceipt automatically accepted under new source fingerprint.'))
 print('PASS independent18rawcases/ownership/recoverySHA/GitAST/physicalsource; newfingerprint '+digest,flush=True)
if __name__=='__main__':main()
