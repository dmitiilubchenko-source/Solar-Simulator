"""Three-day counterfactual Solar pilot using the frozen AU/year+EMB oracle."""
import argparse
from dataclasses import asdict,replace
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_sandbox_models import independent_reference,load_oracle,figure_reference
from scripts.eih_year import force_terms
from scripts.edited_j2 import verify_branch,variants,legacy_trajectory,checkpoint_check
from scripts.fixed_j2_ias import dop_trajectory
from scripts.newton_year import ROOT,hashes,NAMES,agreement,errors,INPUTS
from scripts.assess_sandbox_planets import states
from solar_simulator.sandbox import branch_experiment
from solar_simulator.simulation import G,AU
from solar_simulator.relativity import C
from solar_simulator.storage import load,to_document
from solar_simulator.vector3 import Vector3

CASES=('sun_mass','earth_position','moon_velocity')
YEAR=31557600.


def fixture(case):
    if case not in CASES:raise ValueError('Undeclared Solar edit')
    path='docs/solar-sandbox-strict-checkpoint.json'
    if hashes([path])[path]!=INPUTS[path]:raise ValueError('Strict input changed')
    parent=load(ROOT/path);index={'sun_mass':0,'earth_position':3,'moon_velocity':4}[case]
    b=parent.bodies[index]
    if case=='sun_mass':new=replace(b,mass=b.mass*1.25)
    if case=='earth_position':new=replace(b,position=b.position.add(Vector3(1e6,-2e6,3e6)))
    if case=='moon_velocity':new=replace(b,velocity=b.velocity.add(Vector3(100.,-50.,25.)))
    branch=branch_experiment(parent,replacements=((b.name,new),))
    return parent,branch,np.linspace(0.,259200.,25)


def oracle_check(seed,oracle):
    q=states(seed.bodies);p=q[:,:3]/AU;v=q[:,3:]*YEAR/AU
    mu=np.array([G*b.mass*YEAR**2/AU**3 for b in seed.bodies]);c=C*YEAR/AU
    n,pn=force_terms(p,v,mu,c)
    full=float(np.linalg.norm(oracle(p,v,mu,c)-n-pn,axis=1).max()/np.linalg.norm(n+pn,axis=1).max())
    _,strong=force_terms(p,v,mu,c/10)
    scalar=oracle(p,v,mu,c/10)-oracle(p,v,mu,1e30)
    gap=float(np.linalg.norm(scalar-strong,axis=1).max()/np.linalg.norm(strong,axis=1).max())
    return dict(physical_c_full_relative_error=full,amplified_pn_relative_error=gap,
        checks_passed=bool(full<3e-14 and gap<3e-9))


def within(row,p,v):return row['position_metres']<p and row['velocity_m_per_s']<v


