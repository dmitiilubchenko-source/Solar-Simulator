"""Exterior quadrupole gravity, with fixed or explicitly prescribed axes.

This is a controlled approximation, not coupled spin/orbit dynamics.
Every figure/point interaction includes the reaction on the figure's body.
"""
from dataclasses import dataclass
from math import fsum, isfinite, sqrt

import numpy as np

from .simulation import G

EARTH_PROFILE_SHA256 = "f078a600e0da97fcf1c63e462c1af8b60f75d9fa336382a79ee436e404a14be1"


@dataclass(frozen=True)
class FixedJ2:
    body: str
    coefficient: float
    reference_radius: float
    axis: tuple[float, float, float]
    provenance: str = "user-specified"

    def __post_init__(self):
        if type(self.body) is not str or not self.body.strip():
            raise ValueError("J2 требует имя тела")
        if (type(self.coefficient) not in (int, float) or not isfinite(self.coefficient)
                or not 0 < abs(self.coefficient) <= 0.01):
            raise ValueError("Для ограниченной модели нужно 0 < |J2| <= 0.01")
        if (type(self.reference_radius) not in (int, float) or not isfinite(self.reference_radius)
                or self.reference_radius <= 0):
            raise ValueError("Опорный радиус J2 должен быть положительным конечным числом")
        if (type(self.axis) is not tuple or len(self.axis) != 3
                or any(type(x) not in (int, float) or not isfinite(x) for x in self.axis)
                or abs(sqrt(fsum(x*x for x in self.axis))-1) > 1e-12):
            raise ValueError("Ось J2 должна быть единичным вектором из трёх чисел")
        if type(self.provenance) is not str or not 1 <= len(self.provenance) <= 1000:
            raise ValueError("Нужно происхождение параметров J2")


@dataclass(frozen=True)
class PrescribedQuadrupole:
    body: str
    coefficient: float
    reference_radius: float
    c22: float
    orientation: str
    profile_sha256: str
    provenance: str = "DE441 nominal coefficients and prescribed orientation"

    def __post_init__(self):
        from .orientation import PROFILE_SHA256
        if (self.body, self.orientation) not in (("Earth", "earth-de441"), ("Moon", "moon-de441")):
            raise ValueError("Неизвестная модель заданной ориентации")
        if self.profile_sha256 != PROFILE_SHA256:
            raise ValueError("Неизвестный профиль ориентации; контрольная точка требует совместимых данных")
        if (any(type(x) not in (int, float) or not isfinite(x) or abs(x) > .01
                for x in (self.coefficient, self.c22)) or not (self.coefficient or self.c22)):
            raise ValueError("Нужны конечные J2/C22 в пределах 0.01 и ненулевое поле")
        if self.orientation == "earth-de441" and self.c22 != 0:
            raise ValueError("Модель полюса Земли поддерживает только осесимметричное J2")
        if (type(self.reference_radius) not in (int, float) or not isfinite(self.reference_radius)
                or self.reference_radius <= 0):
            raise ValueError("Опорный радиус должен быть положительным конечным числом")
        if type(self.provenance) is not str or not 1 <= len(self.provenance) <= 1000:
            raise ValueError("Нужно происхождение параметров квадруполя")


def prescribed(figures):
    return any(isinstance(f, PrescribedQuadrupole) for f in figures)


def validate_orientation_origin(figures, origin):
    if prescribed(figures):
        from .orientation import profile
        data = profile()
        if (origin is None or origin.dataset_sha256 != data["dataset_sha256"]
                or origin.epoch_jd_tdb != data["epoch_jd_tdb"] or origin.frame != data["frame"]):
            raise ValueError("Заданная ориентация требует solar-system-moon с эпохой 2026-10-08 TDB")


def validate_figures(bodies, figures, time=0.):
    if type(figures) is not tuple or any(not isinstance(f, (FixedJ2, PrescribedQuadrupole)) for f in figures):
        raise ValueError("Параметры фигур должны быть кортежем FixedJ2/PrescribedQuadrupole")
    if len({f.body for f in figures}) != len(figures):
        raise ValueError("Повторяющаяся фигура J2")
    names = [b.name for b in bodies]
    if figures and (len(set(names)) != len(names) or any(b.radius or b.spin.magnitude() for b in bodies)):
        raise ValueError("J2 требует уникальные имена, нулевые контактные радиусы и passive spin")
    for figure in figures:
        if figure.body not in names:
            raise ValueError("Тело фигуры J2 отсутствует в эксперименте")
        source = bodies[names.index(figure.body)]
        for target in bodies:
            if target is not source and target.position.distance_to(source.position) <= figure.reference_radius:
                raise ValueError("J2 определена только вне опорного радиуса источника")
    if prescribed(figures):
        from .orientation import profile, validate_time
        profile()
        validate_time(time)


def prepare(bodies, figures):
    validate_figures(bodies, figures)
    names = [b.name for b in bodies]
    return tuple((names.index(f.body), f.coefficient, f.reference_radius,
                  np.array(f.axis) if isinstance(f, FixedJ2) else f) for f in figures)


