"""Six predeclared conditions for the two isolated roundoff candidates."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
import hashlib
import json
from math import cos, sin, sqrt, pi
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import numpy as np

from scripts.assess_kepler_phase import ROOT, differences, evaluate, fixture, fingerprints, maximum, decimal_relative
from scripts.assess_sandbox_planets import states
from scripts.kepler_reference import propagate
from scripts.kepler_roundoff import solver_class
from solar_simulator.continuous import ContinuousRun
from solar_simulator.simulation import G, AU, SUN_MASS, EARTH_MASS
from solar_simulator.vector3 import Vector3


CASES=(('circular',0.,0.,False),('moderate',.5,0.,False),
       ('original',.95,0.,False),('permuted',.95,0.,True),
       ('apocentre',.95,pi,False),('eccentric_phase',.97,1.,False))


def holdout_fixture(e,anomaly,permuted):
    seed,old_times=fixture(e)
    period=old_times[-1]/2
    if anomaly or permuted:
        arrays=states(seed.bodies)
        if anomaly:
            axis=np.array([1.,2.,-1.]);axis/=np.linalg.norm(axis)
            tangent=np.cross(axis,np.array([0.,1.,1.]));tangent/=np.linalg.norm(tangent)
            sine,cosine=(0.,-1.) if anomaly==pi else (sin(anomaly),cos(anomaly))
            position=AU*((cosine-e)*axis+sqrt(1-e*e)*sine*tangent)
            rate=sqrt(G*(SUN_MASS+EARTH_MASS)/AU**3)
            velocity=AU*rate/(1-e*cosine)*(-sine*axis+sqrt(1-e*e)*cosine*tangent)
            fraction=EARTH_MASS/(SUN_MASS+EARTH_MASS)
            offset,drift=np.array([3e9,-2e9,1e9]),np.array([75.,-50.,25.])
            arrays=np.array([np.concatenate((offset-fraction*position,drift-fraction*velocity)),
                np.concatenate((offset+(1-fraction)*position,drift+(1-fraction)*velocity))])
        if permuted:
            arrays=arrays[:,[1,2,0,4,5,3]]*np.array([1.,-1.,-1.,1.,-1.,-1.])
        bodies=[replace(b,position=Vector3(*row[:3]),velocity=Vector3(*row[3:])) for b,row in zip(seed.bodies,arrays)]
        seed=replace(seed,bodies=bodies,initial=bodies)
    times=np.unique(np.concatenate((old_times,period*(np.arange(16)+.37)/8,
        period*np.array([.4999,.5,.5001,1.4999,1.5,1.5001]))))
    return seed,times


def reference_rows(seed,times):
    with localcontext() as context:
        context.prec=110
        relative=decimal_relative(states(seed.bodies))
        mu=D.from_float(G)*sum(D.from_float(float(b.mass)) for b in seed.bodies)
        expected=[];uncertainties=[]
        start=perf_counter()
        for time in times:
            elapsed=D.from_float(float(time))
            low=propagate(relative[:3],relative[3:],mu,elapsed,precision=70)
            high=propagate(relative[:3],relative[3:],mu,elapsed,precision=100)
            uncertainties.append(differences(low,high));expected.append(high)
        uncertainty=maximum(uncertainties)
        assert uncertainty['position_metres']<1e-6 and uncertainty['velocity_m_per_s']<1e-12
        assert expected[0]==(relative[:3],relative[3:])
        return expected,dict(**uncertainty,wall_seconds=perf_counter()-start)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous results')
    sources=fingerprints()
    for name in ('scripts/assess_kepler_holdout.py','scripts/kepler_roundoff.py',
                 'docs/kepler-holdout-protocol.md'):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    results={};arrays={}
    for name,e,anomaly,permuted in CASES:
        seed,times=holdout_fixture(e,anomaly,permuted)
        arrays[f'{name}_times']=times
        expected,uncertainty=reference_rows(seed,times)
        rows={}
        for variant in ('original','sum','carry'):
            selected=(ContinuousRun if variant=='original' else solver_class(
                accurate_sums=variant=='sum',compensated=variant=='carry',
                divisor=64,mu=G*sum(b.mass for b in seed.bodies)))
            if variant=='original':
                values,metrics=evaluate(seed,times,expected)
            else:
                with patch('solar_simulator.continuous.PerBodyDOP853',selected):
                    values,metrics=evaluate(seed,times,expected)
            arrays[f'{name}_{variant}']=values;rows[variant]=metrics
            print(name,variant,{k:v for k,v in metrics.items() if k!='sampled_errors'},flush=True)
        arrays[f'{name}_reference']=np.array(expected,dtype=float)
        results[name]=dict(eccentricity_nominal=e,initial_anomaly_nominal=anomaly,
            exact_signed_permutation=permuted,samples=len(times),oracle_uncertainty=uncertainty,
            initial_state=states(seed.bodies).tolist(),results=rows,
            decimal_reference=[[list(map(str,group)) for group in row] for row in expected])
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(dict(protocol='docs/kepler-holdout-protocol.md',source_sha256=sources,
            npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
            source_unchanged=True,results=results,runtime_modified=False,general_release_passed=False),
            stream,indent=2,allow_nan=False);stream.write('\n')
    print('Saved',output,flush=True)


if __name__=='__main__':
    main()
