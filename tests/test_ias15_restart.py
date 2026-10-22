from decimal import Decimal as D, localcontext
import hashlib
import json
from math import pi, sqrt
from pathlib import Path

import numpy as np
import pytest

from scripts.ias15_reference import load_library, ias_trajectory
from scripts.ias15_restart import MODES, bits, checkpoint, restore, trajectory, validate
from solar_simulator.experiment import Settings, create_experiment
from solar_simulator.simulation import Body, G
from solar_simulator.vector3 import Vector3


@pytest.fixture
def library():
    path = Path(__file__).resolve().parents[1]/'.tools/ias15165/dependency'
    if path.is_dir():
        return load_library(path)
    pytest.importorskip('rebound', reason='Optional isolated IAS15 research package is absent')
    return load_library()


def circle():
    mass, radius = 1e20, 1e7
    omega = sqrt(2*G*mass/radius**3)
    period = 2*pi/omega
    initial = np.array([[-radius/2, 0., 0., 0., -.3*radius*omega, -.4*radius*omega],
                        [radius/2, 0., 0., 0., .3*radius*omega, .4*radius*omega]])
    return np.array([mass, mass]), initial, np.array([0., period/4, period/2, period, 2*period]), period/50, omega


@pytest.mark.parametrize('mode', MODES)
@pytest.mark.parametrize('epsilon', [1e-9, 1e-11])
def test_tilted_circle_all_restarts_against_independent_quarter_orbits(library, mode, epsilon):
    masses, initial, times, dt, omega = circle()
    values, stats, saved = trajectory(masses, initial, times, dt, library, epsilon, mode, 'analytic-circle')
    for time, row in zip(times, values):
        c, s = np.cos(omega*time), np.sin(omega*time)
        position = 1e7*np.array([c, .6*s, .8*s])
        velocity = 1e7*omega*np.array([-s, .6*c, .8*c])
        relative = row[1]-row[0]
        assert np.linalg.norm(relative[:3]-position) < 1e-3
        assert np.linalg.norm(relative[3:]-velocity) < 1e-8
    assert bits(values[0]) == bits(initial)
    assert saved['packet_endpoints'][-1] == times[-1]
    assert stats['simulations'] == (1 if mode == 'warm' else 2 if mode == 'one-cold' else stats['packets'])
    for text, digest, time, state in zip(saved['checkpoint_json'], saved['checkpoint_sha256'],
                                         saved['packet_endpoints'], saved['packet_states']):
        clock, mass, q = restore(str(text), str(digest), 'analytic-circle')
        assert clock == time and bits(mass) == bits(masses) and bits(q) == bits(state)


def test_warm_matches_old_stand_and_counted_repeats_preserve_all_physical_bits(library):
    masses, initial, times, dt, _ = circle()
    bodies = [Body(str(i), float(m), Vector3(*q[:3]), Vector3(*q[3:])) for i, (m, q) in enumerate(zip(masses, initial))]
    seed = create_experiment(bodies, Settings(dt, backend='rust', integrator='dop853'))
    old, old_stats = ias_trajectory(seed, times, library, 1e-9)
    warm = trajectory(masses, initial, times, dt, library, 1e-9, 'warm', 'circle')
    assert bits(old) == bits(warm[0])
    assert old_stats['packet_endpoints'] == warm[2]['packet_endpoints'][1:].tolist()
    for mode in MODES:
        a = trajectory(masses, initial, times, dt, library, 1e-9, mode, 'circle')
        b = trajectory(masses, initial, times, dt, library, 1e-9, mode, 'circle', count_forces=True)
        assert bits(a[0]) == bits(b[0]) and a[1]['steps_done'] == b[1]['steps_done']
        assert b[1]['force_evaluations'] > 0
        for key in a[2]:
            assert np.array_equal(a[2][key], b[2][key])
    cold = trajectory(masses, initial, times, dt, library, 1e-9, 'one-cold', 'circle')
    stop = cold[1]['restart_output_index']
    assert bits(cold[0][:stop+1]) == bits(warm[0][:stop+1])


