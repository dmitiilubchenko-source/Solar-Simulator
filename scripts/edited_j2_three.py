"""Three-body membership edits with full EIH, fixed J2 and active oracle caps."""
import argparse
from dataclasses import asdict,replace
from importlib import import_module
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.edited_j2 import (verify_branch,variants,legacy_trajectory,checkpoint_check,
    reference_gate,metrics,agreement,within)
from scripts.fixed_j2_ias import model,reference,dop_trajectory,balances,entries,figure_force
from scripts.eih_year import force_terms
from scripts.newton_year import ROOT,hashes
from scripts.assess_sandbox_planets import states
from solar_simulator.experiment import create_experiment
from solar_simulator.sandbox import branch_experiment
from solar_simulator.simulation import Body,G
from solar_simulator.relativity import C,eih_acceleration
from solar_simulator.native_forces import prepare as native_prepare
from solar_simulator.storage import to_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3

CASES=('add_start','remove_quarter','mass_quarter')


def fixture(case):
    if case not in CASES:raise ValueError('Undeclared three-body case')
    old,times,period=model('eih_two');q=states(old.bodies)
    bodies=[replace(b,position=Vector3(*map(float,row[:3])),velocity=Vector3(*map(float,row[3:])))
        for b,row in zip(old.bodies,q)]
    parent=create_experiment(bodies,old.settings);np.testing.assert_array_equal(states(parent.bodies),q)
    total=sum(b.mass for b in parent.bodies);speed=float(np.sqrt(G*total/1e8))
    gamma=Body('Gamma',.05*total,Vector3(7e8,0.,0.),Vector3(20000.,-10000.+.25*speed,5000.+.15*speed))
    if case=='add_start':branch=branch_experiment(parent,additions=(gamma,))
    else:
        parent=branch_experiment(parent,additions=(gamma,)).child
        while parent.time<period/4:parent=advance_towards(parent,period/4,20)
        if case=='remove_quarter':branch=branch_experiment(parent,removals=('Gamma',))
        else:
            alpha=parent.bodies[0]
            branch=branch_experiment(parent,replacements=(('Alpha',replace(alpha,mass=alpha.mass*1.25)),))
    return parent,branch,times,period


def snapshot_controls(seed):
    q=states(seed.bodies);p,v=q[:,:3],q[:,3:];m=np.array([b.mass for b in seed.bodies])
    newton,pn=force_terms(p,v,G*m,C);point=native_prepare(m);pn_scale=np.linalg.norm(pn,axis=1).max()
    native_pn_error=float(np.linalg.norm(point(p,v,C)-point(p,v)-pn,axis=1).max()/pn_scale)
    python_pn_error=float(np.linalg.norm(eih_acceleration(p,v,m)-newton-pn,axis=1).max()/pn_scale)
    force=m[:,None]*figure_force(p,m,entries(seed));scale=np.linalg.norm(force,axis=1).sum()
    missing=force.copy();missing[0]=0.
    net=float(np.linalg.norm(force.sum(axis=0))/scale);without=float(np.linalg.norm(missing.sum(axis=0))/scale)
    pair_gap=None
    if len(m)==3:
        isolated=np.zeros_like(pn)
        for i in range(3):
            for j in range(i+1,3):
                _,pair=force_terms(p[[i,j]],v[[i,j]],G*m[[i,j]],C)
                isolated[i]+=pair[0];isolated[j]+=pair[1]
        pair_gap=float(np.linalg.norm(isolated-pn,axis=1).max()/pn_scale)
    return dict(native_pn_relative_error=native_pn_error,python_pn_relative_error=python_pn_error,
        correct_scaled_net_force=net,missing_source_scaled_net_force=without,pair_only_relative_pn_gap=pair_gap,
        checks_passed=bool(native_pn_error<3e-9 and python_pn_error<3e-9 and net<5e-13 and without>1e-3
            and (pair_gap is None or pair_gap>1e-4)))


