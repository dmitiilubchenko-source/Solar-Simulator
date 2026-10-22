"""Offline verification of the dt control and its preserved failures."""
from decimal import Decimal as D
import json
from pathlib import Path

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases, compare, decimal_relative_guard
from scripts.assess_ias15_restart_step import PROTOCOL, RECIPES, restore_step
from scripts.assess_kepler_phase import ROOT
from scripts.ias15_reference import EPSILONS
from scripts.ias15_restart import bits, restore
from scripts.kepler_transport import sha, public_path
from scripts.replay_ias15_restart import replay as replay_baseline, RECEIPT as BASELINE

RECEIPT = 'docs/ias15-restart-step-validation.json'


def replay(root=ROOT):
    root = Path(root).resolve()
    baseline_summary = replay_baseline(root)
    report = json.loads((root/RECEIPT).read_text(encoding='utf-8'))
    if (report.get('protocol') != PROTOCOL or not report.get('complete')
            or report.get('runtime_modified') is not False or report.get('production_eligible') is not False
            or not all(report.get(k) for k in ('source_unchanged', 'input_unchanged', 'library_unchanged', 'reset_control_bitexact'))
            or report['baseline_integrity'] != baseline_summary):
        raise ValueError('Require complete step research receipt and faithful baseline')
    for name, expected in {**report['source_sha256'], **report['input_sha256']}.items():
        if sha(public_path(root, name)) != expected:
            raise ValueError('Changed step source/input: '+name)
    archive = public_path(root, report['sample_archive'])
    if sha(archive) != report['npz_sha256']:
        raise ValueError('Step archive SHA mismatch')
    original = json.loads((root/BASELINE).read_text(encoding='utf-8'))
    with np.load(public_path(root, original['sample_archive']), allow_pickle=False) as saved:
        baseline = {k:saved[k].copy() for k in saved.files}
    with np.load(archive, allow_pickle=False) as saved:
        data = {k:saved[k].copy() for k in saved.files}
    cases, _ = load_cases(root)
    if set(report['results']) != set(cases):
        raise ValueError('All nine step cases required')
    expected_keys, counts, failures, snapshots = set(), {r:0 for r in RECIPES}, [], 0
    for name, case in cases.items():
        req, times = case['request'], case['times']
        if set(report['results'][name]) != {str(e)+'__'+r for e in EPSILONS for r in RECIPES}:
            raise ValueError('Missing epsilon/recipe')
        for epsilon in EPSILONS:
            base = name+'__'+str(epsilon)+'__every-packet__'
            reset = data[name+'__'+str(epsilon)+'__reset__values']
            warm = baseline[name+'__'+str(epsilon)+'__warm__values']
            for recipe in RECIPES:
                key = str(epsilon)+'__'+recipe
                prefix, row = name+'__'+key+'__', report['results'][name][key]
                fields = ('values', 'packet_endpoints', 'packet_states', 'checkpoint_json',
                          'checkpoint_sha256', 'step_json', 'step_sha256', 'restart_used_dt')
                expected_keys.update(prefix+f for f in fields)
                values, ends, states, texts, hashes, steps, step_hashes, used = (data[prefix+f] for f in fields)
                if (values.shape != (len(times), 2, 6) or states.shape != (len(ends), 2, 6)
                        or bits(ends) != bits(baseline[base+'packet_endpoints'])
                        or not np.isfinite(values).all() or not np.isfinite(states).all()
                        or any(len(x) != len(ends) for x in (texts, hashes, steps, step_hashes))
                        or len(used) != len(ends)-1):
                    raise ValueError('Changed step physical arrays or grid')
                proposals = []
                for time, state, text, digest, s, h in zip(ends, states, texts, hashes, steps, step_hashes):
                    t, masses, q = restore(str(text), str(digest), case['origin'])
                    if bits(t) != bits(time) or bits(masses) != bits(req['masses']) or bits(q) != bits(state):
                        raise ValueError('Changed physical checkpoint')
                    proposals.append(restore_step(str(s), str(h), float(time), epsilon, case['origin']))
                    snapshots += 1
                wanted = proposals[:-1] if recipe == 'saved-dt' else [req['packet_dt']/200]*len(used)
                if bits(used) != bits(wanted) or bits(used[0]) != bits(req['packet_dt']/200):
                    raise ValueError('Used restart dt differs from the declared recipe')
                if bits(values) != bits(states[np.searchsorted(ends, times)]) or bits(values[0]) != bits(case['initial']):
                    raise ValueError('Changed initial or committed outputs')
                recalculated = metrics(case['seed'], times, values, [(y[:3], y[3:]) for y in case['expected']])
                if (recalculated != row['metrics']
                        or compare(values, [decimal_relative_guard(y) for y in reset], times) != row['difference_from_reset']
                        or compare(values, [decimal_relative_guard(y) for y in warm], times) != row['difference_from_warm']):
                    raise ValueError('Changed step metrics')
                stats = row['statistics']
                packets = len(ends)-1
                if (stats['recipe'] != recipe or stats['mode'] != 'every-packet' or stats['epsilon'] != epsilon
                        or stats['packets'] != packets or stats['simulations'] != packets
                        or stats['restart_packet_indices'] != list(range(1, packets))
                        or not row['repeat_bitexact'] or not row['counter_bitexact']
                        or len(row['seconds']) != 3 or min(row['seconds']) <= 0
                        or sorted(row['seconds'])[1] != row['median_seconds']):
                    raise ValueError('Changed step metadata')
                if recipe == 'reset':
                    if bits(values) != bits(baseline[base+'values']):
                        raise ValueError('Reset does not reproduce353')
                    for field in ('packet_endpoints', 'packet_states', 'checkpoint_json', 'checkpoint_sha256'):
                        if not np.array_equal(data[prefix+field], baseline[base+field]):
                            raise ValueError('Reset physical data differ from353')
                    old_stats = original['results'][name]['modes'][str(epsilon)+'__every-packet']['statistics']
                    if any(stats[k] != v for k,v in old_stats.items()):
                        raise ValueError('Reset counters differ from353')
                counts[recipe] += int(recalculated['checks_passed'])
                if not recalculated['checks_passed']:
                    failures.append(dict(case=name, variant=key))
    if set(data) != expected_keys or len(data) != 288 or report['experimental_all_passed'] != (counts['saved-dt'] == 18):
        raise ValueError('Changed arrays or experimental gate')
    return dict(variants=36, arrays=len(data), physical_checkpoints=snapshots,
                passed=counts, failures=failures, experimental_all_passed=counts['saved-dt'] == 18,
                reset_control_bitexact=True, metrics_reproduced=True)


if __name__ == '__main__':
    print(json.dumps(replay(), indent=2))
