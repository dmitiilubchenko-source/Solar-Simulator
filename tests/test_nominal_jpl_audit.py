"""Independent corruption/threshold controls for public frozen JPL440 evidence."""
from copy import deepcopy
import json

import numpy as np
import pytest

from scripts import assess_nominal_jpl as module
from scripts import fetch_nominal_jpl
from scripts.fixed_j2_year import inputs


@pytest.fixture(scope='module')
def evidence():
    return module.load_archive(module.ROOT/module.ARCHIVE)


def test_frozen_payload_and_raw_data_qualify_without_network_or_propagation(evidence, monkeypatch):
    from scripts import nominal_jpl
    monkeypatch.setattr(nominal_jpl, 'fetch', lambda url: pytest.fail('Offline audit used network'))
    seed, prior, *_ = inputs()
    values, receipt = module.validate_frozen(evidence, seed)
    expected, timing = module.validate_data(evidence, seed, prior)
    assert values['times'].shape == (440,) and expected.shape == (440, 10, 6)
    assert receipt['reference_passed'] and timing['maximum_calendar_offset_seconds'] == 0.
    assert timing['maximum_jd_offset_seconds'] <= .0001
    assert module.validate_probe(evidence)['Moon-Earth']['position_metres'] < .2


def test_historical_plot_snapshot_is_verified_by_its_original_bytes(tmp_path,monkeypatch):
    name='src/solar_simulator/plot_artists.py'
    snapshot,expected=module.SOURCE_FILE_SNAPSHOTS[name]
    original=(module.ROOT/snapshot).read_bytes()
    assert module.digest(original)==expected
    current=tmp_path/name;current.parent.mkdir(parents=True);current.write_bytes(b'new runtime bytes')
    frozen=tmp_path/snapshot;frozen.parent.mkdir(parents=True);frozen.write_bytes(original)
    monkeypatch.setattr(module,'ROOT',tmp_path)
    module.verify_frozen_sources({name:expected})
    frozen.write_bytes(original+b'changed')
    with pytest.raises(ValueError,match='Frozen source SHA mismatch'):
        module.verify_frozen_sources({name:expected})


def test_windows_receipt_paths_are_portable_with_posix_path_rules(evidence,monkeypatch):
    from pathlib import PurePosixPath
    seed,*_=inputs()
    before,receipt=module.validate_frozen(evidence,seed)
    monkeypatch.setattr(module,'Path',PurePosixPath)
    after,copy=module.validate_frozen(evidence,seed)
    assert receipt==copy and set(before)==set(after)
    assert all(before[name].tobytes()==after[name].tobytes() for name in before)


def test_archive_byte_tampering_is_rejected_before_parsing(tmp_path):
    raw = (module.ROOT/module.ARCHIVE).read_bytes()
    path = tmp_path/'altered.zip'
    path.write_bytes(raw+b'changed')
    with pytest.raises(ValueError, match='archive SHA'):
        module.load_archive(path)


@pytest.mark.parametrize('mutation', ['body', 'time', 'unit', 'incomplete', 'fit', 'missing_request'])
def test_reference_metadata_and_completeness_cannot_be_forged(evidence, mutation):
    files = evidence.copy()
    reference = json.loads(files['reference230.json'])
    if mutation == 'body':
        reference['bodies'][0]['id'] = 399
    elif mutation == 'time':
        reference['epochs_seconds'][1] += 1
    elif mutation == 'unit':
        reference['units'] = 'KM-S'
    elif mutation == 'incomplete':
        reference['complete'] = False
    elif mutation == 'fit':
        reference['physical_parameters_fitted'] = True
    else:
        reference['bodies'][0]['requests'].pop()
    files['reference230.json'] = json.dumps(reference).encode()
    seed, prior, *_ = inputs()
    with pytest.raises(ValueError):
        module.validate_data(files, seed, prior)


def test_raw_vectors_cannot_change_even_if_reference_looks_qualified(evidence):
    files = evidence.copy()
    files['raw/horizons-10-regular.json'] += b' '
    seed, prior, *_ = inputs()
    with pytest.raises(ValueError, match='SHA/request provenance'):
        module.validate_data(files, seed, prior)


def test_altered_nominal_npz_or_receipt_is_rejected_by_public_predecessor_pin(evidence):
    seed, *_ = inputs()
    for name in ('annual.json', 'annual.npz'):
        files = evidence.copy()
        files[name] += b' '
        with pytest.raises(ValueError, match='qualification/lineage'):
            module.validate_frozen(files, seed)


def test_failed_time_probe_is_not_overruled_by_valid_main_vectors(evidence):
    files = evidence.copy()
    probe = json.loads(files['probe229.json'])
    probe['checks_passed'] = False
    files['probe229.json'] = json.dumps(probe).encode()
    with pytest.raises(ValueError, match='probe did not qualify'):
        module.validate_probe(files)


def test_constant_velocity_timing_allowance_is_separate_from_raw_residual():
    expected = np.zeros((2, 10, 6))
    actual = expected.copy()
    actual[1, :, 0] = 9995.
    # Every body passes the raw10km criterion, but Sun fails after +10m.
    row = module.timed_residuals(actual, expected, [0., 72000.])
    assert row['physical_goals_passed'] and not row['timing_aware_goals_passed']
    assert row['jpl_residuals']['Sun']['position_metres'] == 9995.
    assert row['jpl_residuals']['Sun']['position_plus_timing_allowance_metres'] == 10005.
    actual[:] = 0.
    actual[1, 4, 0] = 999.9
    row = module.timed_residuals(actual, expected, [0., 72000.])
    assert row['physical_goals_passed'] and not row['timing_aware_goals_passed']
    assert row['moon_relative_jpl']['position_plus_timing_allowance_metres'] > 1000.


def test_jpl_success_does_not_replace_failed_numerical_or_missing_modes():
    reference = dict(timing_aware_goals_passed=True)
    good = {name: deepcopy(reference) for name in module.MODES}
    assert module.qualified(True, good, reference)
    assert not module.qualified(False, good, reference)
    missing = good.copy()
    del missing['legacy_python']
    assert not module.qualified(True, missing, reference)
    good['continuous_rust']['timing_aware_goals_passed'] = False
    assert not module.qualified(True, good, reference)


@pytest.mark.parametrize('function', ['fetch', 'assess'])
def test_old_failure_report_is_preserved_before_any_inputs(function, tmp_path, monkeypatch):
    target = fetch_nominal_jpl if function == 'fetch' else module
    monkeypatch.setattr(target, 'ROOT', tmp_path)
    output = tmp_path/'.tools'/'failed.json'
    output.parent.mkdir()
    output.write_bytes(b'previous failure')
    with pytest.raises(ValueError):
        if function == 'fetch':
            target.fetch_grid(output, tmp_path/'.tools/cache', cached=True)
        else:
            target.run(tmp_path/'unused.zip', output)
    assert output.read_bytes() == b'previous failure'
