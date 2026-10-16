"""Research-only full native EIH callback; no application backend registration."""
from dataclasses import replace
from math import pi, sqrt

import numpy as np
from scipy.integrate import solve_ivp

from scripts.assess_relativity import independent_acceleration
from scripts.assess_sandbox_planets import states
from scripts.ias15_reference import EPSILONS
from scripts.newton_year import DAY, YEAR, packet_end, errors
from solar_simulator.continuous import ContinuousRun
from solar_simulator.experiment import Settings, create_experiment
from solar_simulator.native_forces import prepare
from solar_simulator.relativity import C
from solar_simulator.simulation import AU, G, Body
from solar_simulator.vector3 import Vector3


def validate(seed,times):
    times = np.asarray(times,dtype=float)
    if (times.ndim!=1 or len(times)<2 or times[0]!=0 or not np.isfinite(times).all()
            or not (np.diff(times)>0).all()):
        raise ValueError('Expected increasing finite epochs from zero')
    if (seed.time!=0 or seed.settings.physics!='eih-1pn' or seed.settings.figures
            or seed.rotations or seed.initial_rotations or seed.events or seed.halted
            or seed.dissipated_energy or seed.model_energy_offset or seed.orientation_work
            or any(b.radius or b.spin.magnitude() for b in seed.bodies)
            or not seed.bodies or not np.isfinite(states(seed.bodies)).all()
            or any(not np.isfinite(b.mass) or b.mass<=0 for b in seed.bodies)):
        raise ValueError('Expected fresh EIH point masses without figures, spin or events')
    if not np.isfinite(seed.settings.dt) or seed.settings.dt<=0:
        raise ValueError('Expected positive finite packet interval')
    return times


class FullForce:
    """Contain ctypes callback exceptions, then rethrow before committing output."""
    def __init__(self,acceleration):
        self.acceleration = acceleration
        self.error = None
        self.calls = 0

    def __call__(self,pointer):
        sim = pointer.contents
        particles = sim.particles
        self.calls += 1
        if self.error is None:
            try:
                q = np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in particles])
                a = np.asarray(self.acceleration(q[:,:3],q[:,3:]),dtype=float)
                if a.shape!=(len(particles),3) or not np.isfinite(a).all():
                    raise ValueError('Invalid full-force callback result')
                for p,row in zip(particles,a):
                    p.ax,p.ay,p.az = row
                return
            except Exception as error:
                self.error = error
        for p in particles:
            p.ax=p.ay=p.az=0.
        sim.stop()

    def check(self):
        if self.error is not None:
            raise RuntimeError('EIH research callback failed; no output committed') from self.error


def configured(initial,masses,library,epsilon,initial_dt,force,*,velocity_dependent=True):
    if epsilon not in EPSILONS:
        raise ValueError('Undeclared IAS15 epsilon')
    sim = library.Simulation()
    sim.G = G
    sim.integrator = 'ias15'
    sim.integrator.epsilon = epsilon
    sim.integrator.adaptive_mode = 'PRS23'
    sim.integrator.min_dt = 0.
    sim.gravity = 'none'
    sim.softening = 0.
    sim.dt = initial_dt
    sim.force_is_velocity_dependent = int(velocity_dependent)
    for mass,q in zip(masses,initial):
        sim.add(m=float(mass),x=q[0],y=q[1],z=q[2],vx=q[3],vy=q[4],vz=q[5])
    callback = FullForce(force)
    sim.additional_forces = callback
    return sim,callback


def snapshot(sim):
    return np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles])


def integrate_checked(sim,callback,end):
    try:
        sim.integrate(end,exact_finish_time=1)
    finally:
        callback.check()
    if sim.t!=end:
        raise RuntimeError('IAS15 missed exact endpoint')


