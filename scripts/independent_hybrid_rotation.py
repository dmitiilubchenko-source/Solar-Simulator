"""Original ordered EIH action and matrix/body-Euler oracle, G=1.

Does not import hybrid_rotation, runtime figure forces or quaternion formulas.
Noether/velocity derivatives follow the scalar point action, not ADM H57.
"""
import numpy as np

from scripts.assess_relativity import independent_acceleration


def hat(w):
    a, b, c = w
    return np.array([[0., -c, b], [c, 0., -a], [-b, a, 0.]])


def action(x, v, masses, c):
    n = len(masses)
    value = sum(masses[i]*(np.dot(v[i], v[i])/2+np.dot(v[i], v[i])**2/(8*c**2)) for i in range(n))
    distances = {(i, j): np.sqrt(np.dot(x[i]-x[j], x[i]-x[j]))
        for i in range(n) for j in range(n) if i != j}
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            r = distances[i, j]; normal = (x[i]-x[j])/r
            value += masses[i]*masses[j]/(2*r)
            value += masses[i]*masses[j]/(4*r*c**2)*(3*np.dot(v[i], v[i])+3*np.dot(v[j], v[j])
                -7*np.dot(v[i], v[j])-np.dot(normal, v[i])*np.dot(normal, v[j]))
            for k in range(n):
                if k != j:
                    value -= masses[i]*masses[j]*masses[k]/(2*c**2*r*distances[j, k])
    return value


def momentum1(x, v, masses, c):
    # Analytic first derivative of the ordered action; remains complex analytic.
    result = np.array([mass*np.dot(w, w)*w/(2*c**2) for mass, w in zip(masses, v)],
        dtype=np.result_type(x, v, float))
    for i in range(len(masses)):
        for j in range(len(masses)):
            if i == j:
                continue
            r = x[i]-x[j]; radius = np.sqrt(np.dot(r, r)); normal = r/radius
            result[i] += masses[i]*masses[j]/(2*c**2*radius)*(
                6*v[i]-7*v[j]-normal*np.dot(normal, v[j]))
    return result


def derivatives(x, v, masses, c):
    step = 1e-25
    h = np.empty((x.size, x.size))
    gx = np.empty_like(x)
    for k in range(x.size):
        z = v.astype(complex); z.ravel()[k] += 1j*step
        h[:, k] = momentum1(x, z, masses, c).imag.ravel()/step
        z = x.astype(complex); z.ravel()[k] += 1j*step
        gx.ravel()[k] = action(z, v, masses, c).imag/step
    transport = momentum1(x+1j*step*v, v, masses, c).imag/step
    return h, gx-transport


def body_field(x, masses, matrix, moments, source, radius):
    force = np.zeros_like(x); torque = np.zeros(3); energy = 0.
    for j in range(len(masses)):
        if j == source:
            continue
        r = x[j]-x[source]; d = np.linalg.norm(r)
        if d <= radius:
            raise ValueError('Reference figure external field only')
        n = matrix.T@(r/d); inertia_n = np.array(moments)*n; projection = np.dot(n, inertia_n)
        f = -3*masses[j]/d**4*(inertia_n+.5*(sum(moments)-5*projection)*n)
        force[j] += matrix@f; force[source] -= matrix@f
        torque += 3*masses[j]/d**3*np.cross(n, inertia_n)
        energy += masses[j]*(3*projection-sum(moments))/(2*d**3)
    return force, torque, energy


def pack(x, v, force):
    return np.r_[sum(np.dot(a, b) for a, b in zip(v, force)),
        sum(force), sum(np.cross(a, b) for a, b in zip(x, force))]


def rhs(time, state, masses, c, moments, source, radius, mode):
    n = len(masses); x = state[:3*n].reshape(n, 3); v = state[3*n:6*n].reshape(n, 3)
    delta = x[:, None, :]-x[None, :, :]
    distances = np.linalg.norm(delta, axis=2); np.fill_diagonal(distances, np.inf)
    if (not np.isfinite(x).all() or not np.isfinite(v).all() or np.any(distances == 0)
            or not np.isfinite(c) or c <= 0):
        raise ValueError('Finite distinct reference states and positive c required')
    potential = np.sum(np.asarray(masses)[None, :]/distances, axis=1)
    if max(float(potential.max()), float(np.sum(v*v, axis=1).max()))/c**2 >= 1e-4:
        raise ValueError('Reference outside weak-field domain')
    matrix = state[6*n:6*n+9].reshape(3, 3); pi = state[6*n+9:6*n+12]
    f, torque_body, _ = body_field(x, masses, matrix, moments, source, radius)
    # OR uses a separate scalar-target EIH implementation; exact variant uses
    # the full Euler-Lagrange force from the original scalar action.
    step = 1e-25
    if mode == 'finite-action':
        h, k = derivatives(x, v, masses, c)
        a = np.linalg.solve(np.diag(np.repeat(masses, 3))+h, (k+f).ravel()).reshape(n, 3)
        budget = np.zeros((2, 7))
    elif mode == 'order-reduced':
        point = independent_acceleration(x, v, np.asarray(masses), c)
        an = np.zeros_like(x)
        for i in range(n):
            for j in range(n):
                if i != j:
                    r = x[j]-x[i]; an[i] += masses[j]*r/np.linalg.norm(r)**3
        aq = f/np.asarray(masses)[:, None]
        a = point+aq
        response = [momentum1(x, v+1j*step*b, masses, c).imag/step for b in (point-an, aq)]
        budget = np.array([pack(x, v, row) for row in response])
    else:
        raise ValueError('Unknown reference truncation')
    omega_body = pi/np.array(moments)
    return np.r_[v.ravel(), a.ravel(), (matrix@hat(omega_body)).ravel(),
        np.cross(pi, omega_body)+torque_body, budget.ravel()]


def quantities(state, masses, c, moments, source, matrix=None):
    n = len(masses); x = state[:3*n].reshape(n, 3); v = state[3*n:6*n].reshape(n, 3)
    if matrix is None:
        raise ValueError('Explicit orientation required; no quaternion conversion in reference')
    spin = state[6*n+4:6*n+7]
    p = np.asarray(masses)[:, None]*v+momentum1(x, v, masses, c)
    energy = sum(np.dot(a, b) for a, b in zip(v, p))-action(x, v, masses, c)
    local_spin = matrix.T@spin
    energy += .5*np.sum(local_spin**2/np.array(moments))
    energy += body_field(x, masses, matrix, moments, source, 0.)[2]
    return np.r_[energy, p.sum(axis=0), np.cross(x, p).sum(axis=0)+spin]
