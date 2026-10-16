"""Independent conditioned EIH reference for the pinned ten-body year."""
from dataclasses import replace

import numpy as np
from scipy.integrate import solve_ivp

from scripts.newton_year import inputs as newton_inputs,encode,decode,YEAR
from scripts.ias15_eih import validate
from scripts.assess_sandbox_planets import states
from solar_simulator.experiment import create_experiment,copy_bodies
from solar_simulator.relativity import C
from solar_simulator.simulation import AU,G


def inputs():
    original,times = newton_inputs()
    seed = create_experiment(copy_bodies(original.bodies),
        replace(original.settings,physics='eih-1pn',figures=()),origin=original.origin)
    np.testing.assert_array_equal(states(seed.bodies),states(original.bodies))
    validate(seed,times)
    return seed,times


def force_terms(p,v,mu,c,relative_pair=None):
    """Scalar source->target EIH equation evaluated as a full interaction matrix.

    Return Newton and c^-2 correction separately so tests cannot hide a wrong
    small correction behind the much larger Newtonian term.
    """
    d = p[None,:,:]-p[:,None,:]
    if relative_pair is not None:
        first,second,rho = relative_pair
        d[first,second],d[second,first] = rho,-rho
    radius = np.linalg.norm(d,axis=2)
    np.fill_diagonal(radius,np.inf)
    if np.any(radius==0):
        raise ValueError('Coincident reference point masses')
    with np.errstate(over='raise',divide='raise',invalid='raise'):
        inv = 1/radius
        n = d*inv[:,:,None]
        potential = np.sum(mu[None,:]*inv,axis=1)
        speed2 = np.sum(v*v,axis=1)
        if max(potential.max(),speed2.max())/(c*c)>=1e-4:
            raise ValueError('Reference outside weak-field domain')
        newton = np.sum(d*(mu[None,:]*inv**3)[:,:,None],axis=1)
        source_projection = np.sum(n*v[None,:,:],axis=2)
        bracket = (speed2[:,None]+2*speed2[None,:]-4*(v@v.T)-1.5*source_projection**2
            -4*potential[:,None]-potential[None,:]+.5*np.sum(d*newton[None,:,:],axis=2))
        dv = v[:,None,:]-v[None,:,:]
        velocity_projection = np.sum(n*(4*v[:,None,:]-3*v[None,:,:]),axis=2)
        pair_terms = (mu[None,:]*inv**2)[:,:,None]*(n*bracket[:,:,None]
            -velocity_projection[:,:,None]*dv)
        pair_terms += 3.5*(mu[None,:]*inv)[:,:,None]*newton[None,:,:]
        correction = np.sum(pair_terms,axis=1)/(c*c)
    return newton,correction


def reference(seed,times,rtol,maximum_step,clock=YEAR):
    times = validate(seed,times)
    names = [b.name for b in seed.bodies]
    pair = names.index('Earth'),names.index('Moon')
    e,m = pair
    masses = np.array([b.mass for b in seed.bodies])
    fraction = masses[m]/(masses[e]+masses[m])
    q = encode(states(seed.bodies),masses,pair,clock)
    mu = G*masses*clock**2/AU**3
    def rhs(t,y):
        state = y.reshape(len(masses),6)
        absolute = state.copy()
        absolute[e] = state[e]-fraction*state[m]
        absolute[m] = state[e]+(1-fraction)*state[m]
        newton,correction = force_terms(absolute[:,:3],absolute[:,3:],mu,C*clock/AU,
            (e,m,state[m,:3]))
        a = newton+correction
        relative = a[m]-a[e]
        a[e] += fraction*relative
        a[m] = relative
        return np.c_[state[:,3:],a].ravel()
    atol = np.tile([1e-17]*3+[1e-17*clock/YEAR]*3,len(masses))
    result = solve_ivp(rhs,(0,times[-1]/clock),q.ravel(),method='RK45',t_eval=times/clock,
        rtol=rtol,atol=atol,max_step=maximum_step/clock)
    if not result.success or result.t[-1]!=times[-1]/clock:
        raise RuntimeError(result.message)
    values = decode(result.y.T.reshape(len(times),len(masses),6),masses,pair,clock)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite independent EIH reference')
    return values,dict(rtol=rtol,max_step_seconds=maximum_step,clock_seconds=clock,
        rhs_calls=result.nfev,interpolation='RK45 quartic at t_eval',
        force='independent source-to-target matrix EIH',coordinates='AU/clock interleaved EMB+rho')
