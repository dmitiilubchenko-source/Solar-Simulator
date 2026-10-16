"""Matched-initial, independent elliptic validation; never changes runtime."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
import hashlib
import json
from math import pi, sqrt
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_continuous import invariant_rows, json_scalar
from scripts.assess_sandbox_planets import states
from scripts.kepler_reference import propagate
from solar_simulator.continuous import ContinuousRun
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.simulation import AU, G, SUN_MASS, EARTH_MASS, Body
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[1]


def fixture(e):
    """Exactly the construction and 60 epochs of the original failed audit."""
    axis=np.array([1.,2.,-1.]);axis/=np.linalg.norm(axis)
    tangent=np.cross(axis,np.array([0.,1.,1.]));tangent/=np.linalg.norm(tangent)
    rate=sqrt(G*(SUN_MASS+EARTH_MASS)/AU**3)
    period=2*pi/rate
    fraction=EARTH_MASS/(SUN_MASS+EARTH_MASS)
    offset,drift=np.array([3e9,-2e9,1e9]),np.array([75.,-50.,25.])
    p=AU*(1-e)*axis;v=AU*rate*sqrt((1+e)/(1-e))*tangent
    bodies=[Body('A',SUN_MASS,Vector3(*(offset-fraction*p)),Vector3(*(drift-fraction*v))),
            Body('B',EARTH_MASS,Vector3(*(offset+(1-fraction)*p)),Vector3(*(drift+(1-fraction)*v)))]
    seed=create_experiment(bodies,Settings(period/50,backend='rust',integrator='dop853',
        relative_pair=('A','B'),rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13))
    times=np.unique(np.concatenate((np.linspace(0,2*period,51),period*np.array(
        [.0001,.001,.01,.999,1.0001,1.001,1.01,1.999,1.9999]))))
    return seed,times


def decimal_relative(array):
    # Subtraction is exact in the active >=110 digit context for this fixture.
    return tuple(D.from_float(float(b))-D.from_float(float(a)) for a,b in zip(array[0],array[1]))


def differences(actual, expected):
    with localcontext() as context:
        context.prec=110
        groups=[tuple(abs(a-b) for a,b in zip(left,right)) for left,right in zip(actual,expected)]
        return dict(position_metres=float(sum(x*x for x in groups[0]).sqrt()),
                    velocity_m_per_s=float(sum(x*x for x in groups[1]).sqrt()))


def maximum(rows):
    return {key:max(row[key] for row in rows) for key in rows[0]}


def references(seed,times):
    with localcontext() as context:
        context.prec=110
        array=states(seed.bodies)
        exact=decimal_relative(array)
        encoded=tuple(D.from_float(float(x)) for x in array[1]-array[0])
        mu=D.from_float(G)*(D.from_float(SUN_MASS)+D.from_float(EARTH_MASS))
        native_mu=D.from_float(G*SUN_MASS)+D.from_float(G*EARTH_MASS)
        expected=[];precision=[];representation=[];gm=[];rounding=[]
        start=perf_counter()
        for time in times:
            elapsed=D.from_float(float(time))
            low=propagate(exact[:3],exact[3:],mu,elapsed,precision=70)
            high=propagate(exact[:3],exact[3:],mu,elapsed,precision=100)
            encoded_ref=propagate(encoded[:3],encoded[3:],mu,elapsed,precision=70)
            native_ref=propagate(exact[:3],exact[3:],native_mu,elapsed,precision=70)
            precision.append(differences(low,high))
            representation.append(differences(encoded_ref,high))
            gm.append(differences(native_ref,high))
            rounded=tuple(tuple(D.from_float(float(x)) for x in group) for group in high)
            rounding.append(differences(rounded,high))
            expected.append(high)
        assert expected[0] == (exact[:3],exact[3:])
        uncertainty=maximum(precision)
        assert uncertainty['position_metres']<1e-6 and uncertainty['velocity_m_per_s']<1e-12
        return expected,dict(precision_convergence=uncertainty,
            float_output_rounding=maximum(rounding),
            rounded_initial_relative_effect=maximum(representation),
            rounded_native_gm_effect=maximum(gm),
            mu_exact=str(mu),mu_native_rounded_sum=str(native_mu),wall_seconds=perf_counter()-start,
            exact_t0_passed=True)


def evaluate(seed,times,expected,legacy=False):
    session=None if legacy else ContinuousRun(seed,float(times[-1]))
    current=seed;array=[];rows=[]
    initial_energy,initial_p,initial_l=invariant_rows(seed.bodies)
    p_scale=sum(b.mass*b.velocity.magnitude() for b in seed.bodies)
    energy_drift=angular_drift=linear_drift=0.
    start=perf_counter()
    with localcontext() as context:
        context.prec=110
        for time,reference in zip(times,expected):
            if legacy:
                current=advance(replace(seed,settings=replace(seed.settings,dt=float(time))),1) if time>0 else seed
            else:
                while current.time<time:
                    current=session.next(1,until=float(time))
            assert current.time==time
            state=states(current.bodies);array.append(state)
            actual=decimal_relative(state)
            rows.append(differences((actual[:3],actual[3:]),reference))
            energy,linear,angular=invariant_rows(current.bodies)
            energy_drift=max(energy_drift,abs(energy-initial_energy)/abs(initial_energy))
            angular_drift=max(angular_drift,float(np.linalg.norm(angular-initial_l)/np.linalg.norm(initial_l)))
            linear_drift=max(linear_drift,float(np.linalg.norm(linear-initial_p)/p_scale))
    elapsed=perf_counter()-start
    metrics=maximum(rows)
    passed=(metrics['position_metres']<.1 and metrics['velocity_m_per_s']<1e-6
        and max(energy_drift,angular_drift,linear_drift)<1e-10)
    return np.array(array),dict(**metrics,relative_energy_drift=energy_drift,
        relative_angular_drift=angular_drift,scaled_momentum_drift=linear_drift,
        checks_passed=passed,wall_seconds=elapsed,
        worst_position_time_seconds=float(times[max(range(len(rows)),key=lambda i:rows[i]['position_metres'])]),
        sampled_errors=rows,
        **(session.statistics if session else dict(legacy_from_same_initial_per_epoch=True,
            cost_comparable_to_continuation=False)))


def fingerprints():
    paths=[]
    for folder in ('src/solar_simulator','rust/solar_core/src','rust/solar_native/src'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file()
                     and p.suffix in ('.py','.rs','.json'))
    paths.extend(ROOT/name for name in ('scripts/kepler_reference.py','scripts/assess_kepler_phase.py',
        'scripts/kepler_cache.py','scripts/assess_continuous.py','docs/kepler-phase-protocol.md'))
    paths.extend((ROOT/'.venv/Lib/site-packages').glob('solar_native/*.pyd'))
    paths.extend(ROOT/'.venv/Lib/site-packages/scipy/integrate/_ivp'/name for name in ('rk.py','base.py'))
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous results')
    output.parent.mkdir(parents=True,exist_ok=True)
    sources=fingerprints();results={};arrays={}
    for e in (0.,.5,.95):
        seed,times=fixture(e)
        expected,oracle=references(seed,times)
        rows={}
        for mode in ('continuous','legacy'):
            values,metrics=evaluate(seed,times,expected,legacy=mode=='legacy')
            arrays[f'{e}_{mode}']=values;rows[mode]=metrics
            print(e,mode,{k:v for k,v in metrics.items() if k!='sampled_errors'},flush=True)
        arrays[f'{e}_reference']=np.array(expected,dtype=float)
        results[str(e)]=dict(oracle=oracle,results=rows,
            decimal_reference=[[list(map(str,group)) for group in row] for row in expected])
    arrays['times']=times
    assert sources==fingerprints()
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    receipt=dict(protocol='docs/kepler-phase-protocol.md',source_sha256=sources,
        npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
        samples=len(times),results=results,source_unchanged=True,
        checks_passed=all(row['results']['continuous']['checks_passed'] for row in results.values()),
        runtime_modified=False,old_failures_retained=True)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(receipt,stream,indent=2,allow_nan=False,default=json_scalar);stream.write('\n')
    print('Saved',output,'checks_passed',receipt['checks_passed'],flush=True)
    if not receipt['checks_passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
