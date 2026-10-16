import numpy as np
import pytest
from scipy.integrate import quad

from scripts import harmonic_sphere as harmonic


def test_raw_rhs_satisfies_independent_self_adjoint_harmonic_operator():
    s=.43;c=.23;f=1.2;first=.07;second=harmonic.rhs(s,[f,first],c)[1]
    def flux_coefficient(r):
        u=np.sqrt(1-2*c*r*r);n=(3*np.sqrt(1-2*c)-u)/2
        return r*r*u*n
    derivative=flux_coefficient(s+1j*1e-20).imag/1e-20
    u=np.sqrt(1-2*c*s*s);n=(3*np.sqrt(1-2*c)-u)/2
    residual=flux_coefficient(s)*(2*first+s*second)+derivative*(f+s*first)-2*n/u*s*f
    assert abs(residual)<4e-16


def test_regular_origin_and_Newton_raw_curvature_limit():
    c=1e-4;flow=harmonic.rhs(0.,[1.,-0.],c)
    assert flow[0]==0. and abs(flow[1]/c-1)<1e-3
    with pytest.raises(ValueError,match='Regular'):harmonic.rhs(0.,[1.,.01],c)


@pytest.mark.parametrize('c',[.0005,.1,.3])
@pytest.mark.parametrize('s',[1.,3.,10.])
def test_decaying_basis_matches_independent_positive_integral_and_vacuum_equation(c,s):
    value,first,second=harmonic.exterior_basis(s,c)
    expected=3*quad(lambda t:t*t/((s-c)**2-c*c*t*t),0.,1.,epsabs=1e-13)[0]
    assert abs(value-expected)*s*s<4e-15
    assert abs(s*(s-2*c)*second+(2*s-2*c)*first-2*value)*s*s<2e-14
    assert value>0 and first<0 and second>0
    assert max(harmonic.basis_tail_bounds(s,c))<1e-24


@pytest.mark.parametrize('bad',[0.,1e-12,.31,float('nan'),True,1j])
def test_explicit_harmonic_compactness_domain_rejected(bad):
    with pytest.raises(ValueError):harmonic.rhs(.5,[1.,0.],bad)


@pytest.mark.parametrize('bad',[.99,float('inf'),True,1j])
def test_exterior_radius_domain_rejected(bad):
    with pytest.raises(ValueError):harmonic.exterior_basis(bad,.1)
