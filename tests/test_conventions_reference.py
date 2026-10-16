import numpy as np
from scipy.integrate import solve_ivp

from scripts import independent_conventions_reference as reference


def test_numerical_inverse_mass_in_isotropic_chart_agrees_with_areal_quadrature():
    c=.2;start=np.array([np.log(reference.surface_isotropic_fraction(c))])
    sol=solve_ivp(lambda s,z:reference.log_radius_rhs(s,z,c),(1.,0.),start,
        method='DOP853',rtol=2e-13,atol=1e-14,max_step=1/128,dense_output=True)
    assert sol.success
    density=lambda s:.4+.2*s*s
    isotropic,s,x=reference.baryon_isotropic_ratio(c,density,sol,32)
    areal=reference.baryon_areal_ratio(c,density,32)
    assert abs(isotropic-areal)<2e-13
    assert np.max(abs(s*np.exp(sol.sol(s)[0])-x))<2e-14


def test_ZAMO_coframe_recovers_unit_clock_and_relative_speed():
    projected=reference.tetrad_rates(2.,.7,.003,.005)
    assert abs(projected[0]-1.)<2e-16
    assert abs(projected[1]-2.*(.005-.003)/.7)<2e-18


def test_series_changes_follow_mass_radius_clock_definitions():
    # Algebraic first derivatives, independent of radial numerical solutions.
    base=12/35;newton=2/5
    derived=(base,base-newton*3/5,base+2*newton,base-newton,base+newton*(2*newton-1))
    values=reference.response_linear_series(1.)
    assert np.max(abs(np.array(list(values.values()))-newton-np.array(derived)))<2e-16
    assert reference.proper_volume_series(0.)==1.
