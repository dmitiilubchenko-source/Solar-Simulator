"""Independent orbital-basis mpmath oracle + Fraction observer of saved379 data.

No integration, phase fitting, production changes or trust in saved PASS flags.
mpmath is an offline optional tool, not a Solar runtime dependency.
"""
import argparse
from decimal import Decimal as D
from fractions import Fraction as F
import math
from pathlib import Path
import platform
import sys

import mpmath as mp
import numpy as np

from scripts.check_runtime_step379 import PLAN,OLD_ARRAYS,read,sha,write,ROOT
from scripts.assess_runtime_reliability376 import independent_metrics,close_metric
from solar_simulator.simulation import G


def orbital_reference(initial,masses,time,precision=80):
    """Use eccentricity-vector orbital basis and absolute E, not incremental f/g."""
    with mp.workdps(precision):
        dot=lambda a,b:sum(x*y for x,y in zip(a,b))
        cross=lambda a,b:[a[(j+1)%3]*b[(j+2)%3]-a[(j+2)%3]*b[(j+1)%3] for j in range(3)]
        length=lambda a:mp.sqrt(dot(a,a))
        r=[mp.mpf(float(initial[1][j]))-mp.mpf(float(initial[0][j])) for j in range(3)]
        v=[mp.mpf(float(initial[1][j+3]))-mp.mpf(float(initial[0][j+3])) for j in range(3)]
        mu=mp.mpf(G)*sum(mp.mpf(float(m)) for m in masses);R=length(r)
        a=1/(2/R-dot(v,v)/mu);h=cross(r,v);H=length(h)
        ev=[x/mu-y/R for x,y in zip(cross(v,h),r)];e=length(ev)
        if not a>0 or not 0<e<1 or not H>0:raise ValueError('Noncircular bound elliptic audit only')
        p=[x/e for x in ev];q=cross([x/H for x in h],p);b=mp.sqrt(1-e*e)
        E0=mp.atan2(dot(r,q)/(a*b),dot(r,p)/a+e)
        M=E0-e*mp.sin(E0)+mp.sqrt(mu/a**3)*mp.mpf(float(time))
        lo,hi=M-e,M+e
        for _ in range(4*precision+30):
            E=(lo+hi)/2
            if E-e*mp.sin(E)<M:lo=E
            else:hi=E
        E=(lo+hi)/2;s,c=mp.sin(E),mp.cos(E)
        position=[a*((c-e)*x+b*s*y) for x,y in zip(p,q)]
        velocity=[mp.sqrt(mu/a)/(1-e*c)*(-s*x+b*c*y) for x,y in zip(p,q)]
        return tuple(tuple(mp.nstr(x,precision-5) for x in group) for group in (position,velocity))


def audit_steps(steps,trials,divisor,mu,packets):
    if steps.ndim!=2 or steps.shape[1]!=13 or not np.isfinite(steps).all():raise ValueError('Invalid step trace')
    if trials.ndim!=2 or trials.shape[1]!=4 or not np.isfinite(trials).all():raise ValueError('Invalid trial trace')
    maximum_excess=0.;active=0
    for index,row in enumerate(steps):
        packet,t0,t1,cap,x,y,z,proposed,nb,na,count,rejected,clipped=row
        actual=trials[trials[:,1]==index]
        if len(actual)!=count or np.any(actual[:,0]!=packet) or not len(actual) or actual[-1,3]>=1:
            raise ValueError('Accepted/trial trace inconsistency')
        if sum(actual[:,3]>=1)!=rejected or na-nb!=12*count:raise ValueError('Trial/RHS counters differ from SciPy stages')
        if not t1>t0 or actual[-1,2]!=t1-t0:raise ValueError('Accepted step clock differs')
        if divisor is not None:
            # Independent scalar geometry, not dynamic_cap or its np.linalg.norm.
            expected=math.sqrt(math.sqrt(x*x+y*y+z*z)**3/mu)/divisor
            if abs(expected-cap)>8*math.ulp(cap):raise ValueError('Dynamic scale differs')
            allowed=2*max(math.ulp(t0),math.ulp(t1))
            if t1-t0>cap+allowed or np.any(np.abs(actual[:,2])>cap+allowed):raise ValueError('Internal cap not applied')
            maximum_excess=max(maximum_excess,t1-t0-cap);active+=int(clipped)
        elif cap!=0:raise ValueError('Unexpected disabled cap')
        if int(clipped)!=int(cap>0 and proposed>cap):raise ValueError('Clipping flag differs')
    for packet in packets:
        rows=trials[trials[:,0]==packet['packet']]
        #2 initial RHS +12 per attempt +3 endpoint dense-output stages.
        if packet['nfev']!=2+12*len(rows)+3:raise ValueError('nfev does not match pinned SciPy endpoint path')
    return dict(accepted=len(steps),rejected=int(sum(trials[:,3]>=1)),proposal_clipped=active,
        maximum_cap_rounding_excess_seconds=maximum_excess,
        min_step_seconds=float(np.min(steps[:,2]-steps[:,1])),max_step_seconds=float(np.max(steps[:,2]-steps[:,1])))


