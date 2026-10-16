"""Explicit epoch contracts and qualification boundaries of interval experiments."""
import copy
from pathlib import Path

import numpy as np
import pytest

from scripts.edited_solar_interval import validate_epochs, check_regular, cross_grid, run
from scripts.assess_edited_solar_quarter import epoch_grid


def test_quarter_grids_have_only_common_endpoints_and_do_not_change_month_grid():
    from scripts.assess_edited_solar_month import epoch_grid as month
    a, b = epoch_grid('regular'), epoch_grid('shifted')
    assert len(a) == 361 and len(b) == 362
    np.testing.assert_array_equal(np.intersect1d(a, b), [0., 7776000.])
    assert a[1] == 21600. and b[1] == 10800. and b[-2] == 7765200.
    assert month('regular')[-1] == 2592000. and len(month('regular')) == 121
    with pytest.raises(ValueError, match='Undeclared'):
        epoch_grid('best')


@pytest.mark.parametrize('times', ([1, 2, 3], [0, 1, 1], [0, 2, 1], [0, 1, np.nan],
    [0, 1, np.inf], [0, 1], [[0, 1, 2]]))
def test_bad_epoch_contract_is_rejected(times):
    with pytest.raises(ValueError, match='epochs'):
        validate_epochs(times)


def test_epoch_validation_takes_a_copy_and_preserves_each_exact_time():
    times = np.array([0., 7., 1234., 7776000.])
    checked = validate_epochs(times)
    np.testing.assert_array_equal(checked, times)
    times[1] = 8.
    assert checked[1] == 7.


@pytest.mark.parametrize('field', ('complete', 'checks_passed', 'grid', 'epochs_seconds',
    'source_sha256', 'input_sha256', 'dependency_sha256'))
def test_regular_receipt_rejects_wrong_horizon_sources_or_qualification(field):
    times = np.array([0., 1., 2.])
    report = dict(complete=True, checks_passed=True, grid='regular', epochs_seconds=times.tolist(),
        source_sha256={'source': 'a'}, input_sha256={'input': 'b'}, dependency_sha256={'binary': 'c'})
    check_regular(report, times, report['source_sha256'], report['input_sha256'], report['dependency_sha256'])
    changed = copy.deepcopy(report)
    changed[field] = False if field in ('complete', 'checks_passed') else ('shifted' if field == 'grid' else {})
    with pytest.raises(ValueError, match='regular receipt'):
        check_regular(changed, times, report['source_sha256'], report['input_sha256'], report['dependency_sha256'])


def test_cross_grid_checks_relative_moon_even_when_each_absolute_position_passes():
    old = {'case_' + key: np.zeros((3, 10, 6)) for key in ('mode', 'reference_2')}
    current = {key: value.copy() for key, value in old.items()}
    current['case_mode'][-1, 4, 0] = .11
    comparison, passed = cross_grid(current, old, 'case', ['mode'])
    assert comparison['mode']['all_bodies']['position_metres'] < 10. and not passed
    current['case_mode'][-1, 4, 0] = .01
    assert cross_grid(current, old, 'case', ['mode'])[1]


def test_grid_mismatch_is_rejected_before_writing_any_output(tmp_path):
    output = tmp_path / 'must-not-exist'
    with pytest.raises(ValueError, match='endpoint times'):
        run(output, times=[0., 1., 3.], grid='shifted', protocol='unused', driver_sources=(),
            regular_receipt=Path('unused'), regular_times=[0., 1., 2.])
    assert not output.with_suffix('.json').exists()


def test_saved_receipt_is_preserved_before_loading_dependencies(monkeypatch, tmp_path):
    from scripts import edited_solar_interval as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.chdir(tmp_path)
    output = tmp_path / '.tools' / 'preserved'
    output.parent.mkdir()
    output.with_suffix('.npz').write_bytes(b'previous failure evidence')
    with pytest.raises(ValueError, match='fresh output'):
        run(output, times=[0., 1., 2.], grid='regular', protocol='unused', driver_sources=())
    assert output.with_suffix('.npz').read_bytes() == b'previous failure evidence'
