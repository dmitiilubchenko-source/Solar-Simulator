"""Scalar point force, body inertia and raw R/Pi reference; no quaternion RHS."""
from time import perf_counter
import numpy as np
from scipy.integrate import RK45, solve_ivp

from scripts.assess_relativity import independent_acceleration
from scripts.fixed_j2_ias import figure_force
from scripts.independent_hybrid_rotation import body_field, momentum1, hat, pack
from scripts.free_lunar_rotation import geometry, unpack, tolerances
from solar_simulator.rotation import rotation_matrix


def initial(y, model):
    n = len(model.masses_si); _,_,_,q,s = unpack(y,model)
    r = rotation_matrix(q)
    return np.r_[y[:6*n],r.ravel(),r.T@s,np.zeros(21)]


def rhs(t, y, model, scales):
    n = len(model.masses_si)
    if y.shape != (6*n+33,) or not np.isfinite(y).all():
        raise ValueError('Finite reference matrix/body-spin state required')
    encoded = y[:3*n].reshape(n,3); velocity = y[3*n:6*n].reshape(n,3)
    x,v = model.pair.decode(encoded),model.pair.decode(velocity)
    rho = encoded[model.pair.second]; centered = geometry(x,v,rho,model)
    r,pi = y[6*n:6*n+9].reshape(3,3),y[6*n+9:6*n+12]
    # Extract the coefficient of c^-2 with the formal parameter c=1;
    # do not subtract the tiny real-c correction from the full acceleration.
    delta = x[None]-x[:,None]; delta[model.pair.first,model.pair.second] = rho
    delta[model.pair.second,model.pair.first] = -rho
    d = np.linalg.norm(delta,axis=2); np.fill_diagonal(d,np.inf)
    an = np.sum(delta*(model.masses[None]/d**3)[:,:,None],axis=1)
    ap = (independent_acceleration(x,v,model.masses,1.,(model.pair.first,model.pair.second,rho))-an)/model.c**2
    point = an+ap
    force,torque,_ = body_field(centered,model.masses,r,model.moments,model.source,
        model.figure.bounding_radius/model.units.length_m)
    aq = force/model.masses[:,None]
    af = figure_force(centered,model.masses,model.fixed,g=1.)
    omega_body = pi*model.spin_scale/model.moments
    step = 1e-20
    budget = np.array([pack(x,v,momentum1(centered,v+1j*step*b,model.masses,model.c).imag/step)
        for b in (ap,aq+af)])
    fixed_torque = np.r_[np.zeros(4),np.cross(x,model.masses[:,None]*af).sum(axis=0)]
    return np.r_[velocity.ravel(),model.pair.encode(point+aq+af).ravel(),(r@hat(omega_body)).ravel(),
        np.cross(pi,omega_body)+torque/model.spin_scale,(np.vstack((budget,fixed_torque))/scales).ravel()]


class BlockRK45(RK45):
    def _estimate_error_norm(self, K, h, scale):
        error = self._estimate_error(K,h)/scale
        return max(float(np.linalg.norm(error[b])/np.sqrt(b.stop-b.start)) for b in self.blocks)

    def __init__(self, fun, t0, y0, t_bound, *, body_count, **kwargs):
        n = body_count
        if np.size(y0) != 6*n+33:
            raise ValueError('Wrong reference state size')
        self.blocks = [slice(k,k+3) for k in range(0,6*n,3)]+[slice(6*n,6*n+9),slice(6*n+9,6*n+12)]
        for k in range(6*n+12,6*n+33,7):
            self.blocks += [slice(k,k+1),slice(k+1,k+4),slice(k+4,k+7)]
        super().__init__(fun,t0,y0,t_bound,**kwargs)


def integrate(model, y0, times, scales, tight=False):
    times = np.asarray(times,dtype=float)
    if times.ndim != 1 or len(times) < 2 or times[0] != 0 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError('Strict increasing reference seconds from zero required')
    rtol,step,atol = tolerances(model,tight,matrix=True)
    start = perf_counter(); initial_state = initial(y0,model)
    result = solve_ivp(lambda t,y:rhs(t,y,model,scales),(0.,times[-1]/model.units.time_s),initial_state,
        t_eval=times/model.units.time_s,method=BlockRK45,body_count=len(model.masses_si),
        rtol=rtol,atol=atol,max_step=step/(2*model.units.time_s))
    if not result.success or result.y.shape != (len(initial_state),len(times)) or not np.isfinite(result.y).all():
        raise RuntimeError('Incomplete independent free integration: '+result.message)
    return result.y.T,dict(rhs_calls=result.nfev,wall_seconds=perf_counter()-start,
        rtol=rtol,max_step_seconds=step/2,method='RK45 worst block; raw matrix/body Euler',active_moon_q=True)
