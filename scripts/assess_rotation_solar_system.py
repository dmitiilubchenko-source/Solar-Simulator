"""Predeclared 10-body extension, sharing the independently written matrix oracle."""
from pathlib import Path
import sys
import json
import hashlib
from dataclasses import replace
import numpy as np
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.assess_nbody_rotation import reference,represented,differences,internal_invariants
from solar_simulator.ephemerides import solar_system
from solar_simulator.nbody_rotation import integrate,lunar_initial
from solar_simulator.experiment import Settings,create_experiment,advance
from solar_simulator.storage import to_document,from_document


def audit():
    policy=json.loads((ROOT/'scripts/rotation-solar-system-policy.json').read_text(encoding='utf-8'))
    bodies,origin=solar_system(resolved_moon=True);assert len(bodies)==10
    rotations=lunar_initial(bodies,origin);s=rotations[0]
    times=np.linspace(0.,policy['duration_seconds'],policy['samples'])
    kwargs=dict(rtol=policy['production_rtol'],position_atol=1e-4,velocity_atol=1e-10,
        relative_pair=('Earth','Moon'),max_step=21600.)
    print('10 bodies production / tighter / Rust',flush=True)
    primary=integrate(bodies,rotations,times,**kwargs)
    tighter=(replace(s,quaternion_atol=s.quaternion_atol*.03,momentum_atol=s.momentum_atol*.03),)
    strict=integrate(bodies,tighter,times,**dict(kwargs,rtol=3e-13,position_atol=3e-6,velocity_atol=3e-12,max_step=10800.))
    native=integrate(bodies,rotations,times,backend='rust',**kwargs)
    print('10 bodies independent RK45 levels',flush=True)
    refs=[reference(bodies,s,times,tol,21600.) for tol in policy['reference_rtols']]
    inv=internal_invariants(primary,times)
    energy=np.array([v[0] for v in inv]);angular=np.array([[v[2].x,v[2].y,v[2].z] for v in inv])
    q=np.array([v[1][0].quaternion for v in primary])
    diff=differences(represented(primary),refs[-1],bodies,s)
    uncertainty=differences(refs[0],refs[1],bodies,s)
    start=create_experiment(bodies,Settings(86400.,integrator='dop853',rtol=1e-11,
        position_atol=1e-4,velocity_atol=1e-10,relative_pair=('Earth','Moon')),origin=origin,rotations=rotations)
    whole=advance(start,32);half=advance(start,16)
    continued=advance(from_document(to_document(half)),16)
    restart=differences(represented([(whole.bodies,whole.rotations)]),represented([(continued.bodies,continued.rotations)]),bodies,s)
    metrics=dict(energy_relative=float(np.max(abs(energy-energy[0]))/abs(energy[0])),
        angular_momentum_relative=float(np.max(np.linalg.norm(angular-angular[0],axis=1))/np.linalg.norm(angular[0])),
        quaternion_norm=float(np.max(abs(np.linalg.norm(q,axis=1)-1))),reference_difference=diff['maximum'],
        reference_uncertainty=uncertainty['maximum'],restart_difference=restart['maximum'])
    # Descriptive future comparison follows every free numerical run.
    from solar_simulator.orientation import lunar_rotation
    residuals=[]
    for t,(_,states) in zip(times,primary):
        r=Rotation.from_quat(np.roll(states[0].quaternion,-1)).as_matrix();target,_=lunar_rotation(float(t))
        residuals.append(float(np.linalg.norm(Rotation.from_matrix(r.T@target).as_rotvec())))
    parent=json.loads((ROOT/'docs/nbody-rotation-refinement-validation.json').read_text(encoding='utf-8'))
    for path,sha in parent['code_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
    paths=list(parent['code_sha256'])+['scripts/assess_rotation_solar_system.py',
        'scripts/rotation-solar-system-policy.json','tests/test_rotation_runtime_checks.py','src/solar_simulator/app.py',
        'src/solar_simulator/data/solar-system-moon-20261008.json']
    return dict(model=policy['model'],policy=policy,epoch_jd_tdb=origin.epoch_jd_tdb,frame=origin.frame,
        sample_times_seconds=times.tolist(),initial_document=to_document(start),production_options=kwargs,
        reference_atol_over_rtol=.01,invariant_frame='fixed translating initial COM',
        energy_normalization_joules=float(abs(energy[0])),angular_momentum_normalization_kg_m2_s=float(np.linalg.norm(angular[0])),
        metrics=metrics,reference_components=diff,reference_uncertainty_components=uncertainty,
        production_sensitivity=differences(represented(primary),represented(strict),bodies,s),
        python_rust_difference=differences(represented(primary),represented(native),bodies,s),restart_components=restart,
        DE441_attitude_residuals_rad=residuals,DE441_attitude_maximum_rad=max(residuals),
        passed=all(metrics[k]<limit for k,limit in policy['criteria'].items()),
        code_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in paths})


if __name__=='__main__':
    path=ROOT/'docs/rotation-solar-system-validation.json'
    if path.exists():raise FileExistsError('Preserve original audit')
    result=audit();path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(result['metrics'],'passed',result['passed'],flush=True)
    sys.exit(0 if result['passed'] else 1)
