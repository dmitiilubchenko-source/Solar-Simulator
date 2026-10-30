"""Reduce sealed product runs and independently read their raw scalar metrics."""
import argparse
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import json
import math
from pathlib import Path
import platform

import numpy as np
import scipy

from scripts.check_runtime_reliability376 import ROOT,PROTOCOL,read,sha,write,verify_source

REPORT=ROOT/'docs/runtime-reliability-376-validation.json'
ARRAYS=ROOT/'scripts/validation/runtime-reliability-376.npz'


def decimal(q):return D(q.numerator)/D(q.denominator)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return dot(a,a).sqrt()


def conserved(array,masses):
    """Exact rational kinetic/P/L, Decimal120 sole distance square root."""
    from solar_simulator.simulation import G
    s=[[F(float(v)) for v in row] for row in array];m=list(map(F,masses));g=F(G);M=sum(m)
    r=[s[1][j]-s[0][j] for j in range(3)];R=decimal(dot(r,r)).sqrt()
    v=[s[1][j+3]-s[0][j+3] for j in range(3)]
    P=[sum(m[b]*s[b][j+3] for b in range(2)) for j in range(3)]
    L=[sum(m[b]*(s[b][(j+1)%3]*s[b][(j+2)%3+3]-s[b][(j+2)%3]*s[b][(j+1)%3+3]) for b in range(2)) for j in range(3)]
    energy=decimal(sum(mass*dot(row[3:],row[3:])/2 for mass,row in zip(m,s)))-decimal(g*m[0]*m[1])/R
    eps=decimal(dot(v,v)/2)-decimal(g*M)/R
    return dict(E=energy,P=list(map(decimal,P)),L=list(map(decimal,L)),V=(-2*eps).sqrt(),M=decimal(M),
        COM=energy-decimal(m[0]*m[1]/M)*eps-decimal(dot(P,P)/(2*M)))


def independent_metrics(values,expected,masses):
    with localcontext() as ctx:
        ctx.prec=120;initial=conserved(values[0],masses);maximum={k:D(0) for k in ('r','v','E','L','P','COM')};rows=[]
        for state,ref in zip(values,expected):
            rho=[decimal(F(float(state[1,j]))-F(float(state[0,j]))) for j in range(6)]
            r=norm([rho[j]-D(ref[0][j]) for j in range(3)]);v=norm([rho[j+3]-D(ref[1][j]) for j in range(3)])
            inv=conserved(state,masses)
            row=dict(r=r,v=v,E=abs((inv['E']-initial['E'])/initial['E']),
                L=norm([a-b for a,b in zip(inv['L'],initial['L'])])/norm(initial['L']),
                P=norm([a-b for a,b in zip(inv['P'],initial['P'])])/(initial['M']*initial['V']),COM=abs(inv['COM']/initial['E']))
            rows.append({k:float(v) for k,v in row.items()})
            for key in maximum:maximum[key]=max(maximum[key],row[key])
        return {k:float(v) for k,v in maximum.items()},rows


def close_metric(actual,stored,key):
    # Float serialization/last-rounding check, never an orbital accuracy gate.
    if not math.isfinite(stored) or abs(actual-stored)>8*math.ulp(stored):
        raise ValueError('Independent raw metric disagreement: '+key)


def verify(report_path=REPORT,arrays_path=ARRAYS,*,historical=False,protocol_path=PROTOCOL):
    """Current-source check by default; historical replay is explicit and non-qualifying."""
    if type(historical) is not bool:raise ValueError('historical must be an explicit bool')
    proof=read(report_path);protocol=read(protocol_path)
    if historical:
        from scripts.release_history import ui_historical_sha
        for name,expected in protocol['source_SHA256'].items():
            if ui_historical_sha(ROOT,name,expected)!=expected:raise ValueError('Historical source changed: '+name)
        analysis_SHA=ui_historical_sha(ROOT,'scripts/assess_runtime_reliability376.py',proof['analysis_source_SHA256'])
    else:
        verify_source(protocol)
        analysis_SHA=sha(Path(__file__))
    if sha(protocol_path)!=proof['protocol_SHA256'] or sha(arrays_path)!=proof['arrays_SHA256']:
        raise ValueError('Protocol/array SHA mismatch')
    if analysis_SHA!=proof['analysis_source_SHA256']:raise ValueError('Assessment source changed')
    if [r['job'] for r in proof['runs']]!=protocol['jobs']:raise ValueError('Wrong/missing job list')
    counted=0;maxima=[]
    with np.load(arrays_path,allow_pickle=False) as data:
        for row in proof['runs']:
            job=row['job'];case=next(c for c in protocol['cases'] if c['id']==job['case'])
            times=case['epochs'] if job['schedule']=='grid' else [case['epochs'][0],case['epochs'][-1]]
            values=data[job['id']+'__states'];epochs=data[job['id']+'__epochs']
            if values.shape!=(len(times),2,6) or not np.isfinite(values).all() or not np.array_equal(epochs,times):raise ValueError('Invalid states/grid')
            if not np.array_equal(values[0],case['initial']):raise ValueError('Wrong initial state')
            ref=proof['references'][case['id']]['values'];ref=ref if job['schedule']=='grid' else [ref[0],ref[-1]]
            maximum,observed=independent_metrics(values,ref,case['masses'])
            for k,v in maximum.items():
                if k!='COM':close_metric(v,row['maxima'][k],job['id']+'/'+k)
            if len(observed)!=len(row['per_epoch']):raise ValueError('Missing epoch metrics')
            for i,(actual,stored) in enumerate(zip(observed,row['per_epoch'])):
                for k in ('r','v','E','L','P'):close_metric(actual[k],stored[k],f"{job['id']}/{i}/{k}")
            maxima.append(maximum);counted+=len(times)
    return dict(jobs=len(maxima),state_observations=counted,independent_r_v_E_L_P=True,
        source_mode='historical_replay_only' if historical else 'current_sources',current_runtime_qualified=False,
        reader_SHA256=sha(Path(__file__)),
        shared_assumptions='Newton/IC/G and stored analytic reference; different Fraction arithmetic, not a second numerical IVP',
        COM_not_ulp_compared='different Decimal120/130 cancellation floors; both identities independently evaluated')


