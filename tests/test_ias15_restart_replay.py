import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from scripts.kepler_transport import ROOT, sha
from scripts.replay_ias15_restart import RECEIPT, replay
from scripts.release_history import UI_ARCHIVE

@pytest.fixture
def portable(tmp_path):
    report = json.loads((ROOT/RECEIPT).read_text())
    names = {UI_ARCHIVE, RECEIPT, report['sample_archive'], *report['source_sha256'], *report['input_sha256']}
    for name in names:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return tmp_path, report


def write_report(root, report):
    (root/RECEIPT).write_text(json.dumps(report), encoding='utf-8')


def test_all_metrics_and_6786_checkpoints_replay_without_raw_library_or_network(portable, monkeypatch):
    root, _ = portable
    import scripts.ias15_reference as reference
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline replay must not execute REBOUND')
    monkeypatch.setattr(reference, 'load_library', forbidden)
    assert not (root/'.tools').exists()
    result = replay(root)
    assert (result['cases'], result['variants'], result['physical_checkpoints'], result['arrays']) == (9, 54, 6786, 324)
    assert result['passed'] == 49 and result['failed'] == 5
    assert result['metrics_reproduced'] and not result['all_checks_passed']


@pytest.mark.parametrize('damage', ['source', 'archive', 'partial', 'aggregate', 'metric'])
def test_damaged_sources_receipts_and_aggregate_cannot_turn_failure_into_pass(portable, damage):
    root, report = portable
    if damage == 'source':
        victim = root/'scripts/ias15_restart.py'
        victim.write_bytes(victim.read_bytes()+b'\n')
    elif damage == 'archive':
        victim = root/report['sample_archive']
        victim.write_bytes(victim.read_bytes()+b'bad')
    elif damage == 'partial':
        report['complete'] = False
    elif damage == 'aggregate':
        report['all_checks_passed'] = True
    else:
        case = next(iter(report['results'].values()))
        next(iter(case['modes'].values()))['metrics']['position_metres'] = 123.
    write_report(root, report)
    with pytest.raises(ValueError):
        replay(root)


@pytest.mark.parametrize('field', ['packet_states', 'checkpoint_json'])
def test_inner_physical_corruption_is_detected_even_after_outer_archive_rehash(portable, field):
    root, report = portable
    path = root/report['sample_archive']
    with np.load(path, allow_pickle=False) as saved:
        data = {key:saved[key].copy() for key in saved.files}
    name = next(iter(report['results']))
    key = name+'__1e-09__warm__'+field
    if field == 'packet_states':
        data[key][3, 0, 3] += 1.
    else:
        text = str(data[key][3])
        document = json.loads(text)
        document['masses'][0] *= 2.
        replacement = json.dumps(document, separators=(',', ':'), sort_keys=True)
        values = data[key].tolist()
        values[3] = replacement
        data[key] = np.asarray(values)
    np.savez_compressed(path, **data)
    report['npz_sha256'] = sha(path)
    write_report(root, report)
    with pytest.raises(ValueError, match='Checkpoint|checkpoint'):
        replay(root)
