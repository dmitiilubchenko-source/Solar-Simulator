"""Short research EIH + Newton rotor; no runtime mode or future attitude data."""
from dataclasses import dataclass
from time import perf_counter

import numpy as np
from scipy.integrate import DOP853, solve_ivp

from scripts.canonical_initial import SIUnits
from scripts.eih_year import force_terms
from scripts.fixed_j2_ias import entries
from scripts.fixed_j2_year import inputs
from scripts.hybrid_rotation import hessian, pack
from solar_simulator.coordinates import PairCoordinates
from solar_simulator.nbody_rotation import correction, RotationDOP853
from solar_simulator.oblateness import FixedJ2, prepare, acceleration
from solar_simulator.rotation import angular_velocity, quaternion_rate, rotation_matrix
from solar_simulator.spin_initial import lunar_solid_equivalent_initial
from solar_simulator.simulation import AU, G
from solar_simulator.relativity import C


@dataclass(frozen=True)
class Model:
    masses_si: tuple
    figure: object
    quaternion: tuple
    spin_si: tuple
    pair: PairCoordinates
    prepared: tuple
    fixed: tuple
    units: SIUnits

    def __post_init__(self):
        m = np.asarray(self.masses_si)
        if (m.ndim != 1 or len(m) < 2 or np.any(m <= 0) or not np.isfinite(m).all()
                or not 0 <= self.pair.first < len(m) or not 0 <= self.pair.second < len(m)
                or self.pair.first == self.pair.second or m[self.source] != self.figure.mass
                or abs(self.pair.first_fraction+self.pair.second_fraction-1) > 1e-15
                or not np.allclose([self.pair.first_fraction,self.pair.second_fraction],
                    m[[self.pair.first,self.pair.second]]/m[[self.pair.first,self.pair.second]].sum(),rtol=1e-14,atol=0.)
                or np.shape(self.spin_si) != (3,) or not np.isfinite(self.spin_si).all() or self.spin_scale <= 0
                or abs(np.linalg.norm(self.quaternion)-1) > 1e-12):
            raise ValueError('Consistent finite research masses/pair/figure/spin required')
        rotation_matrix(self.quaternion)

    @property
    def source(self):return self.pair.second

    @property
    def masses(self):return np.asarray(self.masses_si)/self.units.mass_kg

    @property
    def moments(self):return np.asarray(self.figure.moments)/self.units.inertia_kg_m2

    @property
    def spin_scale(self):return np.linalg.norm(self.spin_si)/self.units.spin_kg_m2_s

    @property
    def c(self):return C/self.units.velocity_m_s


def initial():
    seed, *_ = inputs()
    if any(type(f) is not FixedJ2 for f in seed.settings.figures):
        raise ValueError('Research contract requires static fixed axes')
    names = [b.name for b in seed.bodies]; first,second = map(names.index,('Earth','Moon'))
    masses = np.array([b.mass for b in seed.bodies]); weights = masses[[first,second]]/masses[[first,second]].sum()
    figure, _, spin_state, metadata = lunar_solid_equivalent_initial()
    if seed.origin.epoch_jd_tdb != metadata['epoch_jd_tdb']:
        raise ValueError('Orbit and spin epochs differ')
    units = SIUnits(float(masses[0]),AU,G)
    model = Model(tuple(masses),figure,tuple(spin_state[6:10]),tuple(spin_state[10:13]),
        PairCoordinates(first,second,*map(float,weights)),prepare(seed.bodies,seed.settings.figures),
        entries(seed,AU),units)
    x = np.array([[b.position.x,b.position.y,b.position.z] for b in seed.bodies])/AU
    v = np.array([[b.velocity.x,b.velocity.y,b.velocity.z] for b in seed.bodies])/units.velocity_m_s
    y = np.r_[model.pair.encode(x).ravel(),model.pair.encode(v).ravel(),model.quaternion,
        np.asarray(model.spin_si)/np.linalg.norm(model.spin_si),np.zeros(21)]
    return model,y,seed


def unpack(y, model):
    n = len(model.masses_si); state = np.asarray(y)
    if state.shape != (6*n+28,) or not np.isfinite(state).all():
        raise ValueError('Finite encoded x/v/q/scaledS/three-budget state required')
    x,v = state[:3*n].reshape(n,3),state[3*n:6*n].reshape(n,3)
    return model.pair.decode(x),model.pair.decode(v),x[model.pair.second],state[6*n:6*n+4],state[6*n+4:6*n+7]


