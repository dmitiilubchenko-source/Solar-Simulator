"""Isolated ten-body Newton benchmark; no runtime registration or JPL fitting."""
from dataclasses import replace
import hashlib
from math import dist, fsum
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from scripts.assess_sandbox_planets import states
from scripts.ias15_reference import EPSILONS
from solar_simulator.continuous import ContinuousRun
from solar_simulator.experiment import copy_bodies, create_experiment
from solar_simulator.simulation import AU, G
from solar_simulator.storage import load

ROOT = Path(__file__).resolve().parents[1]
YEAR = 31557600.
DAY = 86400.
INPUTS = {
    'docs/solar-sandbox-strict-checkpoint.json': '65cd1b3eb5c815df11cd45a7106d8cc4ecb5828d10761715831aaf2571b3548d',
    'docs/continuous-integration-reference.npz': 'e1cb054f6d5f2ca9b0e983e7f824fcd3e03e99c471266d8bfc3200bd74d67b55',
}
NAMES = ('Sun','Mercury','Venus','Earth','Moon','Mars','Jupiter','Saturn','Uranus','Neptune')
LEVELS = ((1e-13,1800.,YEAR),(3e-14,900.,YEAR),(3e-14,450.,YEAR),(3e-14,450.,DAY))


def hashes(paths):
    return {str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}


def inputs():
    if hashes(INPUTS) != INPUTS:
        raise ValueError('Pinned IC or epoch grid changed')
    original = load(ROOT/'docs/solar-sandbox-strict-checkpoint.json')
    seed = create_experiment(copy_bodies(original.bodies),
        replace(original.settings,physics='newtonian',figures=()),origin=original.origin)
    with np.load(ROOT/'docs/continuous-integration-reference.npz',allow_pickle=False) as cache:
        times = cache['year_times'].copy()
    if tuple(b.name for b in seed.bodies)!=NAMES or len(times)!=125 or times[-1]!=YEAR:
        raise ValueError('Unexpected pinned benchmark')
    np.testing.assert_array_equal(states(seed.bodies),states(original.bodies))
    validate(seed,times)
    return seed,times


def validate(seed,times):
    times = np.asarray(times,dtype=float)
    if (times.ndim!=1 or len(times)<2 or times[0]!=0 or not np.isfinite(times).all()
            or not (np.diff(times)>0).all()):
        raise ValueError('Expected increasing finite epochs starting at zero')
    if (len(seed.bodies)<2 or seed.time!=0 or seed.settings.physics!='newtonian'
            or seed.settings.figures or seed.rotations or seed.initial_rotations
            or seed.events or seed.halted or seed.dissipated_energy or seed.model_energy_offset
            or seed.orientation_work or any(b.radius or b.spin.magnitude() for b in seed.bodies)):
        raise ValueError('Expected fresh Newtonian point-mass research seed')
    if (not np.isfinite(states(seed.bodies)).all()
            or any(not np.isfinite(b.mass) or b.mass<=0 for b in seed.bodies)
            or not np.isfinite(seed.settings.dt) or seed.settings.dt<=0):
        raise ValueError('Expected finite states, positive masses and packet interval')
    return times


def encode(initial,masses,pair,clock):
    """Independent SI -> AU/clock mapping, interleaved EMB plus separation."""
    e,m = pair
    fraction = masses[m]/(masses[e]+masses[m])
    q = np.array(initial,dtype=float,copy=True)
    delta = q[m]-q[e]
    q[e] += fraction*delta
    q[m] = delta
    q[:,:3] /= AU
    q[:,3:] *= clock/AU
    return q


def decode(internal,masses,pair,clock):
    e,m = pair
    fraction = masses[m]/(masses[e]+masses[m])
    q = np.array(internal,dtype=float,copy=True)
    q[...,e,:] = internal[...,e,:]-fraction*internal[...,m,:]
    q[...,m,:] = internal[...,e,:]+(1-fraction)*internal[...,m,:]
    q[...,:3] *= AU
    q[...,3:] *= AU/clock
    return q


def reference_rhs(masses,pair,clock):
    """Full matrix Newton force; shares only G/input constants with production."""
    e,m = pair
    fraction = masses[m]/(masses[e]+masses[m])
    mu = G*np.asarray(masses)*clock**2/AU**3
    def rhs(t,y):
        q = y.reshape(len(masses),6)
        p = q[:,:3].copy()
        p[e] = q[e,:3]-fraction*q[m,:3]
        p[m] = q[e,:3]+(1-fraction)*q[m,:3]
        d = p[None,:,:]-p[:,None,:]
        d[e,m],d[m,e] = q[m,:3],-q[m,:3]
        distance = np.linalg.norm(d,axis=2)
        np.fill_diagonal(distance,np.inf)
        with np.errstate(divide='raise',invalid='raise',over='raise'):
            a = np.sum(d*(mu[None,:]/distance**3)[:,:,None],axis=1)
        relative = a[m]-a[e]
        a[e] += fraction*relative
        a[m] = relative
        return np.concatenate((q[:,3:],a),axis=1).ravel()
    return rhs