def build(work,*,protocol_path=PROTOCOL,report_path=REPORT,arrays_path=ARRAYS,run_directory=None,guard_files=()):
    # Old defaults retain the historical two-attempt accounting. A new run
    # supplies its own paths/guards; it must not inherit old failures or CPU.
    REPORT,ARRAYS=Path(report_path),Path(arrays_path)
    directory=Path(run_directory) if run_directory is not None else work/'data-02'
    if REPORT.exists() or ARRAYS.exists():raise FileExistsError('Preserve prior validation')
    receipt=read(directory/'receipt.json');p=read(protocol_path);verify_source(p)
    if (not receipt['complete'] or receipt['failure'] is not None or receipt['protocol_SHA256']!=sha(protocol_path)
            or [r['job'] for r in receipt['jobs']]!=p['jobs']):raise ValueError('Incomplete/changed run')
    for name,h in receipt['files'].items():
        if sha(directory/name)!=h:raise ValueError('Changed saved output: '+name)
    arrays={};references={}
    for case in p['cases']:references[case['id']]=read(directory/(case['id']+'-reference.json'))
    for row in receipt['jobs']:
        job=row['job'];path=directory/(job['id']+'.npz')
        if sha(path)!=row['array_SHA256']:raise ValueError('Changed raw array')
        with np.load(path,allow_pickle=False) as data:
            for key in ('states','epochs'):arrays[job['id']+'__'+key]=data[key].copy()
    with ARRAYS.open('xb') as stream:np.savez_compressed(stream,**arrays)
    guards=[read(path) for path in guard_files] if run_directory is not None else [read(work/name/'supervisor.json') for name in ('guard','guard-02')]
    proof=dict(stage=376,protocol_SHA256=sha(protocol_path),arrays_SHA256=sha(ARRAYS),analysis_source_SHA256=sha(Path(__file__)),
        environment=dict(python=platform.python_version(),scipy=scipy.__version__,numpy=np.__version__),
        runs=receipt['jobs'],references=references,source_SHA256=p['source_SHA256'],
        prior_preflight_failure=read(work/'grid-mre.json') if run_directory is None else None,
        original_run_status=read(work/'data/receipt.json')['failure']['message'] if run_directory is None else None,
        preparation_test_failure='17 PASS /1 FAIL: normalized test velocity used with SI G; corrected before main protocol, not a runtime bug' if run_directory is None else None,
        resources=dict(guards=guards,total_CPU_seconds=sum(v['worker_CPU_seconds']+v['parent_supervision_CPU_seconds'] for v in guards),
                       active_wall_seconds=sum(v['wall_seconds'] for v in guards),peak_private=max((v['peak_private_tree_sampled'] for v in guards),default=None),
                       measurement_available=bool(guards)),
        scope=p['scope'],runtime_modified=False,release_qualification_changed=False)
    write(REPORT,proof)
    result=verify(REPORT,ARRAYS,protocol_path=protocol_path);write(work/'independent-observer.json',result);print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('build','verify'));parser.add_argument('--work',type=Path)
    parser.add_argument('--historical',action='store_true',help='Verify archived source provenance and saved arrays only; never qualify current runtime')
    parser.add_argument('--protocol',type=Path,default=PROTOCOL)
    parser.add_argument('--report',type=Path,default=REPORT);parser.add_argument('--arrays',type=Path,default=ARRAYS)
    parser.add_argument('--run-directory',type=Path);parser.add_argument('--guard-file',type=Path,action='append',default=[])
    args=parser.parse_args()
    if args.historical and args.mode!='verify':parser.error('--historical is only valid for saved-data verify')
    if args.mode=='build':build(args.work or ROOT/'.tools/runtime376',protocol_path=args.protocol,
        report_path=args.report,arrays_path=args.arrays,run_directory=args.run_directory,guard_files=args.guard_file)
    else:print(json.dumps(verify(args.report,args.arrays,historical=args.historical,protocol_path=args.protocol)))
