"""Fixed application402 executor. Existing GUI/runtime/reference, no new solver."""
import ast,json,sys,time,traceback
from pathlib import Path
from dataclasses import replace
from contextlib import contextmanager
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
from scripts.qualification401.qualify import activate,observed
W=R/'.tools/qualification402-20261108';PLAN=R/'scripts/qualification402/plan.json'
TOOLS=W/'tools-v2.json'
def read(p):return json.loads(Path(p).read_bytes())
def put(p,x):q.atomic_json(p,x)
def plan():return read(PLAN)
def setup():
 p=plan();m,identity,fp=activate('candidate')
 if identity['commit']!=p['candidate'] or identity['environment_LF_SHA256']!=p['fingerprint']:raise ValueError('402 exact source/environment mismatch')
 q.require_sha(Path(identity['compiled_native']),p['native_SHA256'])
 for name,digest in read(TOOLS)['files'].items():q.require_sha(R/name,digest)
 return p,m,identity,fp
def document(job):
 p=plan();d=json.loads(json.dumps(p['initial']))
 if job['kind']=='reference':return d
 level=next(x for x in p['levels'] if x['id']==job['level'])
 d['settings'].update(backend=job['backend'],rtol=level['rtol'],position_atol=level['position_atol'],velocity_atol=level['velocity_atol'])
 for name in ('rotations','initial_rotations'):
  for s in d[name]:s['quaternion_atol']*=level['spin_factor'];s['momentum_atol']*=level['spin_factor']
 return d
def represented(states):
 import numpy as np
 from scipy.spatial.transform import Rotation
 return dict(positions=np.array([[[b.position.x,b.position.y,b.position.z] for b in s.bodies] for s in states]),velocities=np.array([[[b.velocity.x,b.velocity.y,b.velocity.z] for b in s.bodies] for s in states]),quaternions=np.array([[r.quaternion for r in s.rotations] for s in states]),spins=np.array([[r.angular_momentum for r in s.rotations] for s in states]),orientation=np.array([[Rotation.from_quat(np.roll(r.quaternion,-1)).as_matrix() for r in s.rotations] for s in states]))
@contextmanager
def domain_observer(m):
 import numpy as np
 nb=m['nbody_rotation'];original=nb._corrections;row=dict(calls=0,min_distance_m=None,overlap_rejected=False)
 def call(positions,masses,sources,rotations,*a,**kw):
  delta=np.asarray(positions)[sources[1]]-np.asarray(positions)[sources[0]]
  pair=kw.get('pair_displacement')
  if pair is not None and set(sources)==set(pair[:2]):delta=pair[2]
  distance=float(np.linalg.norm(delta));row['calls']+=1
  row['min_distance_m']=distance if row['min_distance_m'] is None else min(row['min_distance_m'],distance)
  try:return original(positions,masses,sources,rotations,*a,**kw)
  except ValueError:row['overlap_rejected']=distance<=1900.;raise
 nb._corrections=call
 try:yield row
 finally:nb._corrections=original
