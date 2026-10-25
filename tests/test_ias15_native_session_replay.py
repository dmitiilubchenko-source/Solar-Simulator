import json
import shutil

import pytest

from scripts.kepler_transport import ROOT
from scripts.replay_ias15_native_newton import RECEIPT as COUPLING
from scripts.replay_ias15_native_session import RECEIPT, replay
from scripts.replay_ias15_restart import RECEIPT as RESTART
from scripts.replay_ias15_session import FROZEN_SESSION, RECEIPT as OWNED
from scripts.release_history import ARCHIVE, MANIFEST

@pytest.fixture
def portable(tmp_path):
    names = {FROZEN_SESSION}
    for name in (RESTART, OWNED, COUPLING, RECEIPT):
        report = json.loads((ROOT/name).read_text(encoding='utf-8'))
        names.update((name, report['sample_archive'], *report['source_sha256'], *report['input_sha256'],
                      *report.get('cargo_lf_sha256', {})))
    names.update((ARCHIVE, MANIFEST))
    for name in names:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return tmp_path, json.loads((tmp_path/RECEIPT).read_text(encoding='utf-8'))


def test_new_session_replays_all_modes_without_native_library_raw_or_network(portable, monkeypatch):
    import scripts.ias15_native_session as module
    import scripts.ias15_reference as reference
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline replay must not execute a numerical backend')
    monkeypatch.setattr(module, 'require_native', forbidden)
    monkeypatch.setattr(module, 'prepare', forbidden)
    monkeypatch.setattr(reference, 'load_library', forbidden)
    root, _ = portable
    assert not (root/'.tools').exists()
    result = replay(root)
    assert result['passed'] == dict(basic=18, native=18) and result['all_checks_passed']
    assert result['archive_reused357'] and result['arrays'] == 180
    assert result['physical_checkpoints'] == 4524 and result['packets'] == 4488


@pytest.mark.parametrize('damage', ['live-source', 'historical-source', 'lifecycle', 'metrics', 'gate', 'cargo', 'partial'])
def test_changed_live_history_or_receipt_cannot_reuse_old_pass(portable, damage):
    root, report = portable
    row = next(iter(report['results'].values()))['1e-09__native']
    if damage in ('live-source', 'historical-source'):
        path = root/('scripts/ias15_session.py' if damage == 'live-source' else FROZEN_SESSION)
        path.write_bytes(path.read_bytes()+b'changed')
    elif damage == 'lifecycle':
        row['statistics']['closed'] = False
    elif damage == 'metrics':
        row['metrics']['position_metres'] = 0.
    elif damage == 'gate':
        report['all_checks_passed'] = False
    elif damage == 'cargo':
        report['cargo_raw_after_sha256']['rust/solar_core/Cargo.toml'] = '0'*64
    else:
        report['complete'] = False
    (root/RECEIPT).write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError):
        replay(root)
