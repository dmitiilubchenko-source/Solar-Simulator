"""Reproduce edited EIH+fixed-J2 model checks; no runtime/default changes."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
from importlib import import_module
import inspect
import json
from pathlib import Path
import platform
from statistics import median
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.edited_j2 import (CASES,fixture,verify_branch,variants,legacy_trajectory,
    checkpoint_check,agreement,reference_gate,metrics,within)
from scripts.fixed_j2_ias import reference,entries,figure_force,scales,balances,dop_trajectory
from scripts.newton_year import ROOT,hashes
from scripts.assess_sandbox_planets import states
from solar_simulator.storage import to_document


def run(output,*,cases=CASES,factory=fixture,protocol='docs/edited-j2-protocol.md',extra_sources=()):
    output=Path(output).resolve()
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a new output path; preserve earlier audits')
    output.parent.mkdir(parents=True,exist_ok=True)
    prior=json.loads((ROOT/'docs/fixed-j2-ias-validation.json').read_bytes())
    for group in ('source_sha256','native_sha256'):
        bindings=prior['measurements'][group]
        if hashes(bindings)!=bindings:raise ValueError('Qualified fixedJ2 sources/binary changed')
    paths=[p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    paths += ['scripts/'+p+'.py' for p in ('assess_edited_j2','edited_j2','fixed_j2_ias',
        'eih_year','ias15_eih','ias15_reference','newton_year','assess_sandbox_planets')]
    paths += [protocol,'tests/test_edited_j2.py',Path(inspect.getsourcefile(factory)).resolve().relative_to(ROOT).as_posix()]
    paths += list(extra_sources)
    paths=list(dict.fromkeys(paths));source_before=hashes(paths)
    inputs=hashes(['docs/fixed-j2-ias-validation.json'])
    native_paths=[Path(import_module(n).__file__) for n in ('solar_native','solar_native.solar_native')]
    native=hashes(native_paths)
    import scipy.integrate._ivp.base as base
    import scipy.integrate._ivp.rk as rk
    scipy_paths=[Path(base.__file__),Path(rk.__file__)];scipy_source=hashes(scipy_paths)
    report=dict(protocol=protocol,started_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=source_before,input_sha256=inputs,native_sha256=native,
        scipy_source_sha256=scipy_source,environment=dict(python=platform.python_version(),
            platform=platform.platform(),numpy=np.__version__,scipy=scipy.__version__),
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
            for case in cases:
                parent,branch,times,period=factory(case)
                provenance=verify_branch(parent,branch);before=to_document(parent)
                seed=branch.child;initial=states(seed.bodies);names=[b.name for b in seed.bodies]
                masses=np.array([b.mass for b in seed.bodies])
                scale=scales(initial,masses,entries(seed),seed.settings.physics)
                row=dict(provenance=provenance,settings=asdict(seed.settings),names=names,
                    masses_kg=masses.tolist(),samples=len(times),duration_seconds=float(times[-1]),
                    nominal_period_seconds=period,reference_levels=[],reference_comparisons={},candidates={})
                report['cases'][case]=row
                arrays[case+'_initial'],arrays[case+'_times']=initial,times
                for level,(rtol,division) in enumerate(((1e-13,200),(3e-14,400),(3e-14,800))):
                    start=perf_counter();values,budgets,metadata=reference(seed,times,rtol,period/division)
                    metadata['wall_seconds']=perf_counter()-start
                    metadata['initial_roundtrip']=agreement(values[:1],initial[None],names)
                    metadata['balance']=balances(values,budgets,seed)
                    arrays[case+'_reference_'+str(level)]=values
                    arrays[case+'_budgets_'+str(level)]=budgets
                    row['reference_levels'].append(metadata);save()
                    print(case,'reference',level,'RHS',metadata['rhs_calls'],'seconds',metadata['wall_seconds'],flush=True)
                for level in (1,2):
                    row['reference_comparisons'][f'{level-1}_to_{level}']=reference_gate(
                        arrays[case+'_reference_'+str(level-1)],arrays[case+'_reference_'+str(level)],
                        arrays[case+'_budgets_'+str(level-1)],arrays[case+'_budgets_'+str(level)],seed)
                ref_ok=(row['reference_comparisons']['1_to_2']['checks_passed']
                    and all(within(m['initial_roundtrip']['all_bodies'],1e-6,1e-8) for m in row['reference_levels']))
                row['reference_passed']=bool(ref_ok)
                expected=arrays[case+'_reference_2'];budgets=arrays[case+'_budgets_2']
                force=masses[:,None]*figure_force(initial[:,:3],masses,entries(seed))
                missing=force.copy();missing[0]=0.
                row['reaction_control']=dict(correct_scaled_net_force=float(np.linalg.norm(force.sum(axis=0))/np.linalg.norm(force,axis=1).sum()),
                    missing_source_scaled_net_force=float(np.linalg.norm(missing.sum(axis=0))/np.linalg.norm(force,axis=1).sum()))
                versions=variants(seed)
                functions={'legacy_python':lambda:legacy_trajectory(versions['python'],times),
                    'legacy_rust':lambda:legacy_trajectory(versions['rust'],times),
                    'continuous_rust':lambda:dop_trajectory(versions['rust'],times)}
                bounds=None
                for name,function in functions.items():
                    values,stats=function();arrays[case+'_'+name]=values;save()
                    np.testing.assert_array_equal(values[0],initial)
                    repeat,repeated_stats=function();np.testing.assert_array_equal(values,repeat)
                    if bounds is None:bounds=stats['packet_endpoints']
                    if (stats['packet_endpoints']!=bounds or repeated_stats['packet_endpoints']!=bounds
                            or not set(times[1:]).issubset(bounds) or bounds[-1]!=times[-1]
                            or not np.all(np.diff(bounds)>0) or stats['failed'] or not stats['finished']):
                        raise ValueError('Different or incomplete packet/output grid')
                    result=metrics(values,expected,budgets,seed,ref_ok)
                    result.update(statistics=stats,repeat_bitexact=True,
                        legacy_checkpoint_continue_exact=(checkpoint_check(versions[name.removeprefix('legacy_')],
                            float(times[len(times)//2])) if name.startswith('legacy_') else None))
                    result['negative_raw_angular_control_passed']=result['balance']['raw']['angular']>1e-6
                    result['checks_passed']=bool(result['checks_passed'] and result['negative_raw_angular_control_passed']
                        and row['reaction_control']['correct_scaled_net_force']<5e-13
                        and row['reaction_control']['missing_source_scaled_net_force']>1e-3)
                    row['candidates'][name]=result;save()
                    print(case,name,result['all_bodies'],result['relative_pair'],result['balance']['corrected'],
                        'passed',result['checks_passed'],flush=True)
                row['packet_endpoints_equal']=True;row['packets']=len(bounds)
                durations={name:[] for name in functions}
                for iteration in range(3):
                    order=list(functions) if iteration%2==0 else list(reversed(functions))
                    for name in order:
                        start=perf_counter();values,stats=functions[name]();elapsed=perf_counter()-start
                        np.testing.assert_array_equal(values,arrays[case+'_'+name])
                        if stats['packet_endpoints']!=bounds:raise ValueError('Timed grid differs')
                        durations[name].append(elapsed)
                row['cost']={name:dict(seconds=rows,median_seconds=median(rows)) for name,rows in durations.items()}
                if to_document(parent)!=before or verify_branch(parent,branch)!=provenance:
                    raise ValueError('Parent/child/provenance changed')
                row['parent_child_preserved']=True;save()
            report['warnings']=[str(w.message) for w in caught]
        if (hashes(paths)!=source_before or hashes(inputs)!=inputs or hashes(native_paths)!=native
                or hashes(scipy_paths)!=scipy_source):
            raise ValueError('Source/input/actual native/SciPy changed during calculation')
        report['source_input_native_scipy_unchanged']=True
        report['complete']=True
        report['checks_passed']=all(c['checks_passed'] for row in report['cases'].values() for c in row['candidates'].values())
        save()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    print('complete',output,'checks_passed',report['checks_passed'],flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not run(args.output)['checks_passed']:raise RuntimeError('Declared model checks failed; results preserved')


if __name__=='__main__':main()
