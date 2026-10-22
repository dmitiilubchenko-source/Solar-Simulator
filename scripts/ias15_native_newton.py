"""Nine-case Newton force coupling experiment; no runtime backend registration."""
from decimal import Decimal as D, localcontext

import numpy as np

from scripts.ias15_reference import packet_end
from scripts.ias15_restart import bits, checkpoint, simulation, snapshot, validate
from scripts.native_audit import require_native
from solar_simulator.native_forces import prepare
from solar_simulator.simulation import G

MODES = ('basic', 'native')


def force_metrics(masses, state, actual):
    """Independent potential gradient in Decimal100, with exact binary64 inputs."""
    actual = np.asarray(actual, dtype=float)
    if actual.shape != (2, 3) or not np.isfinite(actual).all():
        raise ValueError('Invalid force sample')
    with localcontext() as context:
        context.prec = 100
        m = [D.from_float(float(x)) for x in masses]
        p = [[D.from_float(float(x)) for x in row[:3]] for row in state]
        rho = [b-a for a, b in zip(*p)]
        radius = sum(x*x for x in rho).sqrt()
        # -grad(U)/mass; computed once as an equal/opposite pair force.
        pair = [D.from_float(G)*m[0]*m[1]*x/(radius**3) for x in rho]
        expected = [[x/m[0] for x in pair], [-x/m[1] for x in pair]]
        errors = []
        for row, reference in zip(actual, expected):
            error = sum((D.from_float(float(x))-y)**2 for x, y in zip(row, reference)).sqrt()
            errors.append(float(error/sum(x*x for x in reference).sqrt()))
    return dict(actual=actual.tolist(), decimal100=[[str(x) for x in row] for row in expected],
                relative_errors=errors, checks_passed=max(errors) < 5e-13)


class NewtonCallback:
    """Latch even interruptions inside ctypes; never return a usable partial result."""
    def __init__(self, force):
        self.force, self.error, self.calls = force, None, 0

    def __call__(self, pointer):
        sim = pointer.contents
        self.calls += 1
        if self.error is None:
            try:
                state = snapshot(sim)
                acceleration = np.asarray(self.force(state[:, :3], state[:, 3:]), dtype=float)
                if acceleration.shape != (sim.N, 3) or not np.isfinite(acceleration).all():
                    raise ValueError('Invalid complete Newton acceleration')
                for particle, row in zip(sim.particles, acceleration):
                    particle.ax, particle.ay, particle.az = row
                return
            except BaseException as error:
                self.error = error
        for particle in sim.particles:
            particle.ax = particle.ay = particle.az = 0.
        sim.stop()

    def check(self):
        if self.error is not None:
            raise RuntimeError('Newton callback failed; no trajectory committed') from self.error


def guard(sim, masses, epsilon, mode):
    if (sim.gravity != ('none' if mode == 'native' else 'basic') or sim.G != G
            or sim.softening != 0 or sim.force_is_velocity_dependent != 0 or sim.N != 2
            or sim.integrator.epsilon != epsilon or sim.integrator.adaptive_mode != 'PRS23'
            or sim.integrator.min_dt != 0 or bits([p.m for p in sim.particles]) != bits(masses)):
        raise ArithmeticError('Changed Newton model/settings; double gravity is forbidden')


def trajectory(request, library, epsilon, origin, mode):
    if mode not in MODES:
        raise ValueError('Undeclared Newton force mode')
    masses, initial, times, _ = validate(request['masses'], request['states'], request['times'],
                                        request['packet_dt'], epsilon, 'warm')
    callback, calls = None, 0
    if mode == 'native':
        require_native()
        native = prepare(masses)
        callback = NewtonCallback(lambda p, v: native(p, v, None, None))
    def counter(pointer):
        nonlocal calls
        calls += 1
    sim = simulation(library, 0., masses, initial, request['packet_dt'], epsilon)
    sim.force_is_velocity_dependent = 0
    sim.gravity = 'none' if mode == 'native' else 'basic'
    sim.additional_forces = callback if callback is not None else counter
    guard(sim, masses, epsilon, mode)
    clocks, states, texts, digests, values = [], [], [], [], []
    def keep():
        state = snapshot(sim)
        raw, digest = checkpoint(float(sim.t), masses, state, origin)
        clocks.append(float(sim.t))
        states.append(state)
        texts.append(raw)
        digests.append(digest)
    keep()
    for epoch in times:
        while sim.t < epoch:
            guard(sim, masses, epsilon, mode)
            end = packet_end(float(sim.t), float(epoch), request['packet_dt'])
            try:
                sim.integrate(end, exact_finish_time=1)
            finally:
                if callback is not None:
                    callback.check()
            if sim.t != end:
                raise ArithmeticError('Newton trajectory missed exact packet endpoint')
            guard(sim, masses, epsilon, mode)
            keep()
        values.append(snapshot(sim))
    stats = dict(mode=mode, packets=len(clocks)-1, simulations=1, steps_done=int(sim.steps_done),
                 force_evaluations=callback.calls if callback is not None else calls,
                 gravity=sim.gravity, velocity_dependent=False)
    artifacts = dict(packet_endpoints=np.asarray(clocks), packet_states=np.asarray(states),
                     checkpoint_json=np.asarray(texts), checkpoint_sha256=np.asarray(digests))
    return np.asarray(values), stats, artifacts
