"""Corruption controls for prefetching DE441; no network or local cache required."""
from pathlib import Path
import json

import pytest

from scripts import prefetch_physics_sources as module


def header():
    return b'''GROUP   1040
2 DENUM EMRAT
GROUP   1041
2 441 81.30057
GROUP   1050
3 0 0 0 0 0 0 0 0 0 0 0 0 0 0
14 0 0 0 0 0 0 0 0 0 0 0 0 0 0
4 0 0 0 0 0 0 0 0 0 0 0 0 0 0
GROUP   1070
'''


def record(number, count=1018, coefficient='0', shift=0):
    start = module.FIRST+(number-1)*32+shift
    text = f'{number} {count}\n{start} {start+32} {coefficient} '+'0 '*1015
    assert len(text) < module.STRIDE
    return text.encode('ascii').ljust(module.STRIDE, b' ')


@pytest.fixture(scope='module')
def records():
    return b''.join(record(n) for n in range(306, 421))


def test_full_predeclared_range_has_contiguous_finite_records_and_covers_ten_years(records):
    result = module.validate_records(records, header(), records[:13*module.STRIDE])
    assert result['records'] == 115
    assert result['raw_start_jd_tdb'] == 2461296.5
    assert result['raw_end_jd_tdb'] == 2464976.5
    assert result['intended_end_jd_tdb'] == 2464974.
    assert result['old_overlap_bitexact'] and not result['simulator_ten_year_accuracy_qualified']


@pytest.mark.parametrize('change', ['truncated', 'old_overlap', 'id', 'count', 'nan', 'epoch'])
def test_invalid_records_are_rejected_without_relaxing_range_or_epoch_contract(records, change):
    old = records[:13*module.STRIDE]
    if change == 'truncated':
        data = records[:-1]
    elif change == 'old_overlap':
        data = b'X'+records[1:]
    else:
        number = 320
        replacement = record(number+1) if change == 'id' else record(number,
            count=1017 if change == 'count' else 1018,
            coefficient='NaN' if change == 'nan' else '0', shift=1 if change == 'epoch' else 0)
        offset = (number-306)*module.STRIDE
        data = records[:offset]+replacement+records[offset+module.STRIDE:]
    with pytest.raises(ValueError):
        module.validate_records(data, header(), old)


def test_bad_pointer_layout_is_rejected(records):
    bad = header().replace(b'3 0 0', b'1000 0 0')
    with pytest.raises(ValueError, match='pointer'):
        module.validate_records(records, bad, records[:13*module.STRIDE])


def test_cached_mode_never_downloads_missing_data(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'download', lambda *a: pytest.fail('Cached mode used network'))
    with pytest.raises(FileNotFoundError):
        module.run(tmp_path/'.tools/missing', cached=True)


def test_source_reserve_tampering_is_detected_before_any_coefficient_use(tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps(dict(complete=True,
        source_sha256=module.sha(Path(module.__file__).read_bytes()),
        files=[dict(file='raw.txt', bytes=3, sha256='0'*64)])), encoding='utf-8')
    (tmp_path/'raw.txt').write_bytes(b'bad')
    with pytest.raises(ValueError, match='checksum changed'):
        module.verify_reserve(tmp_path)


def test_existing_download_attempt_cannot_be_overwritten(tmp_path):
    path = tmp_path/'source.txt'
    part = path.with_suffix('.txt.part')
    part.write_bytes(b'partial retained')
    with pytest.raises(FileExistsError):
        module.download(path, 'https://example.invalid/')
    assert part.read_bytes() == b'partial retained'


@pytest.mark.parametrize('damage', [None, 'etag', 'range', 'size'])
def test_small_range_recovery_checks_object_range_and_length_and_keeps_original_prefix(tmp_path, monkeypatch, damage):
    from subprocess import CompletedProcess
    path = tmp_path/'paper.pdf'
    prefix = path.with_suffix('.pdf.part')
    prefix.write_bytes(b'%PDF-abc')
    path.with_suffix('.headers').write_text('HTTP/1.1 200 OK\nContent-Length: 16\nETag: "old"\n', encoding='ascii')

    def fetched(command, **kwargs):
        assert command[command.index('--range')+1] == '8-15'
        assert '--insecure' not in command and command[command.index('--proto')+1] == '=https'
        body = Path(command[command.index('--output')+1])
        http = Path(command[command.index('--dump-header')+1])
        body.write_bytes(b'1234567' if damage == 'size' else b'12345678')
        text = 'HTTP/1.1 206 Partial Content\nContent-Range: bytes 8-15/16\nETag: "old"\n'
        if damage == 'range':
            text = text.replace('8-15', '7-14')
        if damage == 'etag':
            text = text.replace('"old"', '"new"')
        http.write_text(text, encoding='ascii')
        return CompletedProcess(command, 0, stdout=b'', stderr=b'')

    monkeypatch.setattr(module.subprocess, 'run', fetched)
    if damage:
        with pytest.raises(ValueError, match='ETag or size'):
            module.resume_download(tmp_path, 'paper.pdf', 'https://example.invalid/paper.pdf', None)
        assert not path.exists()
    else:
        result = module.resume_download(tmp_path, 'paper.pdf', 'https://example.invalid/paper.pdf', None)
        assert path.read_bytes() == b'%PDF-abc12345678' and result['recovered_from_timeout']
        assert result['sha256'] == module.sha(path.read_bytes())
    assert prefix.read_bytes() == b'%PDF-abc'


def test_fallback_cannot_silently_claim_preferred_api_page_was_downloaded(tmp_path):
    name = module.API_FALLBACK[0]
    (tmp_path/name).write_bytes(b'official instructions')
    manifest = dict(complete=True, source_sha256=module.sha(Path(module.__file__).read_bytes()),
        files=[dict(file=name, bytes=21, sha256=module.sha(b'official instructions'))])
    (tmp_path/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError, match='disclose missing preferred API'):
        module.verify_reserve(tmp_path)
