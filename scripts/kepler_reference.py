"""Independent Decimal elliptic f/g oracle, deliberately outside runtime.

See docs/kepler-phase-protocol.md for derivation, sources and bounded scope.
No production force, coordinates, integrator or nominal orbital elements are
used here. Inputs are Decimal, so callers control exact binary-float decoding.
"""
from decimal import Decimal, localcontext


def _sincos(angle, precision):
    """Taylor sums with guard digits; caller restricts |angle| below 40 rad."""
    sine, cosine = angle, Decimal(1)
    st, ct = sine, cosine
    threshold = Decimal(10) ** (-precision - 5)
    square = -angle * angle
    for k in range(1, 400):
        st *= square / ((2*k)*(2*k+1))
        ct *= square / ((2*k-1)*(2*k))
        sine += st
        cosine += ct
        if max(abs(st), abs(ct)) < threshold:
            return sine, cosine
    raise ArithmeticError("Decimal trigonometric series did not converge")


def propagate(position, velocity, mu, elapsed, *, precision=70):
    """Return Decimal (r,v) for a nonradial ellipse, |n*elapsed| <= 32 rad.

    This bounded verification oracle is not a general production propagator.
    Seventy digits and one hundred digits are compared before using its output.
    """
    if type(precision) is not int or not 40 <= precision <= 150:
        raise ValueError("Oracle precision must be 40..150 decimal digits")
    p, v = tuple(position), tuple(velocity)
    values = (*p, *v, mu, elapsed)
    if (len(p) != 3 or len(v) != 3 or
            any(not isinstance(x, Decimal) or not x.is_finite() for x in values)):
        raise ValueError("Oracle requires finite Decimal vectors, mu and elapsed")
    if mu <= 0:
        raise ValueError("Oracle requires positive mu")
    with localcontext() as context:
        context.prec = precision + 20
        radius = sum(x*x for x in p).sqrt()
        angular = tuple(p[(i+1)%3]*v[(i+2)%3]-p[(i+2)%3]*v[(i+1)%3]
                        for i in range(3))
        if radius == 0 or not any(angular):
            raise ValueError("Oracle requires nonzero radius and angular momentum")
        alpha = 2/radius - sum(x*x for x in v)/mu
        if alpha <= 0:
            raise ValueError("Oracle supports bound ellipses only")
        semi = 1/alpha
        rate = (mu/semi**3).sqrt()
        mean = rate*elapsed
        if abs(mean) > 32:
            raise ValueError("Oracle supports |n*elapsed| <= 32 rad")
        if elapsed == 0:
            return p, v
        radial = sum(x*y for x, y in zip(p, v))/(mu*semi).sqrt()
        cosine0 = 1-radius/semi
        # u-q*sin(u)+s*(1-cos(u))=n*dt, derivative r(u)/a > 0.
        width = abs(cosine0)+2*abs(radial)+1
        lower, upper = mean-width, mean+width
        if max(abs(lower), abs(upper)) >= 40:
            raise ValueError("Oracle anomaly bracket exceeds trigonometric scope")
        tolerance = Decimal(10)**(-precision)
        for _ in range(4*precision+30):
            anomaly = (lower+upper)/2
            sine, cosine = _sincos(anomaly, precision)
            residual = anomaly-cosine0*sine+radial*(1-cosine)-mean
            if residual < 0:
                lower = anomaly
            else:
                upper = anomaly
            if upper-lower < tolerance:
                break
        else:
            raise ArithmeticError("Decimal Kepler root did not converge")
        sine, cosine = _sincos((lower+upper)/2, precision)
        f = 1-semi/radius*(1-cosine)
        # Algebraically equivalent to dt+(sin(u)-u)/n; avoids cancellation
        # between the elapsed time and completed orbital revolutions.
        g = (semi*radial*(1-cosine)+radius*sine)/(mu/semi).sqrt()
        result_p = tuple(f*x+g*y for x, y in zip(p, v))
        result_radius = sum(x*x for x in result_p).sqrt()
        df = -(mu*semi).sqrt()*sine/(radius*result_radius)
        dg = 1-semi/result_radius*(1-cosine)
        result_v = tuple(df*x+dg*y for x, y in zip(p, v))
        return result_p, result_v
