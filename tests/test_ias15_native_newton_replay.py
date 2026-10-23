import json
import shutil

import numpy as np
import pytest

from scripts.kepler_transport import ROOT, sha
from scripts.replay_ias15_native_newton import RECEIPT, replay
from scripts.replay_ias15_restart import RECEIPT as BASELINE


@pytest.fixture
def portable(tmp_path):
    names = set()
    for name in (BASELINE, RECEIPT):
        report = json.loads((ROOT/name).read_text(encoding='utf-8'))
        names.update((name, report['sample_archive'], *report['source_sha256'], *report['input_sha256'],
                      *report.get('cargo_lf_sha256', {})))
    names.update(('scripts/validation/release030-sources.zip', 'scripts/validation/release031-history.json'))
    for name in names:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return tmp_path, json.loads((tmp_path/RECEIPT).read_text(encoding='utf-8'))


def test_all_nine_force_swaps_replay_without_native_library_raw_or_network(portable, monkeypatch):
    import scripts.ias15_native_newton as coupling
    import scripts.ias15_reference as reference
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline replay must not execute either external binary')
    monkeypatch.setattr(coupling, 'require_native', forbidden)
    monkeypatch.setattr(coupling, 'prepare', forbidden)
    monkeypatch.setattr(reference, 'load_library', forbidden)
    root, report = portable
    assert not (root/'.tools').exists()
    result = replay(root)
    assert result['variants'] == 36 and result['arrays'] == 180 and result['all_control353_bitexact']
    assert result['physical_checkpoints'] == 4524 and result['packets'] == 4488
    assert result['metrics_reproduced'] and result['all_checks_passed'] == report['all_checks_passed']


def test_cargo_checkout_eol_change_preserves_replay_but_content_change_does_not(portable):
    root, report = portable
    for name in report['cargo_lf_sha256']:
        path = root/name
        data = path.read_bytes()
        # Exercise both directions regardless of the host checkout policy.
        path.write_bytes(data.replace(b'\r\n', b'\n') if b'\r\n' in data else data.replace(b'\n', b'\r\n'))
    assert replay(root)['all_checks_passed'] == report['all_checks_passed']
    path = root/'rust/solar_core/Cargo.toml'
    path.write_bytes(path.read_bytes()+b'changed-content')
    with pytest.raises(ValueError, match='Cargo content'):
        replay(root)


@pytest.mark.parametrize('damage', ['physical', 'force', 'model', 'gate', 'source', 'partial'])
def test_corruption_is_rejected_even_with_outer_archive_rehash(portable, damage):
    root, report = portable
    name = next(iter(report['results']))
    if damage == 'physical':
        path = root/report['sample_archive']
        with np.load(path, allow_pickle=False) as saved:
            data = {k:saved[k].copy() for k in saved.files}
        data[name+'__1e-09__native__values'][2, 0, 0] += 1.
        np.savez_compressed(path, **data)
        report['npz_sha256'] = sha(path)
    elif damage == 'force':
        report['initial_force'][name]['actual'][0][0] *= 2
    elif damage == 'model':
        report['results'][name]['1e-09__native']['statistics']['gravity'] = 'basic'
    elif damage == 'gate':
        report['all_checks_passed'] = not report['all_checks_passed']
    elif damage == 'source':
        path = root/'scripts/ias15_native_newton.py'
        path.write_bytes(path.read_bytes()+b'changed')
    else:
        report['complete'] = False
    (root/RECEIPT).write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError):
        replay(root)
