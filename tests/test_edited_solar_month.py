"""Reject misleading refinement and grid comparisons before costly trajectories."""
import numpy as np
import pytest

from scripts.assess_edited_solar_month import (epoch_grid, reference_gate,
    candidate_metrics, endpoint_comparison, packet_check, finite_states, run,
    check_same_experiment)


def test_declared_grids_have_distinct_interiors_and_identical_endpoints():
    a, b = epoch_grid('regular'), epoch_grid('shifted')
    assert len(a) == 121 and len(b) == 122
    np.testing.assert_array_equal(np.intersect1d(a, b), [0., 2592000.])
    assert np.all(np.diff(a) == 21600.)
    assert b[1] == 10800. and b[-2] == 2581200.
    assert np.all(np.diff(b) > 0) and np.max(np.diff(b)) == 21600.
    with pytest.raises(ValueError, match='Undeclared'):
        epoch_grid('tuned')


@pytest.mark.parametrize('calls', ([10, 20, 20], [20, 20, 40], [10, 20], [10, 20, 40, 80]))
def test_identical_or_incomplete_rhs_refinement_cannot_qualify(calls):
    zero = dict(position_metres=0., velocity_m_per_s=0.)
    comparison = dict(all_bodies=zero, moon_relative_to_earth=zero)
    assert not reference_gate(comparison, comparison, calls, dict(checks_passed=True))
    assert reference_gate(comparison, comparison, [10, 20, 40], dict(checks_passed=True))


def test_single_body_or_moon_relative_failure_cannot_be_hidden_by_averaging():
    expected = np.zeros((2, 10, 6))
    actual = expected.copy()
    actual[1, 9, 0] = 10.
    assert not candidate_metrics(actual, expected)['checks_passed']
    actual[:] = 0.
    actual[1, 4, 0] = .11
    assert not candidate_metrics(actual, expected)['checks_passed']
    actual[1, 4, 0] = .01
    assert candidate_metrics(actual, expected)['checks_passed']


def test_endpoint_comparison_uses_only_common_physical_epochs():
    a, b = np.zeros((121, 10, 6)), np.zeros((122, 10, 6))
    a[1:-1] = 1e8
    b[-1, 4, 0] = .05
    result = endpoint_comparison(a, b)
    assert result['all_bodies']['position_metres'] == .05
    assert result['moon_relative_to_earth']['position_metres'] == .05


def test_actual_settings_compare_after_json_without_accepting_parameter_changes():
    from dataclasses import asdict
    import json
    from scripts.assess_edited_solar import fixture
    from scripts.edited_j2 import verify_branch
    parent, branch, _ = fixture('sun_mass')
    row = dict(settings=asdict(branch.child.settings), provenance=verify_branch(parent, branch),
        masses_kg=[b.mass for b in branch.child.bodies], names=[b.name for b in branch.child.bodies])
    stored = json.loads(json.dumps(row))
    assert row['settings'] != stored['settings']  # Reproduces the former false rejection.
    check_same_experiment(row, stored)
    for key in row:
        changed = json.loads(json.dumps(stored))
        if key == 'settings':
            changed[key]['rtol'] *= 2.
        elif key == 'provenance':
            changed[key]['child_checkpoint_sha256'] = 'changed'
        elif key == 'masses_kg':
            changed[key][0] *= 2.
        else:
            changed[key][0] = 'Different star'
        with pytest.raises(ValueError, match=key):
            check_same_experiment(row, changed)


@pytest.mark.parametrize('bounds', ([2., 1., 3.], [1., 2.], [1., 1., 3.], [3.]))
def test_packet_guard_rejects_missing_duplicate_or_unordered_epochs(bounds):
    with pytest.raises(ValueError, match='packet/output'):
        packet_check(dict(packet_endpoints=bounds, finished=True, failed=False), np.array([0., 1., 2., 3.]))


def test_nonfinite_states_and_existing_receipts_are_rejected(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='Nonfinite'):
        finite_states(np.full((2, 10, 6), np.nan), [0., 1.])
    from scripts import assess_edited_solar_month as module
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    path = tmp_path / '.tools' / 'saved'
    path.parent.mkdir()
    path.with_suffix('.json').write_text('prior failure', encoding='utf-8')
    with pytest.raises(ValueError, match='fresh'):
        run(path, 'regular')
    assert path.with_suffix('.json').read_text(encoding='utf-8') == 'prior failure'