def reference(seed,times,rtol,maximum_step,clock=YEAR):
    times = validate(seed,times)
    names = [b.name for b in seed.bodies]
    pair = names.index('Earth'),names.index('Moon')
    masses = np.array([b.mass for b in seed.bodies])
    q = encode(states(seed.bodies),masses,pair,clock)
    atol = np.tile([1e-17]*3+[1e-17*clock/YEAR]*3,len(masses))
    solution = solve_ivp(reference_rhs(masses,pair,clock),(0,times[-1]/clock),
        q.ravel(),method='RK45',t_eval=times/clock,rtol=rtol,atol=atol,max_step=maximum_step/clock)
    if not solution.success or solution.t[-1]!=times[-1]/clock:
        raise RuntimeError(solution.message)
    values = decode(solution.y.T.reshape(len(times),len(masses),6),masses,pair,clock)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite independent reference')
    return values,dict(rtol=rtol,max_step_seconds=maximum_step,clock_seconds=clock,
        rhs_calls=solution.nfev,interpolation='RK45 quartic at t_eval')


def packet_end(current,target,dt):
    end = min(current+dt*20,float(target)) if dt <= (target-current)/20 else float(target)
    if end<=current:
        raise ValueError('Packet endpoint cannot advance')
    return end


def dop_trajectory(seed,times):
    times = validate(seed,times)
    session = ContinuousRun(seed,float(times[-1]))
    current = seed
    values,bounds = [],[]
    for epoch in times:
        while current.time<epoch:
            current = session.next(20,until=float(epoch))
            bounds.append(current.time)
        values.append(states(current.bodies))
    return np.array(values),dict(**session.statistics,packet_endpoints=bounds)


def ias_trajectory(seed,times,library,epsilon,*,count_forces=False):
    times = validate(seed,times)
    if epsilon not in EPSILONS:
        raise ValueError('Undeclared IAS15 epsilon')
    sim = library.Simulation()
    sim.G = G
    sim.integrator = 'ias15'
    sim.integrator.epsilon = epsilon
    sim.integrator.adaptive_mode = 'PRS23'
    sim.integrator.min_dt = 0.
    sim.gravity = 'basic'
    sim.softening = 0.
    sim.dt = seed.settings.dt/200
    calls = 0
    if count_forces:
        def counter(pointer):
            nonlocal calls
            calls += 1
        sim.additional_forces = counter
    for b,row in zip(seed.bodies,states(seed.bodies)):
        sim.add(m=b.mass,x=row[0],y=row[1],z=row[2],vx=row[3],vy=row[4],vz=row[5])
    def snapshot():
        return np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles])
    np.testing.assert_array_equal(snapshot(),states(seed.bodies))
    if ([p.m for p in sim.particles]!=[b.mass for b in seed.bodies]
            or sim.N!=len(seed.bodies) or sim.G!=G or sim.gravity!='basic'
            or sim.softening!=0 or sim.integrator.epsilon!=epsilon
            or sim.integrator.adaptive_mode!='PRS23' or sim.integrator.min_dt!=0):
        raise RuntimeError('IAS15 initialization changed')
    values,bounds = [],[]
    for epoch in times:
        while sim.t<epoch:
            end = packet_end(sim.t,epoch,seed.settings.dt)
            sim.integrate(end,exact_finish_time=1)
            if sim.t!=end:
                raise RuntimeError('IAS15 missed exact endpoint')
            bounds.append(end)
        values.append(snapshot())
    values = np.array(values)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite IAS15 output')
    return values,dict(steps_done=int(sim.steps_done),packets=len(bounds),packet_endpoints=bounds,
        force_evaluations=calls if count_forces else None,epsilon=epsilon,
        adaptive_mode='PRS23',initial_step_seconds=seed.settings.dt/200)


def errors(actual,expected):
    delta = actual-expected
    return dict(position_metres=float(np.linalg.norm(delta[...,:3],axis=-1).max()),
        velocity_m_per_s=float(np.linalg.norm(delta[...,3:],axis=-1).max()))


def agreement(actual,expected,names):
    e,m = names.index('Earth'),names.index('Moon')
    return dict(all_bodies=errors(actual,expected),
        moon_relative_to_earth=errors(actual[:,m]-actual[:,e],expected[:,m]-expected[:,e]))


def invariants(values,masses):
    """Independent fsum inertial Newton invariants for an arbitrary N-body array."""
    rows = []
    for q in values:
        p,v = q[:,:3],q[:,3:]
        energy = fsum(.5*m*fsum(x*x for x in vel) for m,vel in zip(masses,v))
        energy += fsum(-G*masses[i]*masses[j]/dist(p[i],p[j])
            for i in range(len(masses)) for j in range(i+1,len(masses)))
        linear = [fsum(masses*v[:,k]) for k in range(3)]
        angular = [fsum(masses*(p[:,(k+1)%3]*v[:,(k+2)%3]-p[:,(k+2)%3]*v[:,(k+1)%3])) for k in range(3)]
        rows.append([energy,*linear,*angular])
    rows = np.array(rows)
    momentum_scale = fsum(m*np.linalg.norm(v) for m,v in zip(masses,values[0,:,3:]))
    return dict(relative_energy_drift=float(np.max(np.abs(rows[:,0]-rows[0,0]))/abs(rows[0,0])),
        scaled_momentum_drift=float(np.linalg.norm(rows[:,1:4]-rows[0,1:4],axis=1).max()/momentum_scale),
        relative_angular_drift=float(np.linalg.norm(rows[:,4:]-rows[0,4:],axis=1).max()/np.linalg.norm(rows[0,4:])))
