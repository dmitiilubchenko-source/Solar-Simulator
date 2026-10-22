"""Independent model and negative API controls, before the full nine-case audit."""
from math import pi, sqrt

import numpy as np
import pytest

import scripts.ias15_native_newton as coupling
from scripts.assess_ias15_restart import load_cases
from scripts.ias15_reference import load_library
from scripts.ias15_restart import bits, simulation
from scripts.kepler_transport import ROOT
from solar_simulator.native_forces import prepare
from solar_simulator.simulation import G


@pytest.fixture
def library():
    directory = ROOT/'.tools/ias15165/dependency'
    if not directory.is_dir():
        pytest.importorskip('rebound', reason='Optional research IAS15 not installed')
        return load_library()
    return load_library(directory)


def circle():
    radius, mass = 1e7, 1e25
    omega = sqrt(2*G*mass/radius**3)
    period = 2*pi/omega
    u, w = np.array([.6, .8, 0.]), np.array([-.48, .36, .8])
    initial = np.array([np.r_[-radius/2*u, -radius/2*omega*w],
                        np.r_[radius/2*u, radius/2*omega*w]])
    times = np.linspace(0., period, 5)
    reference = np.array([np.array([np.r_[sign*radius/2*(u*np.cos(omega*t)+w*np.sin(omega*t)),
        sign*radius/2*omega*(-u*np.sin(omega*t)+w*np.cos(omega*t))] for sign in (-1, 1)]) for t in times])
    return dict(masses=[mass, mass], states=initial.tolist(), times=times.tolist(), packet_dt=period/80), reference


def test_all_nine_initial_native_forces_against_independent_potential_gradient():
    cases, _ = load_cases()
    for case in cases.values():
        q, masses = case['initial'], case['request']['masses']
        force = prepare(masses)(q[:, :3], q[:, 3:], None, None)
        assert coupling.force_metrics(masses, q, force)['checks_passed']
        assert not coupling.force_metrics(masses, q, force*2)['checks_passed']


def test_reaction_rotation_permutation_and_velocity_independence():
    masses = np.array([2e25, 7e24])
    positions = np.array([[-2e9, 4e9, 1e9], [7e9, -6e9, 3e9]])
    velocity = np.array([[400., 500., -200.], [-70., 200., 800.]])
    force = prepare(masses)(positions, velocity)
    scale = np.linalg.norm(masses[:, None]*force)
    assert np.linalg.norm(np.sum(masses[:, None]*force, axis=0))/scale < 5e-13
    rotation = np.array([[0., -1., 0.], [0., 0., -1.], [1., 0., 0.]])
    np.testing.assert_allclose(prepare(masses)(positions@rotation.T, velocity@rotation.T),
                               force@rotation.T, rtol=5e-13, atol=0.)
    np.testing.assert_allclose(prepare(masses[::-1])(positions[::-1], velocity[::-1]), force[::-1], rtol=5e-13, atol=0.)
    assert bits(prepare(masses)(positions, velocity*1000)) == bits(force)


@pytest.mark.parametrize('epsilon', [1e-9, 1e-11])
def test_native_full_force_inclined_circle(library, epsilon):
    request, expected = circle()
    actual, stats, _ = coupling.trajectory(request, library, epsilon, 'analytic-circle', 'native')
    assert np.max(np.linalg.norm(actual[:, :, :3]-expected[:, :, :3], axis=2)) < .1
    assert np.max(np.linalg.norm(actual[:, :, 3:]-expected[:, :, 3:], axis=2)) < 1e-6
    assert stats['gravity'] == 'none' and not stats['velocity_dependent'] and stats['force_evaluations'] > 0
    assert bits(actual[0]) == bits(request['states'])


@pytest.mark.parametrize('failure', ['exception', 'nan', 'shape', 'interrupt'])
def test_callback_failures_rethrow_before_any_trajectory_is_returned(library, monkeypatch, capsys, failure):
    def bad(p, v, *args):
        if failure == 'exception':
            raise ValueError('injected native error')
        if failure == 'interrupt':
            raise KeyboardInterrupt('injected interruption')
        return np.full_like(p, np.nan) if failure == 'nan' else np.zeros(3)
    monkeypatch.setattr(coupling, 'prepare', lambda masses:bad)
    with pytest.raises(RuntimeError, match='no trajectory committed') as error:
        coupling.trajectory(circle()[0], library, 1e-9, 'negative-control', 'native')
    assert isinstance(error.value.__cause__, KeyboardInterrupt if failure == 'interrupt' else ValueError)
    assert 'Exception ignored' not in capsys.readouterr().err


def test_double_gravity_is_rejected_before_integration(library):
    request, _ = circle()
    sim = simulation(library, 0., request['masses'], request['states'], request['packet_dt'], 1e-9)
    sim.force_is_velocity_dependent = 0
    with pytest.raises(ArithmeticError, match='double gravity'):
        coupling.guard(sim, request['masses'], 1e-9, 'native')
    sim.gravity = 'none'
    coupling.guard(sim, request['masses'], 1e-9, 'native')
    assert sim.t == 0. and sim.steps_done == 0


def test_missing_real_native_is_an_error_without_fallback(library, monkeypatch):
    def missing():
        raise RuntimeError('real native unavailable')
    monkeypatch.setattr(coupling, 'require_native', missing)
    with pytest.raises(RuntimeError, match='native unavailable'):
        coupling.trajectory(circle()[0], library, 1e-9, 'negative-control', 'native')