def preflight():
 p,m,identity,fp=setup();root=Path(identity['source'])
 for path,digest in p['input_SHA256'].items():q.require_sha(R/path,digest)
 q.require_sha(root/'src/solar_simulator/data/two-q2-demo380.json',p['demo_SHA256'])
 old=read(R/'scripts/two-q2-380-plan.json')
 q.require_sha(R/'scripts/two-q2-380-plan.json','26eaaf67878e34bd292682b90e07b0df5e3ad9b096f8ee9d0f5a0cf6e9b94d68')
 q.require_sha(R/'.tools/qualification401-backup-20261108/Solar-Simulator-stage401-20261108.zip','c3f74ffa847eecc82bcfd2914151a607f3d65a176715bf30efabc6638e9a8b90')
 if old['cases'][0]['initial']!=p['initial'] or read(root/'src/solar_simulator/data/two-q2-demo380.json')!=p['initial']:raise ValueError('IC differ')
 state=m['storage'].from_document(p['initial']);before=m['storage'].to_document(state)
 from scripts import two_q2_reference380 as original,q2_reference397 as adapter
 def prefix(module):
  node=next(x for x in ast.parse(Path(module.__file__).read_bytes()).body if isinstance(x,ast.FunctionDef) and x.name=='reference');index=next(i for i,x in enumerate(node.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='solution' for t in x.targets));return [ast.dump(x,include_attributes=False) for x in node.body[:index+1]]
 assert prefix(original)==prefix(adapter)
 assert original.solve_ivp is adapter.solve_ivp
 import numpy as np
 # Technical controls use validators/RHS only, never an integrated trajectory.
 damaged=[]
 for name in ('duplicate','mass','q','I','mixing','contact','overlap','nan','bool'):
  d=json.loads(json.dumps(before))
  if name=='duplicate':d['rotations'][1]['body']='A'
  if name=='mass':d['rotations'][1]['figure']['mass']*=.5
  if name=='q':d['rotations'][1]['quaternion']=[0.,0.,0.,0.]
  if name=='I':d['rotations'][1]['figure']['moments'][0]=-1.
  if name=='mixing':d['settings']['physics']='eih-1pn'
  if name=='contact':d['bodies'][0]['radius']=1.
  if name=='overlap':d['bodies'][1]['position']=[d['bodies'][0]['position'][0]+1899.,*d['bodies'][0]['position'][1:]]
  if name=='nan':d['bodies'][0]['mass']=float('nan')
  if name=='bool':d['settings']['rtol']=True
  try:m['storage'].from_document(d)
  except (ValueError,TypeError):damaged.append(name)
  else:raise AssertionError('Malformed input accepted:'+name)
 # Call the genuine nested RHS at an inadmissible stage; no solve_ivp executed.
 nb=m['nbody_rotation'];solve=nb.solve_ivp;seen=[]
 def stage(fun,span,y0,**kw):
  y=y0.copy();y[3:6]=[1899.,0.,0.] # relative-pair B position is encoded rho_AB
  try:fun(0.,y)
  except ValueError as error:seen.append(str(error));raise
  raise AssertionError('RHS did not reject overlapping figures')
 nb.solve_ivp=stage
 try:
  try:m['experiment'].advance(state,1)
  except ValueError:pass
  else:raise AssertionError('Failed packet committed')
 finally:nb.solve_ivp=solve
 assert seen and m['storage'].to_document(state)==before
 # Existing independent potential-gradient/reaction check, two-body case only.
 import runpy
 tests=runpy.run_path(str(R/'tests/test_two_q2.py'))
 tests['test_field_from_independent_position_and_attitude_gradients'](False)
 from scripts.qualification402.metrics import geometry_controls
 controls=geometry_controls()
 unit=runpy.run_path(str(R/'tests/test_q2_application402.py'))
 for name,fn in unit.items():
  if name.startswith('test_'):fn()
 put(W/'preflight.json',dict(status='PASS',source=identity,actual_environment=fp,malformed_rejected=damaged,RHS_overlap_rejected=seen,last_complete_input_unchanged=True,reference_AST_prefix_exact=True,reference_force_callbacks='independent scalar-I, no production fields',gradient_reaction='existing380 test False passed',geometry_controls=controls,integrated_trajectories=0))
 print('PASS preflight source/env/IC/referenceAST/validation/RHSdomain/gradient/observer; no scientific integrations',flush=True)
def gui_run(job,directory,m,doc):
 import tkinter as tk
 from unittest.mock import patch
 from solar_simulator.app import Laboratory
 storage=m['storage'];root=tk.Tk();app=Laboratory(root);states=[];errors=[];record=app._record
 def capture():
  value=record()
  if len(app.experiment.rotations)==2:
   state=app.experiment
   if not states or state.time!=states[-1].time:
    states.append(state);put(directory/('frame-%03d.json'%int(state.time)),storage.to_document(state))
    if state.time==100.:storage.save(state,directory/'checkpoint-100.json')
  return value
 app._record=capture
 def fail(*a,**kw):errors.append(str(a));root.quit()
 def done():
  if errors or (states and states[-1].time>=200. and app.future is None and not app.running):root.quit()
  else:root.after(10,done)
 try:
  with patch('solar_simulator.app.messagebox.showerror',side_effect=fail):
   app.backend.set(job['backend'])
   next(x for x in app.actions if isinstance(x,tk.ttk.Button) and str(x.cget('text')).startswith('Две Q2')).invoke()
   assert storage.to_document(app.experiment)==doc and app.batch.get()=='1'
   app.target.set('200');app.target_button.invoke();assert app.running and app.target_time==200.
   root.after(10,done);root.after(15000,lambda:fail('GUI wall watchdog'));root.mainloop()
   if errors:raise RuntimeError('GUI error:'+repr(errors))
   assert [s.time for s in states]==[0.,50.,100.,150.,200.]
   final=storage.to_document(app.experiment);saved=directory/'gui-saved.json'
   with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(saved)):
    next(x for x in app.actions if isinstance(x,tk.ttk.Button) and str(x.cget('text'))=='Сохранить JSON').invoke()
   with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(saved)):
    next(x for x in app.actions if isinstance(x,tk.ttk.Button) and str(x.cget('text'))=='Открыть JSON').invoke()
   assert storage.to_document(app.experiment)==final and storage.to_document(storage.load(saved))==final
   return states,dict(actual_Tk_widgets=True,target_button_invoked=True,unchanged_poll_and_executor=True,packet_steps=1,saved_loaded_exact=True,errors=errors)
 finally:app.close()
