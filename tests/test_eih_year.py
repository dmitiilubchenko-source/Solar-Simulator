"""Small corrections, dimensions and conditioning of the independent year oracle."""
from dataclasses import replace
import numpy as np
import pytest

from scripts.eih_year import inputs,force_terms,reference
from scripts.newton_year import YEAR,DAY,errors
from scripts.assess_relativity import independent_acceleration
from scripts.assess_sandbox_planets import states
from solar_simulator.native_forces import prepare
from solar_simulator.relativity import C
from solar_simulator.simulation import AU,G


@pytest.mark.parametrize('count',[2,3,10])
def test_matrix_and_separate_pn_agree_with_scalar_and_native(count):
    rng = np.random.default_rng(180+count)
    p = rng.normal(size=(count,3))*1e11
    v = rng.normal(size=(count,3))*1e4
    masses = rng.uniform(.1,1.,count)*1e29
    mu = G*masses
    newton,pn = force_terms(p,v,mu,C)
    native = prepare(masses)
    scalar = independent_acceleration(p,v,mu,C)
    scale = np.linalg.norm(scalar,axis=1).max()
    assert np.linalg.norm(newton+pn-scalar,axis=1).max()/scale<3e-14
    assert np.linalg.norm(newton+pn-native(p,v,C),axis=1).max()/scale<3e-14
    newton,pn = force_terms(p,v,mu,1e7)
    for actual in (independent_acceleration(p,v,mu,1e7)-newton,
                   native(p,v,1e7)-native(p,v)):
        assert np.linalg.norm(pn-actual,axis=1).max()/np.linalg.norm(pn,axis=1).max()<3e-9


@pytest.mark.parametrize('clock',[YEAR,DAY])
@pytest.mark.parametrize('pair',[(3,4),(4,3)])
def test_units_and_conditioned_pair(clock,pair):
    seed,_ = inputs()
    q = states(seed.bodies)
    masses = np.array([b.mass for b in seed.bodies])
    rho = q[pair[1],:3]-q[pair[0],:3]
    n,pn = force_terms(q[:,:3],q[:,3:],G*masses,C,(*pair,rho))
    a,b = force_terms(q[:,:3]/AU,q[:,3:]*clock/AU,G*masses*clock**2/AU**3,
        C*clock/AU,(*pair,rho/AU))
    scaled = (a+b)*AU/clock**2
    assert np.linalg.norm(scaled-n-pn,axis=1).max()/np.linalg.norm(n+pn,axis=1).max()<3e-14
    native = prepare(masses)(q[:,:3],q[:,3:],C,(*pair,rho))
    assert np.linalg.norm(n+pn-native,axis=1).max()/np.linalg.norm(native,axis=1).max()<3e-14


def test_newton_limit_and_reference_domain_guards():
    seed,_ = inputs()
    q = states(seed.bodies);mu = G*np.array([b.mass for b in seed.bodies])
    n,pn = force_terms(q[:,:3],q[:,3:],mu,1e30)
    np.testing.assert_array_equal(n+pn,n)
    with pytest.raises(ValueError,match='weak-field'):
        force_terms(q[:,:3],q[:,3:]+1e8,mu,C)
    q[1,:3] = q[0,:3]
    with pytest.raises(ValueError,match='Coincident'):
        force_terms(q[:,:3],q[:,3:],mu,C)


def test_new_seed_preserves_origin_and_explicitly_disables_figures():
    from solar_simulator.storage import load
    from scripts.newton_year import ROOT
    original = load(ROOT/'docs/solar-sandbox-strict-checkpoint.json')
    seed,times = inputs()
    assert seed.origin==original.origin and seed.settings.physics=='eih-1pn'
    assert original.settings.figures and not seed.settings.figures
    np.testing.assert_array_equal(states(seed.bodies),states(original.bodies))
    assert [b.mass for b in seed.bodies]==[b.mass for b in original.bodies]
    assert len(times)==125 and times[-1]==YEAR


def test_short_reference_roundtrip_and_clock_change():
    seed,_ = inputs();times = np.array([0.,1.,3600.])
    a,_ = reference(seed,times,3e-14,450.,YEAR)
    b,_ = reference(seed,times,3e-14,450.,DAY)
    assert errors(a[0],states(seed.bodies))['position_metres']<.002
    assert errors(a,b)['position_metres']<.01
    assert errors(a,b)['velocity_m_per_s']<1e-7
    with pytest.raises(ValueError,match='EIH point'):
        reference(replace(seed,settings=replace(seed.settings,physics='newtonian')),times,3e-14,450.)


def test_failed_reference_cannot_certify_a_candidate():
    from scripts.assess_eih_year import metrics,reference_gate
    seed,_ = inputs()
    values = np.stack([states(seed.bodies)]*2)
    row = metrics(values,values,seed,False)
    assert row['numerical_targets_passed'] and not row['checks_passed']
    assert not reference_gate(dict(all_bodies=dict(position_metres=.2,velocity_m_per_s=0.),
        moon_relative_to_earth=dict(position_metres=.02,velocity_m_per_s=0.)))


def test_relative_moon_error_remains_visible_among_ten_bodies():
    from scripts.assess_eih_year import metrics
    seed,_ = inputs()
    expected = np.stack([states(seed.bodies)]*2)
    values = expected.copy()
    values[1,4,0] += .2
    row = metrics(values,expected,seed,True)
    assert row['all_bodies']['position_metres']<10.
    assert row['moon_relative_to_earth']['position_metres']>.1
    assert not row['numerical_targets_passed'] and not row['checks_passed']
