"""Research fixed-axis J2 adapter and independent truncation/torque budgets."""
from math import pi,sqrt

import numpy as np
from scipy.integrate import solve_ivp

from scripts.eih_year import force_terms
from scripts.ias15_eih import configured,snapshot,integrate_checked,noether
from scripts.newton_year import packet_end
from scripts.assess_sandbox_planets import states
from solar_simulator.experiment import Settings,create_experiment,copy_bodies
from solar_simulator.continuous import ContinuousRun
from solar_simulator.native_forces import prepare as native_prepare
from solar_simulator.oblateness import FixedJ2,prepare,acceleration
from solar_simulator.relativity import C
from solar_simulator.simulation import G,Body
from solar_simulator.vector3 import Vector3


def validate(seed,times):
    times = np.asarray(times,dtype=float)
    if (times.ndim!=1 or len(times)<2 or times[0]!=0 or not np.isfinite(times).all()
            or not (np.diff(times)>0).all()):
        raise ValueError('Expected increasing finite epochs from zero')
    if (seed.time!=0 or seed.settings.physics not in ('newtonian','eih-1pn')
            or not seed.settings.figures or any(type(f) is not FixedJ2 for f in seed.settings.figures)
            or seed.rotations or seed.initial_rotations or seed.events or seed.halted
            or seed.dissipated_energy or seed.model_energy_offset or seed.orientation_work
            or any(b.radius or b.spin.magnitude() for b in seed.bodies)):
        raise ValueError('Expected fresh point masses with fixed J2 only')
    create_experiment(copy_bodies(seed.bodies),seed.settings,origin=seed.origin)
    return times


def full_force(seed):
    masses = np.array([b.mass for b in seed.bodies])
    point = native_prepare(masses)
    figures = prepare(seed.bodies,seed.settings.figures)
    def force(p,v):
        return point(p,v,C if seed.settings.physics=='eih-1pn' else None)+acceleration(p,masses,figures)
    return force


def ias_trajectory(seed,times,library,epsilon):
    times = validate(seed,times)
    masses = np.array([b.mass for b in seed.bodies])
    initial = states(seed.bodies)
    sim,callback = configured(initial,masses,library,epsilon,seed.settings.dt/200,full_force(seed))
    np.testing.assert_array_equal(snapshot(sim),initial)
    if sim.gravity!='none' or sim.force_is_velocity_dependent!=1:
        raise RuntimeError('Wrong fixedJ2 callback configuration')
    values,bounds = [],[]
    for epoch in times:
        while sim.t<epoch:
            end = packet_end(sim.t,epoch,seed.settings.dt)
            integrate_checked(sim,callback,end)
            bounds.append(end)
        values.append(snapshot(sim))
    values = np.array(values)
    if not np.isfinite(values).all():raise ValueError('Nonfinite fixedJ2 output')
    return values,dict(packets=len(bounds),packet_endpoints=bounds,steps_done=int(sim.steps_done),
        force_evaluations=callback.calls,epsilon=epsilon,gravity='none',velocity_dependent=True,
        physics=seed.settings.physics,figures='fixed J2 only',callback_failed=False)


def dop_trajectory(seed,times):
    times = validate(seed,times)
    run = ContinuousRun(seed,float(times[-1]));current = seed
    values,bounds = [],[]
    for epoch in times:
        while current.time<epoch:
            current = run.next(20,until=float(epoch));bounds.append(current.time)
        values.append(states(current.bodies))
    return np.array(values),dict(**run.statistics,packet_endpoints=bounds)


def entries(seed,length=1.):
    names = [b.name for b in seed.bodies]
    return tuple((names.index(f.body),f.reference_radius/length,
        f.coefficient*(f.reference_radius/length)**2*(3*np.outer(f.axis,f.axis)-np.eye(3)))
        for f in seed.settings.figures)


def potential(p,masses,figures,g=G):
    """Scalar tensor potential, analytic in p for independent complex-step QA."""
    value = 0.
    for i,radius,q in figures:
        for j in range(len(masses)):
            if i==j:continue
            r = p[j]-p[i]
            length = np.sqrt(np.dot(r,r))
            value += g*masses[i]*masses[j]*(r@q@r)/(2*length**5)
    return value


def figure_force(p,masses,figures,g=G):
    """Independent tensor gradient, with source reaction and exterior guard."""
    result = np.zeros_like(p)
    for i,radius,q in figures:
        for j in range(len(masses)):
            if i==j:continue
            r = p[j]-p[i];length = np.linalg.norm(r)
            if length<=radius:raise ValueError('Inside reference figure radius')
            gradient = q@r/length**5-2.5*(r@q@r)*r/length**7
            result[j] -= g*masses[i]*gradient
            result[i] += g*masses[j]*gradient
    return result


def pn_response(p,v,masses,b,*,g=G,c=C):
    """H_PN times b at fixed p,v; derivative of the published EIH L_PN."""
    response = np.zeros_like(v)
    for i,m in enumerate(masses):
        response[i] = m*(.5*np.dot(v[i],v[i])*b[i]+v[i]*np.dot(v[i],b[i]))
        for j in range(len(masses)):
            if i==j:continue
            r = p[i]-p[j];radius = np.linalg.norm(r);n = r/radius
            response[i] += g*m*masses[j]/(2*radius)*(6*b[i]-7*b[j]-n*np.dot(n,b[j]))
    return response/(c*c)


def sources(p,v,masses,a_pn,a_q,*,g=G,c=C):
    """Separate torque, c^-4 truncation and c^-2*J2 bookkeeping, not forces."""
    result = np.zeros((3,7))
    result[0,4:] = np.sum(np.cross(p,masses[:,None]*a_q),axis=0)
    for k,b in ((1,a_pn),(2,a_q)):
        response = pn_response(p,v,masses,b,g=g,c=c)
        result[k,0] = np.sum(v*response)
        result[k,1:4] = np.sum(response,axis=0)
        result[k,4:] = np.sum(np.cross(p,response),axis=0)
    return result


