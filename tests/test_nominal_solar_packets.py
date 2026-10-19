"""Protect nominal provenance, exact epochs and independent qualification gates."""
from dataclasses import replace

import numpy as np
import pytest

from scripts.assess_nominal_solar_packets import versions, shared_epochs, scope_qualified, run
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.fixed_j2_year import inputs
from solar_simulator.storage import to_document


def test_force_backend_variants_preserve_nominal_calendar_and_initial_experiment():
    seed, *_ = inputs()
    before = to_document(seed)
    modes = versions(seed)
    assert to_document(modes['rust']) == before
    assert to_document(replace(modes['python'], settings=seed.settings)) == before
    assert modes['python'].settings.backend == 'python'
    assert modes['rust'].origin is not None and modes['python'].origin == seed.origin
    modes['rust'].bodies.clear()
    assert to_document(seed) == before and len(modes['python'].bodies) == 10


def test_only_exact_24_common_epochs_are_selected_without_adding_outputs():
    _, prior, *_ = inputs()
    packet = epoch_grid()
    before = packet.copy()
    common, a, b = shared_epochs(packet, prior)
    assert len(common) == 24 and len(a) == len(b) == 24
    np.testing.assert_array_equal(common, packet[a])
    np.testing.assert_array_equal(common, prior[b])
    np.testing.assert_array_equal(packet, before)
    assert len(packet) == 440 and common[-1] == 31557600.
    prior[-1] -= .001
    with pytest.raises(ValueError, match='exactly shared'):
        shared_epochs(packet, prior)


@pytest.mark.parametrize('key', ['checks_passed', 'physical_goals_passed'])
def test_io_or_jpl_success_cannot_replace_failed_numerical_reference_or_mode(key):
    rows = {name: dict(checks_passed=True, physical_goals_passed=True)
        for name in ('legacy_python', 'legacy_rust', 'continuous_rust')}
    assert scope_qualified(True, rows)
    assert not scope_qualified(False, rows)
    rows['legacy_python'][key] = False
    assert not scope_qualified(True, rows)
    del rows['legacy_python']
    assert not scope_qualified(True, rows)


def test_existing_failure_archive_is_preserved_before_loading_any_inputs(monkeypatch, tmp_path):
    from scripts import assess_nominal_solar_packets as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.chdir(tmp_path)
    output = tmp_path / '.tools' / 'kept'
    output.parent.mkdir()
    output.with_suffix('.npz').write_bytes(b'retained failure')
    with pytest.raises(ValueError, match='fresh output'):
        run(output, 'unused')
    assert output.with_suffix('.npz').read_bytes() == b'retained failure'
