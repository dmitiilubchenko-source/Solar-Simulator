"""The quarter endpoint must never become an observation three hours later."""
import numpy as np
import pytest

from scripts.assess_edited_solar_prefix import matching_indices, reference_metrics, same_bits, run
from scripts.assess_edited_solar_year import epoch_grid as annual
from scripts.assess_edited_solar_quarter import epoch_grid as quarter


def test_regular_overlap_preserves_all_quarter_epochs_exactly():
    common, a, q = matching_indices(annual('regular'), quarter('regular'), 'regular')
    assert len(common) == 361 and common[-1] == 7776000.
    np.testing.assert_array_equal(annual('regular')[a], quarter('regular')[q])


def test_shifted_overlap_omits_the_forced_endpoint_instead_of_using_searchsorted():
    y, p = annual('shifted'), quarter('shifted')
    common, a, q = matching_indices(y, p, 'shifted')
    assert len(common) == 361 and common[-1] == 7765200.
    np.testing.assert_array_equal(common, p[:-1])
    np.testing.assert_array_equal(y[a], p[q])
    assert y[np.searchsorted(y, p[-1])] == p[-1] + 10800.
    assert p[-1] not in common


@pytest.mark.parametrize('which', ('annual', 'quarter'))
def test_a_missing_or_changed_epoch_cannot_silently_change_the_comparison(which):
    y, p = annual('regular'), quarter('regular')
    if which == 'annual':
        y = np.delete(y, 17)
    else:
        p[-1] += 10800.
    with pytest.raises(AssertionError):
        matching_indices(y, p, 'regular')


def test_reference_gate_checks_lunar_relative_and_outer_body_errors_separately():
    expected = np.zeros((2, 10, 6))
    actual = expected.copy()
    actual[-1, 4, 0] = .011
    assert not reference_metrics(actual, expected)['checks_passed']
    actual[-1, 4, 0] = .001
    assert reference_metrics(actual, expected)['checks_passed']
    actual[-1, 9, 0] = 1.1
    assert not reference_metrics(actual, expected)['checks_passed']


def test_numeric_zero_equality_is_not_reported_as_bitwise_identity():
    a, b = np.zeros((1,10,6)), np.zeros((1,10,6))
    b[0,0,0] = -0.
    assert np.array_equal(a,b) and not same_bits(a,b)
    assert same_bits(a,a.copy())


def test_existing_prefix_evidence_is_preserved_before_loading_inputs(monkeypatch, tmp_path):
    from scripts import assess_edited_solar_prefix as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    path = tmp_path / '.tools' / 'kept'
    path.parent.mkdir()
    path.with_suffix('.json').write_text('prior failure', encoding='utf-8')
    with pytest.raises(ValueError, match='fresh output'):
        run(path, 'unused', 'unused', 'unused', 'unused')
    assert path.with_suffix('.json').read_text(encoding='utf-8') == 'prior failure'