def self_test():
    from decimal import localcontext
    from scripts.kepler_reference import propagate
    initial=[[-.5,0.,0.,0.,-2.**-17,0.],[.5,0.,0.,0.,2.**-17,0.]]
    for time in (0.,10000.):
        with localcontext() as ctx:
            ctx.prec=130
            other=propagate((D(1),D(0),D(0)),(D(0),D.from_float(2.**-16),D(0)),D.from_float(G)*2,D.from_float(time),precision=100)
            current=orbital_reference(initial,[1.,1.],time)
            if any(abs(a-D(b))>D('1e-60') for group,now in zip(other,current) for a,b in zip(group,now)):
                raise ArithmeticError('Synthetic oracle mismatch')
    step=np.array([[1,0,.1,1,1,0,0,.1,2,14,1,0,0.]])
    trial=np.array([[1,0,.1,.1]])
    audit_steps(step,trial,1,1.,[dict(packet=1,nfev=17)])
    for index in (3,10,11):
        broken=step.copy();broken[0,index]+=1
        try:audit_steps(broken,trial,1,1.,[dict(packet=1,nfev=17)])
        except ValueError:pass
        else:raise AssertionError('Corrupt trace accepted')
    print('PASS: two independent synthetic oracle epochs and three corrupt trace controls')


