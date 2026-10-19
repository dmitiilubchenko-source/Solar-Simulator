"""Whole E/P/J directional derivative with a moving rigid figure, Decimal.

Reuses independently tested scalar EIH action/forces/Hessian; never rounds
Decimal coordinate, orientation or velocity perturbations through float64.
"""
from decimal import Decimal, localcontext

from scripts.noether_identities import dec, dot, cross, norm, plus, parts, forces, response, pack

ZERO = Decimal(0)
ONE = Decimal(1)


def matrix(q):
    q = [v/dot(q, q).sqrt() for v in q]
    w, x, y, z = q
    return [[ONE-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
        [2*(x*y+w*z), ONE-2*(x*x+z*z), 2*(y*z-w*x)],
        [2*(x*z-w*y), 2*(y*z+w*x), ONE-2*(x*x+y*y)]]


def tensor(r, inertia, mass):
    diag = [(3*i-sum(inertia))/mass for i in inertia]
    return [[sum((r[a][k]*diag[k]*r[b][k] for k in range(3)), ZERO)
        for b in range(3)] for a in range(3)]


def quantities(x, v, masses, inertia, source, radius, c, r, spin):
    fig = [(source, radius, tensor(r, inertia, masses[source]))]
    values = parts(x, v, masses, fig, ONE, c)
    row = plus(values['newton'], values['pn'], values['figure'])
    body_spin = [sum((r[k][j]*spin[k] for k in range(3)), ZERO) for j in range(3)]
    row[0] += sum((s*s/i for s, i in zip(body_spin, inertia)), ZERO)/2
    row[4:] = plus(row[4:], spin)
    return row


def snapshot(state, model, precision):
    if type(precision) is not int or precision not in (70, 90):
        raise ValueError('Declared precision is 70 or 90')
    with localcontext() as context:
        context.prec = precision
        n = len(model.masses); a = model.source
        x = [[dec(t) for t in state[3*k:3*k+3]] for k in range(n)]
        v = [[dec(t) for t in state[3*n+3*k:3*n+3*k+3]] for k in range(n)]
        m = list(map(dec, model.masses)); inertia = list(map(dec, model.moments))
        spin = list(map(dec, state[6*n+4:6*n+7])); r = matrix(list(map(dec, state[6*n:6*n+4])))
        c, radius = dec(model.c), dec(model.radius)
        q = tensor(r, inertia, m[a]); fig = [(a, radius, q)]
        an, ap, aq = forces(x, v, m, fig, ONE, c)
        total_a = [plus(*row) for row in zip(an, ap, aq)]
        body_spin = [sum((r[k][j]*spin[k] for k in range(3)), ZERO) for j in range(3)]
        omega = [sum((r[k][j]*body_spin[j]/inertia[j] for j in range(3)), ZERO) for k in range(3)]
        dr = [[cross(omega, [r[k][j] for k in range(3)])[i] for j in range(3)] for i in range(3)]
        tau = [ZERO]*3
        for j in range(n):
            if j == a:
                continue
            d = [y-z for y, z in zip(x[j], x[a])]; distance = norm(d); normal = [t/distance for t in d]
            qn = [dot(row, normal) for row in q]
            tau = plus(tau, [m[a]*m[j]*t/distance**3 for t in cross(normal, qn)])
        expected_parts = [pack(x, v, response(x, v, m, b, ONE, c)) for b in (ap, aq)]
        expected = plus(*expected_parts)
        scale = [abs(quantities(x, v, m, inertia, a, radius, c, r, spin)[0]),
            sum((mass*norm(w) for mass, w in zip(m, v)), ZERO),
            norm(quantities(x, v, m, inertia, a, radius, c, r, spin)[4:])]
        if not all(s > 0 for s in scale):
            raise ValueError('Strictly positive E/P/J scales required')
        scales = [scale[0], *([scale[1]]*3), *([scale[2]]*3)]
        levels = []
        for htext in ('1e-6', '1e-9', '1e-12'):
            h = Decimal(htext); totals = []
            for sign in (-1, 1):
                shift = lambda rows, rates: [[y+sign*h*z for y, z in zip(row, rate)] for row, rate in zip(rows, rates)]
                totals.append(quantities(shift(x, v), shift(v, total_a), m, inertia, a, radius, c,
                    shift(r, dr), [s+sign*h*t for s, t in zip(spin, tau)]))
            rate = [(b-a)/(2*h) for a, b in zip(*totals)]
            blocks = {}
            for k, (name, block) in enumerate((('energy', slice(0, 1)), ('momentum', slice(1, 4)), ('angular', slice(4, 7)))):
                error = norm([y-z for y, z in zip(rate[block], expected[block])]); signal = norm(expected[block])
                blocks[name] = dict(scaled=float(error/scale[k]), relative_active=float(error/signal) if signal else None,
                    checks_passed=bool(error/scale[k] < Decimal('1e-10') and (not signal or error/signal < Decimal('1e-7'))))
            levels.append(dict(h_model_time=htext, rates=list(map(str, rate)), blocks=blocks))
        refine = max(abs(Decimal(a)-Decimal(b))/s for a, b, s in zip(levels[-1]['rates'], levels[-2]['rates'], scales))
        bad_angular = [Decimal(z)-t for z, t in zip(levels[-1]['rates'][4:], tau)]
        control = norm([y-z for y, z in zip(bad_angular, expected[4:])])/norm(tau) if norm(tau) else ZERO
        return dict(precision=precision, levels=levels, scales=list(map(str, scales)),
            expected_sources=[list(map(str, row)) for row in expected_parts],
            derivative_refinement_scaled=float(refine), missing_spin_torque_relative=float(control),
            checks_passed=bool(all(b['checks_passed'] for b in levels[-1]['blocks'].values()) and refine < Decimal('1e-10')))


def precision_agreement(low, high):
    with localcontext() as context:
        context.prec = 100
        value = max(abs(Decimal(a)-Decimal(b))/Decimal(s) for a, b, s in zip(
            low['levels'][-1]['rates'], high['levels'][-1]['rates'], high['scales']))
        return dict(maximum_scaled=float(value), checks_passed=bool(value < Decimal('1e-30')))
