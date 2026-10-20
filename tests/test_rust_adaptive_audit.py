"""Evidence integrity checks; no optional Rust binary or network is required."""
from copy import deepcopy
import hashlib
from pathlib import Path
import subprocess
from zipfile import ZipFile

import numpy as np
import pytest

from scripts import assess_rust_adaptive as audit


def good_response():
    initial = np.array([[1., 2., 3., 4., 5., 6.], [-1., -2., -3., -4., -5., -6.]])
    frames = [dict(time=t, states=initial.tolist()) for t in (0., 1.)]
    return initial, dict(complete=True, error=None, snapshots=frames, committed=deepcopy(frames[-1]),
        packet_endpoints=[1.], statistics=dict(rhs_calls=12, accepted=1, rejected=0, packets=1, failed=False))


@pytest.mark.parametrize('damage', ['incomplete', 'error', 'missing', 'epoch', 'initial',
                                  'nan', 'packet', 'commit', 'counter', 'failed'])
def test_incomplete_or_changed_rust_evidence_cannot_pass(damage):
    initial, response = good_response()
    if damage == 'incomplete': response['complete'] = False
    elif damage == 'error': response['error'] = 'force failed'
    elif damage == 'missing': response['snapshots'].pop()
    elif damage == 'epoch': response['snapshots'][-1]['time'] = .999
    elif damage == 'initial': response['snapshots'][0]['states'][0][0] = np.nextafter(1., 2.)
    elif damage == 'nan': response['snapshots'][-1]['states'][0][0] = float('nan')
    elif damage == 'packet': response['packet_endpoints'] = [1.001]
    elif damage == 'commit': response['committed']['time'] = .999
    elif damage == 'counter': response['statistics']['accepted'] = True
    else: response['statistics']['failed'] = True
    with pytest.raises(ValueError):
        audit.validate_response(response, np.array([0., 1.]), initial, [1.])


def test_complete_evidence_retains_exact_initial_bits_and_epoch_grid():
    initial, response = good_response()
    values = audit.validate_response(response, np.array([0., 1.]), initial, [1.])
    np.testing.assert_array_equal(values[0], initial)
    assert values.shape == (2, 2, 6)


@pytest.mark.parametrize('suffix', ['.json', '.npz'])
def test_existing_results_are_protected_before_any_binary_or_source_read(tmp_path, suffix):
    output = tmp_path/'kept.json'
    protected = output.with_suffix(suffix)
    protected.write_bytes(b'previous failure')
    with pytest.raises(FileExistsError):
        audit.run(tmp_path/'missing.exe', output)
    assert protected.read_bytes() == b'previous failure'


def test_dirty_snapshot_keeps_patch_and_untracked_unicode_bytes(tmp_path, monkeypatch):
    def git(*args):
        subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True)
    git('init', '-q')
    (tmp_path/'.gitignore').write_text('.tools/\n')
    tracked = tmp_path/'tracked.py'
    tracked.write_bytes(b'old\n')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.test', 'commit', '-qm', 'fixture')
    tracked.write_bytes(b'changed\n')
    raw = 'проверка данных\n'.encode('utf-8')
    name = 'новый.rs'
    (tmp_path/name).write_bytes(raw)
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    target = tmp_path/'.tools/provenance'
    receipt = audit.provenance(target)
    assert receipt['git_status']
    assert receipt['untracked_source_sha256'] == {name: hashlib.sha256(raw).hexdigest()}
    with ZipFile(target/'untracked.zip') as archive:
        assert archive.read(name) == raw
    assert b'changed' in (target/'tracked.patch').read_bytes()
