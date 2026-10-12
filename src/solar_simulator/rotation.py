"""Conservative Newtonian model tasks, not the planetary runtime.

One rigid figure and one point mass, truncated at second mass moment.
SI; quaternion (w,x,y,z) maps principal body axes to an inertial right frame;
spin angular momentum is inertial. See docs/conservative-rotation.md.
"""
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .simulation import G


def _vector(value, size, name):
    result = np.array(value, dtype=float, copy=True)
    if result.shape != (size,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name}: требуется {size} конечных чисел")
    return result


@dataclass(frozen=True)
class RigidFigure:
    mass: float
    moments: tuple[float, float, float]
    bounding_radius: float

    def __post_init__(self):
        inertia = _vector(self.moments, 3, "Инерция")
        if (not np.isfinite(self.mass) or self.mass <= 0
                or not np.isfinite(self.bounding_radius) or self.bounding_radius <= 0
                or np.any(inertia <= 0)):
            raise ValueError("Масса, радиус и моменты инерции должны быть положительными")
        # Second mass moments D = tr(I)/2 - I must be nonnegative.
        second = .5*sum(inertia)-inertia
        if np.any(second < 0) or sum(second) > self.mass*self.bounding_radius**2:
            raise ValueError("Инерция несовместима с массой и ограничивающей сферой")
        object.__setattr__(self, "moments", tuple(map(float, inertia)))

    @property
    def quadrupole(self):
        """Specific Q in m²; it is derived, never a separate fitted input."""
        inertia = np.array(self.moments)
        return np.diag((3*inertia-sum(inertia))/self.mass)


def rotation_matrix(quaternion):
    q = _vector(quaternion, 4, "Кватернион")
    norm = np.linalg.norm(q)
    if norm == 0:
        raise ValueError("Нулевой кватернион")
    w, x, y, z = q/norm
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                     [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                     [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])


def angular_velocity(figure, quaternion, spin):
    rotation = rotation_matrix(quaternion)
    return rotation @ ((rotation.T @ _vector(spin, 3, "S"))/figure.moments)


def quaternion_rate(quaternion, omega):
    """qdot = (0, omega_inertial) ⊗ q / 2; no artificial damping."""
    w, xyz = quaternion[0], np.asarray(quaternion[1:])
    return .5*np.concatenate(([-np.dot(omega, xyz)], w*omega+np.cross(omega, xyz)))


def pair_field(figure, point_mass, displacement, quaternion):
    """Return U [J], force on point [N], torque on figure [N m]."""
    if not np.isfinite(point_mass) or point_mass <= 0:
        raise ValueError("Масса точки должна быть положительной")
    r = _vector(displacement, 3, "r")
    distance = np.linalg.norm(r)
    if distance <= figure.bounding_radius:
        raise ValueError("Разложение определено только вне ограничивающей сферы")
    n = r/distance
    rotation = rotation_matrix(quaternion)
    q = rotation @ figure.quadrupole @ rotation.T
    qn = q @ n
    coupling = G*figure.mass*point_mass
    potential = -coupling/distance+coupling*np.dot(n, qn)/(2*distance**3)
    force = -coupling*n/distance**2-coupling*(qn-2.5*np.dot(n, qn)*n)/distance**4
    torque = coupling*np.cross(n, qn)/distance**3
    return float(potential), force, torque


def free_rhs(figure, state):
    """State q[4], S[3]. Free body's inertial S is constant."""
    q, spin = state[:4], state[4:]
    return np.concatenate((quaternion_rate(q, angular_velocity(figure, q, spin)), np.zeros(3)))


def pair_rhs(figure, point_mass, state):
    """State r[3], relative v[3], q[4], inertial S[3]; COM eliminated."""
    r, velocity, q, spin = state[:3], state[3:6], state[6:10], state[10:13]
    _, force, torque = pair_field(figure, point_mass, r, q)
    inverse_reduced_mass = 1/figure.mass+1/point_mass
    return np.concatenate((velocity, force*inverse_reduced_mass,
        quaternion_rate(q, angular_velocity(figure, q, spin)), torque))


def invariants(figure, state, point_mass=None):
    """Internal energy and total angular momentum in the COM frame."""
    if point_mass is None:
        q, spin = state[:4], state[4:]
        return .5*np.dot(spin, angular_velocity(figure, q, spin)), np.array(spin, copy=True)
    r, velocity, q, spin = state[:3], state[3:6], state[6:10], state[10:13]
    reduced_mass = figure.mass*point_mass/(figure.mass+point_mass)
    potential, _, _ = pair_field(figure, point_mass, r, q)
    energy = .5*reduced_mass*np.dot(velocity, velocity)+potential
    energy += .5*np.dot(spin, angular_velocity(figure, q, spin))
    return energy, reduced_mass*np.cross(r, velocity)+spin


def integrate(figure, initial, times, *, point_mass=None, rtol=1e-11,
              atol=1e-12, max_step=np.inf):
    """DOP853 model solver; atol may specify each state's SI component.

    Raw quaternion norm is retained for audit; only the field's rotation
    matrix uses its normalized representation. This is not symplectic.
    """
    initial = _vector(initial, 7 if point_mass is None else 13, "Состояние")
    times = np.asarray(times, dtype=float)
    if (times.ndim != 1 or len(times) < 2 or not np.all(np.isfinite(times))
            or np.any(np.diff(times) <= 0)):
        raise ValueError("Нужна строго возрастающая конечная сетка времени")
    q = initial[:4] if point_mass is None else initial[6:10]
    if abs(np.linalg.norm(q)-1) > 1e-12:
        raise ValueError("Начальный кватернион должен быть единичным")
    if point_mass is None:
        rhs = lambda t, y: free_rhs(figure, y)
    else:
        rhs = lambda t, y: pair_rhs(figure, point_mass, y)
    solution = solve_ivp(rhs, (times[0], times[-1]), initial, t_eval=times,
                         method="DOP853", rtol=rtol, atol=atol, max_step=max_step)
    if not solution.success or not np.all(np.isfinite(solution.y)):
        raise ValueError(f"Расчёт вращения не завершён: {solution.message}")
    return solution.y.T