def ias_trajectory(seed,times,library,epsilon,*,acceleration=None):
    times = validate(seed,times)
    masses = np.array([b.mass for b in seed.bodies])
    native = prepare(masses)
    force = acceleration if acceleration is not None else lambda p,v:native(p,v,C)
    initial = states(seed.bodies)
    sim,callback = configured(initial,masses,library,epsilon,seed.settings.dt/200,force)
    np.testing.assert_array_equal(snapshot(sim),initial)
    if (sim.gravity!='none' or sim.force_is_velocity_dependent!=1 or sim.G!=G
            or [p.m for p in sim.particles]!=masses.tolist()):
        raise RuntimeError('Wrong EIH force or frame configuration')
    values,bounds = [],[]
    for epoch in times:
        while sim.t<epoch:
            end = packet_end(sim.t,epoch,seed.settings.dt)
            integrate_checked(sim,callback,end)
            bounds.append(end)
        values.append(snapshot(sim))
    values = np.array(values)
    if not np.isfinite(values).all():
        raise RuntimeError('Nonfinite EIH trajectory')
    return values,dict(packets=len(bounds),packet_endpoints=bounds,steps_done=int(sim.steps_done),
        force_evaluations=callback.calls,epsilon=epsilon,force_is_velocity_dependent=1,
        gravity='none',force='complete native order-reduced EIH',callback_failed=False)


def dop_trajectory(seed,times):
    times = validate(seed,times)
    run = ContinuousRun(seed,float(times[-1]))
    current = seed
    values,bounds = [],[]
    for epoch in times:
        while current.time<epoch:
            current = run.next(20,until=float(epoch))
            bounds.append(current.time)
        values.append(states(current.bodies))
    return np.array(values),dict(**run.statistics,packet_endpoints=bounds)


def model(name,q,masses,dt):
    bodies = [Body(str(i),float(m),Vector3(*row[:3]),Vector3(*row[3:]))
        for i,(row,m) in enumerate(zip(q,masses))]
    settings = Settings(dt,backend='rust',integrator='dop853',physics='eih-1pn',
        rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13,error_control='per-body')
    return create_experiment(bodies,settings)


def circle():
    radius,u = 1e8,1e-6
    mu = u*radius*C*C
    masses = np.array([mu/(2*G)]*2)
    # Use actual stored G and masses in the analytic orbit, not nominal mu.
    mu = G*(masses[0]+masses[1])
    compactness = mu/(radius*C*C)
    rate = sqrt(mu/radius**3*(1-4.5*compactness)/(1-1.75*compactness))
    period = 2*pi/rate
    uvec,wvec = np.array([1.,0.,0.]),np.array([0.,.6,.8])
    offset = np.array([3e8,-2e8,1e8])
    times = np.unique(np.r_[np.linspace(0,2*period,81),.001*period])
    values = []
    for t in times:
        p = radius*(np.cos(rate*t)*uvec+np.sin(rate*t)*wvec)
        v = radius*rate*(-np.sin(rate*t)*uvec+np.cos(rate*t)*wvec)
        values.append([np.r_[offset-p/2,-v/2],np.r_[offset+p/2,v/2]])
    expected = np.array(values)
    return model('circle',expected[0],masses,period/100),times,expected,dict(
        radius_metres=radius,omega_per_second=rate,period_seconds=period,compactness=compactness)


def triple():
    p = AU*np.array([[-.5,0.,0.],[.8,.5,.1],[-.3,.9,-.4]])
    v = np.array([[30000.,-8000.,6000.],[18000.,30000.,-3000.],[-12000.,22000.,7000.]])
    times = np.unique(np.r_[np.linspace(0,30*DAY,61),1.,72000.125])
    return model('triple',np.c_[p,v],np.array([1e30,3e29,2e28]),3600.),times


