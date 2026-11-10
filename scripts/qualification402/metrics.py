"""D1 saved-state observers; no integration, fitting or changes to raw R/q."""
import math
import numpy as np
from decimal import Decimal,localcontext
from itertools import combinations
NAMES=('r_A','r_B','rho_BA','distance_AB','v_A','v_B','v_BA','theta_A','theta_B','S_A','S_B')
def projected(raw,*,independent=False):
 raw=np.asarray(raw,dtype=float)
 if raw.shape!=(3,3) or not np.isfinite(raw).all() or np.linalg.det(raw)<=0:raise ValueError('Uninterpretable reference rotation')
 if independent:
  u,s,vt=np.linalg.svd(raw);matrix=u@vt
 else:
  values,vectors=np.linalg.eigh(raw.T@raw)
  if np.min(values)<=0:raise ValueError('Singular reference rotation')
  matrix=raw@(vectors@np.diag(values**-.5)@vectors.T)
 if np.linalg.det(matrix)<=0 or np.linalg.norm(matrix.T@matrix-np.eye(3))>1e-12:raise ValueError('Projection did not produce SO3')
 return matrix,float(np.linalg.norm(raw-matrix)),float(np.linalg.norm(raw.T@raw-np.eye(3))),float(np.linalg.det(raw))
def angle(a,b,*,independent=False,precision=80):
 if independent:
  from scipy.spatial.transform import Rotation
  from scripts.q2_frame_observer393 import orientation_angle
  qa=np.roll(Rotation.from_matrix(a).as_quat(),1).tolist();qb=np.roll(Rotation.from_matrix(b).as_quat(),1).tolist()
  return orientation_angle(qa,qb,precision)
 Q=np.asarray(a).T@np.asarray(b);skew=np.array([Q[2,1]-Q[1,2],Q[0,2]-Q[2,0],Q[1,0]-Q[0,1]])*.5
 return math.atan2(float(np.linalg.norm(skew)),max(-1.,min(1.,float((np.trace(Q)-1)*.5))))
def geometry(arrays,*,independent=False):
 mats=[];defects=[];orth=[];dets=[]
 for sample in arrays['orientation']:
  entries=[projected(x,independent=independent) for x in sample]
  mats.append([x[0] for x in entries]);defects.append([x[1] for x in entries]);orth.append([x[2] for x in entries]);dets.append([x[3] for x in entries])
 return dict(matrices=np.array(mats),projection_defect=np.array(defects),orthogonality=np.array(orth),determinants=np.array(dets))
def gaps(a,b,*,independent=False,precision=80):
 """Eleven physical errors per epoch; vector and scalar distance stay distinct."""
 pa=np.asarray(a['positions']);pb=np.asarray(b['positions']);va=np.asarray(a['velocities']);vb=np.asarray(b['velocities']);sa=np.asarray(a['spins']);sb=np.asarray(b['spins'])
 ga=geometry(a,independent=independent);gb=geometry(b,independent=independent)
 if independent:
  from scripts.q2_frame_observer393 import number,norm
  def normdiff(x,y):
   with localcontext() as ctx:ctx.prec=precision;return float(norm([number(float(u))-number(float(v)) for u,v in zip(x,y)]))
  def relative(x):return [[Decimal.from_float(float(v))-Decimal.from_float(float(u)) for u,v in zip(sample[0],sample[1])] for sample in x]
  with localcontext() as ctx:
   ctx.prec=precision;pra=relative(pa);prb=relative(pb);vra=relative(va);vrb=relative(vb)
   relp=[float(norm([u-v for u,v in zip(x,y)])) for x,y in zip(pra,prb)];relv=[float(norm([u-v for u,v in zip(x,y)])) for x,y in zip(vra,vrb)];dist=[float(abs(norm(x)-norm(y))) for x,y in zip(pra,prb)]
  p=np.array([[normdiff(x,y) for x,y in zip(aa,bb)] for aa,bb in zip(pa,pb)]);v=np.array([[normdiff(x,y) for x,y in zip(aa,bb)] for aa,bb in zip(va,vb)]);s=np.array([[normdiff(x,y) for x,y in zip(aa,bb)] for aa,bb in zip(sa,sb)])
 else:
  p=np.linalg.norm(pa-pb,axis=2);v=np.linalg.norm(va-vb,axis=2);s=np.linalg.norm(sa-sb,axis=2);pra=pa[:,1]-pa[:,0];prb=pb[:,1]-pb[:,0];relp=np.linalg.norm(pra-prb,axis=1);relv=np.linalg.norm((va[:,1]-va[:,0])-(vb[:,1]-vb[:,0]),axis=1);dist=np.abs(np.linalg.norm(pra,axis=1)-np.linalg.norm(prb,axis=1))
 theta=np.array([[angle(x,y,independent=independent,precision=precision) for x,y in zip(aa,bb)] for aa,bb in zip(ga['matrices'],gb['matrices'])])
 return np.array([p[:,0],p[:,1],relp,dist,v[:,0],v[:,1],relv,theta[:,0],theta[:,1],s[:,0],s[:,1]]).T
def reference_gap(coarse,fine,*,independent=False):
 x=gaps(coarse,fine,independent=independent);a=geometry(coarse,independent=independent);b=geometry(fine,independent=independent)
 x[:,7:9]+=(a['projection_defect']+b['projection_defect'])/math.sqrt(2)
 return x