def assess(work,output):
    p=read(PLAN);receipt=read(work/'receipt.json')
    if not receipt['complete'] or receipt['plan_SHA256']!=sha(PLAN):raise ValueError('Partial or changed execution')
    for name,digest in (p['input_SHA256']|p['source_SHA256']).items():
        if sha(ROOT/name)!=digest:raise ValueError('Source/input changed: '+name)
    for name,digest in receipt['files'].items():
        if sha(work/name)!=digest:raise ValueError('Saved output changed: '+name)
    if [(r['job'],r['variant']) for r in receipt['jobs']]!=[(j,v) for v in p['variants'] for j in p['jobs']]:
        raise ValueError('Wrong, duplicate or missing job list')
    refs={};oracle_rows=[];results=[];arrays={}
    for case in p['cases']:
        reference=read(work/(case['id']+'-reference.json'))['values'];refs[case['id']]=reference
        gap_r=gap_v=convergence_r=convergence_v=0.
        for time,expected in zip(case['epochs'],reference):
            low=orbital_reference(case['initial'],case['masses'],time,80)
            high=orbital_reference(case['initial'],case['masses'],time,110)
            with mp.workdps(120):
                for j in range(2):
                    gap=float(mp.sqrt(sum((mp.mpf(a)-mp.mpf(b))**2 for a,b in zip(high[j],expected[j]))))
                    conv=float(mp.sqrt(sum((mp.mpf(a)-mp.mpf(b))**2 for a,b in zip(high[j],low[j]))))
                    if j==0:gap_r=max(gap_r,gap);convergence_r=max(convergence_r,conv)
                    else:gap_v=max(gap_v,gap);convergence_v=max(convergence_v,conv)
        if max(gap_r,convergence_r)>=1e-6 or max(gap_v,convergence_v)>=1e-12:raise ArithmeticError('Independent analytic reference unresolved')
        oracle_rows.append(dict(case=case['id'],position_gap_m=gap_r,velocity_gap_m_s=gap_v,
            precision80_110_r=convergence_r,precision80_110_v=convergence_v))
        arrays[case['id']+'__epochs']=np.array(case['epochs'])
    for row in receipt['jobs']:
        job=row['job'];name=job['id']+'__'+row['variant'];case=next(c for c in p['cases'] if c['id']==job['case'])
        with np.load(work/(name+'.npz'),allow_pickle=False) as data:
            values=data['states'];steps=data['steps'];trials=data['trials'];epochs=data['epochs']
            if values.shape!=(49,2,6) or not np.isfinite(values).all() or not np.array_equal(epochs,case['epochs']):raise ValueError('Wrong state/grid')
            if not np.array_equal(values[0],case['initial']):raise ValueError('IC changed')
            if len(row['per_epoch'])!=49 or [k['packet'] for k in row['packets']]!=list(range(1,49)) or not all(k['success'] for k in row['packets']):
                raise ValueError('Missing epoch/packet results')
            maximum,per_epoch=independent_metrics(values,refs[case['id']],case['masses'])
            for actual,stored in zip(per_epoch,row['per_epoch']):
                for key in ('r','v','E','L','P'):close_metric(actual[key],stored[key],name+'/'+key)
            for key in ('r','v','E','L','P'):close_metric(maximum[key],row['maxima'][key],name+'/max/'+key)
            for key in ('r','v'):
                close_metric(per_epoch[-1][key],row['endpoint'][key],name+'/endpoint/'+key)
                close_metric(max(per_epoch[i][key] for i in p['peri_indices'][case['id']]),row['pericentre'][key],name+'/peri/'+key)
            for key in ('r','v','E','L','P'):
                if row['maximum_indices'][key]!=int(np.argmax([v[key] for v in per_epoch])):raise ValueError('Wrong maximum epoch')
            if row['variant']=='disabled':
                with np.load(OLD_ARRAYS,allow_pickle=False) as old:
                    if values.tobytes()!=old[job['id']+'__states'].tobytes():raise ArithmeticError('Baseline376 not byte-exact')
            trace=audit_steps(steps,trials,None if row['variant']=='disabled' else p['divisor'],G*sum(case['masses']),row['packets'])
            for i in range(1,49):
                packet_steps=steps[steps[:,0]==i]
                if not len(packet_steps) or packet_steps[0,1]!=0 or packet_steps[-1,2]!=epochs[i]-epochs[i-1] or not np.array_equal(packet_steps[1:,1],packet_steps[:-1,2]):
                    raise ValueError('Internal steps changed packet boundaries')
            if trace['accepted']!=row['accepted_steps'] or trace['rejected']!=row['rejected_trials'] or sum(k['nfev'] for k in row['packets'])!=row['RHS']:
                raise ValueError('Incomplete step/RHS metrics')
            arrays[name+'__states']=values;arrays[name+'__steps']=steps;arrays[name+'__trials']=trials
        results.append(dict(row,independent_trace=trace))
    contrasts=[]
    for job in p['jobs']:
        a=next(r for r in results if r['job']==job and r['variant']=='disabled')
        b=next(r for r in results if r['job']==job and r['variant']=='dynamic32')
        ratios={k:b['maxima'][k]/a['maxima'][k] for k in ('r','v')}
        peri_end_ok=all(b[scope][k]<=a[scope][k]+tol for scope in ('pericentre','endpoint') for k,tol in [('r',1e-6),('v',1e-12)])
        contrasts.append(dict(job=job['id'],max_error_ratios=ratios,RHS_ratio=b['RHS']/a['RHS'],
            integration_CPU_ratio=b['integration_CPU_seconds']/a['integration_CPU_seconds'],
            necessary_check=all(v<=.9 for v in ratios.values()) and peri_end_ok and b['RHS']<=2*a['RHS'],
            peri_endpoint_not_worse=peri_end_ok))
    array_path=output.with_suffix('.npz')
    if output.exists() or array_path.exists():raise FileExistsError('Preserve previous assessment')
    np.savez_compressed(array_path,**arrays)
    report=dict(stage=379,plan_SHA256=sha(PLAN),arrays_SHA256=sha(array_path),runs=results,contrasts=contrasts,
        independent_oracle=oracle_rows,independent_metrics_state_observations=392,
        assessment_source_SHA256=sha(Path(__file__)),observer_environment=dict(python=sys.version,mpmath=mp.__version__,numpy=np.__version__),
        exploratory_further_study=all(c['necessary_check'] for c in contrasts),production_decision='NO-GO: bounded exploratory evidence is not runtime qualification',
        shared_assumptions='Both analytic oracles use Newton ellipse/exact binary IC/G; different basis/library, not external review. Fraction observer shares mathematical invariant definitions.',
        runtime_changed=False,phase_fit=False,parameter_search=False)
    write(output,report);print('Independent audit complete; exploratory screen:',report['exploratory_further_study'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--work',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--self-test',action='store_true');args=parser.parse_args()
    if args.self_test:self_test()
    elif args.work is None or args.output is None:parser.error('--work and --output required')
    else:assess(args.work,args.output)
