import json
import shutil

import numpy as np
import pytest

from scripts.kepler_transport import ROOT, sha
from scripts.replay_native_newton_year import RECEIPT, replay
from scripts.release_history import ARCHIVE, MANIFEST, UI_ARCHIVE, HISTORICAL_ARCHIVES

@pytest.fixture
def portable(tmp_path):
    report = json.loads((ROOT/RECEIPT).read_text(encoding='utf-8'))
    names = {RECEIPT, report['sample_archive'], *report['source_sha256'], *report['input_sha256'],
             *report['cargo_lf_sha256']}
    # Cache qualification also reports all historical bindings, including protocol171.
    history = json.loads((ROOT/'docs/newton-year-validation.json').read_text(encoding='utf-8'))
    names.update(history['year']['source_sha256'])
    names.update((ARCHIVE, MANIFEST, UI_ARCHIVE))
    names.update(HISTORICAL_ARCHIVES)
    for name in names:
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return tmp_path, report


def test_all_eight_variants_and_reference_levels_replay_without_numerical_backends(portable, monkeypatch):
    import scripts.native_newton_year as module
    import scripts.newton_year as old
    import scripts.ias15_reference as reference
    def forbidden(*args, **kwargs):
        raise AssertionError('Offline replay must not integrate or execute native code')
    monkeypatch.setattr(module, 'require_native', forbidden)
    monkeypatch.setattr(module, 'prepare', forbidden)
    monkeypatch.setattr(old, 'reference', forbidden)
    monkeypatch.setattr(old, 'solve_ivp', forbidden)
    monkeypatch.setattr(reference, 'load_library', forbidden)
    root, _ = portable
    assert not (root/'.tools').exists()
    result = replay(root)
    assert result['passed'] == dict(pilot=4, year=4) and result['all_checks_passed']
    assert result['arrays'] == 26 and result['packet_states'] == 2244 and result['packets'] == 2236


@pytest.mark.parametrize('damage', ['physical', 'clock', 'reference', 'force', 'metric', 'source', 'partial', 'gate'])
def test_corruption_is_rejected_even_with_outer_npz_rehash(portable, damage):
    root, report = portable
    control = replay(root)
    assert control['metrics_reproduced'] and control['arrays'] > 0
    if damage in ('physical', 'clock', 'reference'):
        path = root/report['sample_archive']
        with np.load(path, allow_pickle=False) as saved:
            data = {k:saved[k].copy() for k in saved.files}
        if damage == 'physical':
            data['year__1e-09__native__values'][2, 4, 0] += 1.
        elif damage == 'clock':
            data['year__1e-09__native__packet_endpoints'][2] += 1.
        else:
            data['year__reference_recheck'][2, 4, 0] += 1.
        np.savez_compressed(path, **data)
        report['npz_sha256'] = sha(path)
    elif damage == 'force':
        report['initial_force']['actual'][0][0] *= 2
    elif damage == 'metric':
        report['results']['year']['1e-09__native']['metrics']['per_body']['Moon']['position_metres'] = 0.
    elif damage == 'source':
        path = root/'scripts/native_newton_year.py'
        path.write_bytes(path.read_bytes()+b'changed')
    elif damage == 'partial':
        report['complete'] = False
    else:
        report['all_checks_passed'] = False
    (root/RECEIPT).write_text(json.dumps(report), encoding='utf-8')
    expected_error = {'physical': 'Output differs from its exact N-body packet state', 'clock': 'Invalid N-body IC/shape/clock', 'reference': 'Regenerated RK45 reference', 'force': 'Independent N-body force', 'metric': 'N-body per-body/relative/invariant', 'source': 'Changed historical source or Cargo content', 'partial': 'complete, qualified N-body', 'gate': 'aggregate gate'}[damage]
    with pytest.raises(ValueError, match=expected_error):
        replay(root)


def test_original_reference_corruption_cannot_be_accepted_by_outer_rehash(portable):
    root, report = portable
    control = replay(root)
    assert control['metrics_reproduced'] and control['arrays'] > 0
    name = 'docs/native-newton-year-reference.npz'
    path = root/name
    path.write_bytes(path.read_bytes()+b'changed')
    report['input_sha256'][name] = sha(path)
    (root/RECEIPT).write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(ValueError, match='original RK45 cache'):
        replay(root)