def independent_reference(seed,times,rtol,max_step,clock=YEAR):
    times = validate(seed,times)
    masses = np.array([b.mass for b in seed.bodies])
    initial = states(seed.bodies)
    q = initial.copy()
    q[:,:3] /= AU
    q[:,3:] *= clock/AU
    mu = G*masses*clock**2/AU**3
    def rhs(t,y):
        state = y.reshape(len(masses),6)
        a = independent_acceleration(state[:,:3],state[:,3:],mu,C*clock/AU)
        return np.c_[state[:,3:],a].ravel()
    atol = np.tile([1e-17]*3+[1e-17*clock/YEAR]*3,len(masses))
    result = solve_ivp(rhs,(0,times[-1]/clock),q.ravel(),method='RK45',
        t_eval=times/clock,rtol=rtol,atol=atol,max_step=max_step/clock)
    if not result.success or result.t[-1]!=times[-1]/clock:
        raise RuntimeError(result.message)
    values = result.y.T.reshape(len(times),len(masses),6).copy()
    values[:,:,:3] *= AU
    values[:,:,3:] *= AU/clock
    return values,dict(rtol=rtol,max_step_seconds=max_step,clock_seconds=clock,
        rhs_calls=result.nfev,initial_roundtrip=errors(values[0],initial))


def lagrangian(p,v,masses):
    """Independent scalar EIH action (Vines p3), unordered pairs plus all U_i^2."""
    value = sum(m*(np.dot(vel,vel)/2+np.dot(vel,vel)**2/(8*C*C)) for m,vel in zip(masses,v))
    for i,m in enumerate(masses):
        potential = 0.
        for j in range(len(masses)):
            if i==j:
                continue
            d = p[i]-p[j]
            radius = np.sqrt(np.dot(d,d))
            n = d/radius
            potential += G*masses[j]/radius
            if i<j:
                value += G*m*masses[j]/radius*(1+(1.5*(np.dot(v[i],v[i])+np.dot(v[j],v[j]))
                    -3.5*np.dot(v[i],v[j])-.5*np.dot(n,v[i])*np.dot(n,v[j]))/(C*C))
        value -= m*potential**2/(2*C*C)
    return value


def noether(q,masses):
    """Complex-step velocity derivatives of the action, never runtime invariants."""
    p,v = q[:,:3],q[:,3:]
    canonical = np.zeros_like(v)
    for i in range(len(masses)):
        for k in range(3):
            changed = v.astype(complex)
            changed[i,k] += 1e-12j
            canonical[i,k] = lagrangian(p,changed,masses).imag/1e-12
    return np.r_[np.sum(v*canonical)-lagrangian(p,v,masses),np.sum(canonical,axis=0),
        np.sum(np.cross(p,canonical),axis=0)]


def invariant_drift(values,masses):
    rows = np.array([noether(q,masses) for q in values])
    pscale = sum(m*np.linalg.norm(v) for m,v in zip(masses,values[0,:,3:]))
    return dict(relative_energy_drift=float(abs(rows[:,0]-rows[0,0]).max()/abs(rows[0,0])),
        scaled_momentum_drift=float(np.linalg.norm(rows[:,1:4]-rows[0,1:4],axis=1).max()/pscale),
        relative_angular_drift=float(np.linalg.norm(rows[:,4:]-rows[0,4:],axis=1).max()/np.linalg.norm(rows[0,4:])))


def drag_probe(library,velocity_dependent=True):
    initial = np.array([[1e6,-2e6,3e6,1000.,-300.,75.]])
    times = np.linspace(0,3000.,21)
    sim,callback = configured(initial,[1e20],library,1e-9,.25,
        lambda p,v:-v/1000.,velocity_dependent=velocity_dependent)
    values = []
    for t in times:
        if sim.t<t:
            integrate_checked(sim,callback,float(t))
        values.append(snapshot(sim))
    decay = np.exp(-times[:,None,None]/1000.)
    expected = np.concatenate((initial[None,:,:3]+1000*initial[None,:,3:]*(1-decay),
        initial[None,:,3:]*decay),axis=2)
    return np.array(values),expected,dict(force_evaluations=callback.calls,
        steps_done=int(sim.steps_done),velocity_dependent=bool(velocity_dependent))
