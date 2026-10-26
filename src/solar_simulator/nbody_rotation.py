"""Conservative Newtonian N-body with ONE dynamical rigid Q2 figure.

SI; q=(w,x,y,z) body→inertial, S inertial. Point forces are computed once;
the figure correction, reaction and torque follow one common potential.
No prescribed axes, tides, EIH, contacts or figure–figure terms.
"""
from dataclasses import dataclass, replace
from math import fsum, isfinite

import numpy as np
from scipy.integrate import DOP853, solve_ivp

from .coordinates import prepare_pair
from .rotation import RigidFigure, angular_velocity, quaternion_rate, rotation_matrix, _vector
from .simulation import Body, G
from .vector3 import Vector3
from ._numbers import finite_number


@dataclass(frozen=True)
class RotationState:
    body: str
    figure: RigidFigure
    quaternion: tuple[float, float, float, float]
    angular_momentum: tuple[float, float, float]
    quaternion_atol: float
    momentum_atol: float
    provenance: str = "user-specified rigid Q2"

    def __post_init__(self):
        for name in ("quaternion_atol", "momentum_atol"):
            object.__setattr__(self, name, finite_number(getattr(self, name), name))
        if not isinstance(self.figure, RigidFigure) or type(self.body) is not str or not self.body.strip():
            raise ValueError("Нужны имя и инерция вращающегося тела")
        q = _vector(self.quaternion, 4, "q")
        s = _vector(self.angular_momentum, 3, "S")
        if abs(np.linalg.norm(q)-1) > 1e-8:
            raise ValueError("Норма q вышла за область проверенного вращения")
        for value in (self.quaternion_atol, self.momentum_atol):
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise ValueError("Допуски q/S должны быть положительными конечными")
        if type(self.provenance) is not str or not 1 <= len(self.provenance) <= 1000:
            raise ValueError("Нужно происхождение вращательного состояния")
        object.__setattr__(self, "quaternion", tuple(map(float, q)))
        object.__setattr__(self, "angular_momentum", tuple(map(float, s)))


def validate(bodies, rotations, settings=None):
    """Unsupported combinations fail before integration/serialization."""
    if type(rotations) is not tuple or len(rotations) != 1 or not isinstance(rotations[0], RotationState):
        raise ValueError("Этот режим поддерживает ровно одну динамическую фигуру")
    names = [b.name for b in bodies]
    state = rotations[0]
    if not bodies or len(set(names)) != len(names) or state.body not in names:
        raise ValueError("Нужны уникальные тела и существующая вращающаяся фигура")
    index = names.index(state.body)
    if state.figure.mass != bodies[index].mass:
        raise ValueError("Масса инерции не совпадает с массой тела")
    if any(b.radius != 0 or b.spin.magnitude() != 0 for b in bodies):
        raise ValueError("Динамическое Q2 требует нулевых контактных радиусов и passive spin")
    if settings is not None and (settings.physics != "newtonian" or settings.integrator != "dop853"
            or settings.figures or settings.error_control != "per-body"):
        raise ValueError("Вращение требует Newton/DOP853/per-body без заданных фигур")
    p = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    correction(p, np.array([b.mass for b in bodies]), index, state.figure, state.quaternion)
    return index


def correction(positions, masses, source, figure, quaternion, pair_displacement=None):
    """Return Q2 acceleration, figure torque and Q2 potential (not monopole)."""
    positions, masses = np.asarray(positions, dtype=float), np.asarray(masses, dtype=float)
    if (masses.ndim != 1 or not masses.size or positions.shape != (len(masses),3)
            or not np.all(np.isfinite(positions)) or not np.all(np.isfinite(masses))
            or np.any(masses <= 0) or type(source) is not int or not 0 <= source < len(masses)
            or masses[source] != figure.mass):
        raise ValueError("Неверные позиции/массы/индекс динамической фигуры")
    targets = np.flatnonzero(np.arange(len(masses)) != source)
    r = positions[targets]-positions[source]
    if pair_displacement is not None:
        first, second, relative = pair_displacement
        if source in (first, second):
            target = second if source == first else first
            r[targets == target] = relative if source == first else -relative
    d = np.linalg.norm(r, axis=1)
    if np.any(d <= figure.bounding_radius):
        raise ValueError("Q2 определена только вне ограничивающей сферы")
    n = r/d[:, None]
    matrix = rotation_matrix(quaternion)
    tensor = matrix@figure.quadrupole@matrix.T
    qn = n@tensor
    nqn = np.sum(n*qn, axis=1)
    coupling = G*figure.mass*masses[targets]
    forces = -coupling[:, None]*(qn-2.5*nqn[:, None]*n)/d[:, None]**4
    acceleration = np.zeros_like(positions)
    acceleration[targets] = forces/masses[targets, None]
    acceleration[source] = -np.sum(forces, axis=0)/figure.mass
    torque = np.sum(coupling[:, None]*np.cross(n, qn)/d[:, None]**3, axis=0)
    potential = float(np.sum(coupling*nqn/(2*d**3)))
    if not np.all(np.isfinite(acceleration)) or not np.all(np.isfinite(torque)) or not isfinite(potential):
        raise ValueError("Переполнение поля динамического Q2")
    return acceleration, torque, potential


