"""403 actual source/AST/environment and non-evolving UI assertions."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
from scripts.q2_text_delta403 import compare
W=R/'.tools/qualification403-20261108';PLAN=R/'scripts/qualification403/plan.json'
def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args])
def main():
 p=json.loads(PLAN.read_bytes());root=Path(p['new_source']);old=Path(p['original_source']);expected=p['new_commit']
 assert git(root,'rev-parse','HEAD').decode().strip()==expected and not git(root,'status','--porcelain')
 changed=git(root,'diff','--name-only',p['original_commit'],expected).decode().splitlines();assert changed==['src/solar_simulator/inspection.py']
 path=changed[0];before=git(root,'show',p['original_commit']+':'+path);after=git(root,'show',expected+':'+path)
 assert (root/path).read_bytes()==after and (old/path).read_bytes()==before
 delta=compare(before,after)
 def inventory(commit):
  rows={}
  for row in git(root,'ls-tree','-r','-z',commit).split(b'\0'):
   if row:
    meta,name=row.split(b'\t',1);rows[name.decode()]=meta.decode()
  return rows
 a,b=inventory(p['original_commit']),inventory(expected);assert a.keys()==b.keys();assert [k for k in a if a[k]!=b[k]]==[path]
 sys.path.insert(0,str(root/'src'))
 import solar_simulator,numpy,scipy,solar_native,tkinter as tk
 from solar_simulator import recipe,experiment,storage,inspection,inspection_view,application_profiles,accuracy,nbody_rotation,app as module
 from scripts.q2_source_adapter396 import require_origins
 require_origins(solar_simulator.__file__,[numpy.__file__,scipy.__file__,solar_native.__file__],root,sys.prefix,Path(p['interpreter']).parents[1])
 fp=recipe.runtime_fingerprint('rust');baseline=json.loads((R/'.tools/qualification401-20261108/profiles/candidate-actual-emission.json').read_bytes());q.require_sha(R/'.tools/qualification401-20261108/profiles/candidate-actual-emission.json',p['original_fingerprint'])
 assert {k:v for k,v in fp.items() if k!='package_files'}=={k:v for k,v in baseline.items() if k!='package_files'}
 assert {k for k in fp['package_files'].keys()|baseline['package_files'].keys() if fp['package_files'].get(k)!=baseline['package_files'].get(k)}=={'inspection.py'}
 compiled=getattr(solar_native,'solar_native',solar_native).__file__;q.require_sha(compiled,p['native_SHA256'])
 raw=(json.dumps(fp,indent=2)+'\n').encode();digest=hashlib.sha256(raw).hexdigest();assert digest!=p['original_fingerprint']
 with (W/'new-actual-environment.json').open('xb') as stream:stream.write(raw)
 calls=[]
 def forbidden(*a,**kw):calls.append(True);raise AssertionError('No evolution for403warning')
 variants=[];reports={};root_ui=tk.Tk();root_ui.withdraw();lab=None;view=None
 from copy import deepcopy
 try:
  with patch.object(module,'advance',forbidden),patch.object(experiment,'advance',forbidden),patch.object(nbody_rotation,'integrate',forbidden),patch.object(nbody_rotation,'solve_ivp',forbidden),patch.object(accuracy,'evolve_accurate',forbidden),patch.object(solar_native,'point_acceleration',forbidden):
   states=[('zero',application_profiles.scenario('sun-earth')),('one',application_profiles.lunar_rotation()),('two',application_profiles.two_q2_demo())]
   d=deepcopy(storage.to_document(states[-1][1]));renamed={'A':'Custom','B':'Other'}
   for field in ('bodies','initial'):
    for item in d[field]:item['name']=renamed[item['name']]
    d[field][0]['position'][0]+=123.
   for field in ('rotations','initial_rotations'):
    for item in d[field]:item['body']=renamed[item['body']]
   d['settings']['relative_pair']=['Custom','Other'];file=W/'arbitrary-two.json';q.atomic_json(file,d);custom=storage.load(file);states.append(('arbitrary_loaded_two',custom));file_hash=q.sha(file)
   lab=module.Laboratory(root_ui,states[0][1]);warning=inspection.TWO_Q2_EXPERIMENTAL_WARNING
   for name,state in states:
    initial=storage.to_document(state);numeric=inspection.cli.report(state);reported=inspection.report(state);lab._set_experiment(state)
    expected_two=len(state.rotations)==2
    assert bool(inspection.experimental_q2_warning(state.rotations))==expected_two
    assert (warning in lab.model_info.get())==expected_two
    payload=inspection_view.prepare_inspection(initial,lambda:False,lambda *a:None)
    assert (warning in inspection_view.rotation_text(payload))==expected_two
    assert reported['numerical_reliability']['qualification']['current_trajectory_certified'] is False
    assert {k:v for k,v in reported.items() if k!='numerical_reliability'}==numeric
    assert storage.to_document(state)==initial
    if expected_two:
     view=lab._show_inspection();view.future.result(timeout=5);view._poll();assert all(warning in field.get('1.0','end') for field in view.texts);view.close();view=None
    variants.append(dict(name=name,figures=len(state.rotations),warning_present=expected_two,automatic_certification=False,q_S_settings_unchanged=True,numerical_diagnostics_unchanged=True));reports[name]=numeric
   assert q.sha(file)==file_hash and not calls
   for token in p['required_text_tokens']:assert token in warning,token
   assert 'владельцем не утверждены' not in warning and 'ещё не выполнена' not in warning
 finally:
  if view is not None:view.close()
  if lab is not None:lab.close()
  else:root_ui.destroy()
 assert recipe.runtime_fingerprint('rust')==fp
 q.atomic_json(W/'presentation.json',dict(status='PASS_TEXT_AND_NON_EVOLVING_UI',source_commit=expected,original_commit=p['original_commit'],actual_import=solar_simulator.__file__,dependency_prefix=sys.prefix,native=compiled,native_SHA256=p['native_SHA256'],new_actual_source_fingerprint=digest,original_fingerprint=p['original_fingerprint'],fingerprint_kind='actual source, not wheel/portable',delta=delta,Git_tree_inventory_old=a,Git_tree_inventory_new=b,variants=variants,numerical_reports=reports,evolution_calls=len(calls),candidate_clean=not bool(git(root,'status','--porcelain')),scope='Exact computation/callback/storage/native identity; historical399/401/402 applicability only in original fixed scope, no automatic source-bound gate transfer'))
 print('PASS one-literal fullGit/AST/bytes;4UIstates no evolution; actual fingerprint '+digest,flush=True)
if __name__=='__main__':main()
