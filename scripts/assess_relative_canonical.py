"""Predeclared 32-day Jacobi/independent matrix research audit, no checkpoint."""
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts.assess_canonical_solar import initial_checkpoint
from scripts.canonical_checkpoint import CanonicalDOP853, verify_sources
from scripts.relative_canonical import Pair, from_cartesian, to_cartesian, rhs, invariants
from scripts.independent_relative_canonical import matrix_rhs
from scripts.assess_rigid_pn import attitudes, convert_reference


def differences(first, first_r, second, second_r, units, pair, figure, spin_scale):
    """Report each absolute body and the stored relative vector separately."""
    a,b = np.asarray(first),np.asarray(second); ra,rb = np.asarray(first_r),np.asarray(second_r)
    count = len(pair.masses)
    if (a.ndim != 2 or a.shape != b.shape or a.shape[1] != 9*count
            or ra.shape != rb.shape or ra.shape != (len(a),3,3)
            or not all(np.all(np.isfinite(v)) for v in [a,b,ra,rb])
            or not 0 <= figure < count or not np.isfinite(spin_scale) or spin_scale <= 0):
        raise ValueError('Matched finite grids and positive figure spin scale required')
    aa,bb = a.reshape(-1,3,count,3),b.reshape(-1,3,count,3)
    # Difference first, then transform the difference to avoid two AU-scale exports.
    error = aa[:,0]-bb[:,0]; fa,fd = pair.fractions
    centre,relative = error[:,pair.first].copy(),error[:,pair.second].copy()
    error[:,pair.first] = centre-fd*relative
    error[:,pair.second] = centre+fa*relative
    position = np.linalg.norm(error*units.length_m,axis=-1)
    return dict(positions_m=float(position.max()),positions_per_body_m=position.max(axis=0).tolist(),
        earth_moon_position_m=float(np.linalg.norm(relative*units.length_m,axis=1).max()),
        figure_spin_relative=float(np.linalg.norm(aa[:,2,figure]-bb[:,2,figure],axis=1).max()/spin_scale),
        attitude_matrix=float(np.linalg.norm(ra-rb,axis=(1,2)).max()))


