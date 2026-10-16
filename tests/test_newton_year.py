"""Independent analytic and dimensional checks of the offline Newton oracle."""
from dataclasses import replace
from math import sqrt, pi

import numpy as np
import pytest

from scripts.newton_year import (YEAR,DAY,encode,decode,reference_rhs,reference,
    inputs,validate,errors,packet_end,invariants)
from scripts.assess_newton_year import candidate_metrics,reference_gate
from scripts.assess_sandbox_planets import states
from solar_simulator.simulation import Body,G,AU
from solar_simulator.vector3 import Vector3
from solar_simulator.experiment import create_experiment,Settings


def triangle():
    mass,radius = 3e24,6e7
    rate = sqrt(G*mass/(sqrt(3)*radius**3))
    u,v = np.array([1.,0.,0.]),np.array([0.,.6,.8])
    angles = np.arange(3)*2*pi/3
    q = np.array([np.r_[radius*(np.cos(a)*u+np.sin(a)*v),
        radius*rate*(-np.sin(a)*u+np.cos(a)*v)] for a in angles])
    bodies = [Body(name,mass,Vector3(*row[:3]),Vector3(*row[3:]))
        for name,row in zip(('Sun','Earth','Moon'),q)]
    return create_experiment(bodies,Settings(100.)),rate,u,v


@pytest.mark.parametrize('clock',[YEAR,DAY])
def test_reference_rhs_independent_scalar_si(clock):
    seed,_,_,_ = triangle()
    q = states(seed.bodies)
    # Asymmetry and inertial translation/drift prevent accidental symmetry cancellation.
    q[0] += np.array([7e7,4e7,-5e7,130.,-71.,60.])
    masses = np.array([1e26,3e24,7e22])
    encoded = encode(q,masses,(1,2),clock)
    derivative = reference_rhs(masses,(1,2),clock)(0,encoded.ravel()).reshape(3,6)
    actual = decode(np.c_[np.zeros((3,3)),derivative[:,3:]],masses,(1,2),clock)[:,3:]/clock
    expected = np.zeros((3,3))
    for i in range(3):
        for j in range(3):
            if i!=j:
                d = q[j,:3]-q[i,:3]
                expected[i] += G*masses[j]*d/np.linalg.norm(d)**3
    np.testing.assert_allclose(actual,expected,rtol=2e-14,atol=1e-17)
    np.testing.assert_allclose(derivative[:,:3],encoded[:,3:],rtol=0,atol=0)


@pytest.mark.parametrize('clock',[YEAR,DAY])
def test_equilateral_three_body_analytic_orbit(clock):
    seed,rate,u,v = triangle()
    period = 2*pi/rate
    times = np.linspace(0,period,25)
    actual,_ = reference(seed,times,3e-14,period/700,clock)
    expected = []
    for time in times:
        angles = np.arange(3)*2*pi/3+rate*time
        expected.append([np.r_[6e7*(np.cos(a)*u+np.sin(a)*v),
            6e7*rate*(-np.sin(a)*u+np.cos(a)*v)] for a in angles])
    error = errors(actual,np.array(expected))
    assert error['position_metres']<.001
    assert error['velocity_m_per_s']<1e-7
    assert max(invariants(actual,np.array([b.mass for b in seed.bodies])).values())<1e-11


def test_pinned_initial_roundtrip_and_model():
    seed,times = inputs()
    masses = np.array([b.mass for b in seed.bodies])
    q = states(seed.bodies)
    for clock in (YEAR,DAY):
        recovered = decode(encode(q,masses,(3,4),clock),masses,(3,4),clock)
        assert errors(recovered,q)['position_metres']<.002
        assert errors(recovered[4]-recovered[3],q[4]-q[3])['position_metres']<.0001
    assert seed.settings.physics=='newtonian' and not seed.settings.figures
    assert len(times)==125 and times[-1]==YEAR


@pytest.mark.parametrize('times',[[0,0],[0,np.inf],[1,2]])
def test_bad_epoch_grid_rejected(times):
    seed,_,_,_ = triangle()
    with pytest.raises(ValueError):
        validate(seed,times)


def test_non_newton_model_rejected():
    seed,_,_,_ = triangle()
    with pytest.raises(ValueError):
        validate(replace(seed,settings=replace(seed.settings,physics='eih-1pn')),[0,1])


def test_reference_failure_prevents_candidate_certification():
    seed,_,_,_ = triangle()
    values = np.stack([states(seed.bodies)]*2)
    row = candidate_metrics(values,values,seed,False)
    assert row['numerical_targets_passed'] and not row['checks_passed']
    assert not reference_gate(dict(all_bodies=dict(position_metres=.2,velocity_m_per_s=0.),
        moon_relative_to_earth=dict(position_metres=.02,velocity_m_per_s=0.)))


def test_packet_endpoint_and_nonprogress():
    assert packet_end(0.,700000.,3600.)==72000.
    assert packet_end(72000.,72000.5,3600.)==72000.5
    with pytest.raises(ValueError):
        packet_end(0.,0.,3600.)


@pytest.fixture
def library():
    from scripts.ias15_reference import load_library
    from scripts.newton_year import ROOT
    directory = ROOT/'.tools/ias15165/dependency'
    if not directory.is_dir():
        pytest.importorskip('rebound',reason='Optional REBOUND research library absent')
        return load_library()
    return load_library(directory)


@pytest.mark.parametrize('epsilon',[1e-9,1e-11])
def test_ias_multibody_analytic_triangle(library,epsilon):
    from scripts.newton_year import ias_trajectory
    seed,rate,u,v = triangle()
    period = 2*pi/rate
    times = np.linspace(0,period,25)
    actual,_ = ias_trajectory(seed,times,library,epsilon)
    expected = []
    for time in times:
        angles = np.arange(3)*2*pi/3+rate*time
        expected.append([np.r_[6e7*(np.cos(a)*u+np.sin(a)*v),
            6e7*rate*(-np.sin(a)*u+np.cos(a)*v)] for a in angles])
    assert errors(actual,np.array(expected))['position_metres']<.001
    assert errors(actual,np.array(expected))['velocity_m_per_s']<1e-7


def test_ten_body_exact_packets_and_force_counter(library):
    pytest.importorskip('solar_native')
    from scripts.newton_year import ias_trajectory,dop_trajectory
    seed,_ = inputs()
    times = np.array([0.,72000.,86400.125])
    actual,stats = ias_trajectory(seed,times,library,1e-9)
    counted,counter = ias_trajectory(seed,times,library,1e-9,count_forces=True)
    dop,dop_stats = dop_trajectory(seed,times)
    np.testing.assert_array_equal(actual,counted)
    np.testing.assert_array_equal(actual[0],states(seed.bodies))
    assert stats['packet_endpoints']==dop_stats['packet_endpoints']==[72000.,86400.125]
    assert counter['force_evaluations']>0
    assert errors(actual,dop)['position_metres']<.1


def test_pair_error_is_not_hidden_by_total_energy():
    seed,_,_,_ = triangle()
    expected = np.stack([states(seed.bodies)]*2)
    actual = expected.copy()
    actual[-1,2,0] += .2
    row = candidate_metrics(actual,expected,seed,True)
    assert not row['numerical_targets_passed'] and not row['checks_passed']
