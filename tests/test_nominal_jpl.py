"""Time/provenance controls; tests never need network access."""
from fractions import Fraction
import json
from urllib.parse import parse_qs, urlsplit

import numpy as np
import pytest

from scripts import nominal_jpl as module


def payload():
    return dict(signature=dict(source='NASA/JPL Horizons API', version='1.2'), result='''
Target body name: Earth (399) {source: DE441}
Center body name: Solar System Barycenter (0)
Output units    : KM-S
GEOMETRIC cartesian states
Ecliptic of J2000.0
JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ,
$$SOE
2461322.333333333, A.D. 2026-Oct-08 20:00:00.0000,1,2,3,4,5,6,
$$EOE
''')


def test_fractional_day_roundtrip_is_measured_without_float_cancellation():
    row = module.parse_vectors(payload(), 399, [72000])[0]
    assert row['jd_offset_seconds'] == -0.0000288
    assert row['calendar_offset_seconds'] == 0
    assert row['position'] == [1000, 2000, 3000]
    assert abs((Fraction(module.jd_text(72000))-module.EPOCH)*86400-72000) < Fraction(1, 10**9)
    assert module.calendar_seconds('A.D. 2027-Oct-08 06:00:00.0000') == 31557600


@pytest.mark.parametrize('old,new', [
    ('20:00:00.0000', '20:00:00.0002'),
    ('2461322.333333333', '2461322.333333335'),
    ('Calendar Date (TDB)', 'Calendar Date (UT)'),
    ('Earth (399)', 'Moon (301)'), ('KM-S', 'AU-D'), ('DE441', 'DE440')])
def test_shifted_time_or_wrong_scientific_metadata_is_rejected(old, new):
    data = payload()
    data['result'] = data['result'].replace(old, new)
    with pytest.raises(ValueError):
        module.parse_vectors(data, 399, [72000])


def test_missing_duplicate_or_reordered_epochs_cannot_pass():
    for times in ([0, 72000], [72000, 72000], [72000, 0]):
        with pytest.raises(ValueError):
            module.parse_vectors(payload(), 399, times)


@pytest.mark.parametrize('times', [[], [-1], [float('nan')], [.5], [31557601]])
def test_invalid_nominal_seconds_are_rejected(times):
    with pytest.raises(ValueError):
        module.seconds_grid(times)


def test_urls_use_explicit_tdb_and_no_conflicting_time_inputs():
    regular = parse_qs(urlsplit(module.request_url(399, [0, 72000], 'regular')).query)
    listed = parse_qs(urlsplit(module.request_url(399, [72000], 'jd')).query)
    assert regular['TIME_TYPE'] == ["'TDB'"] and regular['STEP_SIZE'] == ["'20h'"]
    assert regular['TIME_DIGITS'] == ["'FRACSEC'"] and 'TLIST' not in regular
    assert listed['TLIST_TYPE'] == ["'JD'"] and 'STEP_SIZE' not in listed
    assert listed['TLIST'] == ["'2461322.333333333333333'"]
    with pytest.raises(ValueError):
        module.request_url(399, [0, 72001], 'regular')


def test_cached_response_never_fetches_and_rejects_url_or_hash_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'fetch', lambda url: json.dumps(payload()).encode())
    path = tmp_path/'raw.json'
    rows, record = module.response(path, 399, [72000], 'jd')
    monkeypatch.setattr(module, 'fetch', lambda url: pytest.fail('Offline mode fetched network'))
    assert module.response(path, 399, [72000], 'jd', cached=True) == (rows, record)
    with pytest.raises(FileNotFoundError):
        module.response(tmp_path/'missing.json', 399, [72000], 'jd', cached=True)
    with pytest.raises(ValueError, match='URL changed'):
        module.response(path, 301, [72000], 'jd', cached=True)
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError, match='SHA or URL'):
        module.response(path, 399, [72000], 'jd', cached=True)


def test_bad_download_is_kept_and_cannot_be_replaced_silently(tmp_path, monkeypatch):
    raw = b'{"error":"test failure"}'
    monkeypatch.setattr(module, 'fetch', lambda url: raw)
    path = tmp_path/'bad.json'
    with pytest.raises(ValueError):
        module.response(path, 399, [72000], 'jd')
    assert path.read_bytes() == raw and path.with_suffix('.request.json').exists()
    monkeypatch.setattr(module, 'fetch', lambda url: pytest.fail('Must preserve existing failure'))
    with pytest.raises(ValueError):
        module.response(path, 399, [72000], 'jd')


def test_transport_failure_is_recorded_with_request(tmp_path, monkeypatch):
    def failed(url):
        raise RuntimeError('network unavailable')
    monkeypatch.setattr(module, 'fetch', failed)
    path = tmp_path/'failed.json'
    with pytest.raises(RuntimeError, match='network unavailable'):
        module.response(path, 399, [72000], 'jd')
    assert json.loads(path.with_suffix('.failure.json').read_bytes())['url'].startswith('https://ssd.jpl.nasa.gov/')
    assert not path.exists()
