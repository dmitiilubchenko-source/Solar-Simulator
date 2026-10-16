import numpy as np
import pytest
from scipy.integrate import quad

from scripts.continuum_sphere import Sphere
from scripts import continuum_stress as stress
from scripts import independent_stress_reference as reference


@pytest.mark.parametrize('c',[1e-12,.0005,.1,.3])
def test_Komar_stress_sum_matches_independent_metric_gradient_and_surface_mass(c):
    body=Sphere(3.,2.,.4,np.sqrt(.4*3/(2*c)));s=np.linspace(0.,1.,33)
    values=stress.komar_measures(s,body)
    metric=reference.metric_komar_charge(s,c)
    assert np.max(abs(values['komar_metric_charge_kg']/3-metric))<8e-16
    assert np.max(abs(values['komar_mass_rate_kg']/3-3*s*s))<2e-15
    mass=quad(lambda r:stress.komar_measures(r,body)['komar_mass_rate_kg'],0.,1.,epsabs=1e-12)[0]
    assert abs(mass-3)<2e-15
    assert values['pressure_trace_rate_kg'][0]==0. and values['pressure_trace_rate_kg'][-1]==0.


def test_ordered_current_terms_sum_to_independent_direct_integrand():
    s=np.linspace(0.,1.,33);c=.2;h=.5+.3*s*s
    values=stress.spin_terms(s,h,c)
    total=sum(values[key] for key in ('newton','pressure','proper_volume','lapse','frame_profile'))
    direct=reference.direct_inertia_integrand(s,h,c)
    assert np.max(abs(total-direct))<9e-16
    assert np.max(abs(total-values['full']))<9e-16
    assert np.all(values['frame_profile']<=0.)
    assert np.all(values['lapse']>=0.)


def test_linear_bookkeeping_and_paired_omission_coefficients_are_distinct():
    terms=reference.term_linear_coefficients();second=reference.second_order_coefficients()
    assert abs(sum(terms.values())-12/35)<6e-17
    assert terms['lapse']==-terms['frame_profile']
    assert abs(second['paired_omission']-second['correct']-second['difference'])<6e-17


@pytest.mark.parametrize('bad',[0.,-1.,1.01,float('nan'),True,[1.,2.],1j])
def test_invalid_spin_profile_explicitly_rejected(bad):
    with pytest.raises(ValueError):stress.spin_terms(np.array([0.,.5,1.]),bad,.2)


def test_invalid_Komar_sphere_and_singular_spin_origin_rejected():
    with pytest.raises(ValueError):stress.komar_measures(.5,None)
    with pytest.raises(ValueError,match='Regular'):reference.spin_log_rhs(0.,[1.,0.],.2)
