import json
import shutil

import numpy as np
import pytest

from scripts.kepler_transport import ROOT, sha
from scripts.replay_ias15_restart import RECEIPT as BASELINE
from scripts.replay_ias15_session import FROZEN_SESSION, RECEIPT, replay
from scripts.release_history import UI_ARCHIVE

@pytest.fixture
def portable(tmp_path):
    names = {FROZEN_SESSION, UI_ARCHIVE}
    for name in (BASELINE, RECEIPT):
        row = json.loads((ROOT/name).read_text())
        names.update((name, row['sample_archive'], *row['source_sha256'], *row['input_sha256']))
    for name in names:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return tmp_path, json.loads((tmp_path/RECEIPT).read_text())


def test_all_18_owned_sessions_replay_without_library_raw_or_network(portable, monkeypatch):
    import scripts.ias15_reference as reference
    def forbidden(*args, **kwargs):
        raise AssertionError('Replay must not execute REBOUND')
    monkeypatch.setattr(reference, 'load_library', forbidden)
    root, _ = portable
    assert not (root/'.tools').exists()
    result = replay(root)
    assert result['passed'] == 18 and result['all_checks_passed'] and result['all_warm353_bitexact']
    assert result['arrays'] == 90 and result['physical_checkpoints'] == 2262 and result['packets'] == 2244


def test_historical_receipt_uses_exact_frozen_source_without_qualifying_live_extension(portable):
    root, report = portable
    assert sha(root/FROZEN_SESSION) == report['source_sha256']['scripts/ias15_session.py']
    (root/'scripts/ias15_session.py').write_bytes(b'unrelated future implementation')
    assert replay(root)['passed'] == 18


@pytest.mark.parametrize('damage', ['physical', 'lifecycle', 'source', 'partial'])
def test_corrupt_physical_arrays_lifecycle_source_or_partial_receipt_are_rejected(portable, damage):
    root, report = portable
    if damage == 'physical':
        path = root/report['sample_archive']
        with np.load(path, allow_pickle=False) as saved:
            data = {key:saved[key].copy() for key in saved.files}
        name = next(iter(report['results']))
        data[name+'__1e-09__values'][2, 0, 0] += 1.
        np.savez_compressed(path, **data)
        report['npz_sha256'] = sha(path)
    elif damage == 'lifecycle':
        next(iter(report['results'].values()))['1e-09']['statistics']['closed'] = False
    elif damage == 'source':
        path = root/FROZEN_SESSION
        path.write_bytes(path.read_bytes()+b'changed')
    else:
        report['complete'] = False
    (root/RECEIPT).write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError):
        replay(root)