def tensors(prepared, time=0.):
    """Q and dQ/dt for V2 = G*m_i*m_j*(r Q r)/(2*r^5)."""
    result = []
    for source, coefficient, radius, axis in prepared:
        if isinstance(axis, PrescribedQuadrupole):
            from .orientation import earth_pole, lunar_rotation
            if axis.orientation == "earth-de441":
                s, ds = earth_pole(time)
                q = coefficient*radius**2*(3*np.outer(s, s)-np.eye(3))
                dq = 3*coefficient*radius**2*(np.outer(ds, s)+np.outer(s, ds))
            else:
                rotation, derivative = lunar_rotation(time)
                body_q = radius**2*np.diag([-coefficient-6*axis.c22, -coefficient+6*axis.c22, 2*coefficient])
                q = rotation @ body_q @ rotation.T
                dq = derivative @ body_q @ rotation.T + rotation @ body_q @ derivative.T
        else:
            q = coefficient*radius**2*(3*np.outer(axis, axis)-np.eye(3))
            dq = np.zeros((3, 3))
        result.append((source, radius, q, dq))
    return result


def acceleration(positions, masses, prepared, time=0.):
    """Quadrupole correction only; includes the source reaction for every pair."""
    positions = np.asarray(positions, dtype=float)
    result = np.zeros_like(positions)
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        for entry, (source, radius, q, _) in zip(prepared, tensors(prepared, time)):
            targets = np.arange(len(masses)) != source
            r = positions[targets]-positions[source]
            distance = np.linalg.norm(r, axis=1)
            if np.any(distance <= radius):
                raise ValueError("J2 определена только вне опорного радиуса источника")
            direction = r/distance[:, None]
            if not isinstance(entry[3], PrescribedQuadrupole):
                # Keep the axis-specific expression as an independent
                # representation of the tensor field for the fixed model.
                coefficient, axis = entry[1], entry[3]
                latitude = direction @ axis
                field = (1.5*G*masses[source]*coefficient*(radius/distance)**2/distance**2)[:, None]*(
                    (5*latitude**2-1)[:, None]*direction-2*latitude[:, None]*axis)
            else:
                qn = direction @ q
                field = (-G*masses[source]/distance**4)[:, None]*(
                    qn-2.5*np.sum(direction*qn, axis=1)[:, None]*direction)
            result[targets] += field
            result[source] -= np.sum(field*(masses[targets]/masses[source])[:, None], axis=0)
    return result


def potential_energy(bodies, figures, time=0.):
    """Additional pair potential, with no quadrupole/quadrupole term."""
    prepared = prepare(bodies, figures)
    validate_figures(bodies, figures, time)
    terms = []
    for index, _, q, _ in tensors(prepared, time):
        source = bodies[index]
        for target in bodies:
            if target is source:
                continue
            r = target.position.subtract(source.position)
            distance = r.magnitude()
            direction = np.array([r.x, r.y, r.z])/distance
            terms.append(float(G*source.mass*target.mass/(2*distance**3)*(direction @ q @ direction)))
    result = fsum(terms)
    if not isfinite(result):
        raise ValueError("Неконечная потенциальная энергия J2")
    return result


def orientation_power(positions, masses, prepared, time):
    """Explicit partial derivative of potential at fixed positions, in watts."""
    terms = []
    for source, radius, _, dq in tensors(prepared, time):
        r = positions[np.arange(len(masses)) != source]-positions[source]
        distance = np.linalg.norm(r, axis=1)
        if np.any(distance <= radius):
            raise ValueError("Квадруполь определён только вне опорного радиуса источника")
        direction = r/distance[:, None]
        mass = masses[np.arange(len(masses)) != source]
        terms.extend(G*masses[source]*mass/(2*distance**3)*np.sum((direction @ dq)*direction, axis=1))
    return float(fsum(terms))


def orbital_torque(bodies, figures, time=0.):
    """Instantaneous dL_orb/dt due to fixed figures, in kg m²/s².

    The opposite torque would act on the spins in a coupled model.
    Computing about the first body avoids large absolute-coordinate cancellation.
    """
    from .vector3 import Vector3
    p = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    m = np.array([b.mass for b in bodies])
    force = acceleration(p-p[0], m, prepare(bodies, figures), time)*m[:, None]
    torque = np.sum(np.cross(p-p[0], force), axis=0)
    return Vector3(*map(float, torque))


def earth_j2(bodies, origin):
    """Pinned DE441 coefficient + approximate IAU pole frozen at snapshot epoch.

    Explicitly restricted to the verified resolved Earth/Moon initial dataset.
    Checkpoints store all numbers, so profile updates cannot change a saved run.
    """
    import json
    import hashlib
    from importlib.resources import files
    data = files("solar_simulator.data").joinpath("earth-j2-20261008.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != EARTH_PROFILE_SHA256:
        raise ValueError("Изменён закреплённый профиль Earth J2; требуется проверка параметров")
    profile = json.loads(data)
    if (origin is None or origin.dataset_sha256 != profile["dataset_sha256"]
            or origin.frame != profile["frame"] or origin.epoch_jd_tdb != profile["epoch_jd_tdb"]
            or {b.name for b in bodies} != set(profile["bodies"])):
        raise ValueError("earth-j2 требует исходный solar-system-moon с эпохой 2026-10-08 TDB")
    figure = FixedJ2("Earth", profile["coefficient"], profile["reference_radius_metres"],
                     tuple(profile["axis"]), profile["provenance"])
    validate_figures(bodies, (figure,))
    return (figure,)


def earth_moon_quadrupoles(bodies, origin, *, moon=True):
    """Published nominal fields; orientation is a separate, pinned input."""
    from .orientation import PROFILE_SHA256, profile
    data = profile()
    figures = tuple(PrescribedQuadrupole(name, data["figures"][name]["j2"],
        data["figures"][name]["radius_metres"], data["figures"][name]["c22"],
        name.lower()+"-de441", PROFILE_SHA256) for name in (("Earth", "Moon") if moon else ("Earth",)))
    validate_orientation_origin(figures, origin)
    validate_figures(bodies, figures)
    return figures