def audit():
    output = ROOT/'docs/relative-canonical-validation.json'
    if output.exists(): raise FileExistsError('Preserve original relative canonical audit')
    policy = json.loads((ROOT/'scripts/relative-canonical-policy.json').read_text(encoding='utf-8'))
    original_policy = json.loads((ROOT/policy['input_policy']).read_text(encoding='utf-8'))
    cp,units,names = initial_checkpoint(original_policy); verify_sources(cp,ROOT)
    params = cp.parameters; count = len(names); figure = params.index
    if (policy['pair'] != [names.index('Earth'),figure] or policy['physical_lunar_mapping_certified'] is not False
            or policy['duration_seconds'] != original_policy['duration_seconds']
            or policy['samples'] != original_policy['samples']):
        raise ValueError('Incompatible fixed audit contract')
    pair = Pair(params.orbital.masses,*policy['pair']); initial = from_cartesian(cp.state,pair)
    paths = ['scripts/relative_canonical.py','scripts/independent_relative_canonical.py',
        'scripts/assess_relative_canonical.py','scripts/relative-canonical-policy.json',
        'tests/test_relative_canonical.py','tests/test_relative_canonical_audit.py',
        'scripts/independent_rigid_pn.py','scripts/independent_nbody_pn_spin.py',
        'scripts/assess_rigid_pn.py']
    sha = lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    hashes = {r['path']:r['sha256'] for r in cp.metadata['provenance']['sources']}
    hashes.update({p:sha(p) for p in paths})
    work = ROOT/'.tools/rotation62'; times = np.linspace(0.,policy['duration_seconds']/units.time_s,policy['samples'])
    atol = np.array(cp.metadata['integration']['atol'])
    # Jacobi P uses pair total mass; pr uses its reduced mass, not Moon mass alone.
    ma,md = pair.masses[pair.first],pair.masses[pair.second]
    atol[3*count+3*pair.first:3*count+3*pair.first+3] = (ma+md)*policy['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s
    atol[3*count+3*pair.second:3*count+3*pair.second+3] = ma*md/(ma+md)*policy['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s
    atol[:3*count] = policy['position_atol_m']/units.length_m
    jobs = {}; archives = {}
    def integrate(name,field,method,start,rtol,absolute,max_step,**extra):
        print(name,'started',flush=True); clock = time.perf_counter()
        result = solve_ivp(field,(0.,float(times[-1])),start,t_eval=times,method=method,
            rtol=rtol,atol=absolute,max_step=max_step/units.time_s,**extra)
        if (not result.success or result.y.shape != (len(start),len(times))
                or not np.array_equal(result.t,times) or not np.all(np.isfinite(result.y))):
            raise ValueError('Failed/incomplete independent relative audit: '+name)
        jobs[name] = dict(seconds=time.perf_counter()-clock,nfev=result.nfev)
        path = work/(name+'.npz')
        with path.open('xb') as f:np.savez_compressed(f,times=times,states=result.y.T,
            representation='mass-weighted-pair-Jacobi-X-r-P-pr-spatial-S-quaternion' if method==CanonicalDOP853
                else 'mass-weighted-pair-Jacobi-X-r-P-pr-body-figure-spin-raw-R')
        archives[path.relative_to(ROOT).as_posix()] = sha(path.relative_to(ROOT))
        print(name,round(jobs[name]['seconds'],2),'seconds',flush=True)
        return result.y.T
    production_field = lambda t,y:rhs(t,y,params,pair)
    primary = integrate('production',production_field,CanonicalDOP853,initial,policy['production_rtol'],
        atol,policy['max_step_seconds'],body_count=count)
    strict = integrate('tighter',production_field,CanonicalDOP853,initial,policy['tighter_rtol'],
        atol*policy['tighter_atol_factor'],policy['tighter_max_step_seconds'],body_count=count)
    rotation = Rotation.from_quat(np.roll(initial[-4:],-1)).as_matrix()
    start = np.r_[initial[:-4],rotation.ravel()]; ss = slice(6*count+3*figure,6*count+3*figure+3)
    start[ss] = rotation.T@initial[ss]
    scales = np.linalg.norm(initial[:-4].reshape(3,count,3),axis=-1); points = [i for i in range(count) if i!=figure]
    raw_refs = []; refs = []
    ref_field = lambda t,y:matrix_rhs(t,y,params.orbital.masses,params.orbital.c,params.figure.moments,figure,pair.first,pair.second)
    for i,tolerance in enumerate(policy['reference_rtols']):
        absolute = tolerance*policy['reference_atol_over_rtol']*np.r_[np.repeat(scales.ravel(),3),np.ones(9)]
        for index in points:absolute[6*count+3*index:6*count+3*index+3] = policy['zero_point_spin_atol_model_units']
        if np.any(absolute<=0):raise ValueError('Reference blocks need explicit positive atol')
        raw = integrate(f'reference-{i}',ref_field,'RK45',start,tolerance,absolute,policy['max_step_seconds'])
        raw_refs.append(raw); refs.append(convert_reference(raw,count,figure))
    delta = lambda a,ra,b,rb:differences(a,ra,b,rb,units,pair,figure,scales[2,figure])
    components = dict(reference=delta(primary[:,:-4],attitudes(primary),*refs[-1]),
        reference_uncertainty=delta(*refs[0],*refs[1]),
        tighter=delta(primary[:,:-4],attitudes(primary),strict[:,:-4],attitudes(strict)))
    values = [invariants(y,params,pair) for y in primary]
    h = np.array([v[0] for v in values]); p = np.array([v[1] for v in values]); j = np.array([v[2] for v in values])
    momentum_scale = np.linalg.norm(np.array(cp.state[:-4]).reshape(3,count,3)[1],axis=1).sum()
    if min(abs(h[0]),np.linalg.norm(j[0]),momentum_scale)<=0:raise ValueError('Degenerate invariant scale')
    raw_r = np.concatenate([r[1] for r in refs])
    metrics = dict(energy_relative=float(abs(h-h[0]).max()/abs(h[0])),
        momentum_scaled=float(np.linalg.norm(p-p[0],axis=1).max()/momentum_scale),
        angular_momentum_relative=float(np.linalg.norm(j-j[0],axis=1).max()/np.linalg.norm(j[0])),
        quaternion_norm=float(abs(np.linalg.norm(primary[:,-4:],axis=1)-1).max()),
        reference_rotation_orthogonality=float(np.linalg.norm(np.swapaxes(raw_r,1,2)@raw_r-np.eye(3),axis=(1,2)).max()),
        reference_rotation_determinant=float(abs(np.linalg.det(raw_r)-1).max()))
    for name,result in components.items():
        for key in ['positions_m','earth_moon_position_m','figure_spin_relative','attitude_matrix']:metrics[name+'_'+key] = result[key]
    confirmations = dict(source_hashes_preserved=hashes=={p:sha(p) for p in hashes},
        initial_spin_orientation_bitwise=np.array_equal(initial[6*count:].view(np.uint64),np.array(cp.state[6*count:]).view(np.uint64)),
        point_spins_exactly_zero=all(np.array_equal(y[:,:9*count].reshape(-1,3,count,3)[:,2,points],np.zeros((len(y),len(points),3)))
            for y in [primary,strict]+raw_refs),initial_checkpoint_SHA_verified=True)
    failed = [k for k,v in policy['criteria'].items() if not metrics[k]<v]+[k for k in policy['required_true'] if not confirmations[k]]
    report = dict(change=62,policy=policy,metrics=metrics,confirmations=confirmations,components=components,
        job_stats=jobs,initial_state=initial.tolist(),initial_cartesian_state=list(cp.state),
        sample_times_seconds=(times*units.time_s).tolist(),units_SI=vars(units),
        code_and_input_sha256=hashes,trajectory_archives=archives,
        physical_lunar_mapping_certified=False,physical_accuracy_claimed=False,
        future_ephemerides_called=False,runtime_changed=False,checkpoint_schema_added=False,
        passed=not failed,failed_criteria=failed)
    with output.open('x',encoding='utf-8') as f:f.write(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(metrics=metrics,confirmations=confirmations,passed=not failed,failed=failed),indent=2),flush=True)
    return not failed


if __name__=='__main__':sys.exit(0 if audit() else 1)
