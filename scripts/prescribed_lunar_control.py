"""Externally prescribed Moon attitude: an orbit diagnostic, never a forecast."""
from time import perf_counter
import numpy as np
from scipy.integrate import DOP853, RK45, solve_ivp
from scipy.spatial.transform import Rotation

from scripts import free_lunar_rotation as production
from scripts import independent_free_lunar as reference
from scripts import free_lunar_diagnostics as diagnostic
from scripts.independent_hybrid_rotation import body_field
from solar_simulator.orientation import lunar_rotation
from solar_simulator.nbody_rotation import correction


def attitude(seconds):
    r,rate = lunar_rotation(float(seconds))
    hat = rate@r.T
    omega = .5*np.array([hat[2,1]-hat[1,2],hat[0,2]-hat[2,0],hat[1,0]-hat[0,1]])
    q = np.roll(Rotation.from_matrix(r).as_quat(),1)
    return r,q,omega


def external_source(omega, torque):
    """Normalized orbital E/P/J source: potential time derivative and reaction."""
    omega,torque = np.asarray(omega),np.asarray(torque)
    if omega.shape != (3,) or torque.shape != (3,) or not np.isfinite([omega,torque]).all():
        raise ValueError('Finite spatial omega and torque required')
    return np.r_[-omega@torque,np.zeros(3),-torque]


def embed(y, model, r, q, is_reference=False):
    """Zero spin is a readout adapter; no spin is integrated in this experiment."""
    n = len(model.masses_si)
    return np.r_[y[:6*n],r.ravel() if is_reference else q,np.zeros(3),y[6*n:]]


def expanded(values, model, times, is_reference=False):
    return np.array([embed(y,model,*attitude(t)[:2],is_reference) for y,t in zip(values,times,strict=True)])


def initial():
    model,free,seed = production.initial();n=len(model.masses_si)
    y = np.r_[free[:6*n],np.zeros(21)]
    r,q,_ = attitude(0.)
    scale = diagnostic.scales(embed(y,model,r,q),model)
    return model,y,scale,seed


def rhs(t, y, model, scale, is_reference=False):
    n = len(model.masses_si)
    if y.shape != (6*n+21,) or not np.isfinite(y).all():raise ValueError('Finite orbit and three source budgets required')
    r,q,omega = attitude(t*model.units.time_s)
    state = embed(y,model,r,q,is_reference)
    if is_reference:
        derivative = reference.rhs(t,state,model,scale)
        torque = r@(derivative[6*n+9:6*n+12]*model.spin_scale)
    else:
        derivative = production.rhs(t,state,model,scale)
        torque = derivative[6*n+4:6*n+7]*model.spin_scale
    result = np.r_[derivative[:6*n],derivative[-21:]]
    result[-7:] += external_source(omega*model.units.time_s,torque)/scale
    return result


def blocks(body_count):
    n=body_count
    result=[slice(k,k+3) for k in range(0,6*n,3)]
    for k in range(6*n,6*n+21,7):result += [slice(k,k+1),slice(k+1,k+4),slice(k+4,k+7)]
    return result


class OrbitalDOP853(DOP853):
    def __init__(self, fun, t0, y0, t_bound, *, body_count, **kwargs):
        if np.size(y0) != 6*body_count+21:raise ValueError('Wrong controlled orbit state size')
        self.blocks=blocks(body_count)
        super().__init__(fun,t0,y0,t_bound,**kwargs)
    _estimate_error_norm=production.FreeDOP853._estimate_error_norm


class OrbitalRK45(RK45):
    def __init__(self, fun, t0, y0, t_bound, *, body_count, **kwargs):
        if np.size(y0) != 6*body_count+21:raise ValueError('Wrong controlled orbit state size')
        self.blocks=blocks(body_count)
        super().__init__(fun,t0,y0,t_bound,**kwargs)
    _estimate_error_norm=reference.BlockRK45._estimate_error_norm


