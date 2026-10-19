"""Accounting/metric controls for model diagnostics, independent of chosen residuals."""
import numpy as np
import pytest

from scripts import assess_solar_defect as module


def test_declared_variants_replace_earth_field_without_double_counting_it():
    parts = {name:np.full((10, 3), float(2**i)) for i, name in enumerate(module.COMPONENTS)}
    result = module.compose(parts)
    assert set(result) == set(module.CASES)
    np.testing.assert_array_equal(result['strict'], np.full((10, 3), 15.))
    np.testing.assert_array_equal(result['earth_orientation'], np.full((10, 3), 23.))
    np.testing.assert_array_equal(result['earth_orientation_plus_moon'], np.full((10, 3), 55.))


@pytest.mark.parametrize('changed', ['missing', 'extra'])
def test_unexpected_component_inventory_is_rejected(changed):
    parts = {name:np.zeros((10, 3)) for name in module.COMPONENTS}
    if changed == 'missing': parts.pop('earth_fixed')
    else: parts['unapproved_force'] = np.zeros((10, 3))
    with pytest.raises(ValueError, match='all declared'):
        module.compose(parts)


def test_exact_zero_source_cannot_hide_spurious_nonzero_force_with_epsilon():
    expected = np.zeros((10, 3))
    assert module.relative_gap(expected, expected) == 0.
    actual = expected.copy()
    actual[0, 0] = 1e-100
    assert module.relative_gap(actual, expected) == float('inf')


@pytest.mark.parametrize('bad', [np.full((10, 3), np.nan), np.zeros((9, 3))])
def test_invalid_force_comparison_is_rejected(bad):
    with pytest.raises(ValueError):
        module.relative_gap(bad, np.zeros((10, 3)))


def test_vector_rms_and_worst_epoch_have_known_geometric_values():
    result = module.statistics(np.array([[0., 0., 0.], [3., 4., 0.], [0., 0., 0.]]), [0., 2., 5.])
    assert result['maximum_m_per_s2'] == 5. and result['worst_seconds'] == 2.
    assert result['initial_m_per_s2'] == result['final_m_per_s2'] == 0.
    assert result['rms_m_per_s2'] == pytest.approx(5/np.sqrt(3))


def test_previous_diagnostic_failure_is_preserved_before_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    output = tmp_path/'.tools/preserved'
    output.parent.mkdir()
    output.with_suffix('.npz').write_bytes(b'previous failure')
    with pytest.raises(ValueError, match='fresh'):
        module.run(output, 'unused')
    assert output.with_suffix('.npz').read_bytes() == b'previous failure'