def geometry(x, v, rho, model):
    distance = np.linalg.norm(x[:,None]-x[None,:],axis=2)
    np.fill_diagonal(distance,np.inf)
    a,b = model.pair.first,model.pair.second
    distance[a,b] = distance[b,a] = np.linalg.norm(rho)
    if (np.any(distance == 0) or max(np.max((1/distance)@model.masses),np.max(np.sum(v*v,axis=1)))/model.c**2 >= 1e-4
            or distance[model.source].min() <= model.figure.bounding_radius/model.units.length_m):
        raise ValueError('Research external figure/weak-field domain exceeded')
    centered = x-x[model.source]
    centered[a] = -rho
    return centered


def fields(y, model, active=True):
    x,v,rho,q,s = unpack(y,model); centered = geometry(x,v,rho,model)
    unit = model.units; acceleration_unit = unit.length_m/unit.time_s**2
    an,ap = force_terms(x,v,model.masses,model.c,(model.pair.first,model.pair.second,rho))
    af = acceleration(centered*unit.length_m,np.asarray(model.masses_si),model.prepared)/acceleration_unit
    aq = np.zeros_like(x); torque = np.zeros(3); potential = 0.
    if active:
        aq,torque,potential = correction(centered*unit.length_m,np.asarray(model.masses_si),
            model.source,model.figure,q)
        aq = aq/acceleration_unit
    energy_unit = unit.mass_kg*unit.velocity_m_s**2
    torque = torque/energy_unit
    h = hessian(centered,v,model.masses,model.c)
    budgets = np.array([pack(x,v,(h@b.ravel()).reshape(x.shape)) for b in (ap,af+aq)])
    fixed_torque = np.r_[np.zeros(4),np.cross(x,model.masses[:,None]*af).sum(axis=0)]
    return an+ap+af+aq,torque,potential/energy_unit,np.vstack((budgets,fixed_torque))


def rhs(t, y, model, scales, active=True):
    n = len(model.masses_si); _,_,_,q,s = unpack(y,model)
    a,tau,_,budget = fields(y,model,active)
    omega = angular_velocity(model.figure,q,s*np.linalg.norm(model.spin_si))*model.units.time_s
    return np.r_[y[3*n:6*n],model.pair.encode(a).ravel(),quaternion_rate(q,omega),
        tau/model.spin_scale,(budget/scales).ravel()]


class FreeDOP853(DOP853):
    def __init__(self, fun, t0, y0, t_bound, *, body_count, **kwargs):
        n = body_count
        if np.size(y0) != 6*n+28:
            raise ValueError('Wrong free research state size')
        self.blocks = [slice(k,k+3) for k in range(0,6*n,3)]
        self.blocks += [slice(6*n,6*n+4),slice(6*n+4,6*n+7)]
        for k in range(6*n+7,6*n+28,7):
            self.blocks += [slice(k,k+1),slice(k+1,k+4),slice(k+4,k+7)]
        super().__init__(fun,t0,y0,t_bound,**kwargs)

    _estimate_error_norm = RotationDOP853._estimate_error_norm


def tolerances(model, tight=False, matrix=False):
    n = len(model.masses_si); unit = model.units
    values = (3e-14,1800.,1e-4,1e-10,1e-14) if tight else (1e-12,3600.,1e-3,1e-9,1e-13)
    rtol,step,x,v,spin = values
    return rtol,step,np.r_[np.full(3*n,x/unit.length_m),np.full(3*n,v/unit.velocity_m_s),
        np.full(12 if matrix else 7,spin),np.full(21,1e-24)]


def integrate(model, y0, times, scales, tight=False, active=True):
    times = np.asarray(times,dtype=float)
    if times.ndim != 1 or len(times) < 2 or times[0] != 0 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        raise ValueError('Strict increasing research seconds from zero required')
    rtol,step,atol = tolerances(model,tight)
    start = perf_counter()
    result = solve_ivp(lambda t,y:rhs(t,y,model,scales,active),(0.,times[-1]/model.units.time_s),
        y0,t_eval=times/model.units.time_s,method=FreeDOP853,body_count=len(model.masses_si),
        rtol=rtol,atol=atol,max_step=step/model.units.time_s)
    if not result.success or result.y.shape != (len(y0),len(times)) or not np.isfinite(result.y).all():
        raise RuntimeError('Incomplete free research integration: '+result.message)
    return result.y.T,dict(rhs_calls=result.nfev,wall_seconds=perf_counter()-start,
        rtol=rtol,max_step_seconds=step,method='DOP853 worst encoded body/pair/q/S/budgets',active_moon_q=active)