def execute_job(job,m,identity):
 import numpy as np
 directory=job_directory(job['id']);directory.mkdir(parents=True,exist_ok=False);doc=document(job);epochs=job['epochs'];storage=m['storage'];cpu=time.process_time();wall=time.perf_counter()
 binding=dict(job=job,source=identity,IC_SHA256=q.sha(R/'src/solar_simulator/data/two-q2-demo380.json'),initial_SHA256=__import__('hashlib').sha256(q.canonical(doc)).hexdigest(),plan_SHA256=q.sha(PLAN),tools_SHA256=q.sha(TOOLS))
 put(directory/'started.json',q.envelope(binding));put(directory/'input.json',doc)
 try:
  ui=None
  if job['kind']=='reference':
   from scripts import q2_reference397 as ref
   original=ref.solve_ivp;raw={}
   def recording(*a,**kw):
    result=original(*a,**kw);raw.update(scaled_y=result.y.tolist(),t=result.t.tolist(),rtol=kw['rtol'],atol=kw['atol'],max_step=kw['max_step'],RHS=int(result.nfev));return result
   ref.solve_ivp=recording
   try:result=ref.reference(doc,epochs,job['rtol'])
   finally:ref.solve_ivp=original
   arrays={k:v.tolist() for k,v in result.items() if k!='RHS'};documents=[];counts=dict(solver_calls=1,RHS=result['RHS'],nfev=result['RHS'],native_calls=0);domain=None
   scales=[float(np.linalg.norm(r['angular_momentum'])) for r in doc['rotations']]
   y=np.array(raw['scaled_y']);raw['body_momentum']=[[list(y[12+12*k+9:12+12*k+12,i]*scales[k]) for k in range(2)] for i in range(5)]
   raw['spin_scales']=scales;put(directory/'raw-reference.json',raw)
  else:
   state=storage.from_document(doc)
   with observed(m) as counts,domain_observer(m) as domain:
    if job['kind']=='suffix':
     parent=W/'jobs'/('main__'+job['backend']+'__gui__cold')
     q.read_envelope(parent/'complete.json');checkpoint=parent/'checkpoint-100.json';state=storage.load(checkpoint);put(directory/'checkpoint-source.json',dict(path=str(checkpoint),sha256=q.sha(checkpoint)));states=[state]
     for t in epochs[1:]:state=m['experiment'].advance(state,1);states.append(state);put(directory/('frame-%03d.json'%int(t)),storage.to_document(state))
    elif job.get('GUI'):
     states,ui=gui_run(job,directory,m,doc)
    elif job['recipe']=='cold':
     states=[state];put(directory/'frame-000.json',doc)
     for t in epochs[1:]:state=m['experiment'].advance(state,1);states.append(state);put(directory/('frame-%03d.json'%int(t)),storage.to_document(state))
    else:
     s=state.settings;samples=m['nbody_rotation'].integrate(state.bodies,state.rotations,epochs,rtol=s.rtol,position_atol=s.position_atol,velocity_atol=s.velocity_atol,relative_pair=s.relative_pair,backend=s.backend)
     states=[replace(state,bodies=tuple(b),rotations=rot,time=t) for t,(b,rot) in zip(epochs,samples)]
   arrays={k:v.tolist() for k,v in represented(states).items()};documents=[doc if job['recipe']=='continuous' and i==0 else storage.to_document(s) for i,s in enumerate(states)]
   # Continuous t=0 raw readout may differ by frame roundtrip; retain true input.
   if job['recipe']=='continuous':documents[0]=doc
   assert counts['solver_calls']==(1 if job['recipe']=='continuous' else len(epochs)-1)
   assert counts['RHS']==counts['nfev'] and counts['native_calls']==(counts['RHS'] if job['backend']=='rust' else 0)
   if job['recipe']!='continuous':
    for d in documents:assert q.canonical(storage.to_document(storage.from_document(d)))==q.canonical(d)
  result=dict(binding=binding,job=job,epochs=epochs,initial=doc,arrays=arrays,documents=documents,counters=counts,domain=domain,GUI=ui,CPU_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
  q.require_arrays(arrays,doc,epochs,runtime=job['kind']!='reference')
  put(directory/'result.json',result)
  files={x.name:dict(size=x.stat().st_size,sha256=q.sha(x)) for x in directory.iterdir() if x.is_file()}
  put(directory/'complete.json',q.envelope(dict(binding=binding,files=files,frames=len(epochs))))
  print('COMPLETE',job['id'],round(result['CPU_seconds'],6),'CPU',flush=True)
 except BaseException as error:
  put(directory/'failure.json',dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc(),binding=binding));raise
