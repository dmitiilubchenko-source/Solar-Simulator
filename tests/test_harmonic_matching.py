import numpy as np
import pytest
from scipy.integrate import solve_ivp

from scripts import harmonic_sphere as harmonic


@pytest.mark.parametrize('c',[.0005,.1,.3])
def test_smooth_surface_metric_and_current_measure_matching(c):
    solution=solve_ivp(lambda s,z:harmonic.rhs(s,z,c),(0.,1.),[1.,-0.],
        method='DOP853',rtol=2e-12,atol=4e-14,max_step=1/128)
    assert solution.success
    surface=solution.y[:,-1];chart=harmonic.match(surface,c)
    interior=harmonic.interior_geometry(1.,surface,chart);exterior=harmonic.exterior_geometry(1.,chart)
    for key in interior:assert abs(interior[key]-exterior[key])<8e-15
    assert 0<chart.matching_condition<1e8
    assert abs(interior['current_volume_weight']*interior['cartesian_jacobian_determinant']-1/np.sqrt(1-2*c))<3e-15
    origin=harmonic.interior_geometry(0.,[1.,-0.],chart)
    assert origin['harmonic_radius_fraction']==0.
    assert origin['metric_radial']==origin['metric_tangent']
    assert abs(origin['current_volume_weight']-chart.scale**-3)<2e-15


def test_regular_chart_does_not_force_exterior_residual_gauge_to_zero():
    c=.02;sol=solve_ivp(lambda s,z:harmonic.rhs(s,z,c),(0.,1.),[1.,0.],rtol=2e-12,atol=4e-14,max_step=1/128,method='DOP853')
    chart=harmonic.match(sol.y[:,-1],c)
    assert chart.residual_gauge<0.
    assert abs(chart.residual_gauge/c**2+4/35)<.01
    distant=harmonic.exterior_geometry(1e6,chart)
    assert abs(distant['harmonic_radius_fraction']/1e6-1)<1e-7
    assert abs(distant['radius_derivative']-1)<1e-14


@pytest.mark.parametrize('bad',[[-1.,0.],[1.,-1.],[0.,0.]])
def test_invalid_surface_matching_rejected(bad):
    with pytest.raises(ValueError):harmonic.match(bad,.1)


def test_metric_geometry_requires_explicit_chart_and_positive_regular_Jacobian():
    chart=harmonic.MatchedChart(.1,.9,-.001,2.)
    with pytest.raises(ValueError):harmonic.interior_geometry(.5,[1.,-3.],chart)
    with pytest.raises(ValueError):harmonic.interior_geometry(0.,[1.,.01],chart)
    with pytest.raises(ValueError):harmonic.interior_geometry(.5,[1.,0.],None)
    with pytest.raises(ValueError):harmonic.MatchedChart(.1,.9,-.001,1e8)