def budgets(document,precision=80):
 with localcontext() as ctx:
  ctx.prec=precision
  norm=lambda r:sum(Decimal.from_float(float(x))**2 for x in r['angular_momentum']).sqrt()
  spin=[norm(r) for r in document['rotations']]
  B=[Decimal(1)]*4+[Decimal('.001')]*5+[x*Decimal('1e-5') for x in spin]
  delta=[Decimal(10)]*4+[Decimal('.01')]*5+[x*Decimal('1e-4') for x in spin]
  return np.array(list(map(float,B))),np.array(list(map(float,delta))),dict(initial_binary64_norms=[str(x) for x in spin],B=[str(x) for x in B],Delta=[str(x) for x in delta],precision=precision)
def assess(results,plan,*,independent=False):
 refs=[results['reference__'+str(i)]['arrays'] for i in (0,1)];U=reference_gap(*refs,independent=independent);N={b:np.zeros_like(U) for b in ('python','rust')};contrasts=[]
 def contrast(name,backend,a,b):
  values=gaps(a,b,independent=independent);N[backend]=np.maximum(N[backend],values);contrasts.append(dict(name=name,backend=backend,per_epoch=values.tolist()))
 for backend in N:
  for recipe in ('cold','continuous'):
   for a,b in combinations([x['id'] for x in plan['levels']],2):contrast('levels/'+recipe+'/'+a+'/'+b,backend,results[f'main__{backend}__{a}__{recipe}']['arrays'],results[f'main__{backend}__{b}__{recipe}']['arrays'])
  for level in plan['levels']:contrast('recipes/'+level['id'],backend,results[f"main__{backend}__{level['id']}__cold"]['arrays'],results[f"main__{backend}__{level['id']}__continuous"]['arrays'])
  contrast('GUI repeat',backend,results[f'main__{backend}__gui__cold']['arrays'],results[f'repeat__{backend}']['arrays'])
 # Independent observer arithmetic contrasts are included even if much smaller than B.
 for job in plan['jobs']:
  if job['kind']=='reference' or job['kind']=='suffix':continue
  x=results[job['id']]['arrays'];normal=gaps(x,refs[1],independent=False);hi=gaps(x,refs[1],independent=True,precision=80);higher=gaps(x,refs[1],independent=True,precision=120);contrast_values=np.maximum(np.abs(normal-hi),np.abs(hi-higher));N[job['backend']]=np.maximum(N[job['backend']],contrast_values)
  contrasts.append(dict(name='saved-observer/'+job['id'],backend=job['backend'],per_epoch=contrast_values.tolist()))
 B,delta,scales=budgets(plan['initial']);rows=[]
 for job in plan['jobs']:
  if job['kind']=='reference':continue
  r=results[job['id']];indices=[plan['epochs'].index(t) for t in job['epochs']];fine={k:np.asarray(v)[indices].tolist() for k,v in refs[1].items()};error=gaps(r['arrays'],fine,independent=independent);u=U[indices];noise=N[job['backend']][indices]
  original=results['main__'+job['backend']+'__gui__cold']['arrays'] if job['kind']=='suffix' else r['arrays']
  zero={k:[v[0] for _ in indices] for k,v in original.items()};effects=gaps(r['arrays'],zero,independent=independent)
  for j,name in enumerate(NAMES):
   ok=(u[:,j]<=B[j]/10)&(noise[:,j]<=B[j]/10)&(error[:,j]+u[:,j]+noise[:,j]<B[j]);total=error[:,j]+u[:,j]+noise[:,j];index=int(np.argmax(total));effect=float(max(effects[:,j]))
   rows.append(dict(job=job['id'],observable=name,epochs=job['epochs'],e=error[:,j].tolist(),U_ref=u[:,j].tolist(),N_sens=noise[:,j].tolist(),B=float(B[j]),Delta=float(delta[j]),total=total.tolist(),maximum_total=float(total[index]),maximum_epoch=job['epochs'][index],max_e_epoch=job['epochs'][int(np.argmax(error[:,j]))],max_U_epoch=job['epochs'][int(np.argmax(u[:,j]))],max_N_epoch=job['epochs'][int(np.argmax(noise[:,j]))],effect_series=effects[:,j].tolist(),observed_effect=effect,effect_demonstrated=bool(effect>=delta[j]),numerical_status='PASS' if ok.all() else 'FAIL'))
 backend=[]
 for level in plan['levels']:
  for recipe in ('cold','continuous'):
   backend.append(dict(level=level['id'],recipe=recipe,per_epoch=gaps(results[f"main__python__{level['id']}__{recipe}"]['arrays'],results[f"main__rust__{level['id']}__{recipe}"]['arrays'],independent=independent).tolist()))
 return dict(observable_order=NAMES,rows=rows,reference_U=U.tolist(),sensitivity={k:v.tolist() for k,v in N.items()},contrasts=contrasts,backend_diagnostic_only=backend,spin_budget=scales,reference_geometry=[{k:v.tolist() for k,v in geometry(x,independent=independent).items() if k!='matrices'} for x in refs],status='PASS' if all(x['numerical_status']=='PASS' for x in rows) else 'FAIL')
def geometry_controls():
 I=np.eye(3);Z=np.diag([-1.,-1.,1.]);a=angle(I,I);b=angle(I,Z);assert a==0 and abs(b-math.pi)<1e-15
 assert abs(angle(I,Z,independent=True)-math.pi)<1e-15
 M=I.copy();M[0,1]=1e-7;P,defect,ortho,det=projected(M);assert defect>0 and ortho>0 and det>0
 for bad in (np.diag([-1.,1.,1.]),np.zeros((3,3)),np.full((3,3),np.nan)):
  try:projected(bad)
  except ValueError:pass
  else:raise AssertionError('Bad geometry accepted')
 from scripts.q2_frame_observer393 import orientation_angle
 assert orientation_angle([1.,0.,0.,0.],[-1.,0.,0.,0.])==0
 return dict(zero_angle=a,pi_angle=b,antipodal_q=True,raw_R_unchanged=True,nonfinite_reflection_singular_rejected=True)