def integrate(model, y0, times, scale, tight=False, is_reference=False):
    times=np.asarray(times,dtype=float);n=len(model.masses_si)
    if times.ndim != 1 or len(times)<2 or times[0] != 0 or not np.isfinite(times).all() or np.any(np.diff(times)<=0):
        raise ValueError('Strict increasing finite seconds from zero required')
    rtol,step,atol=production.tolerances(model,tight)
    atol=np.r_[atol[:6*n],atol[-21:]];step=step/(2 if is_reference else 1)
    start=perf_counter()
    solution=solve_ivp(lambda t,y:rhs(t,y,model,scale,is_reference),(0.,times[-1]/model.units.time_s),
        y0,t_eval=times/model.units.time_s,method=OrbitalRK45 if is_reference else OrbitalDOP853,
        body_count=n,rtol=rtol,atol=atol,max_step=step/model.units.time_s)
    if not solution.success or solution.y.shape != (6*n+21,len(times)) or not np.isfinite(solution.y).all():
        raise RuntimeError('Incomplete prescribed-attitude orbit: '+solution.message)
    return solution.y.T,dict(rhs_calls=solution.nfev,wall_seconds=perf_counter()-start,rtol=rtol,
        max_step_seconds=step,method='RK45 scalar/rawR' if is_reference else 'DOP853 tensor/quaternion',
        prescribed_attitude=True,free_forecast=False)


def balances(values, model, times, scale, is_reference=False):
    row=diagnostic.balances(expanded(values,model,times,is_reference),model,scale,is_reference)
    row['source_integrals']['external_prescription']=row['source_integrals'].pop('fixed_axes_torque')
    row['rotational_energy_included']=False;row['closed_system']=False
    return row


def probes(values, model, times):
    rows=[];n=len(model.masses_si);unit=model.units
    for i in np.linspace(0,len(times)-1,9,dtype=int):
        r,q,omega=attitude(times[i]);state=embed(values[i],model,r,q)
        x,v,rho,_,_=production.unpack(state,model);centered=production.geometry(x,v,rho,model)
        f,tau_body,u=body_field(centered,model.masses,r,model.moments,model.source,model.figure.bounding_radius/unit.length_m)
        tau=r@tau_body
        a,si_tau,si_u=correction(centered*unit.length_m,np.asarray(model.masses_si),model.source,model.figure,q)
        actual=a*(unit.time_s**2/unit.length_m)*model.masses[:,None]
        torque=si_tau/(unit.mass_kg*unit.velocity_m_s**2)
        potential=si_u/(unit.mass_kg*unit.velocity_m_s**2)
        def gap(a,b):return float(np.linalg.norm(np.asarray(a)-b)/np.linalg.norm(b))
        force_scale=np.linalg.norm(actual,axis=1).sum()
        orbital=np.cross(centered,actual)
        torque_scale=np.linalg.norm(orbital,axis=1).sum()+np.linalg.norm(torque)
        gradients=[]
        for h in (1e-4,5e-5):
            gradient=[]
            for axis in np.eye(3):
                def energy(sign):
                    matrix=Rotation.from_rotvec(sign*h*axis).as_matrix()@r
                    return body_field(centered,model.masses,matrix,model.moments,model.source,model.figure.bounding_radius/unit.length_m)[2]
                gradient.append((energy(1)-energy(-1))/(2*h))
            gradient=np.array(gradient)
            gradients.append(dict(step_rad=h,torque_relative=gap(-gradient,tau),
                power_relative=float(abs(gradient@omega+torque@omega)/(np.linalg.norm(torque)*np.linalg.norm(omega)))))
        power_scale=np.linalg.norm(omega)*np.linalg.norm(torque)
        missing_work=float(abs(gradient@omega)/power_scale)
        wrong_work=float(abs(gradient@omega-omega@torque)/power_scale)
        row=dict(index=int(i),seconds=float(times[i]),force_relative=gap(actual,f),torque_relative=gap(torque,tau),
            potential_relative=gap(potential,u),linear_relative=float(np.linalg.norm(actual.sum(axis=0))/force_scale),
            angular_relative=float(np.linalg.norm(orbital.sum(axis=0)+torque)/torque_scale),gradients=gradients,
            missing_work_signal=missing_work,wrong_work_sign_signal=wrong_work,
            missing_torque_signal=float(np.linalg.norm(orbital.sum(axis=0))/np.linalg.norm(torque)),
            wrong_torque_sign_signal=float(np.linalg.norm(orbital.sum(axis=0)-torque)/np.linalg.norm(torque)))
        row['checks_passed']=bool(all(row[k]<5e-10 for k in ('force_relative','torque_relative','potential_relative'))
            and all(row[k]<5e-12 for k in ('linear_relative','angular_relative'))
            and all(g[k]<2e-6 for g in gradients for k in ('torque_relative','power_relative')))
        rows.append(row)
    return rows
