"""Explicit, bounded DOP853 continuation for smooth native point-mass models.

This session owns solver buffers; ordinary advance/checkpoints keep their old
behavior. Every snapshot is an accepted step endpoint, never extrapolated.
Extending a finished solver relies on the pinned SciPy implementation.
"""
from dataclasses import replace
from math import fsum, isfinite

import numpy as np
import scipy

from .coordinates import prepare_pair
from .error_control import PerBodyDOP853
from .experiment import copy_bodies, create_experiment, validate_start
from .native_forces import prepare as prepare_native
from .oblateness import (prepare, acceleration, orientation_power, potential_energy,
                        prescribed, validate_figures, validate_orientation_origin)
from .relativity import C
from .simulation import Body
from .time_control import validate_target
from .vector3 import Vector3

SCIPY_VERSION = "1.18.1"


def _copy(state):
    return replace(state, initial=copy_bodies(state.initial), bodies=copy_bodies(state.bodies))


class ContinuousRun:
    """Single-threaded run to a finite target; use a new session after editing.

    Pausing requires no step into the future. Loading a physical checkpoint
    starts a new controller; controller buffers are deliberately not serialized.
    Returned snapshots never expose this session's owned mutable body lists.
    """

    def __init__(self, experiment, target):
        if scipy.__version__ != SCIPY_VERSION:
            raise RuntimeError("Продолжение DOP853 проверено только с SciPy "+SCIPY_VERSION)
        settings = experiment.settings
        if settings.backend != "rust" or settings.integrator != "dop853" or settings.error_control != "per-body":
            raise ValueError("Продолжение требует Rust, DOP853 и per-body")
        if (experiment.rotations or experiment.initial_rotations or experiment.events
                or experiment.halted or experiment.dissipated_energy or experiment.model_energy_offset
                or any(body.radius for body in experiment.bodies)):
            raise ValueError("Продолжение поддерживает точечные тела без контактов и динамического вращения")
        validate_start(experiment)
        validate_target(experiment, target)
        # Fresh Body/experiment validation rejects mutations of a caller's state.
        create_experiment(copy_bodies(experiment.bodies), settings, origin=experiment.origin)
        validate_orientation_origin(settings.figures, experiment.origin)
        validate_figures(experiment.bodies, settings.figures, target)
        if not isfinite(experiment.orientation_work):
            raise ValueError("Неконечная накопленная работа ориентации")
        self._seed = _copy(experiment)
        self._current = _copy(experiment)
        self._target = float(target)
        self._start = float(experiment.time)
        self._solver = None
        self._failed = False
        self._packets = 0
        self._count = len(experiment.bodies)
        self._masses = np.array([body.mass for body in experiment.bodies])
        self._force = prepare_native(self._masses)
        self._figures = prepare(experiment.bodies, settings.figures)
        self._moving = prescribed(settings.figures)
        self._pair = prepare_pair(experiment.bodies, settings.relative_pair)
        p = np.array([(b.position.x, b.position.y, b.position.z) for b in experiment.bodies])
        v = np.array([(b.velocity.x, b.velocity.y, b.velocity.z) for b in experiment.bodies])
        weights = self._masses/self._masses.max()
        weights /= fsum(weights)
        self._center = np.array([fsum(weights*p[:, k]) for k in range(3)])
        self._drift = np.array([fsum(weights*v[:, k]) for k in range(3)])
        p0, v0 = p-self._center, v-self._drift
        if self._pair:
            p0 = self._pair.encode(p, offset=self._center)
            v0 = self._pair.encode(v, offset=self._drift)
        self._initial = np.concatenate((p0.ravel(), v0.ravel()))
        self._atol = np.concatenate((np.full(3*self._count, settings.position_atol),
                                     np.full(3*self._count, settings.velocity_atol)))
        self._work_scale = (max(abs(potential_energy(experiment.bodies, settings.figures,
                                                    experiment.time)), 1.) if self._moving else 1.)
        if self._moving:
            self._initial = np.append(self._initial, 0.)
            self._atol = np.append(self._atol, 1e-15)

    @property
    def target(self):
        return self._target

    @property
    def current(self):
        return _copy(self._current)

    @property
    def finished(self):
        return self._current.time == self.target

    @property
    def statistics(self):
        return dict(packets=self._packets, rhs_calls=self._solver.nfev if self._solver else 0,
                    failed=self._failed, finished=self.finished)

    def _rhs(self, time, state):
        n = self._count
        p = state[:3*n].reshape(n, 3)
        v = state[3*n:6*n].reshape(n, 3)
        solver_velocity = v
        pair = None
        if self._pair:
            pair = (self._pair.first, self._pair.second, p[self._pair.second])
            p, v = self._pair.decode(p), self._pair.decode(v)
        epoch = float(self._start+time)
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            force = self._force(p, v+self._drift,
                C if self._seed.settings.physics == "eih-1pn" else None, pair)
            if self._figures:
                force += acceleration(p, self._masses, self._figures, epoch, _pair_displacement=pair)
            encoded = self._pair.encode(force) if self._pair else force
            derivative = np.concatenate((solver_velocity.ravel(), encoded.ravel()))
            if self._moving:
                derivative = np.append(derivative, orientation_power(p, self._masses,
                    self._figures, epoch, _pair_displacement=pair)/self._work_scale)
        return derivative

    def next(self, max_steps=20, *, until=None):
        """Compute one bounded packet, committing only its complete snapshot."""
        validate_target(self._current, self.target, max_steps)
        limit = self.target if until is None else until
        validate_target(self._current, limit, max_steps)
        if limit > self.target:
            raise ValueError("Граница снимка превышает конечное время сессии")
        if self._failed:
            raise RuntimeError("Сессия завершилась ошибкой; начните новую с последнего снимка")
        if self.finished or limit == self._current.time:
            return self.current
        remaining = limit-self._current.time
        dt = self._seed.settings.dt
        end = min(self._current.time+dt*max_steps,float(limit)) if dt <= remaining/max_steps else float(limit)
        local_end = end-self._start
        if end <= self._current.time or self._start+local_end != end:
            raise ValueError("Граница пакета не представима при текущей точности времени")
        try:
            if self._solver is None:
                self._solver = PerBodyDOP853(self._rhs, 0., self._initial, local_end,
                    rtol=self._seed.settings.rtol, atol=self._atol)
            else:
                if self._solver.status != "finished" or self._solver.t >= local_end:
                    raise RuntimeError("Неверное состояние продолжения DOP853")
                self._solver.t_bound = local_end
                self._solver.status = "running"
            while self._solver.status == "running":
                message = self._solver.step()
                if self._solver.status == "failed":
                    raise RuntimeError("DOP853 не достиг границы пакета: "+str(message))
            if self._solver.t != local_end or not np.all(np.isfinite(self._solver.y)):
                raise RuntimeError("DOP853 не выдал конечный снимок")
            state = self._solver.y
            n = self._count
            p, v = state[:3*n].reshape(n, 3), state[3*n:6*n].reshape(n, 3)
            if self._pair:
                p, v = self._pair.decode(p), self._pair.decode(v)
            p, v = p+self._center+self._drift*local_end, v+self._drift
            bodies = [Body(b.name, b.mass, Vector3(*map(float, position)),
                Vector3(*map(float, velocity)), b.radius, b.spin)
                for b, position, velocity in zip(self._seed.bodies, p, v)]
            work = self._seed.orientation_work+(float(state[-1])*self._work_scale if self._moving else 0.)
            if not isfinite(work):
                raise ValueError("Переполнение накопленной работы ориентации")
            self._current = replace(self._seed, bodies=bodies, time=end, orientation_work=work)
            self._packets += 1
        except Exception:
            self._failed = True
            raise
        return self.current
