import numpy as np
import pytest

from scripts import fluid_spin as model
from scripts import continuum_sphere as sphere
from scripts import independent_fluid_reference as reference


def test_pressure_source_metric_derivative_and_exact_regular_origin():
    s=np.linspace(0.,1.,49)
    for c in (1e-6,.02,.1,.3):
        actual=sphere.background(s,c)['logarithmic_j_rate']
        expected=reference.stress_logj_rate(s,c)
        assert np.max(abs(actual-expected))/c<1e-11
        centre=model.rhs(0.,[1.,0.],c)
        nc=(3*np.sqrt(1-2*c)-1)/2
        assert centre[0]==0. and abs(centre[1]-4*c*(2+1/nc)/5)<1e-11
        assert reference.riccati_rhs(0.,[0.],c)[0]==0.


def test_independent_profile_polynomial_solves_ODE_through_C_squared():
    s=np.linspace(.05,1.,33);errors=[]
    for c in (.004,.002,.001):
        f,v,acc=reference.raw_profile_series(s,c)
        remainder=[abs(model.rhs(float(ss),[ff,vv],c)[1]-aa) for ss,ff,vv,aa in zip(s,f,v,acc)]
        errors.append(max(remainder))
    assert all(7.9<a/b<8.1 for a,b in zip(errors,errors[1:]))


def test_surface_matching_SI_charge_scaling_and_no_energy_claim():
    c=.1;raw=np.array([1.14,.28]);old=raw.tobytes();out=model.boundary(raw,c)
    field,derivative=model.exterior(np.array([1.,2.,4.]),out['inertia_factor'],c)
    assert abs(field[0]-out['normalized_surface'])<1e-11
    assert abs(derivative[0]-out['normalized_surface_derivative'])<1e-11
    pars=sphere.Sphere(3.,2.,.4,np.sqrt(.4*3/2/c))
    a=model.charges(raw,pars,.01);b=model.charges(raw,pars,-.02)
    assert abs(a['inertia_kg_m2']-out['inertia_factor']*12)<1e-11
    assert abs(b['angular_kg_m2_s']+2*a['angular_kg_m2_s'])<1e-11
    assert set(a)=={'inertia_kg_m2','angular_kg_m2_s'} and raw.tobytes()==old
    assert reference.inertia_series(0.,0)==.4
    assert abs(reference.inertia_series(.01,1)-(.4+12*.01/35))<1e-11


@pytest.mark.parametrize('call',[lambda:model.rhs(0.,[1.,.01],.1),lambda:model.rhs(1.1,[1.,0.],.1),
    lambda:model.rhs(.5,[np.nan,0.],.1),lambda:model.boundary([1.,0.],.1),
    lambda:model.boundary([-1.,.1],.1),lambda:model.exterior(.99,.4,.1),
    lambda:model.exterior(True,.4,.1),lambda:model.exterior(2.,False,.1),
    lambda:reference.inertia_series(.1,3),lambda:reference.inertia_series(.1,True)])
def test_invalid_spin_inputs_rejected(call):
    with pytest.raises(ValueError):call()


@pytest.mark.parametrize('omega',[10.,1e300])
def test_finite_angular_velocity_must_respect_declared_slowrotation_domain(omega):
    pars=sphere.Sphere(3.,2.,.4,np.sqrt(6.))
    with pytest.raises(ValueError,match='Slow-rotation'):model.charges([1.14,.28],pars,omega)