def test_checkpoint_preserves_signed_zero_and_rejects_corruption_without_mutating_inputs():
    masses, initial, _, _, _ = circle()
    initial[0, 1] = -0.
    saved = initial.copy()
    raw, digest = checkpoint(3.125, masses, initial, 'input-sha')
    time, m, q = restore(raw, digest, 'input-sha')
    assert time == 3.125 and bits(q) == bits(saved) and bits(m) == bits(masses)
    q[:] = 0
    assert bits(initial) == bits(saved)
    for field in ('states', 'masses'):
        changed = json.loads(raw)
        if field == 'states':
            changed[field][0][3] += 1.
        else:
            changed[field][0] *= 2
        damaged = json.dumps(changed)
        with pytest.raises(ValueError, match='SHA'):
            restore(damaged, digest, 'input-sha')
    with pytest.raises(ValueError, match='origin'):
        restore(raw, digest, 'different-input')
    changed = json.loads(raw)
    changed['model'] = 'eih-1pn'
    damaged = json.dumps(changed)
    with pytest.raises(ValueError, match='model'):
        restore(damaged, hashlib.sha256(damaged.encode()).hexdigest(), 'input-sha')


@pytest.mark.parametrize('times', [[0., 0., 1.], [1., 2.], [0., float('nan')], [0., -1.]])
def test_invalid_epoch_grids(times):
    masses, initial, _, dt, _ = circle()
    with pytest.raises(ValueError, match='epoch grid'):
        validate(masses, initial, times, dt, 1e-9, 'warm')


@pytest.mark.parametrize('dt,epsilon,mode', [(0., 1e-9, 'warm'), (1., 1e-8, 'warm'), (1., 1e-9, 'other')])
def test_undeclared_parameters_are_rejected(dt, epsilon, mode):
    masses, initial, times, _, _ = circle()
    with pytest.raises(ValueError, match='Undeclared'):
        validate(masses, initial, times, dt, epsilon, mode)


def test_fractional_endpoint_and_no_progress_guard(library):
    masses, initial, _, _, _ = circle()
    values, _, saved = trajectory(masses, initial, [0., 3.125], 10., library, 1e-9, 'warm', 'fractional')
    assert saved['packet_endpoints'].tolist() == [0., 3.125] and np.isfinite(values).all()
    # A huge finite target with a sub-ULP interval cannot move from a large clock.
    from scripts.ias15_reference import packet_end
    with pytest.raises(ValueError, match='advance'):
        packet_end(1e20, 1e20+1e6, 1.)


def test_nonfinite_and_wrong_shape_physical_states_are_rejected():
    masses, initial, _, _, _ = circle()
    for m, q in (([1., -1.], initial), (masses, [[1.]]), (masses, initial*np.nan)):
        with pytest.raises(ValueError):
            checkpoint(0., m, q, 'origin')


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_previous_audit_outputs_are_preserved(tmp_path, suffix):
    from scripts.assess_ias15_restart import run
    output = tmp_path/'result.json'
    saved = output.with_suffix(suffix)
    saved.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        run(output, tmp_path)
    assert saved.read_bytes() == b'keep'


def test_public_requests_and_original_oracles_are_bound():
    from scripts.assess_ias15_restart import load_cases
    cases, bindings = load_cases()
    assert len(cases) == 9 and len(bindings) == 6
    assert sorted(len(case['times']) for case in cases.values()) == [60]*3+[82]*6
    for case in cases.values():
        assert bits(case['initial']) == bits(case['request']['states'])
        assert case['oracle_uncertainty']['position_metres'] < 1e-6


def test_restarted_oracle_and_inherited_error_have_independent_circular_limit(library):
    from scripts.assess_ias15_restart import restart_oracle, compare
    masses, initial, times, dt, omega = circle()
    values, _, _ = trajectory(masses, initial, times, dt, library, 1e-9, 'one-cold', 'oracle')
    index = 3  # first epoch >= half of the two-period horizon
    oracle, uncertainty = restart_oracle(values[index], masses, times[index:], times[index])
    assert uncertainty['position_metres'] < 1e-6 and uncertainty['velocity_m_per_s'] < 1e-12
    for time, row in zip(times[index:], oracle[100]):
        expected = 1e7*np.array([np.cos(omega*time), .6*np.sin(omega*time), .8*np.sin(omega*time)])
        assert np.linalg.norm(np.asarray(row[:3], dtype=float)-expected) < 1e-3
    assert compare(values[index:], oracle[100], times[index:])['position_metres'] < 1e-3
