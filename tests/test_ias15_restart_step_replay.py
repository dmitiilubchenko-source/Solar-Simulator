import json
import shutil

import numpy as np
import pytest

from scripts.kepler_transport import ROOT, sha
from scripts.replay_ias15_restart import RECEIPT as BASELINE
from scripts.replay_ias15_restart_step import RECEIPT, replay


@pytest.fixture
def portable(tmp_path):
    names = set()
    for name in (BASELINE, RECEIPT):
        report = json.loads((ROOT/name).read_text())
        names.update((name, report['sample_archive'], *report['source_sha256'], *report['input_sha256']))
    for name in names:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return tmp_path, json.loads((tmp_path/RECEIPT).read_text())


def test_all_36_step_cases_replay_without_raw_library(portable):
    root, _ = portable
    assert not (root/'.tools').exists()
    result = replay(root)
    assert result['metrics_reproduced'] and result['reset_control_bitexact']
    assert result['variants'] == 36 and result['arrays'] == 288
    assert result['physical_checkpoints'] == 4524
    assert result['passed'] == {'reset': 13, 'saved-dt': 13}
    assert not result['experimental_all_passed']


@pytest.mark.parametrize('damage', ['used-dt', 'gate', 'source'])
def test_changed_recipe_gate_or_source_is_rejected(portable, damage):
    root, report = portable
    if damage == 'used-dt':
        path = root/report['sample_archive']
        with np.load(path, allow_pickle=False) as saved:
            data = {k:saved[k].copy() for k in saved.files}
        name = next(iter(report['results']))
        data[name+'__1e-09__saved-dt__restart_used_dt'][1] *= 1.01
        np.savez_compressed(path, **data)
        report['npz_sha256'] = sha(path)
    elif damage == 'gate':
        report['experimental_all_passed'] = True
    else:
        path = root/'scripts/assess_ias15_restart_step.py'
        path.write_bytes(path.read_bytes()+b'changed')
    (root/RECEIPT).write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError):
        replay(root)
