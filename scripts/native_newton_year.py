"""Whole-trajectory N-body force substitution; two-body session/storage API unchanged."""
from decimal import Decimal as D, localcontext

import numpy as np

from scripts.assess_sandbox_planets import states
from scripts.ias15_native_newton import MODES, NewtonCallback
from scripts.ias15_reference import EPSILONS, VERSION
from scripts.ias15_restart import bits
from scripts.native_audit import require_native
from scripts.newton_year import G, packet_end, validate
from solar_simulator.native_forces import prepare


def force_metrics(masses, positions, actual):
    actual = np.asarray(actual, dtype=float)
    if actual.shape != (len(masses), 3) or not np.isfinite(actual).all():
        raise ValueError('Invalid N-body force sample')
    with localcontext() as context:
        context.prec = 100
        m = [D.from_float(float(x)) for x in masses]
        p = [[D.from_float(float(x)) for x in row] for row in positions]
        gradient = [[D(0)]*3 for _ in m]
        for i in range(len(m)):
            for j in range(i+1, len(m)):
                delta = [b-a for a,b in zip(p[i], p[j])]
                radius = sum(x*x for x in delta).sqrt()
                for k, x in enumerate(delta):
                    pair = D.from_float(G)*m[i]*m[j]*x/radius**3
                    gradient[i][k] += pair
                    gradient[j][k] -= pair
        expected = [[x/mass for x in row] for mass,row in zip(m, gradient)]
        errors = [float(sum((D.from_float(float(x))-y)**2 for x,y in zip(a,b)).sqrt()
                        /sum(x*x for x in b).sqrt()) for a,b in zip(actual, expected)]
    return dict(actual=actual.tolist(), decimal100=[[str(x) for x in row] for row in expected],
                relative_errors=errors, checks_passed=max(errors) < 5e-13)


def guard(sim, masses, epsilon, mode):
    if (sim.N != len(masses) or sim.G != G or sim.gravity != ('none' if mode == 'native' else 'basic')
            or sim.softening != 0 or sim.force_is_velocity_dependent != 0
            or sim.integrator.epsilon != epsilon or sim.integrator.adaptive_mode != 'PRS23'
            or sim.integrator.min_dt != 0 or bits([p.m for p in sim.particles]) != bits(masses)):
        raise ArithmeticError('Changed N-body model/settings; double gravity forbidden')


def trajectory(seed, times, library, epsilon, mode, *, counted=False):
    times = validate(seed, times)
    if epsilon not in EPSILONS or mode not in MODES or library.__version__ != VERSION:
        raise ValueError('Undeclared N-body solver mode/version/epsilon')
    masses, initial = np.array([b.mass for b in seed.bodies]), states(seed.bodies)
    calls, callback = 0, None
    if mode == 'native':
        require_native()
        native = prepare(masses)
        callback = NewtonCallback(lambda p,v:native(p,v,None,None))
    def counter(pointer):
        nonlocal calls
        calls += 1
    sim = library.Simulation()
    sim.G, sim.gravity, sim.softening = G, 'none' if mode == 'native' else 'basic', 0.
    sim.integrator = 'ias15'
    sim.integrator.epsilon, sim.integrator.adaptive_mode = epsilon, 'PRS23'
    sim.integrator.min_dt, sim.dt = 0., seed.settings.dt/200
    sim.force_is_velocity_dependent = 0
    for mass,q in zip(masses, initial):
        sim.add(m=float(mass),x=q[0],y=q[1],z=q[2],vx=q[3],vy=q[4],vz=q[5])
    if callback is not None:
        sim.additional_forces = callback
    elif counted:
        sim.additional_forces = counter
    def snapshot():
        return np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles])
    if sim.t != 0. or bits(snapshot()) != bits(initial):
        raise ArithmeticError('Changed N-body initial state')
    guard(sim, masses, epsilon, mode)
    values, clocks, packets = [], [0.], [initial.copy()]
    for epoch in times:
        while sim.t < epoch:
            guard(sim, masses, epsilon, mode)
            end = packet_end(sim.t, float(epoch), seed.settings.dt)
            try:
                sim.integrate(end, exact_finish_time=1)
            finally:
                if callback is not None:
                    callback.check()
            guard(sim, masses, epsilon, mode)
            q = snapshot()
            if sim.t != end or not np.isfinite(q).all():
                raise ArithmeticError('Invalid N-body packet endpoint/state')
            clocks.append(end)
            packets.append(q)
        values.append(snapshot())
    stats = dict(steps_done=int(sim.steps_done), packets=len(clocks)-1,
                 force_evaluations=callback.calls if callback is not None else calls if counted else None,
                 simulations=1, gravity=sim.gravity, velocity_dependent=False)
    return np.asarray(values), stats, dict(packet_endpoints=np.asarray(clocks), packet_states=np.asarray(packets))