def series():
 p,m,identity,fp=setup();assert read(W/'preflight.json')['status']=='PASS'
 for job in p['jobs']:execute_job(job,m,identity)
 assert m['recipe'].runtime_fingerprint('rust')==fp
 put(W/'series-complete.json',dict(jobs=[x['id'] for x in p['jobs']],source=identity,environment_unchanged=True))
def job_directory(identifier):
 return W/('attempt2-jobs' if identifier=='main__python__gui__continuous' else 'jobs')/identifier
def series_remaining():
 p,m,identity,fp=setup();oldtools=read(W/'tools.json')
 for name,digest in oldtools['files'].items():
  path=W/'executed-v1'/Path(name).name if name in ('scripts/qualification402/execute.py','scripts/qualification402/audit.py','.tools/qualification402-20261108/guard.py') else R/name
  q.require_sha(path,digest)
 done=W/'jobs/main__python__gui__cold';receipt=q.read_envelope(done/'complete.json');row=read(done/'result.json');job=p['jobs'][0]
 assert job['id']=='main__python__gui__cold' and row['job']==job and row['binding']==receipt['binding'] and row['binding']['source']==identity and row['initial']==document(job)
 assert row['binding']['plan_SHA256']==q.sha(PLAN) and row['binding']['tools_SHA256']==q.sha(W/'tools.json')
 for name,meta in receipt['files'].items():assert (done/name).stat().st_size==meta['size'] and q.sha(done/name)==meta['sha256']
 partial=W/'jobs/main__python__gui__continuous';assert not (partial/'complete.json').exists()
 failure=read(partial/'failure.json');assert failure['type']=='ValueError' and failure['binding']['job']['id']=='main__python__gui__continuous'
 assert failure['binding']['source']==identity and failure['binding']['plan_SHA256']==q.sha(PLAN)
 # Isolated regression of the reporting expression, using the saved physical input.
 from types import SimpleNamespace
 fake=SimpleNamespace(time=0.)
 class Storage:
  @staticmethod
  def to_document(s):raise AssertionError('Continuous t0 readout must not be serialized')
 assert [document(job) if i==0 else Storage.to_document(s) for i,s in enumerate([fake])]==[document(job)]
 put(W/'recovery-decision.json',dict(status='AUTHENTICATED_ONE_COMPLETED_JOB_REUSED_ONLY',completed_reused=[job['id']],failed_partial='main__python__gui__continuous',partial_raw='integration returned, but raw output not committed before serialization error; not recoverable; not labelled completed',new_attempt_directory=str(job_directory('main__python__gui__continuous')),old_failed_files={x.name:q.sha(x) for x in partial.iterdir() if x.is_file()},old_completed_receipt_SHA256=q.sha(done/'complete.json'),previous_total_CPU_seconds=10.625,policy='Never repeat completed jobs; retry only unconfirmed failed job with same frozen settings and independent full continuous solve, no cold continuation.22logicalIDs unchanged;23integrationattempts if completion succeeds.',regression='continuous0 input document selected before serializer; no new integration in regression'))
 for job in p['jobs'][1:]:execute_job(job,m,identity)
 assert m['recipe'].runtime_fingerprint('rust')==fp
 put(W/'series-complete.json',dict(jobs=[x['id'] for x in p['jobs']],source=identity,environment_unchanged=True,reused_completed=1,new_completed=21,failed_uncommitted_attempts=1))
if __name__=='__main__':
 {'preflight':preflight,'series':series,'remaining':series_remaining}[sys.argv[1]]()
