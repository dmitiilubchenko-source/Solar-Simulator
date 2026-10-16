import numpy as np
import pytest
from scipy.integrate import solve_ivp

from scripts import harmonic_sphere as harmonic
from scripts import independent_harmonic_reference as reference


def test_Riccati_and_log_profile_match_independent_production_raw_solution():
    c=.15;s=np.linspace(0.,1.,65)
    prod=solve_ivp(lambda r,z:harmonic.rhs(r,z,c),(0.,1.),[1.,-0.],t_eval=s,
        method='DOP853',rtol=1e-11,atol=2e-13,max_step=1/128)
    other=solve_ivp(lambda r,z:reference.riccati_rhs(r,z,c),(0.,1.),reference.centre_state(c),t_eval=s,
        method='RK45',rtol=2e-11,atol=4e-13,max_step=1/128)
    assert prod.success and other.success
    chart=harmonic.match(prod.y[:,-1],c);matched=reference.boundary(other.y[:,-1],c)
    geo=harmonic.interior_geometry(s,prod.y.T,chart);h,hp=reference.profile(s,other.y.T,matched)
    assert np.max(abs(h-geo['harmonic_radius_fraction']))<1e-9
    assert np.max(abs(hp-geo['radius_derivative']))<1e-9


def test_Riccati_regular_centre_matches_analytic_profile_derivative():
    c=.2;state=reference.centre_state(c)
    assert np.array_equal(reference.riccati_rhs(0.,state,c),np.zeros(2))
    assert np.signbit(state[1])
    with pytest.raises(ValueError,match='Regular'):reference.riccati_rhs(0.,[1.,0.],c)


def test_published_interior_and_exterior_value_derivatives_join_through_C2():
    for c in (.0005,.01,.1):
        hi,di=reference.published_interior(1.,c);he,de=reference.published_exterior(1.,c)
        assert abs(hi-he)<2e-16 and abs(di-de)<2e-16
    for bad in (0,3,True):
        with pytest.raises(ValueError):reference.published_interior(.5,.1,bad)


@pytest.mark.parametrize('c',[.0005,.1,.3])
def test_positive_integral_basis_derivatives_obey_vacuum_operator(c):
    s=np.array([1.,2.,10.]);d,dp,dpp=reference.vacuum_basis(s,c)
    assert np.max(abs(s*(s-2*c)*dpp+(2*s-2*c)*dp-2*d)*s*s)<1e-14


def test_shifted_Riccati_source_remains_regular_to_tiny_radius_without_cutoff():
    c=.02;a=np.sqrt(1-2*c);n0=(3*a-1)/2;w0=c*(6-1/n0)/5
    source0=12*c*c-c*c*(3*a-2)/(2*n0*n0)
    expected=source0-w0*(w0+c/n0-2*c)
    for s in (1e-4,1e-6,1e-8,1e-10,1e-12,1e-14):
        flow=reference.riccati_rhs(s,reference.centre_state(c),c)
        assert abs(flow[0]/s-expected)<1e-10
        assert abs(flow[1]/s-w0)<1e-17
