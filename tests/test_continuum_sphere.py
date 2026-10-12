import numpy as np
import pytest

from scripts import continuum_sphere as model


def sphere(c=.1):return model.Sphere(3.,2.,.4,np.sqrt(.4*3/2/c))


def test_exact_background_TOV_complex_derivative_and_surface_matching():
    s=np.linspace(0.,1.,41)
    for c in (1e-6,.01,.1,.3):
        out=model.background(s,c);z=s+1j*1e-20
        u=np.sqrt(1-2*c*z*z);a=np.sqrt(1-2*c);n=(3*a-u)/2
        raw_pressure=(u-a)/(3*a-u)
        raw_logj=np.log(u/n)
        assert np.max(abs(raw_pressure.imag/1e-20-out['pressure_ratio_rate']))/c<1e-11
        assert np.max(abs(raw_logj.imag/1e-20-out['logarithmic_j_rate']))/c<1e-11
        p=out['pressure_ratio']
        tov=-c*s*(1+p)*(1+3*p)/(1-2*c*s*s)
        assert np.max(abs(out['pressure_ratio_rate']-tov))/c<1e-11
        assert abs(out['lapse'][-1]-np.sqrt(1-2*c))<1e-11
        assert out['pressure_ratio'][-1]==0. and out['j'][-1]==1.
        assert abs(out['nu_rate'][-1]-2*c/(1-2*c))<1e-11


def test_pressure_Newton_limit_and_stable_small_compactness():
    s=np.linspace(0.,1.,33);errors=[]
    for c in (1e-4,5e-5,2.5e-5):
        p=model.background(s,c)['pressure_ratio']/c
        errors.append(np.max(abs(p-.5*(1-s*s))))
    assert all(1.99<a/b<2.01 for a,b in zip(errors,errors[1:]))
    tiny=model.background(s,1e-12)['pressure_ratio']/1e-12
    assert np.max(abs(tiny-.5*(1-s*s)))<1e-11


def test_Newton_hydrostatic_pressure_potential_and_volume_integrals():
    pars=sphere();s,w=np.polynomial.legendre.leggauss(16);s=(s+1)/2;w=w/2
    o=model.newton_profile(s,pars);rho=pars.energy_density_mass;r=pars.areal_radius_m
    totals=model.newton_integrals(pars)
    pressure=4*np.pi*r**3*np.dot(w,o['pressure']*s*s)
    gravity=-.5*4*np.pi*r**3*np.dot(w,rho*o['potential']*s*s)
    inertia=8*np.pi*r**5/3*np.dot(w,rho*s**4)
    assert abs(pressure-totals['pressure_volume_integral'])/pressure<1e-11
    assert abs(gravity-totals['gravitational_energy'])/abs(gravity)<1e-11
    assert abs(inertia-totals['inertia'])/inertia<1e-11
    assert abs(gravity+3*pressure)/abs(gravity)<1e-11
    # Hydrostatic gradient dp/dr=rho*g; pressure force convention explicit.
    gradient=-rho*pars.gravitational_constant*pars.gravitational_mass_kg/r**2*s
    assert np.max(abs(gradient-rho*o['radial_acceleration']))<1e-11


@pytest.mark.parametrize('args',[(0.,2.,.4,2.),(3.,-2.,.4,2.),(3.,2.,False,2.),(3.,2.,.4,np.nan),
    (3.,2.,.4,.1),(1e300,1e200,.4,2.)])
def test_bad_scales_rejected(args):
    with pytest.raises(ValueError):model.Sphere(*args)


@pytest.mark.parametrize('s,c',[(-.1,.1),(1.1,.1),(True,.1),(np.nan,.1),(.5,0.),(.5,.4),(.5,1e-14),(.5,True)])
def test_bad_radius_or_compactness_rejected(s,c):
    with pytest.raises(ValueError):model.background(s,c)
