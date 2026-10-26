"""Predeclared compatible-scaling and supplied-clock/basis research audit."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.rotation_time import (L_B,UniformTimeScaling,rotation_boundary,
    local_rate,global_acceleration)
from scripts.canonical_checkpoint import CanonicalDOP853
from scripts.relative_canonical_checkpoint import load,verify_sources
from scripts.release_history import verify_checkpoint_history
from scripts.rigid_pn_model import Parameters,fields,rhs,invariants,hamiltonian
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.independent_rigid_pn import scalar_hamiltonian,gradients,hat
from scripts.assess_nbody_pn_spin import initial_state,difference
from solar_simulator.rotation import RigidFigure


def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def synthetic(policy):
    p = json.loads((ROOT/policy['synthetic_input_policy']).read_text(encoding='utf-8'))
    i = p['figure_index']
    parameters = Parameters(PointParameters(tuple(p['masses']),p['c']),
        RigidFigure(p['masses'][i],tuple(p['moments']),p['bounding_radius']),i)
    q = np.roll(Rotation.from_rotvec(p['initial_attitude_rotvec']).as_quat(),1)
    return parameters,np.r_[initial_state(p),q],p['nominal_period']


def bound_lunar_initial(policy, *, historical=False):
    path = policy['lunar_initial_checkpoint']
    if sha(path)!=policy['lunar_initial_checkpoint_sha256']:
        raise ValueError('Changed immutable lunar initial checkpoint')
    cp = load(ROOT/path)
    if historical:verify_checkpoint_history(cp,ROOT)
    else:verify_sources(cp,ROOT)
    if (cp.time!=0 or cp.metadata['provenance']['physical_mapping_certified'] is not False
            or policy['physical_lunar_mapping_certified'] is not False):
        raise ValueError('Unsupported physical initial-data claim')
    return cp


def relative(actual,expected):
    scale = np.linalg.norm(expected)
    if scale<=0 or not np.isfinite(scale):raise ValueError('Degenerate comparison scale')
    return float(np.linalg.norm(actual-expected)/scale)


def axis_rotation(axis,angle):
    """Rodrigues polynomial for independent complex-time differentiation."""
    a = np.asarray(axis,dtype=float);a = a/np.linalg.norm(a);k = hat(a)
    return np.eye(3)+np.sin(angle)*k+(1-np.cos(angle))*(k@k)


def boundary_metrics(policy):
    p = policy['clock_boundary'];ba = np.array(p['basis_axis']);ba /= np.linalg.norm(ba)
    la = np.array(p['local_axis']);la /= np.linalg.norm(la)
    wb = p['basis_rate']*ba;wl = p['local_rate']*la
    def basis(t):return axis_rotation(ba,p['basis_rate']*t)
    def local_clock(t):return p['rate_offset']*t+.5*p['rate_slope']*t*t
    def composed(t):return basis(t)@axis_rotation(la,p['local_rate']*local_clock(t))
    def exact_rate(t):return wb+(p['rate_offset']+p['rate_slope']*t)*(basis(t)@wl)
    metrics = dict(boundary_first_derivative_relative=0.,boundary_rate_inverse_relative=0.,
        boundary_acceleration_relative=0.,wrong_missing_basis_rate_minimum=float('inf'),
        wrong_missing_clock_acceleration_minimum=float('inf'))
    step = 1e-25
    for t in np.linspace(0.,1.,policy['random_states']):
        t = float(t);b = basis(t);bd = hat(wb)@b;r = p['rate_offset']+p['rate_slope']*t
        local = axis_rotation(la,p['local_rate']*local_clock(t))
        rotation,derivative,omega = rotation_boundary(local,hat(wl)@local,b,bd,r)
        exact_d = composed(t+1j*step).imag/step
        metrics['boundary_first_derivative_relative'] = max(metrics['boundary_first_derivative_relative'],
            relative(derivative,exact_d),relative(rotation,composed(t)))
        metrics['boundary_rate_inverse_relative'] = max(metrics['boundary_rate_inverse_relative'],
            relative(local_rate(omega,b,bd,r),wl),relative(omega,exact_rate(t)))
        alpha = global_acceleration(wl,np.zeros(3),b,bd,np.zeros(3),r,p['rate_slope'])
        exact_alpha = exact_rate(t+1j*step).imag/step
        metrics['boundary_acceleration_relative'] = max(metrics['boundary_acceleration_relative'],relative(alpha,exact_alpha))
        metrics['wrong_missing_basis_rate_minimum'] = min(metrics['wrong_missing_basis_rate_minimum'],relative(r*(b@wl),omega))
        wrong_alpha = r*np.cross(wb,b@wl)
        metrics['wrong_missing_clock_acceleration_minimum'] = min(metrics['wrong_missing_clock_acceleration_minimum'],relative(wrong_alpha,exact_alpha))
    return metrics


def scaling_metrics(policy,params,initial):
    count = len(params.orbital.masses);rng = np.random.default_rng(policy['seed'])
    metrics = {k:0. for k in ['hamiltonian_scaling_relative','momentum_scaling_relative',
        'angular_momentum_scaling_relative','flow_scaling_relative','independent_H_scaling_relative',
        'independent_orbital_flow_relative']}
    metrics['wrong_unscaled_inertia_rate_minimum'] = float('inf');raw_q = True
    for _ in range(policy['random_states']):
        y = initial.copy();blocks = y[:-4].reshape(3,count,3)
        for i,amplitude in enumerate([.05,.005,.0001]):blocks[i] += rng.normal(size=(count,3))*amplitude
        h,p,j = invariants(y,params);flow = rhs(0.,y,params)
        rotation = Rotation.from_quat(np.roll(y[-4:],-1)).as_matrix()
        oracle_h = scalar_hamiltonian(y[:-4],rotation,params.orbital.masses,params.orbital.c,params.figure.moments,params.index)
        for factor in policy['uniform_factors']:
            scaling = UniformTimeScaling(factor);ps = scaling.parameters(params);ys = scaling.state(y,params)
            raw_q &= np.array_equal(ys[-4:].view(np.uint64),y[-4:].view(np.uint64))
            hs,p_s,j_s = invariants(ys,ps)
            metrics['hamiltonian_scaling_relative'] = max(metrics['hamiltonian_scaling_relative'],abs(hs-factor*h)/abs(factor*h))
            # Total P may be zero in the centred initial state; normalize by sum |p_i|.
            metrics['momentum_scaling_relative'] = max(metrics['momentum_scaling_relative'],
                float(np.linalg.norm(p_s-factor*p)/(factor*np.linalg.norm(blocks[1],axis=1).sum())))
            metrics['angular_momentum_scaling_relative'] = max(metrics['angular_momentum_scaling_relative'],relative(j_s,factor**2*j))
            actual = rhs(0.,ys,ps);expected = flow*scaling.state_factors(count)/factor
            block_errors = np.linalg.norm((actual[:-4]-expected[:-4]).reshape(3,count,3),axis=-1)/np.linalg.norm(expected[:-4].reshape(3,count,3),axis=-1)
            if not np.all(np.isfinite(block_errors)):raise ValueError('Degenerate full-flow comparison')
            metrics['flow_scaling_relative'] = max(metrics['flow_scaling_relative'],float(block_errors.max()),relative(actual[-4:],expected[-4:]))
            independent_h = scalar_hamiltonian(ys[:-4],rotation,ps.orbital.masses,ps.orbital.c,ps.figure.moments,ps.index)
            metrics['independent_H_scaling_relative'] = max(metrics['independent_H_scaling_relative'],
                abs(independent_h-factor*oracle_h)/abs(factor*oracle_h),abs(hs-independent_h)/abs(independent_h))
            g,_ = gradients(ys[:-4],rotation,ps.orbital.masses,ps.orbital.c,ps.figure.moments,ps.index)
            g = g.reshape(3,count,3);expected_orbit = np.stack([g[1],-g[0]])
            errors = np.linalg.norm(actual[:6*count].reshape(2,count,3)-expected_orbit,axis=-1)/np.linalg.norm(expected_orbit,axis=-1)
            if not np.all(np.isfinite(errors)):raise ValueError('Degenerate independent orbital comparison')
            metrics['independent_orbital_flow_relative'] = max(metrics['independent_orbital_flow_relative'],float(errors.max()))
            if factor==policy['wrong_inertia_factor']:
                wrong = replace(ps,figure=RigidFigure(ps.figure.mass,params.figure.moments,ps.figure.bounding_radius))
                correct_w = fields(ys,ps)[2]+fields(ys,ps)[3]
                wrong_w = fields(ys,wrong)[2]+fields(ys,wrong)[3]
                metrics['wrong_unscaled_inertia_rate_minimum'] = min(metrics['wrong_unscaled_inertia_rate_minimum'],relative(wrong_w,correct_w))
    return {k:float(v) for k,v in metrics.items()},bool(raw_q)


def scaled_trajectory(policy,params,initial,period,work):
    count = len(params.orbital.masses);factor = policy['trajectory_factor'];scaling = UniformTimeScaling(factor)
    state_scale = np.r_[np.repeat(np.linalg.norm(initial[:-4].reshape(3,count,3),axis=-1).ravel(),3),np.ones(4)]
    times = np.linspace(0.,policy['periods']*period,policy['samples']);jobs = {}
    for name,ps,start,grid,scales,step in [
        ('base',params,initial,times,state_scale,1.),
        ('scaled',scaling.parameters(params),scaling.state(initial,params),times*factor,state_scale*scaling.state_factors(count),factor)]:
        clock = time.perf_counter();print(name,'started',flush=True)
        sol = solve_ivp(lambda t,y:rhs(t,y,ps),(float(grid[0]),float(grid[-1])),start,t_eval=grid,
            method=CanonicalDOP853,body_count=count,rtol=policy['rtol'],atol=policy['rtol']*policy['atol_over_rtol']*scales,
            max_step=step*policy['max_step_over_period']*period)
        if not sol.success or sol.y.shape!=(len(initial),len(times)) or not np.array_equal(sol.t,grid) or not np.all(np.isfinite(sol.y)):
            raise ValueError('Invalid compatible-scaling trajectory: '+name)
        path = work/(name+'.npz');np.savez(path,times=grid,states=sol.y.T,representation='cartesian-x-p-spatial-S-raw-q')
        jobs[name] = dict(states=sol.y.T,seconds=time.perf_counter()-clock,nfev=sol.nfev,path=path.relative_to(ROOT).as_posix())
        print(name,'finished',round(jobs[name]['seconds'],3),'s',flush=True)
    scaled_back = jobs['scaled']['states']/scaling.state_factors(count)
    comparison = difference(jobs['base']['states'][:,:-4],scaled_back[:,:-4],np.linalg.norm(initial[:-4].reshape(3,count,3),axis=-1))
    qdifference = float(np.linalg.norm(jobs['base']['states'][:,-4:]-scaled_back[:,-4:],axis=-1).max())
    comparison.update(raw_quaternion=qdifference,maximum=max(comparison['maximum'],qdifference))
    return comparison,{k:{f:v for f,v in job.items() if f!='states'} for k,job in jobs.items()}


def evaluate(policy,metrics,confirmations):
    if set(metrics)!=set(policy['criteria']) or set(confirmations)!=set(policy['required_true']):
        raise ValueError('Incomplete declared audit')
    if policy['physical_lunar_mapping_certified'] is not False:raise ValueError('Unsupported physical certification')
    if any(not np.isfinite(v) or v<0 for v in metrics.values()):raise ValueError('Invalid metric')
    checks = {k:bool(metrics[k]>v if k in policy['minimum_metrics'] else metrics[k]<v) for k,v in policy['criteria'].items()}
    return checks,bool(all(checks.values()) and all(v is True for v in confirmations.values()))


def audit():
    output = ROOT/'docs/rotation-time-validation.json'
    if output.exists():raise FileExistsError('Preserve original time/basis audit')
    policy = json.loads((ROOT/'scripts/rotation-time-policy.json').read_text(encoding='utf-8'))
    if policy['uniform_factors'][-1]!=1-L_B:raise ValueError('Changed IAU defining factor')
    cp = bound_lunar_initial(policy);params,initial,period = synthetic(policy)
    paths = {s['path'] for s in cp.metadata['provenance']['sources']}
    paths.update(['scripts/rotation_time.py','scripts/assess_rotation_time.py','scripts/rotation-time-policy.json',
        'tests/test_rotation_time.py','tests/test_rotation_time_audit.py','scripts/independent_rigid_pn.py',
        'scripts/independent_nbody_pn_spin.py','scripts/assess_nbody_pn_spin.py',policy['synthetic_input_policy'],policy['lunar_initial_checkpoint']])
    hashes = {p:sha(p) for p in sorted(paths)};work = ROOT/'.tools/rotation64';work.mkdir(exist_ok=True)
    if any((work/(n+'.npz')).exists() for n in ['base','scaled']):raise FileExistsError('Preserve prior trajectory')
    metrics,raw_q = scaling_metrics(policy,params,initial);metrics.update(boundary_metrics(policy))
    comparison,jobs = scaled_trajectory(policy,params,initial,period,work)
    metrics['scaled_trajectory_difference'] = comparison['maximum']
    confirmations = dict(source_hashes_preserved=all(sha(p)==h for p,h in hashes.items()),
        raw_quaternion_preserved=raw_q,physical_migration_not_claimed=policy['physical_lunar_mapping_certified'] is False)
    checks,passed = evaluate(policy,metrics,confirmations)
    f = 1-L_B;inverse = 1/f
    diagnostic = dict(defining_L_B=L_B,TDB_compatible_factor=f,
        hypothetical_TDB_to_TCB_mass_relative=inverse-1,
        hypothetical_TDB_to_TCB_inertia_relative=inverse**3-1,
        hypothetical_TDB_to_TCB_spin_relative=inverse**2-1,
        hypothetical_TDB_to_TCB_rate_relative=f-1,
        hypothetical_reference_radius_difference_m=1738000.*(inverse-1),
        hypothetical_32day_coordinate_duration_difference_s=32*86400.*(inverse-1),
        interpretation='Uniform compatible-quantity examples only, NOT transformations of the physical Moon/profile. Local radius/inertia time-scale provenance, lunar clock, basis, tetrad, SSC and complete PN Q2 remain unqualified.')
    report = dict(change=64,policy=policy,metrics=metrics,checks=checks,confirmations=confirmations,passed=passed,
        synthetic_initial=initial.tolist(),synthetic_nominal_period=period,trajectory_comparison=comparison,jobs=jobs,
        code_and_input_sha256=hashes,trajectory_archives={j['path']:sha(j['path']) for j in jobs.values()},
        convention_diagnostic=diagnostic,physical_lunar_mapping_certified=False,physical_accuracy_claimed=False,
        runtime_changed=False,future_ephemerides_read=False)
    text = json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    with output.open('x',encoding='utf-8') as stream:stream.write(text)
    print(json.dumps(dict(passed=passed,metrics=metrics),indent=2),flush=True)
    return passed


if __name__=='__main__':raise SystemExit(0 if audit() else 1)
