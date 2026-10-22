"""Owned warm IAS15 research session; no application backend or disk resume."""
from dataclasses import dataclass

import numpy as np

from scripts.ias15_reference import packet_end
from scripts.ias15_restart import bits, checkpoint, physical, simulation, snapshot, validate
from solar_simulator.simulation import G


@dataclass(frozen=True)
class PhysicalSnapshot:
    time: float
    masses: np.ndarray
    state: np.ndarray
    origin: str
    checkpoint_json: str
    checkpoint_sha256: str


def _physical_snapshot(time, masses, state, origin):
    clock, mass, value = physical(time, masses, state)
    raw, digest = checkpoint(clock, mass, value, origin)
    return PhysicalSnapshot(clock, mass, value, origin, raw, digest)


class IAS15Session:
    """One owned controller; only complete checked packets become public snapshots."""

    def __init__(self, masses, initial, packet_dt, target, library, epsilon, origin, *, count_forces=False):
        if type(target) not in (int, float) or not np.isfinite(target) or target <= 0:
            raise ValueError('Expected finite positive target')
        masses, initial, _, _ = validate(masses, initial, [0., target], packet_dt, epsilon, 'warm')
        self._committed = (_physical_snapshot(0., masses, initial, origin), 0, 0, 0)
        self._masses = masses.copy()
        self._target, self._packet_dt, self._epsilon = float(target), float(packet_dt), epsilon
        self._failed = self._closed = False
        self._attempts = 0
        self._force_calls = [0]
        calls = self._force_calls
        def counter(pointer):
            calls[0] += 1
        self._count_forces = bool(count_forces)
        self._sim = simulation(library, 0., masses, initial, packet_dt, epsilon,
                               counter if count_forces else None)

    @property
    def target(self):
        return self._target

    @property
    def current(self):
        current = self._committed[0]
        return PhysicalSnapshot(current.time, current.masses.copy(), current.state.copy(), current.origin,
                                current.checkpoint_json, current.checkpoint_sha256)

    @property
    def finished(self):
        return self._committed[0].time == self._target

    @property
    def statistics(self):
        _, packets, steps, force_calls = self._committed
        return dict(packets=packets, attempts=self._attempts, steps_done=steps,
                    simulations=1, force_evaluations=force_calls if self._count_forces else None,
                    attempted_force_evaluations=self._force_calls[0] if self._count_forces else None,
                    failed=self._failed, closed=self._closed, finished=self.finished)

    def next(self, *, until=None):
        if self._failed:
            raise RuntimeError('IAS15 session failed; the last committed snapshot remains available')
        if self._closed:
            raise RuntimeError('IAS15 session is closed')
        previous = self._committed
        current, packets, committed_steps, _ = previous
        limit = self.target if until is None else until
        if (type(limit) not in (int, float) or not np.isfinite(limit)
                or not current.time <= limit <= self.target):
            raise ValueError('Invalid IAS15 packet limit')
        if limit == current.time:
            return self.current
        end = packet_end(current.time, float(limit), self._packet_dt)
        self._attempts += 1
        try:
            if self._sim.t != current.time:
                raise RuntimeError('IAS15 controller clock differs from committed snapshot')
            self._sim.integrate(end, exact_finish_time=1)
            if self._sim.t != end:
                raise RuntimeError('IAS15 did not reach the exact packet endpoint')
            if (self._sim.G != G or self._sim.gravity != 'basic' or self._sim.softening != 0
                    or self._sim.N != 2 or bits([p.m for p in self._sim.particles]) != bits(self._masses)
                    or self._sim.integrator.epsilon != self._epsilon
                    or self._sim.integrator.adaptive_mode != 'PRS23' or self._sim.integrator.min_dt != 0):
                raise RuntimeError('IAS15 physical model or masses changed inside a packet')
            candidate = _physical_snapshot(end, self._masses, snapshot(self._sim), current.origin)
            steps = int(self._sim.steps_done)
            if steps < committed_steps:
                raise RuntimeError('IAS15 step counter moved backwards')
            self._committed = (candidate, packets+1, steps, self._force_calls[0])
        except BaseException:
            self._committed = previous
            self._failed = True
            self._sim = None
            raise
        return self.current

    def close(self):
        self._sim = None
        self._closed = True

    def __enter__(self):
        if self._closed or self._failed:
            raise RuntimeError('IAS15 session is unavailable')
        return self

    def __exit__(self, *exception):
        self.close()
        return False
