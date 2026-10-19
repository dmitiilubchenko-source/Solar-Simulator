"""Decimal total readout and per-body/pair comparisons, separate from RHS."""
from decimal import Decimal, localcontext
import numpy as np

from scripts.noether_identities import dec, parts, plus, dot, norm
from scripts.decimal_hybrid_rotation import matrix as quaternion_matrix, tensor
from scripts.free_lunar_rotation import unpack
from solar_simulator.rotation import rotation_matrix


def readout(y, model, reference=False, active=True, precision=70):
    if precision not in (70,90):
        raise ValueError('Declared readout precision is 70 or 90')
    with localcontext() as context:
        context.prec = precision
        n = len(model.masses_si); a,b = model.pair.first,model.pair.second
        def decode(values):
            rows = [list(map(dec,row)) for row in values.reshape(n,3)]
            center,rho = rows[a][:],rows[b][:]
            rows[a] = [x-dec(model.pair.second_fraction)*r for x,r in zip(center,rho)]
            rows[b] = [x+dec(model.pair.first_fraction)*r for x,r in zip(center,rho)]
            return rows
        x,v = decode(y[:3*n]),decode(y[3*n:6*n]); m = list(map(dec,model.masses))
        inertia = list(map(dec,model.moments))
        if reference:
            r = [list(map(dec,row)) for row in y[6*n:6*n+9].reshape(3,3)]
            body = [dec(s)*dec(model.spin_scale) for s in y[6*n+9:6*n+12]]
            spin = [dot(row,body) for row in r]
        else:
            r = quaternion_matrix(list(map(dec,y[6*n:6*n+4])))
            spin = [dec(s)*dec(model.spin_scale) for s in y[6*n+4:6*n+7]]
            body = [sum((r[k][j]*spin[k] for k in range(3)),Decimal(0)) for j in range(3)]
        figures = [(i,dec(radius),[list(map(dec,row)) for row in q]) for i,radius,q in model.fixed]
        if active:
            figures.append((model.source,dec(model.figure.bounding_radius/model.units.length_m),tensor(r,inertia,m[model.source])))
        values = parts(x,v,m,figures,Decimal(1),dec(model.c))
        result = plus(values['newton'],values['pn'],values['figure'])
        result[0] += sum((s*s/i for s,i in zip(body,inertia)),Decimal(0))/2
        result[4:] = plus(result[4:],spin)
        return result


def scales(y, model):
    row = readout(y,model)
    _,v,_,_,_ = unpack(y,model)
    momentum = float(np.sum(model.masses*np.linalg.norm(v,axis=1)))
    energy,angular = float(abs(row[0])),float(norm(row[4:]))
    result = np.r_[energy,np.full(3,momentum),np.full(3,angular)]
    if not np.isfinite(result).all() or np.any(result <= 0):
        raise ValueError('Strict positive physical readout scales required')
    return result


def norms(values):
    return dict(energy=float(abs(values[:,0]).max()),momentum=float(np.linalg.norm(values[:,1:4],axis=1).max()),
        angular=float(np.linalg.norm(values[:,4:],axis=1).max()))


def balances(values, model, scale, reference=False, active=True):
    n = len(model.masses_si)
    rows = [readout(y,model,reference,active) for y in values]
    # Subtract in Decimal before casting; never subtract rounded global totals.
    with localcontext() as context:
        context.prec = 90
        delta = np.array([[float(a-b) for a,b in zip(row,rows[0])] for row in rows])/scale
    offset = 6*n+(12 if reference else 7)
    budget = values[:,offset:].reshape(-1,3,7)
    precision_rows = []
    for index in np.linspace(0,len(values)-1,9,dtype=int):
        high = readout(values[index],model,reference,active,90)
        with localcontext() as context:
            context.prec = 100
            error = max(float(abs(a-b)/dec(s)) for a,b,s in zip(rows[index],high,scale))
        precision_rows.append(dict(index=int(index),maximum_scaled=error,checks_passed=error < 1e-30))
    corrected = norms(delta-budget.sum(axis=1))
    return dict(raw=norms(delta),corrected=corrected,
        source_integrals={name:norms(budget[:,i]) for i,name in enumerate(('pn2','pn_q','fixed_axes_torque'))},
        precision_rows=precision_rows,source_visibility_qualified=False,
        checks_passed=all(x < 1e-11 for x in corrected.values()) and all(x['checks_passed'] for x in precision_rows))


def decoded(values, model, reference=False):
    n = len(model.masses_si); unit = model.units
    states = []
    for y in values:
        x = model.pair.decode(y[:3*n].reshape(n,3))*unit.length_m
        v = model.pair.decode(y[3*n:6*n].reshape(n,3))*unit.velocity_m_s
        states.append(np.c_[x,v])
    if reference:
        r = values[:,6*n:6*n+9].reshape(-1,3,3)
        spin = np.einsum('tij,tj->ti',r,values[:,6*n+9:6*n+12])
    else:
        r = np.array([rotation_matrix(q) for q in values[:,6*n:6*n+4]])
        spin = values[:,6*n+4:6*n+7]
    return np.array(states),r,spin


def comparison(first, second, model, first_reference=False, second_reference=False):
    n = len(model.masses_si); a,ra,sa = decoded(first,model,first_reference); b,rb,sb = decoded(second,model,second_reference)
    if a.shape != b.shape or first.shape[0] != second.shape[0]:
        raise ValueError('Matching complete trajectories required')
    difference = a-b; per_body = np.linalg.norm(difference[:,:,:3],axis=2).max(axis=0)
    offset = 3*model.pair.second
    pair = np.linalg.norm(first[:,offset:offset+3]-second[:,offset:offset+3],axis=1)*model.units.length_m
    pair_v = np.linalg.norm(first[:,3*n+offset:3*n+offset+3]-second[:,3*n+offset:3*n+offset+3],axis=1)*model.units.velocity_m_s
    return dict(per_body_metres=per_body.tolist(),all_body_metres=float(per_body.max()),pair_metres=float(pair.max()),
        velocity_m_s=float(max(np.linalg.norm(difference[:,:,3:],axis=2).max(),pair_v.max())),
        attitude_frobenius=float(np.linalg.norm(ra-rb,axis=(1,2)).max()),
        spin_relative_initial=float(np.linalg.norm(sa-sb,axis=1).max()))


def within(row, limits):
    keys = ('all_body_metres','pair_metres','velocity_m_s','attitude_frobenius','spin_relative_initial')
    return all(key in row and np.isfinite(row[key]) and 0 <= row[key] < limit for key,limit in zip(keys,limits))