def run(output):
    output=Path(output).resolve()
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():raise ValueError('Use a fresh output path')
    output.parent.mkdir(parents=True,exist_ok=True)
    prior=json.loads((ROOT/'docs/fixed-j2-ias-validation.json').read_bytes())['measurements']
    for group in ('source_sha256','native_sha256'):
        if hashes(prior[group])!=prior[group]:raise ValueError('Qualified source/native changed')
    paths=[p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    paths += ['scripts/'+n+'.py' for n in ('edited_j2_three','edited_j2','fixed_j2_ias',
        'eih_year','ias15_eih','ias15_reference','newton_year','assess_sandbox_planets')]
    paths += ['tests/test_edited_j2_three.py','docs/edited-j2-three-protocol.md']
    source_before=hashes(paths);inputs=hashes(['docs/fixed-j2-ias-validation.json'])
    native_paths=[Path(import_module(n).__file__) for n in ('solar_native','solar_native.solar_native')]
    native=hashes(native_paths)
    import scipy.integrate._ivp.rk as rk
    import scipy.integrate._ivp.base as base
    scipy_paths=[Path(rk.__file__),Path(base.__file__)];scipy_sources=hashes(scipy_paths)
    report=dict(protocol='docs/edited-j2-three-protocol.md',source_sha256=source_before,input_sha256=inputs,
        native_sha256=native,scipy_source_sha256=scipy_sources,environment=dict(numpy=np.__version__,scipy=scipy.__version__),
        cases={},complete=False,general_release=False,runtime_modified=False)
    arrays={}
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report['npz_sha256']=hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            for case in CASES:
                parent,branch,times,period=fixture(case);seed=branch.child
                provenance=verify_branch(parent,branch);before=to_document(parent)
                initial=states(seed.bodies);names=[b.name for b in seed.bodies]
                row=dict(provenance=provenance,settings=asdict(seed.settings),names=names,
                    masses_kg=[b.mass for b in seed.bodies],samples=len(times),duration_seconds=float(times[-1]),
                    nominal_period_seconds=period,reference_levels=[],reference_comparisons={},candidates={})
                row['snapshot_controls']=snapshot_controls(seed)
                report['cases'][case]=row;arrays[case+'_initial']=initial;arrays[case+'_times']=times
                for division in (800,1600,3200):
                    start=perf_counter();values,budget,meta=reference(seed,times,3e-14,period/division)
                    meta.update(wall_seconds=perf_counter()-start,initial_roundtrip=agreement(values[:1],initial[None],names),
                        balance=balances(values,budget,seed))
                    arrays[case+'_reference_'+str(division)]=values;arrays[case+'_budgets_'+str(division)]=budget
                    row['reference_levels'].append(meta);save()
                    print(case,'reference',division,'RHS',meta['rhs_calls'],'seconds',meta['wall_seconds'],flush=True)
                for a,b in ((800,1600),(1600,3200)):
                    row['reference_comparisons'][f'{a}_to_{b}']=reference_gate(arrays[case+'_reference_'+str(a)],
                        arrays[case+'_reference_'+str(b)],arrays[case+'_budgets_'+str(a)],arrays[case+'_budgets_'+str(b)],seed)
                row['rhs_increased']=row['reference_levels'][1]['rhs_calls']<row['reference_levels'][2]['rhs_calls']
                ref_ok=bool(row['reference_comparisons']['1600_to_3200']['checks_passed'] and row['rhs_increased']
                    and all(within(m['initial_roundtrip']['all_bodies'],1e-6,1e-8) for m in row['reference_levels']))
                row['reference_passed']=ref_ok
                expected=arrays[case+'_reference_3200'];budgets=arrays[case+'_budgets_3200']
                modes=variants(seed)
                functions={'legacy_python':lambda:legacy_trajectory(modes['python'],times),
                    'legacy_rust':lambda:legacy_trajectory(modes['rust'],times),
                    'continuous_rust':lambda:dop_trajectory(modes['rust'],times)}
                bounds=None
                for name,function in functions.items():
                    values,stats=function();arrays[case+'_'+name]=values;save()
                    repeat,repeated_stats=function();np.testing.assert_array_equal(values,repeat)
                    np.testing.assert_array_equal(values[0],initial)
                    if bounds is None:bounds=stats['packet_endpoints']
                    if (stats['packet_endpoints']!=bounds or repeated_stats['packet_endpoints']!=bounds
                            or bounds[-1]!=times[-1] or not np.all(np.diff(bounds)>0)
                            or not set(times[1:]).issubset(bounds) or stats['failed'] or not stats['finished']):
                        raise ValueError('Packet/output grid or completion mismatch')
                    candidate=metrics(values,expected,budgets,seed,ref_ok)
                    candidate.update(statistics=stats,repeat_bitexact=True,
                        legacy_checkpoint_continue_exact=(checkpoint_check(modes[name.removeprefix('legacy_')],
                            float(times[len(times)//2])) if name.startswith('legacy_') else None))
                    candidate['negative_raw_angular_control_passed']=candidate['balance']['raw']['angular']>1e-6
                    candidate['checks_passed']=bool(candidate['checks_passed'] and candidate['negative_raw_angular_control_passed']
                        and row['snapshot_controls']['checks_passed'])
                    row['candidates'][name]=candidate;save()
                    print(case,name,candidate['all_bodies'],candidate['relative_pair'],candidate['balance']['corrected'],
                        'passed',candidate['checks_passed'],flush=True)
                row['packet_endpoints_equal']=True;row['packets']=len(bounds)
                durations={name:[] for name in functions}
                for iteration in range(3):
                    order=list(functions) if iteration%2==0 else list(reversed(functions))
                    for name in order:
                        start=perf_counter();values,stats=functions[name]();elapsed=perf_counter()-start
                        np.testing.assert_array_equal(values,arrays[case+'_'+name])
                        if stats['packet_endpoints']!=bounds:raise ValueError('Timed packet grid mismatch')
                        durations[name].append(elapsed)
                row['cost']={name:dict(seconds=rows,median_seconds=median(rows)) for name,rows in durations.items()}
                if to_document(parent)!=before or verify_branch(parent,branch)!=provenance:
                    raise ValueError('Parent/child changed')
                row['parent_child_preserved']=True;save()
            report['warnings']=[str(w.message) for w in caught]
        if any(hashes(bindings)!=bindings for bindings in (source_before,inputs,native,scipy_sources)):
            raise ValueError('Source/input/native/SciPy changed during audit')
        report.update(complete=True,source_input_native_scipy_unchanged=True,
            checks_passed=all(c['checks_passed'] for row in report['cases'].values() for c in row['candidates'].values()))
        save()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    print('complete',output,'checks_passed',report['checks_passed'],flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not run(args.output)['checks_passed']:raise RuntimeError('Three-body checks failed; report retained')


if __name__=='__main__':main()