def quantities(q,masses,figures,physics):
    if physics=='eih-1pn':
        row = noether(q,masses)
    else:
        p,v = q[:,:3],q[:,3:]
        energy = sum(.5*m*np.dot(vel,vel) for m,vel in zip(masses,v))
        energy -= sum(G*masses[i]*masses[j]/np.linalg.norm(p[j]-p[i])
            for i in range(len(masses)) for j in range(i+1,len(masses)))
        row = np.r_[energy,np.sum(masses[:,None]*v,axis=0),np.sum(np.cross(p,masses[:,None]*v),axis=0)]
    row[0] += potential(q[:,:3],masses,figures)
    return row


def scales(q,masses,figures,physics):
    row = quantities(q,masses,figures,physics)
    return np.r_[abs(row[0]),[sum(m*np.linalg.norm(v) for m,v in zip(masses,q[:,3:]))]*3,
        [np.linalg.norm(row[4:])]*3]


def balances(values,budgets,seed):
    m = np.array([b.mass for b in seed.bodies]);fig = entries(seed)
    rows = np.array([quantities(q,m,fig,seed.settings.physics) for q in values])
    scale = scales(values[0],m,fig,seed.settings.physics)
    delta = rows-rows[0]
    residual = (delta-np.sum(budgets,axis=1))/scale
    def norms(array):
        return dict(energy=float(abs(array[:,0]).max()),momentum=float(np.linalg.norm(array[:,1:4],axis=1).max()),
            angular=float(np.linalg.norm(array[:,4:],axis=1).max()))
    raw = norms(delta/scale)
    return dict(corrected=norms(residual),raw=raw,
        source_integrals={name:norms(budgets[:,i]/scale) for i,name in enumerate(('figure_torque','pn2','pn_q2'))},
        single_axis_angular_projection=(float(abs(delta[:,4:]@np.array(seed.settings.figures[0].axis)).max()/scale[4])
            if len(fig)==1 else None))


def model(case):
    axis,e = 1e8,.2
    mu = axis*C*C*1e-6
    masses = np.array([.8,.2])*mu/G
    mu = G*sum(masses)
    radius = axis*(1-e);speed = sqrt(mu*(1+e)/radius)
    r = np.array([radius,0.,0.]);v = speed*np.array([0.,.8,.6])
    center,drift = np.array([3*axis,-2*axis,axis]),np.array([20000.,-10000.,5000.])
    fraction = masses[1]/sum(masses)
    q = np.array([np.r_[center-fraction*r,drift-fraction*v],
        np.r_[center+(1-fraction)*r,drift+(1-fraction)*v]])
    figures = (FixedJ2('Alpha',.005,axis/5,(0.,0.,1.)),)
    if case!='newton_one':figures += (FixedJ2('Beta',-.003,axis/7,(.6,0.,.8)),)
    if case not in ('newton_one','newton_two','eih_two'):raise ValueError('Undeclared model')
    period = 2*pi*sqrt(axis**3/mu)
    settings = Settings(period/100,backend='rust',integrator='dop853',error_control='per-body',
        physics='eih-1pn' if case=='eih_two' else 'newtonian',figures=figures,
        rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13)
    bodies = [Body(name,float(m),Vector3(*row[:3]),Vector3(*row[3:])) for name,m,row in zip(('Alpha','Beta'),masses,q)]
    return create_experiment(bodies,settings),np.linspace(0,2*period,61),period


def reference(seed,times,rtol,max_step):
    times = validate(seed,times)
    length = 1e8;masses = np.array([b.mass for b in seed.bodies]);mass = sum(masses)
    clock = sqrt(length**3/(G*mass));m = masses/mass
    g = G*mass*clock**2/length**3;c = C*clock/length
    fig = entries(seed,length)
    q = states(seed.bodies).copy();q[:,:3] /= length;q[:,3:] *= clock/length
    count = len(masses);state_size = count*6
    def rhs(t,y):
        state = y[:state_size].reshape(count,6);p,v = state[:,:3],state[:,3:]
        n,pn = force_terms(p,v,g*m,c)
        aq = figure_force(p,m,fig,g)
        if seed.settings.physics!='eih-1pn':pn = np.zeros_like(pn)
        budget = sources(p,v,m,pn,aq,g=g,c=c) if seed.settings.physics=='eih-1pn' else np.zeros((3,7))
        budget[0,4:] = np.sum(np.cross(p,m[:,None]*aq),axis=0)
        return np.r_[np.c_[v,n+pn+aq].ravel(),budget.ravel()]
    y0 = np.r_[q.ravel(),np.zeros(21)]
    result = solve_ivp(rhs,(0,times[-1]/clock),y0,method='RK45',t_eval=times/clock,
        rtol=rtol,atol=1e-17,max_step=max_step/clock)
    if not result.success or result.t[-1]!=times[-1]/clock:raise RuntimeError(result.message)
    values = result.y[:state_size].T.reshape(len(times),count,6).copy()
    values[:,:,:3] *= length;values[:,:,3:] *= length/clock
    unit = np.r_[mass*length**2/clock**2,[mass*length/clock]*3,[mass*length**2/clock]*3]
    budgets = result.y[state_size:].T.reshape(len(times),3,7)*unit
    return values,budgets,dict(rtol=rtol,max_step_seconds=max_step,rhs_calls=result.nfev,
        length_metres=length,clock_seconds=clock,mass_kg=mass,interpolation='RK45 quartic')
