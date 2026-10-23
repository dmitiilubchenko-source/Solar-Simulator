"""Offline physical replay of Newton force coupling, without native/REBOUND."""
import argparse
import json
from pathlib import Path

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_native_newton import PROTOCOL, cargo_hashes, same_array
from scripts.assess_ias15_restart import compare, decimal_relative_guard, load_cases
from scripts.ias15_native_newton import MODES, force_metrics
from scripts.ias15_reference import EPSILONS, packet_end
from scripts.ias15_restart import bits, restore
from scripts.kepler_transport import ROOT, public_path, sha
from scripts.release_history import historical_sha, historical_cargo_hashes
from scripts.replay_ias15_restart import RECEIPT as BASELINE, replay as replay_baseline

RECEIPT = 'docs/ias15-native-newton-validation.json'


def replay(root=ROOT):
    root = Path(root).resolve()
    baseline_integrity = replay_baseline(root)
    report = json.loads((root/RECEIPT).read_text(encoding='utf-8'))
    required = ('complete', 'source_unchanged', 'input_unchanged', 'library_unchanged',
                'native_unchanged', 'cargo_unchanged', 'all_control353_bitexact')
    if (report.get('protocol') != PROTOCOL or not all(report.get(k) is True for k in required)
            or report.get('solver') != 'IAS15 Newton force coupling research'
            or report.get('runtime_modified') is not False or report.get('production_eligible') is not False
            or report['baseline_integrity'] != baseline_integrity
            or report['native']['native_probe_passed'] is not True
            or len(bytes.fromhex(report['native']['sha256'])) != 32):
        raise ValueError('Require complete research-only Newton coupling receipt')
    if (report.get('cargo_hash_policy') != 'cargo-crlf-to-lf-v1'
            or historical_cargo_hashes(root, report['cargo_lf_sha256']) != report['cargo_lf_sha256']
            or report['cargo_raw_before_sha256'] != report['cargo_raw_after_sha256']
            or set(report['cargo_raw_before_sha256']) != set(report['cargo_lf_sha256'])
            or any(len(bytes.fromhex(v)) != 32 for v in report['cargo_raw_before_sha256'].values())):
        raise ValueError('Changed Cargo content or invalid build metadata provenance')
    for name, expected in {**report['source_sha256'], **report['input_sha256']}.items():
        if historical_sha(root, name, expected) != expected:
            raise ValueError('Changed Newton coupling source/input: '+name)
    path = public_path(root, report['sample_archive'])
    if sha(path) != report['npz_sha256']:
        raise ValueError('Newton coupling archive SHA mismatch')
    old = json.loads((root/BASELINE).read_text(encoding='utf-8'))
    with np.load(public_path(root, old['sample_archive']), allow_pickle=False) as saved:
        baseline = {k:saved[k].copy() for k in saved.files}
    with np.load(path, allow_pickle=False) as saved:
        data = {k:saved[k].copy() for k in saved.files}
    cases, _ = load_cases(root)
    if set(report['results']) != set(cases) or set(report['initial_force']) != set(cases):
        raise ValueError('All nine Newton coupling cases required')
    expected_keys, passed, checkpoints, packets = set(), dict.fromkeys(MODES, 0), 0, 0
    for name, case in cases.items():
        force = report['initial_force'][name]
        if force_metrics(case['request']['masses'], case['initial'], force['actual']) != force or not force['checks_passed']:
            raise ValueError('Independent initial force metric differs')
        if set(report['results'][name]) != {str(e)+'__'+mode for e in EPSILONS for mode in MODES}:
            raise ValueError('Both epsilons and both force modes required')
        clock, expected_clocks = 0., [0.]
        for epoch in case['times']:
            while clock < epoch:
                clock = packet_end(clock, float(epoch), case['request']['packet_dt'])
                expected_clocks.append(clock)
        for epsilon in EPSILONS:
            controls = None
            for mode in MODES:
                key = str(epsilon)+'__'+mode
                row = report['results'][name][key]
                prefix, old_prefix = name+'__'+key+'__', name+'__'+str(epsilon)+'__warm__'
                fields = ('values', 'packet_endpoints', 'packet_states', 'checkpoint_json', 'checkpoint_sha256')
                expected_keys.update(prefix+field for field in fields)
                values, ends, states, texts, hashes = (data[prefix+field] for field in fields)
                if (values.shape != (len(case['times']), 2, 6) or ends.shape != (len(expected_clocks),)
                        or states.shape != (len(ends), 2, 6) or texts.shape != ends.shape or hashes.shape != ends.shape
                        or bits(ends) != bits(expected_clocks) or not np.isfinite(values).all()
                        or not np.isfinite(states).all() or bits(values[0]) != bits(case['initial'])
                        or bits(states[0]) != bits(case['initial'])):
                    raise ValueError('Newton physical shapes, IC or packet clocks differ')
                for time, state, text, digest in zip(ends, states, texts, hashes):
                    t, masses, q = restore(str(text), str(digest), case['origin'])
                    if bits(t) != bits(time) or bits(masses) != bits(case['request']['masses']) or bits(q) != bits(state):
                        raise ValueError('Newton checkpoint differs from packet state')
                    checkpoints += 1
                for epoch, value in zip(case['times'], values):
                    indices = np.flatnonzero(ends == epoch)
                    if len(indices) != 1 or bits(states[indices[0]]) != bits(value):
                        raise ValueError('Newton output differs from its exact committed packet')
                measured = metrics(case['seed'], case['times'], values, [(y[:3], y[3:]) for y in case['expected']])
                if measured != row['metrics']:
                    raise ValueError('Newton actual-IC metrics differ')
                stats = row['statistics']
                if (stats['mode'] != mode or stats['gravity'] != ('basic' if mode == 'basic' else 'none')
                        or stats['velocity_dependent'] is not False or stats['simulations'] != 1
                        or stats['packets'] != len(ends)-1 or stats['steps_done'] <= 0
                        or stats['force_evaluations'] < stats['steps_done']
                        or row['repeated_bitexact'] is not True or len(row['seconds']) != 3
                        or min(row['seconds']) <= 0 or sorted(row['seconds'])[1] != row['median_seconds']
                        or row['control353_bitexact'] is not (mode == 'basic')):
                    raise ValueError('Newton coupling settings or counters differ')
                if mode == 'basic':
                    if not all(same_array(data[prefix+field], baseline[old_prefix+field]) for field in fields):
                        raise ValueError('Newton C control is not bitexact353warm')
                    old_stats = old['results'][name]['modes'][str(epsilon)+'__warm']['statistics']
                    if any(stats[k] != old_stats[k] for k in ('packets', 'steps_done', 'force_evaluations', 'simulations')):
                        raise ValueError('Newton C control counters differ from353warm')
                    controls = values
                elif compare(values, [decimal_relative_guard(q) for q in controls], case['times']) != row['control_delta']:
                    raise ValueError('Newton native/C delta differs')
                passed[mode] += int(measured['checks_passed'])
                packets += stats['packets']
    all_passed = all(n == 18 for n in passed.values())
    if set(data) != expected_keys or len(data) != 180 or report['all_checks_passed'] is not all_passed:
        raise ValueError('Newton coupling archive set or aggregate gate differs')
    return dict(cases=9, variants=36, passed=passed, arrays=len(data), physical_checkpoints=checkpoints,
                packets=packets, all_control353_bitexact=True, metrics_reproduced=True,
                all_checks_passed=all_passed, runtime_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    print(json.dumps(replay(parser.parse_args().root), indent=2))


if __name__ == '__main__':
    main()
