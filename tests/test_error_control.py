"""Analytic oscillators expose dilution without a shared numerical reference."""
from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from solar_simulator.accuracy import evolve_accurate
from solar_simulator.error_control import PerBodyDOP853
from solar_simulator.experiment import Settings, advance, create_experiment, preset
from solar_simulator.storage import SCHEMA_VERSION, from_document, load, save, to_document


def oscillator(count, method, *, work=False, first_step=.1):
    initial = np.zeros(6*count + int(work))
    initial[:3] = [.8, .6, 0.]
    initial[3*count:3*count+3] = [-.6, .8, 0.]
    def rhs(time, state):
        derivative = np.zeros_like(state)
        derivative[:3*count] = state[3*count:6*count]
        derivative[3*count:6*count] = -state[:3*count]
        if work:
            derivative[-1] = 60*np.cos(60*time)
        return derivative
    times = np.linspace(0., 2. if work else 20*np.pi, 251)
    result = solve_ivp(rhs, (0., times[-1]), initial, method=method, first_step=first_step,
                       rtol=1e-10, atol=1e-12, t_eval=times)
    assert result.success
    expected = np.array([.8*np.cos(times)-.6*np.sin(times),
                         .6*np.cos(times)+.8*np.sin(times), np.zeros_like(times)])
    error = np.max(np.linalg.norm(result.y[:3]-expected, axis=0))
    return result, float(error)


def test_analytic_orbit_accuracy_does_not_dilute_with_inactive_bodies():
    results = [oscillator(n, PerBodyDOP853) for n in (2, 27, 354)]
    assert max(error for _, error in results) < 1e-8
    # Unchanged active equations and first step retain the same acceptance
    # behavior; allow floating-point noise in BLAS without pinning stage data.
    calls = [result.nfev for result, _ in results]
    assert max(calls) <= 1.05*min(calls)
    assert max(error for _, error in results) <= 1.05*min(error for _, error in results)


@pytest.mark.parametrize("count", [2, 27, 354])
def test_automatic_initial_step_keeps_analytic_accuracy(count):
    _, error = oscillator(count, PerBodyDOP853, first_step=None)
    assert error < 1e-8


@pytest.mark.parametrize("count", [2, 354])
def test_scalar_orientation_work_cannot_hide_among_orbit_equations(count):
    result, error = oscillator(count, PerBodyDOP853, work=True)
    assert error < 1e-10
    assert np.max(np.abs(result.y[-1]-np.sin(60*result.t))) < 1e-9


def test_zero_rhs_and_backward_integration():
    stationary = solve_ivp(lambda t, y: np.zeros_like(y), (0., 10.), np.ones(13), method=PerBodyDOP853)
    assert stationary.success and np.array_equal(stationary.y[:, -1], np.ones(13))
    def rhs(t, y):
        return np.concatenate((y[3:], -y[:3]))
    initial = np.array([1., 0., 0., 0., 1., 0.])
    result = solve_ivp(rhs, (0., -2*np.pi), initial, method=PerBodyDOP853, rtol=1e-11, atol=1e-13)
    assert result.success and np.linalg.norm(result.y[:, -1]-initial) < 1e-9


@pytest.mark.parametrize("slot", [0, 6])
def test_nonfinite_estimate_including_work_is_rejected(slot):
    solver = PerBodyDOP853(lambda t,y:np.zeros_like(y), 0., np.ones(7), 1.)
    stages = np.zeros_like(solver.K)
    stages[0, slot] = np.nan
    with pytest.raises(ValueError, match="Неконечная оценка"):
        solver._estimate_error_norm(stages, 1., np.ones(7))


@pytest.mark.parametrize("size", [0, 1, 5, 8, 14])
def test_invalid_orbit_layout_is_rejected(size):
    with pytest.raises(ValueError, match="6N"):
        PerBodyDOP853(lambda t,y:y, 0., np.ones(size), 1.)


@pytest.mark.parametrize("value", [None, True, [], {}, "unknown", "PER-BODY"])
def test_invalid_control_rejected_in_settings_and_direct_api(value):
    with pytest.raises(ValueError, match="Контроль ошибки"):
        Settings(1., error_control=value)
    with pytest.raises(ValueError, match="Контроль ошибки"):
        evolve_accurate(preset('sun-earth').bodies, 1., error_control=value)


@pytest.mark.parametrize("control", ["per-body", "global-rms"])
@pytest.mark.parametrize("backend", ["python", "rust"])
def test_cli_and_checkpoint_preserve_control_and_resume(tmp_path, capsys, control, backend):
    if backend == "rust":
        pytest.importorskip("solar_native")
    from solar_simulator.cli import main
    path = tmp_path/'initial.json'
    assert main(['new', 'sun-earth', str(path), '--backend', backend, '--integrator', 'dop853',
                 '--error-control', control, '--dt', '3600']) == 0
    import json
    assert json.loads(capsys.readouterr().out)['error_control'] == control
    initial = load(path)
    assert initial.settings.error_control == control
    partial = advance(initial, 24)
    save(partial, tmp_path/'partial.json')
    restored = load(tmp_path/'partial.json')
    assert restored.settings == partial.settings
    assert to_document(restored)['schema_version'] == SCHEMA_VERSION
    whole, resumed = advance(initial, 48), advance(restored, 24)
    assert resumed.time == whole.time
    for a,b in zip(resumed.bodies, whole.bodies):
        assert a.position.distance_to(b.position) < .01
        assert a.velocity.distance_to(b.velocity) < 1e-7


def test_v8_migration_retains_original_global_solver_without_mutation():
    initial = preset('solar-system-moon')
    initial = create_experiment(initial.bodies, replace(initial.settings, error_control='global-rms',
                                                       relative_pair=('Earth','Moon')), origin=initial.origin)
    partial = advance(initial, 4)
    document = to_document(partial)
    document['schema_version'] = 8
    del document['settings']['error_control']
    before = deepcopy(document)
    restored = from_document(document)
    assert restored.settings.error_control == 'global-rms' and document == before
    assert to_document(advance(restored, 4)) == to_document(advance(partial, 4))


def test_old_schema_does_not_accept_future_error_control_field():
    document = to_document(preset('sun-earth'))
    document['schema_version'] = 8
    with pytest.raises(ValueError):
        from_document(document)