def validate_experiment(experiment):
    validate(experiment.initial, experiment.initial_rotations, experiment.settings)
    validate(experiment.bodies, experiment.rotations, experiment.settings)
    first, current = experiment.initial_rotations[0], experiment.rotations[0]
    if (first.body, first.figure, first.quaternion_atol, first.momentum_atol, first.provenance) != (current.body, current.figure, current.quaternion_atol, current.momentum_atol, current.provenance):
        raise ValueError("Инерция/допуски/происхождение вращения изменены в checkpoint")
    if abs(np.linalg.norm(first.quaternion)-1) > 1e-12:
        raise ValueError("Начальный q должен быть единичным")
    if experiment.time == 0 and experiment.initial_rotations != experiment.rotations:
        raise ValueError("При t=0 вращение должно совпадать с исходным")
    if experiment.orientation_work or experiment.dissipated_energy or experiment.model_energy_offset or experiment.events or experiment.halted:
        raise ValueError("Консервативное вращение не поддерживает историю контактов/заданной работы")


class RotationDOP853(DOP853):
    """Worst local 5(3) estimate over each r/v vector and separate q/S blocks."""
    def __init__(self, fun, t0, y0, t_bound, *, body_count, **kwargs):
        if type(body_count) is not int or body_count < 1 or np.size(y0) != 6*body_count+7:
            raise ValueError("Нужна раскладка 6N + q[4] + S[3]")
        self.blocks = [slice(k, k+3) for k in range(0, 6*body_count, 3)]
        self.blocks += [slice(6*body_count, 6*body_count+4), slice(6*body_count+4, 6*body_count+7)]
        super().__init__(fun, t0, y0, t_bound, **kwargs)

    def _estimate_error_norm(self, K, h, scale):
        e5, e3 = (K.T@self.E5)/scale, (K.T@self.E3)/scale
        if not np.all(np.isfinite(e5)) or not np.all(np.isfinite(e3)):
            raise ValueError("Неконечная оценка ошибки вращательного DOP853")
        worst = 0.
        for block in self.blocks:
            a, b = np.hypot.reduce(e5[block]), np.hypot.reduce(e3[block])
            denominator = np.hypot(a, .1*b)
            value = (abs(h)*a)*(a/denominator)/np.sqrt(block.stop-block.start) if denominator else 0.
            worst = max(worst, float(value))
        if not isfinite(worst):
            raise ValueError("Переполнение оценки ошибки вращения")
        return worst


