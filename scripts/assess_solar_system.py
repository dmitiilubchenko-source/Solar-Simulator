"""Separate numerical error (same Newtonian model) from JPL model discrepancy."""
import argparse
from dataclasses import replace
import hashlib
import json
from math import isfinite
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from solar_simulator.ephemerides import solar_system, EXPECTED_IDS
from solar_simulator.experiment import create_experiment, Settings, advance
from solar_simulator.simulation import AU, G, total_energy

YEAR = 365.25*86400


def independent_reference(initial, times):
    """Different integrator (RK45), dimensionless full interaction matrix."""
    count=len(initial)
    state=np.array([[b.position.x/AU,b.position.y/AU,b.position.z/AU,
                     b.velocity.x*YEAR/AU,b.velocity.y*YEAR/AU,b.velocity.z*YEAR/AU] for b in initial])
    coefficients=np.array([G*b.mass*YEAR**2/AU**3 for b in initial])
    def rhs(t,y):
        q=y.reshape(count,6)
        delta=q[None,:,:3]-q[:,None,:3]
        distance=np.linalg.norm(delta,axis=2)
        np.fill_diagonal(distance,np.inf)
        acceleration=np.sum(delta*(coefficients[None,:]/distance**3)[:,:,None],axis=1)
        return np.concatenate((q[:,3:],acceleration),axis=1).ravel()
    solutions=[]
    # Confirm reference stability rather than trusting a single RK45 run.
    for tolerance in (1e-12,1e-13,3e-14):
        solution=solve_ivp(rhs,(0,times[-1]/YEAR),state.ravel(),method='RK45',t_eval=times/YEAR,
                           rtol=tolerance,atol=1e-15)
        if not solution.success:
            raise RuntimeError(solution.message)
        states=solution.y.T.reshape(len(times),count,6)
        states[:,:,:3]*=AU;states[:,:,3:]*=AU/YEAR
        solutions.append(states)
    consistency=np.linalg.norm(solutions[-2][:,:,:3]-solutions[-1][:,:,:3],axis=2).max()
    if not isfinite(consistency) or consistency>10_000:
        raise RuntimeError(f'Independent reference is not converged: {consistency} m')
    return solutions[-1],float(consistency)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,default=Path('docs/solar-system-reference.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/solar-system-validation.json'))
    args=parser.parse_args()
    initial,origin=solar_system()
    doc=json.loads(args.reference.read_text(encoding='utf-8'))
    if (doc['dataset_sha256']!=origin.dataset_sha256 or doc['frame']!=origin.frame or doc['center']!=origin.center
        or doc['ephemeris']!=origin.ephemeris or doc['units']!='SI' or [b['id'] for b in doc['bodies']]!=list(EXPECTED_IDS)):
        raise ValueError('Reference does not match initial dataset')
    times=(np.array(doc['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    if len(times)!=13 or times[0]!=0 or abs(times[-1]-YEAR)>1e-3:
        raise ValueError('Expected one Julian year of reference data')
    reference,consistency=independent_reference(initial,times)
    actual=[]
    state=create_experiment(initial,Settings(3600,integrator='dop853'),origin=origin)
    initial_energy=total_energy(initial)
    energy_error=0.0
    for time in times:
        if time>state.time:
            duration=float(time-state.time)
            state=advance(replace(state,settings=replace(state.settings,dt=duration)),1)
        actual.append([[b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z] for b in state.bodies])
        energy_error=max(energy_error,abs((total_energy(state.bodies)-initial_energy)/initial_energy))
    actual=np.array(actual)
    horizons=np.stack([np.array([s['position']+s['velocity'] for s in b['states']]) for b in doc['bodies']],axis=1)
    rows=[]
    for i,b in enumerate(initial):
        rows.append(dict(name=b.name,
            numerical_position_error_metres=float(np.linalg.norm(actual[:,i,:3]-reference[:,i,:3],axis=1).max()),
            numerical_velocity_error_m_per_s=float(np.linalg.norm(actual[:,i,3:]-reference[:,i,3:],axis=1).max()),
            jpl_position_discrepancy_metres=float(np.linalg.norm(actual[:,i,:3]-horizons[:,i,:3],axis=1).max()),
            jpl_velocity_discrepancy_m_per_s=float(np.linalg.norm(actual[:,i,3:]-horizons[:,i,3:],axis=1).max())))
    checks=dict(numerical_targets=all(r['numerical_position_error_metres']<100_000 and r['numerical_velocity_error_m_per_s']<.1 for r in rows))
    result=dict(schema=1,dataset_sha256=origin.dataset_sha256,interval_seconds=YEAR,sample_count=len(times),
        reference='RK45, dimensionless full interaction matrix; rtol 3e-14; atol 1e-15',
        reference_position_consistency_metres=consistency,relative_energy_error=energy_error,
        warning='JPL discrepancies include omitted physics/bodies and are not pure integration errors',bodies=rows,checks=checks)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(checks))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__=='__main__':
    main()
