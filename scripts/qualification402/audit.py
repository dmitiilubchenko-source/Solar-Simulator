"""Read-only402 auditor: raw bindings, independent arithmetic, separate verdicts."""
import json,sys,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
from scripts.qualification402.execute import W,PLAN,TOOLS,setup,document,represented,job_directory
from scripts.qualification402 import metrics
def read(p):return json.loads(Path(p).read_bytes())
def main():
 import numpy as np
 from decimal import Decimal,localcontext
 from scripts.q2_frame_observer393 import invariants as decimal_invariants
 # Read-only auditor has its own frozen tool revision; runtime receipts retain v1/v2.
 from scripts.qualification401.qualify import activate
 p=read(PLAN);m,identity,fp=activate('candidate');results={}
 assert identity['commit']==p['candidate'] and identity['environment_LF_SHA256']==p['fingerprint']
 for name,digest in read(W/'tools-v4.json')['files'].items():q.require_sha(R/name,digest)
 def snapshot():return {str(x):q.sha(x) for base in ('jobs','attempt2-jobs') for x in (W/base).rglob('*') if x.is_file()}
 before=snapshot()
 assert {x.name for x in (W/'jobs').iterdir()}=={x['id'] for x in p['jobs']}
 persistence=[];invariants=[];observer=[];repeat=[];domain=[]
 for job in p['jobs']:
  directory=job_directory(job['id']);receipt=q.read_envelope(directory/'complete.json');binding=q.read_envelope(directory/'started.json');r=read(directory/'result.json');results[job['id']]=r
  assert receipt['binding']==binding==r['binding'] and binding['job']==job and binding['source']==identity
  assert binding['plan_SHA256']==q.sha(PLAN) and binding['tools_SHA256']==q.sha(W/('tools.json' if job['id']=='main__python__gui__cold' else 'tools-v2.json'))
  doc=document(job);assert doc==r['initial']==read(directory/'input.json')
  assert binding['initial_SHA256']==hashlib.sha256(q.canonical(doc)).hexdigest()
  assert receipt['frames']==len(job['epochs']) and r['epochs']==job['epochs']
  assert set(x.name for x in directory.iterdir())==set(receipt['files'])|{'complete.json'}
  for name,meta in receipt['files'].items():assert (directory/name).stat().st_size==meta['size'] and q.sha(directory/name)==meta['sha256']
  a=r['arrays'];q.require_arrays(a,doc,job['epochs'],runtime=job['kind']!='reference')
  counts=r['counters'];assert counts['RHS']==counts['nfev'] and counts['solver_calls']==(1 if job['kind']=='reference' or job['recipe']=='continuous' else len(job['epochs'])-1)
  assert counts['native_calls']==(counts['RHS'] if job.get('backend')=='rust' else 0)
  if job['kind']=='reference':
   raw=read(directory/'raw-reference.json');assert raw['rtol']==job['rtol'] and raw['atol']==job['rtol']*.01 and raw['max_step']==50. and raw['t']==job['epochs']
   y=np.array(raw['scaled_y']);assert y.shape==(36,5)
   for t in range(5):
    for k in range(2):
     matrix=y[12+12*k:12+12*k+9,t].reshape(3,3)
     assert matrix.tobytes()==np.array(a['orientation'][t][k]).tobytes()
     Pi=y[12+12*k+9:12+12*k+12,t]*raw['spin_scales'][k]
     assert np.array_equal(Pi,raw['body_momentum'][t][k])
     # Keep the exact original397 association; R@(Pi_scaled*scale) is different arithmetic.
     source_expression=(matrix@y[12+12*k+9:12+12*k+12,t])*raw['spin_scales'][k]
     assert np.array_equal(source_expression,a['spins'][t][k])
   continue
  assert counts['RHS']>0 and r['domain']['min_distance_m']>1900 and not r['domain']['overlap_rejected']
  domain.append(dict(job=job['id'],**r['domain']))
  snapshots=[]
  for i,(t,d) in enumerate(zip(job['epochs'],r['documents'])):
   assert d['time']==t and d['settings']==doc['settings'] and d['initial']==doc['initial'] and d['initial_rotations']==doc['initial_rotations']
   state=m['storage'].from_document(d);assert q.canonical(m['storage'].to_document(state))==q.canonical(d);snapshots.append(state)
  derived=represented(snapshots)
  for key in ('positions','velocities','quaternions','spins','orientation'):
   start=1 if job['recipe']=='continuous' else 0
   assert derived[key][start:].tobytes()==np.asarray(a[key],dtype='float64')[start:].tobytes()
  if job.get('GUI'):assert r['GUI']['actual_Tk_widgets'] and r['GUI']['saved_loaded_exact'] and r['GUI']['unchanged_poll_and_executor']
  if job['recipe']=='cold' and job['kind']!='suffix':assert read(directory/'frame-100.json')==r['documents'][2]
  persistence.append(dict(job=job['id'],saved_q_S_and_settings_exact=True,continuous_initial_readout='separate raw COM/pair decoder output, input document retained' if job['recipe']=='continuous' else None))
  runtime=[];high=[]
  for i in range(len(job['epochs'])):
   state={k:a[k][i] for k in ('positions','velocities','quaternions','spins')}
   lo=decimal_invariants(state,doc,p['G_SI'],80);hi=decimal_invariants(state,doc,p['G_SI'],120);runtime.append(lo);high.append(hi)
  with localcontext() as ctx:
   ctx.prec=80;D=Decimal
   norm=lambda v:sum(x*x for x in v).sqrt()
   E=[D(x['E_J']) for x in high];P=[[D(v) for v in x['P_kg_m_s']] for x in high];L=[[D(v) for v in x['L_kg_m2_s']] for x in high]
   mass=sum(D.from_float(float(b['mass'])) for b in doc['bodies']);v0=max(norm([D.from_float(float(v)) for v in row]) for row in a['velocities'][0])
   drifts=dict(energy_drift=float(max(abs(x-E[0]) for x in E)/abs(E[0])),linear_drift=float(max(norm([x-y for x,y in zip(row,P[0])]) for row in P)/(mass*v0)),angular_drift=float(max(norm([x-y for x,y in zip(row,L[0])]) for row in L)/norm(L[0])),quaternion_norm=max(abs(float(x)) for row in high for x in row['qnorm_minus1']))
   precision_gap=max([float(abs(D(lo['E_J'])-D(hi['E_J']))/max(abs(D(hi['E_J'])),D(1))) for lo,hi in zip(runtime,high)])
  legacy=q.drift(a,doc,job['epochs']);fail=[k for k,v in legacy.items() if k in p['criteria380'] and isinstance(v,(int,float)) and v>=p['criteria380'][k]]
  assert all(abs(drifts[k]-legacy[k])<1e-12 for k in drifts)
  invariants.append(dict(job=job['id'],independent_Decimal120=drifts,original380_reduction=legacy,failed_original_gates=fail,Decimal80_120_energy_relative_gap=precision_gap))
 for backend in ('python','rust'):
  main=results[f'main__{backend}__gui__cold'];again=results['repeat__'+backend];suffix=results['suffix__'+backend]
  for key in ('positions','velocities','quaternions','spins'):
   assert np.asarray(main['arrays'][key]).tobytes()==np.asarray(again['arrays'][key]).tobytes()
   assert np.asarray(main['arrays'][key])[2:].tobytes()==np.asarray(suffix['arrays'][key]).tobytes()
  assert main['documents']==again['documents'] and main['documents'][2:]==suffix['documents'] and main['counters']==again['counters']
  repeat.append(dict(backend=backend,exact_same_environment_repeat=True,exact_saved_suffix=True,checkpoint_q_S_settings_exact=True))
 primary=metrics.assess(results,p);independent=metrics.assess(results,p,independent=True)
 B,delta,scales=metrics.budgets(p['initial'],120);_,_,small=metrics.budgets(p['initial'],80)
 assert np.array_equal(B,metrics.budgets(p['initial'],80)[0])
 # Compare actual rederived fields, never accept the primary ready-made flags.
 deltas=[]
 for x,y in zip(primary['rows'],independent['rows']):
  assert (x['job'],x['observable'])==(y['job'],y['observable'])
  j=metrics.NAMES.index(y['observable']);threshold=Decimal(scales['B'][j]);passed=True
  for e,u,n in zip(y['e'],y['U_ref'],y['N_sens']):
   de,du,dn=[Decimal.from_float(float(v)) for v in (e,u,n)];passed &= du<=threshold/10 and dn<=threshold/10 and de+du+dn<threshold
  assert ('PASS' if passed else 'FAIL')==y['numerical_status']
  if x['numerical_status']!=y['numerical_status']:raise ValueError('Independent arithmetic changes D1 classification')
  gap=max(abs(a-b) for field in ('e','U_ref','N_sens','effect_series') for a,b in zip(x[field],y[field]));deltas.append(dict(job=x['job'],observable=x['observable'],maximum_primary_vs_independent_difference=gap,relative_to_B=gap/y['B']))
  if gap>y['B']*.001:raise ValueError('Observer implementations unresolved at D1 scale')
 precision_cases=[]
 for job in p['jobs']:
  if job['kind']=='reference':continue
  a=results[job['id']]['arrays'];idx=[p['epochs'].index(t) for t in job['epochs']];ref={k:np.asarray(v)[idx].tolist() for k,v in results['reference__1']['arrays'].items()}
  g80=metrics.gaps(a,ref,independent=True,precision=80);g120=metrics.gaps(a,ref,independent=True,precision=120)
  precision_cases.append(dict(job=job['id'],observer80_120_gap=np.max(abs(g80-g120),axis=0).tolist()))
 # Short convergence retains every failure independently of D1.
 convergence=[]
 for backend in ('python','rust'):
  for recipe in ('cold','continuous'):
   values=[results[f'main__{backend}__{level}__{recipe}']['arrays'] for level in ('coarse','standard','fine')]
   cf=q.difference(values[0],values[2],p['initial'],p['epochs']);sf=q.difference(values[1],values[2],p['initial'],p['epochs'])
   convergence.append(dict(backend=backend,recipe=recipe,coarse_fine=cf,standard_fine=sf,strict380_rule_pass=max(sf.values())<max(cf.values())))
 for name,digest in p['input_SHA256'].items():q.require_sha(R/name,digest)
 old=read(R/'docs/q2-scientific-qualification-399.json');assert sum(not x['strict_pass'] for x in old['scientific_evaluator']['strict_convergence'])==6
 assert before==snapshot()
 put=lambda name,value:q.atomic_json(W/name,value)
 put('primary-observables.json',primary);put('independent-observables.json',independent)
 put('audit.json',dict(status='PASS_RAW_PROVENANCE_AND_INDEPENDENT_ARITHMETIC',job_count=22,all_job_IDs=[j['id'] for j in p['jobs']],source=identity,persistence=persistence,repeat_restart=repeat,domain=domain,invariants=invariants,observer_arithmetic=deltas,precision80_120=precision_cases,spin_budget120=scales,short_convergence=convergence,historical_three_FAIL_unchanged=True,raw_before_after_SHA256=before,limitations=['Independent observer shares IC,Hamiltonian,SciPy/binary64 and plan definitions; no external peer review.','SO3 eigen-polar vs SVD; matrix atan2 vs normalized-quaternion Decimal arithmetic; residual library rounding remains.','Independent norm/EPL arithmetic80/120 is not highprecision integration or global roundoff bound.','RHS domain guard checks attempted stages; no claim of continuous mathematically certified separation.','Scalar spin/norm observer eventually casts to binary64 for output; exact input Decimal norms and budget strings retained.']))
 print('PASS read-only raw22jobs, independent80/120/SVD/quaternion/EPL/D1/restart/SHA audit; D1='+independent['status'],flush=True)
if __name__=='__main__':main()