def integrate(bodies, rotations, times, *, rtol=1e-11, position_atol=1e-4,
              velocity_atol=1e-10, relative_pair=None, backend="python", max_step=np.inf):
    """Return snapshots (bodies, rotation tuple); retain raw q norm for audit."""
    if isinstance(max_step, np.floating) and max_step.dtype.itemsize <= 8:
        max_step = float(max_step)
    if not (type(max_step) is float and max_step == np.inf):
        max_step = finite_number(max_step, "max_step")
    raw_times = np.asarray(times, dtype=object)
    if raw_times.ndim != 1:
        raise ValueError("Нужна одномерная сетка эпох")
    times = _vector(times, len(raw_times), "Время")
    source = validate(bodies, rotations)
    state = rotations[0]
    if backend not in ("python", "rust"):
        raise ValueError("Неизвестное ядро сил")
    if type(rtol) not in (int, float) or not isfinite(rtol) or not 3e-14 <= rtol <= 1e-2:
        raise ValueError("rtol вне диапазона float64")
    for value in (position_atol, velocity_atol):
        if type(value) not in (int, float) or not isfinite(value) or value <= 0:
            raise ValueError("Допуски орбиты должны быть положительными конечными")
    times = np.asarray(times, dtype=float)
    if times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times)) or np.any(np.diff(times) <= 0):
        raise ValueError("Нужна строго возрастающая конечная сетка эпох")
    masses = np.array([b.mass for b in bodies])
    p = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    v = np.array([[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies])
    weights = masses/masses.max(); weights /= fsum(weights)
    center = np.array([fsum(weights*p[:, k]) for k in range(3)])
    drift = np.array([fsum(weights*v[:, k]) for k in range(3)])
    pair = prepare_pair(bodies, relative_pair)
    p0 = pair.encode(p, offset=center) if pair else p-center
    v0 = pair.encode(v, offset=drift) if pair else v-drift
    count = len(bodies); orbit_size = 6*count
    initial = np.concatenate((p0.ravel(), v0.ravel(), state.quaternion, state.angular_momentum))
    atol = np.array([position_atol]*(3*count)+[velocity_atol]*(3*count)
                    +[state.quaternion_atol]*4+[state.momentum_atol]*3)
    native = None
    if backend == "rust":
        from .native_forces import prepare
        native = prepare(masses)
    pairs = np.triu_indices(count, 1)

    def rhs(time, y):
        positions, velocities = y[:3*count].reshape(count, 3), y[3*count:orbit_size].reshape(count, 3)
        solver_velocity = velocities
        pair_r = (pair.first, pair.second, positions[pair.second]) if pair else None
        if pair:
            positions, velocities = pair.decode(positions), pair.decode(velocities)
        if native is not None:
            acceleration = native(positions, velocities+drift, relative_pair=pair_r)
        else:
            delta = positions[pairs[1]]-positions[pairs[0]]
            if pair_r is not None:
                a, b, rho = pair_r
                delta[(pairs[0] == min(a, b)) & (pairs[1] == max(a, b))] = rho if a < b else -rho
            distance = np.linalg.norm(delta, axis=1)
            if np.any(distance == 0):
                raise ValueError("Совпадающие положения: гравитация не определена")
            field = G*delta/distance[:, None]**3
            acceleration = np.zeros_like(positions)
            np.add.at(acceleration, pairs[0], field*masses[pairs[1], None])
            np.add.at(acceleration, pairs[1], -field*masses[pairs[0], None])
        q, spin = y[orbit_size:orbit_size+4], y[orbit_size+4:]
        additional, torque, _ = correction(positions, masses, source, state.figure, q, pair_r)
        acceleration += additional
        if pair:
            acceleration = pair.encode(acceleration)
        result = np.concatenate((solver_velocity.ravel(), acceleration.ravel(),
            quaternion_rate(q, angular_velocity(state.figure, q, spin)), torque))
        if not np.all(np.isfinite(result)):
            raise ValueError("Неконечная производная вращательного N-body")
        return result

    result = solve_ivp(rhs, (times[0], times[-1]), initial, t_eval=times,
        method=RotationDOP853, body_count=count, rtol=rtol, atol=atol, max_step=max_step)
    if not result.success or not np.all(np.isfinite(result.y)):
        raise ValueError(f"Расчёт вращения не завершён: {result.message}")
    snapshots = []
    for time, y in zip(times, result.y.T):
        positions, velocities = y[:3*count].reshape(count, 3), y[3*count:orbit_size].reshape(count, 3)
        if pair:
            positions, velocities = pair.decode(positions), pair.decode(velocities)
        positions = positions+center+drift*(time-times[0]); velocities = velocities+drift
        output = [Body(b.name, b.mass, Vector3(*map(float, pos)), Vector3(*map(float, vel))) for b, pos, vel in zip(bodies, positions, velocities)]
        rotation = replace(state, quaternion=tuple(y[orbit_size:orbit_size+4]), angular_momentum=tuple(y[orbit_size+4:]))
        snapshots.append((output, (rotation,)))
    return snapshots


def invariants(bodies, rotations):
    """Full Newtonian orbital+spin energy, linear momentum and total L."""
    source = validate(bodies, rotations)
    from .simulation import total_energy, total_momentum
    from .diagnostics import angular_momentum
    state = rotations[0]
    p = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    _, _, potential = correction(p, np.array([b.mass for b in bodies]), source, state.figure, state.quaternion)
    energy = total_energy(bodies)+potential+.5*np.dot(state.angular_momentum,
        angular_velocity(state.figure, state.quaternion, state.angular_momentum))
    return float(energy), total_momentum(bodies), angular_momentum(bodies).add(Vector3(*state.angular_momentum))


def lunar_initial(bodies, origin):
    """Attach the pinned one-epoch rigid surrogate, rejecting altered starts."""
    from .spin_initial import lunar_solid_equivalent_initial, PROFILE_SHA256
    from .perturbers import figure_parent_origin
    figure, point, initial, data = lunar_solid_equivalent_initial()
    parent = figure_parent_origin(origin)
    if parent is None or parent.dataset_sha256 != data["parent_dataset_sha256"] or parent.frame != data["frame"] or parent.epoch_jd_tdb != data["epoch_jd_tdb"]:
        raise ValueError("Начальное вращение требует закреплённой эпохи/данных Moon")
    by_name = {b.name: b for b in bodies}
    if "Earth" not in by_name or "Moon" not in by_name or by_name["Earth"].mass != point:
        raise ValueError("Нужны согласованные исходные Earth/Moon")
    relative_p = by_name["Earth"].position.subtract(by_name["Moon"].position)
    relative_v = by_name["Earth"].velocity.subtract(by_name["Moon"].velocity)
    if not np.allclose([relative_p.x, relative_p.y, relative_p.z], initial[:3], rtol=0, atol=1e-5) or not np.allclose([relative_v.x, relative_v.y, relative_v.z], initial[3:6], rtol=0, atol=1e-10):
        raise ValueError("Изменены закреплённые начальные данные пары")
    rotation = RotationState("Moon", figure, tuple(initial[6:10]), tuple(initial[10:]),
        1e-13, float(np.linalg.norm(initial[10:])*1e-13), "rigid-solid-equivalent; initial-only SHA256="+PROFILE_SHA256)
    rotations = (rotation,)
    validate(bodies, rotations)
    return rotations
