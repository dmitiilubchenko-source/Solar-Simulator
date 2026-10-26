from dataclasses import replace

import numpy as np
import pytest

import scripts.native_newton_year as module
from scripts.assess_sandbox_planets import states
from scripts.ias15_restart import bits
from scripts.native_newton_year import force_metrics, trajectory
from scripts.newton_year import DAY, errors, ias_trajectory, inputs
from scripts.newton_year_cache import load, current_source_changes
from solar_simulator.native_forces import prepare
from test_newton_year import library, triangle


@pytest.mark.parametrize('epsilon', [1e-9, 1e-11])
@pytest.mark.parametrize('mode', ['basic', 'native'])
def test_both_force_modes_against_inclined_analytic_three_body_orbit(library, epsilon, mode):
    seed, rate, u, v = triangle()
    times = np.linspace(0, 2*np.pi/rate, 25)
    values, stats, _ = trajectory(seed, times, library, epsilon, mode)
    expected = []
    for time in times:
        angles = np.arange(3)*2*np.pi/3+rate*time
        expected.append([np.r_[6e7*(np.cos(a)*u+np.sin(a)*v),
            6e7*rate*(-np.sin(a)*u+np.cos(a)*v)] for a in angles])
    measured = errors(values, np.asarray(expected))
    assert measured['position_metres'] < .001 and measured['velocity_m_per_s'] < 1e-7
    assert stats['simulations'] == 1


def test_ten_body_force_against_decimal_potential_gradient_and_symmetries():
    seed, _ = inputs()
    q, masses = states(seed.bodies), np.array([b.mass for b in seed.bodies])
    actual = prepare(masses)(q[:, :3], q[:, 3:], None, None)
    assert force_metrics(masses, q[:, :3], actual)['checks_passed']
    assert not force_metrics(masses, q[:, :3], actual*2)['checks_passed']
    scale = np.linalg.norm(masses[:, None]*actual)
    assert np.linalg.norm(np.sum(masses[:, None]*actual, axis=0))/scale < 5e-13
    rotation = np.array([[0., -1., 0.], [0., 0., -1.], [1., 0., 0.]])
    rotated = prepare(masses)(q[:, :3]@rotation.T, q[:, 3:]@rotation.T)
    np.testing.assert_allclose(rotated, actual@rotation.T, rtol=5e-13, atol=1e-18)
    reversed_force = prepare(masses[::-1])(q[::-1, :3], q[::-1, 3:])
    np.testing.assert_allclose(reversed_force, actual[::-1], rtol=5e-13, atol=1e-18)


@pytest.mark.parametrize('epsilon', [1e-9, 1e-11])
def test_exact_fractional_packets_and_c_control_match_previous_implementation(library, epsilon):
    seed, _ = inputs()
    times = np.array([0., 72000., 86400.125])
    old, old_stats = ias_trajectory(seed, times, library, epsilon, count_forces=True)
    for mode in ('basic', 'native'):
        q, stats, arrays = trajectory(seed, times, library, epsilon, mode, counted=True)
        assert bits(q[0]) == bits(states(seed.bodies))
        assert arrays['packet_endpoints'].tolist() == [0., 72000., 86400.125]
        if mode == 'basic':
            assert bits(q) == bits(old)
            assert all(stats[k] == old_stats[k] for k in ('steps_done', 'packets', 'force_evaluations'))
        else:
            assert errors(q, old)['position_metres'] < .1


@pytest.mark.parametrize('failure', ['exception', 'nan', 'shape', 'interrupt'])
def test_callback_failure_is_rethrown_before_returning_a_trajectory(library, monkeypatch, capsys, failure):
    seed, _ = inputs()
    def bad(p, v, *args):
        if failure == 'exception':
            raise ValueError('native injection')
        if failure == 'interrupt':
            raise KeyboardInterrupt('native injection')
        return np.full_like(p, np.nan) if failure == 'nan' else np.zeros(3)
    monkeypatch.setattr(module, 'prepare', lambda masses:bad)
    with pytest.raises(RuntimeError, match='no trajectory committed') as error:
        trajectory(seed, [0., DAY], library, 1e-9, 'native')
    assert isinstance(error.value.__cause__, KeyboardInterrupt if failure == 'interrupt' else ValueError)
    assert 'Exception ignored' not in capsys.readouterr().err


def test_double_gravity_is_rejected_before_integrating(library, monkeypatch):
    original = module.guard
    def changed(sim, *args):
        sim.gravity = 'basic'
        original(sim, *args)
    monkeypatch.setattr(module, 'guard', changed)
    with pytest.raises(ArithmeticError, match='double gravity'):
        trajectory(inputs()[0], [0., DAY], library, 1e-9, 'native')


def test_cached_reference_has_exact_inputs_narrow_bindings_and_retains_wide_mismatch():
    seed, profiles, qualifications, receipt = load()
    assert len(profiles['pilot']['times']) == 61 and len(profiles['year']['times']) == 125
    assert bits(states(seed.bodies)) == bits(profiles['year']['initial'])
    for row in qualifications.values():
        assert row['reference_passed'] and not row['historical_runtime_requalified']
        assert 'historical_wide_source_changes' not in row
    changes = current_source_changes(receipt)
    assert all('src/solar_simulator/simulation.py' in names for names in changes.values())


def test_missing_native_and_unsupported_model_are_explicit(library, monkeypatch):
    def missing():
        raise RuntimeError('native unavailable')
    seed, _ = inputs()
    monkeypatch.setattr(module, 'require_native', missing)
    with pytest.raises(RuntimeError, match='native unavailable'):
        trajectory(seed, [0., DAY], library, 1e-9, 'native')
    with pytest.raises(ValueError, match='Newtonian'):
        trajectory(replace(seed, settings=replace(seed.settings, physics='eih-1pn')), [0., DAY], library, 1e-9, 'basic')


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_existing_audit_is_preserved_before_loading_any_dependency(tmp_path, suffix):
    from scripts.assess_native_newton_year import run
    output = tmp_path/'result.json'
    output.with_suffix(suffix).write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output, tmp_path, tmp_path)
    assert output.with_suffix(suffix).read_bytes() == b'keep'
