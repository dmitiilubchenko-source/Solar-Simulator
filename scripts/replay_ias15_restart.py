"""Offline replay of all public restart metrics, including scientific FAILs."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases, compare, decimal_relative_guard
from scripts.assess_kepler_phase import ROOT, differences, maximum
from scripts.ias15_reference import EPSILONS, packet_end
from scripts.ias15_restart import MODES, bits, restore
from scripts.kepler_transport import public_path, sha
from scripts.release_history import ui_historical_sha
RECEIPT = 'docs/ias15-restart-validation.json'


def replay(root=ROOT):
    root = Path(root).resolve()
    path = root/RECEIPT
    report = json.loads(path.read_text(encoding='utf-8'))
    if (report.get('protocol') != 'docs/ias15-restart-protocol.md'
            or not report.get('complete') or not report.get('source_unchanged')
            or not report.get('input_unchanged') or not report.get('library_unchanged')
            or report.get('solver') != 'IAS15 research' or report.get('runtime_modified') is not False
            or report.get('production_eligible') is not False):
        raise ValueError('Require complete research-only restart receipt')
    for name, expected in {**report['source_sha256'], **report['input_sha256']}.items():
        if ui_historical_sha(root,name,expected) != expected:
            raise ValueError('Changed restart source/input: '+name)
    archive = public_path(root, report['sample_archive'])
    if sha(archive) != report['npz_sha256']:
        raise ValueError('Restart archive SHA mismatch')
    cases, _ = load_cases(root)
    if set(report['results']) != set(cases):
        raise ValueError('Require all nine restart cases')
    with np.load(archive, allow_pickle=False) as saved:
        data = {key:saved[key].copy() for key in saved.files}
    expected_keys, passed, failures, checkpoints = set(), 0, [], 0
    for name, case in cases.items():
        result = report['results'][name]
        if result['request'] != case['request'] or result['origin'] != case['origin']:
            raise ValueError('Changed case request/provenance')
        times, req = case['times'], case['request']
        if result['original_oracle_uncertainty'] != case['oracle_uncertainty']:
            raise ValueError('Changed original oracle uncertainty')
        expected_keys.update((name+'__times', name+'__original_oracle100'))
        if bits(data[name+'__times']) != bits(times):
            raise ValueError('Changed output epoch grid')
        original_oracle = [tuple(map(D, y)) for y in data[name+'__original_oracle100']]
        if original_oracle != case['expected']:
            raise ValueError('Changed actual-IC oracle')
        expected_grid = [0.]
        for epoch in times:
            while expected_grid[-1] < epoch:
                expected_grid.append(packet_end(expected_grid[-1], float(epoch), req['packet_dt']))
        middle = int(np.searchsorted(times, times[-1]/2))
        mode_keys = {str(e)+'__'+m for e in EPSILONS for m in MODES}
        if set(result['modes']) != mode_keys:
            raise ValueError('Require all six mode/epsilon combinations')
        for epsilon in EPSILONS:
            warm = data[name+'__'+str(epsilon)+'__warm__values']
            for mode in MODES:
                key = str(epsilon)+'__'+mode
                row = result['modes'][key]
                prefix = name+'__'+key+'__'
                fields = ('values', 'packet_endpoints', 'packet_states', 'checkpoint_json', 'checkpoint_sha256')
                expected_keys.update(prefix+field for field in fields)
                values, ends, states, texts, hashes = (data[prefix+field] for field in fields)
                if (values.shape != (len(times), 2, 6) or states.shape != (len(expected_grid), 2, 6)
                        or not np.isfinite(values).all() or not np.isfinite(states).all()
                        or bits(ends) != bits(expected_grid) or len(texts) != len(ends)
                        or len(hashes) != len(ends) or bits(values[0]) != bits(case['initial'])):
                    raise ValueError('Changed state, epoch or checkpoint array dimensions')
                for time, state, text, digest in zip(ends, states, texts, hashes):
                    restored_time, masses, restored = restore(str(text), str(digest), case['origin'])
                    if (bits(restored_time) != bits(time) or bits(masses) != bits(req['masses'])
                            or bits(state) != bits(restored)):
                        raise ValueError('Checkpoint roundtrip differs from physical arrays')
                    checkpoints += 1
                indices = np.searchsorted(ends, times)
                if bits(values) != bits(states[indices]):
                    raise ValueError('Output values differ from committed packet snapshots')
                recalculated = metrics(case['seed'], times, values, [(y[:3], y[3:]) for y in original_oracle])
                if recalculated != row['metrics']:
                    raise ValueError('Published actual metrics differ')
                drift = compare(values, [decimal_relative_guard(y) for y in warm], times)
                if drift != row['cold_minus_warm']:
                    raise ValueError('Published warm differences differ')
                stats = row['statistics']
                restart_indices = ([] if mode == 'warm' else
                    [expected_grid.index(float(times[middle]))] if mode == 'one-cold' else
                    list(range(1, len(expected_grid)-1)))
                if (stats['mode'] != mode or stats['epsilon'] != epsilon or stats['packets'] != len(ends)-1
                        or stats['simulations'] != len(restart_indices)+1
                        or stats['restart_packet_indices'] != restart_indices
                        or stats['restart_output_index'] != (middle if mode == 'one-cold' else None)
                        or stats['initial_dt_seconds'] != req['packet_dt']/200
                        or stats['adaptive_mode'] != 'PRS23' or stats['gravity'] != 'basic'
                        or not stats['physical_roundtrip_bitexact']
                        or stats['force_evaluations'] <= 0 or stats['steps_done'] <= 0
                        or not row['repeat_bitexact'] or not row['counter_bitexact']
                        or len(row['seconds']) != 3 or min(row['seconds']) <= 0
                        or sorted(row['seconds'])[1] != row['median_seconds']):
                    raise ValueError('Changed mode, schedule or measurement metadata')
                if mode == 'one-cold':
                    expected_keys.update(prefix+'restart_oracle'+str(p) for p in (70, 100))
                    low = [tuple(map(D, y)) for y in data[prefix+'restart_oracle70']]
                    high = [tuple(map(D, y)) for y in data[prefix+'restart_oracle100']]
                    if (len(low) != len(times)-middle or len(high) != len(low)
                            or low[0] != decimal_relative_guard(values[middle])
                            or high[0] != low[0] or bits(values[:middle+1]) != bits(warm[:middle+1])):
                        raise ValueError('Changed one-cold initial state or warm prefix')
                    precision = maximum([differences((a[:3], a[3:]), (b[:3], b[3:])) for a,b in zip(low, high)])
                    inherited = maximum([differences((a[:3], a[3:]), (b[:3], b[3:]))
                                         for a,b in zip(high, original_oracle[middle:])])
                    diagnostic = dict(index=middle, time=float(times[middle]), precision_difference=precision,
                        inherited_oracle_difference=inherited,
                        post_restart_error=compare(values[middle:], high, times[middle:]), prefix_bitexact=True)
                    if (diagnostic != row['restart_diagnostics'] or precision['position_metres'] >= 1e-6
                            or precision['velocity_m_per_s'] >= 1e-12):
                        raise ValueError('Published restarted-oracle diagnostics differ')
                passed += int(recalculated['checks_passed'])
                if not recalculated['checks_passed']:
                    failures.append(dict(case=name, variant=key))
    if set(data) != expected_keys or len(expected_keys) != 324:
        raise ValueError('Unexpected or missing public arrays')
    if report['all_checks_passed'] != (passed == 54):
        raise ValueError('Aggregate scientific gate differs from individual results')
    return dict(cases=9, variants=54, passed=passed, failed=54-passed, failures=failures,
                physical_checkpoints=checkpoints, arrays=len(data), metrics_reproduced=True,
                all_checks_passed=passed == 54, runtime_modified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    # A faithful replay of a preserved scientific FAIL is a successful integrity check.
    print(json.dumps(replay(args.root), indent=2))


if __name__ == '__main__':
    main()
