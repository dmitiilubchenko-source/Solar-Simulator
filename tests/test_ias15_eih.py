"""Analytic/API checks for isolated velocity-dependent IAS15 research use."""
from dataclasses import replace

import numpy as np
import pytest

from scripts.ias15_eih import (circle,triple,drag_probe,noether,ias_trajectory,
    errors,validate,configured,snapshot)
from scripts.ias15_reference import load_library
from scripts.newton_year import ROOT
from scripts.assess_sandbox_planets import states
from solar_simulator.native_forces import prepare
from solar_simulator.relativity import C,invariants


@pytest.fixture
def library():
    directory = ROOT/'.tools/ias15165/dependency'
    if not directory.is_dir():
        pytest.importorskip('rebound',reason='Optional research REBOUND absent')
        return load_library()
    return load_library(directory)


def test_velocity_flag_against_independent_exponential(library):
    actual,expected,stats = drag_probe(library)
    error = errors(actual,expected)
    assert error['position_metres']<.001 and error['velocity_m_per_s']<1e-6
    wrong,expected,_ = drag_probe(library,False)
    error = errors(wrong,expected)
    assert error['position_metres']>=.001 or error['velocity_m_per_s']>=1e-6
    assert stats['force_evaluations']>0


@pytest.mark.parametrize('factory',[circle,triple])
def test_independent_action_noether_against_runtime(factory):
    seed = factory()[0]
    q,masses = states(seed.bodies),np.array([b.mass for b in seed.bodies])
    energy,p,l = invariants(seed.bodies)
    expected = np.array([energy,p.x,p.y,p.z,l.x,l.y,l.z])
    actual = noether(q,masses)
    scale = np.r_[abs(energy),[sum(m*np.linalg.norm(v) for m,v in zip(masses,q[:,3:]))]*3,
        [np.linalg.norm(expected[4:])]*3]
    assert np.max(abs(actual-expected)/scale)<5e-14


def test_analytic_equal_mass_eih_circle_force():
    seed,times,expected,details = circle()
    masses = np.array([b.mass for b in seed.bodies])
    q = states(seed.bodies)
    force = prepare(masses)(q[:,:3],q[:,3:],C)
    relative = q[1,:3]-q[0,:3]
    np.testing.assert_allclose(force[1]-force[0],-details['omega_per_second']**2*relative,rtol=3e-15,atol=1e-12)
    assert len(times)==82


@pytest.mark.parametrize('epsilon',[1e-9,1e-11])
def test_ias15_exact_order_reduced_circle(library,epsilon):
    seed,times,expected,_ = circle()
    actual,stats = ias_trajectory(seed,times,library,epsilon)
    error = errors(actual,expected)
    assert error['position_metres']<.1 and error['velocity_m_per_s']<1e-4
    np.testing.assert_array_equal(actual[0],expected[0])
    assert stats['gravity']=='none' and stats['force_is_velocity_dependent']==1


@pytest.mark.parametrize('failure',['exception','nan','shape','weak-field'])
def test_callback_errors_are_latched_and_rethrown(library,failure,capsys):
    seed = circle()[0]
    def bad(p,v):
        if failure=='exception':
            raise ValueError('Injected physical failure')
        if failure=='weak-field':
            return prepare(np.array([b.mass for b in seed.bodies]))(p,v+1e8,C)
        return np.full_like(p,np.nan) if failure=='nan' else np.zeros(3)
    with pytest.raises(RuntimeError,match='no output committed') as caught:
        ias_trajectory(seed,[0.,.1],library,1e-9,acceleration=bad)
    assert isinstance(caught.value.__cause__,ValueError)
    assert 'Exception ignored' not in capsys.readouterr().err


def test_callback_keeps_original_inertial_velocities(library):
    seed,times = triple()
    initial = states(seed.bodies)
    seen = []
    native = prepare(np.array([b.mass for b in seed.bodies]))
    def force(p,v):
        if not seen:
            seen.append((p.copy(),v.copy()))
        return native(p,v,C)
    ias_trajectory(seed,[0.,1.],library,1e-9,acceleration=force)
    np.testing.assert_array_equal(seen[0][0],initial[:,:3])
    np.testing.assert_array_equal(seen[0][1],initial[:,3:])


def test_wrong_model_rejected():
    seed = triple()[0]
    with pytest.raises(ValueError,match='EIH point'):
        validate(replace(seed,settings=replace(seed.settings,physics='newtonian')),[0.,1.])


def test_no_builtin_newton_or_com_shift(library):
    seed = circle()[0]
    initial = states(seed.bodies)
    sim,_ = configured(initial,[b.mass for b in seed.bodies],library,1e-9,.1,lambda p,v:np.zeros_like(p))
    np.testing.assert_array_equal(snapshot(sim),initial)
    assert sim.gravity=='none' and sim.force_is_velocity_dependent==1
