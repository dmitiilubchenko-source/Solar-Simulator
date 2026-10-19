"""Independent analytic EIH Noether readout for exact stored float64 inputs.

This is diagnostic arithmetic, never an integrator or a replacement force.
The momentum is the analytic velocity derivative of Vines' scalar EIH action.
Figure tensors are the already constructed float64 coefficients, not refitted.
"""
from decimal import Decimal, localcontext

import numpy as np

from solar_simulator.relativity import C
from solar_simulator.simulation import G


def exact(value):
    return Decimal.from_float(float(value))


def quantities(state, masses, figures=(), *, precision=70, g=G, c=C):
    q = np.asarray(state, dtype=float)
    m = np.asarray(masses, dtype=float)
    if (type(precision) is not int or precision < 40 or q.shape != (len(m), 6)
            or not len(m) or not np.isfinite(q).all() or not np.isfinite(m).all()
            or not (m > 0).all() or not np.isfinite(g) or g < 0 or not np.isfinite(c) or c <= 0):
        raise ValueError('Invalid Decimal Noether inputs or precision')
    with localcontext() as context:
        context.prec = precision
        zero = Decimal(0)
        p = [[exact(x) for x in row[:3]] for row in q]
        v = [[exact(x) for x in row[3:]] for row in q]
        mass = list(map(exact, m))
        grav, light2 = exact(g), exact(c)**2
        dot = lambda a,b: sum((x*y for x,y in zip(a,b)), zero)
        speed2 = [dot(w,w) for w in v]
        canonical = [[mass[i]*x*(1+speed2[i]/(2*light2)) for x in v[i]] for i in range(len(m))]
        energy = sum((mass[i]*(speed2[i]/2+3*speed2[i]**2/(8*light2)) for i in range(len(m))), zero)
        potentials = [zero for _ in m]
        for i in range(len(m)):
            for j in range(i+1, len(m)):
                r = [a-b for a,b in zip(p[i],p[j])]
                radius = dot(r,r).sqrt()
                if not radius:
                    raise ValueError('Coincident Decimal Noether point masses')
                n = [x/radius for x in r]
                ni,nj = dot(n,v[i]),dot(n,v[j])
                factor = grav*mass[i]*mass[j]/radius
                potentials[i] += grav*mass[j]/radius
                potentials[j] += grav*mass[i]/radius
                pair_velocity = (3*(speed2[i]+speed2[j])-7*dot(v[i],v[j])-ni*nj)/2
                energy += -factor+factor*pair_velocity/light2
                for k in range(3):
                    canonical[i][k] += factor*(6*v[i][k]-7*v[j][k]-n[k]*nj)/(2*light2)
                    canonical[j][k] += factor*(6*v[j][k]-7*v[i][k]-n[k]*ni)/(2*light2)
        energy += sum((mass[i]*potentials[i]**2/(2*light2) for i in range(len(m))),zero)
        for source, radius_value, tensor in figures:
            tensor = np.asarray(tensor, dtype=float)
            if not 0 <= source < len(m) or tensor.shape != (3,3) or not np.isfinite(tensor).all():
                raise ValueError('Invalid fixed tensor')
            tensor_d = [[exact(x) for x in row] for row in tensor]
            for j in range(len(m)):
                if j == source:
                    continue
                r = [a-b for a,b in zip(p[j],p[source])]
                radius = dot(r,r).sqrt()
                if radius <= exact(radius_value):
                    raise ValueError('Inside Decimal figure radius')
                qr = [dot(row,r) for row in tensor_d]
                energy += grav*mass[source]*mass[j]*dot(r,qr)/(2*radius**5)
        momentum = [sum((row[k] for row in canonical),zero) for k in range(3)]
        angular = [sum((p[i][(k+1)%3]*canonical[i][(k+2)%3]
            -p[i][(k+2)%3]*canonical[i][(k+1)%3] for i in range(len(m))),zero) for k in range(3)]
        return tuple([energy,*momentum,*angular])


def compare_readouts(values, budgets, masses, figures, scale, float_rows):
    """Subtract large Decimal totals before float conversion, keeping state bits."""
    if budgets.shape != (len(values),3,7) or not np.isfinite(budgets).all():
        raise ValueError('Invalid Decimal readout budgets')
    scale = np.asarray(scale, dtype=float)
    float_rows = np.asarray(float_rows, dtype=float)
    if scale.shape != (7,) or not np.isfinite(scale).all() or not (scale > 0).all() or float_rows.shape != (len(values),7):
        raise ValueError('Invalid Decimal readout scales or float rows')
    high = [quantities(q,masses,figures,precision=70) for q in values]
    low = [quantities(q,masses,figures,precision=50) for q in values]
    with localcontext() as context:
        context.prec = 80
        resolution = np.array([[float((h-l)/exact(s)) for h,l,s in zip(hr,lr,scale)] for hr,lr in zip(high,low)])
        arithmetic = np.array([[float((exact(f)-h)/exact(s)) for f,h,s in zip(fr,hr,scale)] for fr,hr in zip(float_rows,high)])
        delta = np.array([[float((hr[k]-high[0][k])/exact(scale[k])) for k in range(7)] for hr in high])
        residual = np.array([[float((hr[k]-high[0][k]-sum((exact(x) for x in budgets[i,:,k]),Decimal(0)))
            /exact(scale[k])) for k in range(7)] for i,hr in enumerate(high)])
        float_delta = np.array([[float((exact(fr[k])-exact(float_rows[0,k]))/exact(scale[k]))
            for k in range(7)] for fr in float_rows])
    def norms(x):
        return dict(energy=float(abs(x[:,0]).max()),momentum=float(np.linalg.norm(x[:,1:4],axis=1).max()),
            angular=float(np.linalg.norm(x[:,4:],axis=1).max()))
    return dict(precision_50_to_70_maximum_scaled_component=float(abs(resolution).max()),
        precision_checks_passed=bool(abs(resolution).max() < 1e-40),
        float_total_readout_difference=norms(arithmetic),float_delta_arithmetic_difference=norms(float_delta-delta),
        decimal_raw=norms(delta),decimal_corrected=norms(residual),
        trajectories_reintegrated=False,full_source_observability_qualified=False),dict(decimal_delta=delta,decimal_residual=residual)