def run(output):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools'):raise ValueError('Pilot output must be inside project .tools')
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():raise ValueError('Use fresh output')
    output.parent.mkdir(parents=True,exist_ok=True)
    cache_names={case:output.parent.relative_to(ROOT/'.tools').as_posix()+'/'+output.stem+'-reference-'+case for case in CASES}
    cache_paths={case:ROOT/'.tools'/(name+'.npz') for case,name in cache_names.items()}
    if any(p.exists() for p in cache_paths.values()):raise ValueError('Preserve old reference caches')
    prior=json.loads((ROOT/'docs/strict-profile-validation.json').read_bytes())
    if hashes(prior['source_sha256'])!=prior['source_sha256']:raise ValueError('Qualified Solar source changed')
    oracle=load_oracle();dll=ROOT/'.tools'/('independent-eih-'+oracle.source_sha256[:16]+'.dll')
    from importlib import import_module
    native_paths=[Path(import_module(n).__file__) for n in ('solar_native','solar_native.solar_native')]
    import scipy.integrate._ivp.rk as rk
    import scipy.integrate._ivp.base as base
    dependency_paths=[dll,*native_paths,Path(rk.__file__),Path(base.__file__)]
    dependencies=hashes(dependency_paths)
    paths=list(prior['source_sha256'])+['scripts/'+n+'.py' for n in ('assess_edited_solar',
        'assess_relative_coordinates','assess_sandbox_models','edited_j2','fixed_j2_ias',
        'eih_year','ias15_eih','newton_year','assess_sandbox_planets')]
    paths+=['tests/test_edited_solar.py','docs/edited-solar-protocol.md']
    paths+= [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    sources=hashes(list(dict.fromkeys(paths)))
    inputs=hashes(['docs/solar-sandbox-strict-checkpoint.json','docs/strict-profile-validation.json'])
    report=dict(protocol='docs/edited-solar-protocol.md',source_sha256=sources,input_sha256=inputs,
        dependency_sha256=dependencies,scalar_oracle_source_sha256=oracle.source_sha256,compiler=oracle.compiler_version,
        cases={},complete=False,general_release=False,runtime_modified=False,jpl_comparison=False,source_integrals_verified=False)
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
                parent,branch,times=fixture(case);seed=branch.child;initial=states(seed.bodies)
                provenance=verify_branch(parent,branch);before=to_document(parent)
                row=dict(provenance=provenance,settings=asdict(seed.settings),masses_kg=[b.mass for b in seed.bodies],
                    names=[b.name for b in seed.bodies],oracle_snapshot=oracle_check(seed,oracle),candidates={})
                if tuple(row['names'])!=NAMES:raise ValueError('Wrong Solar order')
                report['cases'][case]=row;arrays[case+'_initial']=initial;arrays[case+'_times']=times
                calls=[]
                def counted_figure(p,mu,figures,names,t,pair):
                    if t==0.:calls.append(0)
                    calls[-1]+=1
                    return figure_reference(p,mu,figures,names,t,pair)
                start=perf_counter()
                expected,convergence=independent_reference(seed.bodies,seed.settings.figures,times,
                    levels=((1e-13,1800.),(3e-14,900.),(3e-14,450.)),cache_name=cache_names[case],
                    acceleration_function=oracle,figure_acceleration_function=counted_figure)
                row.update(reference_wall_seconds=perf_counter()-start,reference_rhs_calls=calls,reference_comparisons={})
                with np.load(cache_paths[case],allow_pickle=False) as data:
                    np.testing.assert_array_equal(data['times'],times)
                    for i in range(3):arrays[case+'_reference_'+str(i)]=data['level_'+str(i)].copy()
                for i in (1,2):row['reference_comparisons'][f'{i-1}_to_{i}']=agreement(arrays[case+'_reference_'+str(i-1)],
                    arrays[case+'_reference_'+str(i)],list(NAMES))
                last=row['reference_comparisons']['1_to_2'];initial_error=agreement(expected[:1],initial[None],list(NAMES))
                ref_ok=bool(len(calls)==3 and calls[2]>calls[1] and within(last['all_bodies'],1.,1e-6)
                    and within(last['moon_relative_to_earth'],.01,1e-7) and within(initial_error['all_bodies'],.002,1e-8)
                    and initial_error['moon_relative_to_earth']['position_metres']<.0001 and row['oracle_snapshot']['checks_passed'])
                row.update(reference_passed=ref_ok,reference_initial_roundtrip=initial_error,
                    reference_cache_sha256=hashes([cache_paths[case]]).popitem()[1]);save()
                versions=variants(seed)
                functions={'legacy_python':lambda:legacy_trajectory(versions['python'],times),
                    'legacy_rust':lambda:legacy_trajectory(versions['rust'],times),
                    'continuous_rust':lambda:dop_trajectory(versions['rust'],times)}
                bounds=None
                for name,function in functions.items():
                    values,stats=function();arrays[case+'_'+name]=values;save()
                    repeated,other=function();np.testing.assert_array_equal(values,repeated);np.testing.assert_array_equal(values[0],initial)
                    if bounds is None:bounds=stats['packet_endpoints']
                    if stats['packet_endpoints']!=bounds or other['packet_endpoints']!=bounds or bounds[-1]!=times[-1]:
                        raise ValueError('Different output/packet grid')
                    per={n:errors(values[:,i],expected[:,i]) for i,n in enumerate(NAMES)}
                    a=agreement(values,expected,list(NAMES))
                    passed=bool(ref_ok and all(within(e,10.,1e-4) for e in per.values())
                        and within(a['moon_relative_to_earth'],.1,1e-5))
                    row['candidates'][name]=dict(**a,per_body=per,statistics=stats,repeat_bitexact=True,checks_passed=passed,
                        legacy_checkpoint_continue_exact=(checkpoint_check(versions[name.removeprefix('legacy_')],float(times[12]))
                            if name.startswith('legacy_') else None))
                    print(case,name,a,'passed',passed,flush=True);save()
                durations={n:[] for n in functions}
                for iteration in range(3):
                    for name in (list(functions) if iteration%2==0 else list(reversed(functions))):
                        start=perf_counter();values,stats=functions[name]();elapsed=perf_counter()-start
                        np.testing.assert_array_equal(values,arrays[case+'_'+name])
                        if stats['packet_endpoints']!=bounds:raise ValueError('Timed grid differs')
                        durations[name].append(elapsed)
                row['cost']={n:dict(seconds=v,median_seconds=median(v)) for n,v in durations.items()}
                if to_document(parent)!=before or verify_branch(parent,branch)!=provenance:raise ValueError('Parent/child changed')
                row.update(parent_child_preserved=True,packet_endpoints_equal=True,samples=len(times),duration_seconds=float(times[-1]));save()
            report['warnings']=[str(w.message) for w in caught]
        if any(hashes(b)!=b for b in (sources,inputs,dependencies)):raise ValueError('Source/input/actual binary changed')
        report.update(complete=True,source_input_dependencies_unchanged=True,
            checks_passed=all(c['checks_passed'] for row in report['cases'].values() for c in row['candidates'].values()))
        save()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not run(args.output)['checks_passed']:raise RuntimeError('Pilot criteria failed; report retained')


if __name__=='__main__':main()
