import numpy as np
import pytest
from scipy.integrate import quad, solve_ivp

from scripts.continuum_sphere import Sphere
from scripts import continuum_conventions as convention
from scripts import fluid_spin


def sphere(c=.2):
    return Sphere(3., 2., .4, np.sqrt(.4*3/(2*c)))


@pytest.mark.parametrize('c', [1e-12, .0005, .1, .3])
def test_proper_energy_volume_matches_independent_radial_quadrature(c):
    for s in (0., .1, .7, 1.):
        expected = 3*quad(lambda r:r*r/np.sqrt(1-2*c*r*r), 0., s, epsabs=1e-13)[0]
        assert abs(convention.proper_volume_fraction(s,c)-expected)<2e-13


@pytest.mark.parametrize('c', [.0005, .1, .3])
def test_isotropic_metric_inverse_and_independent_log_coordinate_ODE(c):
    s = np.linspace(0., 1., 101); geo = convention.isotropic_geometry(s,c)
    x = geo['isotropic_radius_fraction']; dx = geo['radius_derivative']
    assert np.max(abs(convention.areal_from_isotropic(x,c)-s))<2e-15
    assert abs(x[-1]*(1+c/(2*x[-1]))**2-1)<2e-15
    # g=log(x/s) has a regular ODE at s=0: rationalize 1/u-1.
    def rhs(r,z):
        u = np.sqrt(1-2*c*r*r)
        return [2*c*r/(u*(1+u))]
    start = np.log(x[-1]); sol = solve_ivp(rhs, (1.,0.), [start], t_eval=s[::-1],
        method='DOP853', rtol=2e-13, atol=1e-14, max_step=1/128)
    assert sol.success
    x_over_s = np.exp(sol.y[0,::-1])
    assert np.max(abs(dx/x_over_s-1/np.sqrt(1-2*c*s*s)))<2e-13
    assert np.max(abs(x_over_s[1:]-x[1:]/s[1:]))<2e-13
    assert np.max(abs(geo['isotropic_volume_weight']*x*x*dx-s*s/np.sqrt(1-2*c*s*s)))<3e-15


def test_baryon_density_is_explicit_and_different_from_energy_density():
    body = sphere(); s = np.linspace(0.,1.,11); density = body.energy_density_mass*(.4+.2*s*s)
    values = convention.mass_integrands(s,body,density)
    assert np.max(abs(values['baryon_mass_rate_kg'][1:]/values['proper_energy_mass_rate_kg'][1:]-(.4+.2*s[1:]**2)))<2e-15
    assert values['baryon_mass_rate_kg'][0]==0.
    assert values['isotropic_conserved_density_kg_m3'][0]>density[0]
    assert values['areal_conserved_density_kg_m3'][0]==density[0]
    with pytest.raises(TypeError): convention.mass_integrands(s,body)


@pytest.mark.parametrize('omega', [-.001, 0., .001])
def test_local_clock_shift_and_exterior_J_use_signed_distant_rate(omega):
    body = sphere(); surface=np.array([1.8,.9]); matched=fluid_spin.boundary(surface,body.compactness)
    h = np.array([.4, matched['normalized_surface']]); s=np.array([0.,1.])
    result=convention.observer_rates(s,h,body,omega,surface_state=surface)
    expected_lapse=np.array([(3*np.sqrt(.6)-1)/2,np.sqrt(.6)])
    assert np.max(abs(result['static_rate_s_inv']*expected_lapse-omega))<2e-18
    assert np.max(abs(result['zamo_relative_rate_s_inv']*expected_lapse+result['dragging_rate_s_inv']-omega))<2e-18
    assert np.max(abs(result['apparent_static_response_kg_m2']*result['static_rate_s_inv']-result['exterior_angular_momentum_kg_m2_s']))<2e-18
    assert np.max(abs(result['apparent_zamo_response_kg_m2']*result['zamo_relative_rate_s_inv']-result['exterior_angular_momentum_kg_m2_s']))<2e-18
    assert result['equatorial_zamo_speed_m_s'][0]==0.
    assert np.all(result['apparent_zamo_response_kg_m2']>0)


@pytest.mark.parametrize('bad', [-1., float('nan'), True, [1.,2.], 1j])
def test_invalid_baryon_density_rejected(bad):
    with pytest.raises(ValueError): convention.mass_integrands(np.array([0.,.5,1.]),sphere(),bad)


@pytest.mark.parametrize('bad', [-.1, 1., float('nan'), True, 1j])
def test_inverse_isotropic_radius_domain_rejected(bad):
    with pytest.raises(ValueError): convention.areal_from_isotropic(bad,.2)


@pytest.mark.parametrize('bad', [0., -1., 1.01, float('nan'), True, [1.,2.], 1j])
def test_invalid_observer_profile_rejected(bad):
    with pytest.raises(ValueError): convention.observer_rates(np.array([0.,.5,1.]),bad,sphere(),.001,surface_state=[1.8,.9])


def test_observer_rate_preserves_existing_slow_rotation_domain():
    with pytest.raises(ValueError,match='Slow-rotation'):
        convention.observer_rates(1.,.8,sphere(),1.,surface_state=[1.8,.9])
