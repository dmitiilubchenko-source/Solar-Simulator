"""Independent block and scalar H1 responses for exact float64 SI inputs.

Diagnostic arithmetic only: cancellation of internal Earth/Moon forces in a
distant body's tiny response cannot be audited reliably with two float sums.
"""
from decimal import Decimal, localcontext

import numpy as np

from scripts.noether_identities import dec, dot, norm, response


def converted(x, v, masses, components):
    convert = lambda a:[[dec(z) for z in row] for row in a]
    return convert(x), convert(v), list(map(dec, masses)), {k:convert(b) for k,b in components.items()}


def block_responses(x, v, masses, components, g, c, precision):
    if type(precision) is not int or precision not in (50, 70):
        raise ValueError('Declared block precision is 50 or 70')
    with localcontext() as context:
        context.prec = precision
        x, v, m, b = converted(x, v, masses, components)
        g, c = dec(g), dec(c); zero = Decimal(0); count = len(m)
        h = [[zero]*(3*count) for _ in range(3*count)]
        for i in range(count):
            speed = dot(v[i], v[i])
            for a in range(3):
                for d in range(3):
                    h[3*i+a][3*i+d] += m[i]*(v[i][a]*v[i][d]+(speed/2 if a == d else zero))
            for j in range(i+1, count):
                r = [a-z for a,z in zip(x[i], x[j])]; distance = norm(r)
                if not distance:
                    raise ValueError('Distinct block response positions required')
                n = [a/distance for a in r]; factor = g*m[i]*m[j]/(2*distance)
                for a in range(3):
                    h[3*i+a][3*i+a] += 6*factor
                    h[3*j+a][3*j+a] += 6*factor
                    for d in range(3):
                        value = -factor*(n[a]*n[d]+(7 if a == d else zero))
                        h[3*i+a][3*j+d] = value
                        h[3*j+d][3*i+a] = value
        result = {}
        for name, field in b.items():
            flat = [z for row in field for z in row]
            result[name] = [[dot(h[3*i+a], flat)/(m[i]*c*c) for a in range(3)] for i in range(count)]
        return result


def scalar_responses(x, v, masses, components, g, c):
    with localcontext() as context:
        context.prec = 70
        x, v, m, b = converted(x, v, masses, components)
        return {name:np.array([[float(z/mass) for z in row] for row,mass in zip(
            response(x, v, m, field, dec(g), dec(c)), m)]) for name,field in b.items()}


def agreement(low, high):
    with localcontext() as context:
        context.prec = 90
        maximum = Decimal(0)
        for name in high:
            for a,b in zip(low[name], high[name]):
                error = norm([x-y for x,y in zip(a,b)]); scale = norm(b)
                if not scale:
                    if error:
                        raise ValueError('Nonzero arithmetic defect against exact zero')
                else:
                    maximum = max(maximum, error/scale)
        return float(maximum)
