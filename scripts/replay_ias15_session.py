"""Offline qualification of the owned warm session; never executes REBOUND."""
import argparse
import json
from pathlib import Path

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases
from scripts.assess_kepler_phase import ROOT
from scripts.ias15_reference import EPSILONS
from scripts.ias15_restart import bits, restore
from scripts.kepler_transport import public_path, sha
from scripts.replay_ias15_restart import RECEIPT as BASELINE, replay as replay_baseline
from scripts.release_history import UI_FILES,ui_historical_sha
RECEIPT = 'docs/ias15-session-validation.json'
FROZEN_SESSION = 'scripts/validation/ias15_session_356.py'
FROZEN_SHA = '1058c0f065edc4dfef26df9f153c4c2dbb071342f7cdd122e9e1c76d15fe17c2'


def source_path(root, name, expected):
    """Receipt356 describes historical code, never the subsequently extended live class."""
    if name == 'scripts/ias15_session.py' and expected == FROZEN_SHA:
        name = FROZEN_SESSION
    path = public_path(root, name)
    if sha(path) != expected:
        raise ValueError('Changed session source/input: '+name)
    return path


def replay(root=ROOT):
    root = Path(root).resolve()
    baseline_summary = replay_baseline(root)
    report = json.loads((root/RECEIPT).read_text(encoding='utf-8'))
    if (report.get('protocol') != 'docs/ias15-session-protocol.md'
            or not all(report.get(k) for k in ('complete', 'source_unchanged', 'input_unchanged',
                                                'library_unchanged', 'all_warm353_bitexact'))
            or report.get('runtime_modified') is not False or report.get('production_eligible') is not False
            or report.get('solver') != 'IAS15 owned warm research session'
            or report['baseline_integrity'] != baseline_summary):
        raise ValueError('Require complete owned-session research receipt and faithful baseline')
    for name, expected in {**report['source_sha256'], **report['input_sha256']}.items():
        if name in UI_FILES:
            if ui_historical_sha(root,name,expected)!=expected:raise ValueError('Changed session source/input: '+name)
        else:source_path(root, name, expected)
    archive = public_path(root, report['sample_archive'])
    if sha(archive) != report['npz_sha256']:
        raise ValueError('Session archive SHA mismatch')
    original = json.loads((root/BASELINE).read_text(encoding='utf-8'))
    with np.load(public_path(root, original['sample_archive']), allow_pickle=False) as saved:
        baseline = {k:saved[k].copy() for k in saved.files}
    with np.load(archive, allow_pickle=False) as saved:
        data = {k:saved[k].copy() for k in saved.files}
    cases, _ = load_cases(root)
    if set(report['results']) != set(cases):
        raise ValueError('All nine owned-session cases required')
    expected_keys, passed, checkpoints, packets = set(), 0, 0, 0
    for name, case in cases.items():
        if set(report['results'][name]) != set(map(str, EPSILONS)):
            raise ValueError('Both session epsilon values required')
        for epsilon in EPSILONS:
            row = report['results'][name][str(epsilon)]
            prefix, old_prefix = name+'__'+str(epsilon)+'__', name+'__'+str(epsilon)+'__warm__'
            fields = ('values', 'packet_endpoints', 'packet_states', 'checkpoint_json', 'checkpoint_sha256')
            expected_keys.update(prefix+field for field in fields)
            for field in fields:
                actual, expected = data[prefix+field], baseline[old_prefix+field]
                same = (actual.shape == expected.shape and bits(actual) == bits(expected)) if actual.dtype.kind == 'f' else np.array_equal(actual, expected)
                if not same:
                    raise ValueError('Session physical arrays differ from353warm: '+field)
            values, ends, states, texts, hashes = (data[prefix+field] for field in fields)
            for time, state, text, digest in zip(ends, states, texts, hashes):
                t, masses, q = restore(str(text), str(digest), case['origin'])
                if bits(t) != bits(time) or bits(masses) != bits(case['request']['masses']) or bits(q) != bits(state):
                    raise ValueError('Session checkpoint differs from committed physical state')
                checkpoints += 1
            old_row = original['results'][name]['modes'][str(epsilon)+'__warm']
            recalculated = metrics(case['seed'], case['times'], values, [(y[:3], y[3:]) for y in case['expected']])
            if recalculated != row['metrics'] or recalculated != old_row['metrics']:
                raise ValueError('Session actual metrics differ')
            stats = row['statistics']
            if (stats['simulations'] != 1 or stats['attempts'] != stats['packets']
                    or stats['failed'] or not stats['closed'] or not stats['finished']
                    or stats['packets'] != len(ends)-1
                    or stats['attempted_force_evaluations'] != stats['force_evaluations']
                    or any(stats[k] != old_row['statistics'][k]
                           for k in ('packets', 'steps_done', 'force_evaluations', 'simulations'))
                    or not all(row[k] for k in ('warm353_bitexact', 'repeated_bitexact', 'forcecounter_bitexact'))
                    or len(row['seconds']) != 3 or min(row['seconds']) <= 0
                    or sorted(row['seconds'])[1] != row['median_seconds']):
                raise ValueError('Session counters, lifecycle flags or measurement metadata differ')
            passed += int(recalculated['checks_passed'])
            packets += stats['packets']
    if set(data) != expected_keys or len(data) != 90 or report['all_checks_passed'] != (passed == 18):
        raise ValueError('Session array set or aggregate gate differs')
    return dict(cases=9, variants=18, passed=passed, arrays=len(data), physical_checkpoints=checkpoints,
                packets=packets, all_warm353_bitexact=True, metrics_reproduced=True,
                all_checks_passed=passed == 18, runtime_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(replay(args.root), indent=2))


if __name__ == '__main__':
    main()
