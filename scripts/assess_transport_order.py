"""Two predeclared nonlinear attribution orders on the same frozen native steps."""
import argparse
from decimal import Decimal as D
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_kepler_phase import ROOT, differences, maximum
from scripts.assess_rust_adaptive import provenance
from scripts.assess_transport_split import split_increments
from scripts.kepler_shadow import exact_elapsed
from scripts.kepler_transport import (
    sha, public_path, load_public_inputs, accepted_nodes, flow, exact_difference, exact_sum, summarize,
)

PROTOCOL = 'docs/rust-transport-order-protocol.md'
CACHE = 'docs/rust-transport-split-validation.json'


def load_split(path, root=ROOT):
    root, path = Path(root).resolve(), Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Split cache must be inside project')
    report = json.loads(path.read_text(encoding='utf-8'))
    if (report.get('protocol') != 'docs/rust-transport-split-protocol.md' or not report.get('complete')
            or not report.get('source_unchanged') or not report.get('input_unchanged')
            or report.get('runtime_modified') is not False or report.get('production_eligible') is not False
            or report.get('ordered_split') is not True or report.get('unique_causal_attribution') is not False
            or len(report.get('results', {})) != 9):
        raise ValueError('Require complete350 ordered split')
    archive = public_path(root, report['sample_archive']) if 'sample_archive' in report else path.with_suffix('.npz')
    inputs = {**report['input_sha256'], path.relative_to(root).as_posix(): sha(path),
              archive.relative_to(root).as_posix(): report['npz_sha256']}
    for name, expected in {**report['source_sha256'], **inputs}.items():
        if sha(public_path(root, name)) != expected:
            raise ValueError('Changed split source/input: '+name)
    with np.load(archive, allow_pickle=False) as data:
        arrays = {key: data[key].copy() for key in data.files}
    return report, arrays, inputs


def reversed_step(exact_step, shadow, native):
    rk_defect = exact_difference(shadow, exact_step)
    native_defect = exact_difference(native, shadow)
    reverse = exact_sum([exact_step, native_defect])
    if exact_sum([reverse, rk_defect]) != tuple(native):
        raise ArithmeticError('Reversed local split endpoint changed')
    return reverse


def order_changes(old_rk, old_native, new_rk, new_native):
    if not (len(old_rk) == len(old_native) == len(new_rk) == len(new_native)) or not old_rk:
        raise ValueError('Order component counts differ')
    changes = []
    for a, b, c, d in zip(old_rk, old_native, new_rk, new_native):
        rk_change, native_change = exact_difference(c, a), exact_difference(d, b)
        if exact_sum([rk_change, native_change]) != (D(0),)*6:
            raise ArithmeticError('Order change does not cancel')
        changes.append(rk_change)
    return changes


def run(output, cache_path=ROOT/CACHE):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous order audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    old_report, old_arrays, inputs = load_split(cache_path)
    receipts, public, public_hashes = load_public_inputs()
    local_report, coarse_report, _ = receipts
    local, coarse, _ = public
    inputs.update(public_hashes)
    # The exact349 receipt used by350 may be a new raw run, not its public default.
    candidates = []
    for name in old_report['input_sha256']:
        if name.endswith('.json'):
            candidate = json.loads(public_path(ROOT, name).read_text(encoding='utf-8'))
            if candidate.get('protocol') == 'docs/rust-transport-protocol.md':
                candidates.append((name, candidate))
    if len(candidates) != 1:
        raise ValueError('Expected one bound349 cache')
    from scripts.assess_transport_split import load_transport
    _, native_arrays, bindings = load_transport(ROOT/candidates[0][0])
    inputs.update(bindings)
    if set(old_report['results']) != set(local_report['results']):
        raise ValueError('All nine cases required')
    sources = {**old_report['source_sha256'], PROTOCOL: sha(ROOT/PROTOCOL),
               'scripts/assess_transport_order.py': sha(Path(__file__))}
    def verify():
        for name, expected in {**sources, **inputs}.items():
            if sha(public_path(ROOT, name)) != expected:
                raise ValueError('Changed order source/input: '+name)
    verify()
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, production_eligible=False, runtime_modified=False,
        unique_causal_attribution=False, global_error_bound=False, source_sha256=sources,
        input_sha256=inputs, provenance=snapshot, results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    save()
    try:
        for name, old in old_report['results'].items():
            stamp = perf_counter()
            report['active_case'] = name
            save()
            case = {key[len(name)+1:]: value for key, value in local.items() if key.startswith(name+'_')}
            states, elapsed, times, ids = accepted_nodes(case)
            if (states.astype('>f8').tobytes() != native_arrays[name+'_native'].astype('>f8').tobytes()
                    or not np.array_equal(times, native_arrays[name+'_native_times'])
                    or not np.array_equal(ids, native_arrays[name+'_attempt_indices'])
                    or tuple(map(D, native_arrays[name+'_elapsed'])) != elapsed):
                raise ValueError('Order native inputs differ from349')
            decode = lambda array: [tuple(map(D, y)) for y in array]
            nodes = decode(native_arrays[name+'_transport100'])
            exact_steps = decode(case['flow100'][ids])
            shadow = decode(case['shadow80'][ids])
            native = [tuple(map(D.from_float, row)) for row in case['trial'][ids]]
            reverse_inputs = [reversed_step(a, r, n) for a, r, n in zip(exact_steps, shadow, native)]
            remaining = [exact_elapsed(F(elapsed[-1])-F(t)) for t in elapsed[1:]]
            mu = D(coarse_report['results'][name]['mu_exact'])
            transported, costs = {}, {}
            for precision in (70, 100):
                tick = perf_counter()
                transported[precision] = []
                for i, (state, dt) in enumerate(zip(reverse_inputs, remaining)):
                    transported[precision].append(flow(state, mu, dt, precision))
                    if i % 100 == 0:
                        print(name, 'reverse', precision, 'step', i, flush=True)
                costs[str(precision)] = perf_counter()-tick
            pair = lambda y: (y[:3], y[3:])
            agreement = maximum([differences(pair(a), pair(b)) for a, b in zip(transported[70], transported[100])])
            if agreement['position_metres'] >= 1e-20 or agreement['velocity_m_per_s'] >= 1e-26:
                raise ArithmeticError('Reverse transport precision check failed')
            native_first, rk_second = split_increments(nodes, transported[100])
            old_rk = decode(old_arrays[name+'_rk_increments'])
            old_native = decode(old_arrays[name+'_native_increments'])
            changes = order_changes(old_rk, old_native, rk_second, native_first)
            if changes[-1] != (D(0),)*6:
                raise ArithmeticError('Zero-remaining mixed difference must vanish')
            reference = tuple(map(D, coarse[name+'_prepared_oracle100'][-1]))
            delta = summarize(changes, reference)
            zero = (D(0),)*6
            per_step = maximum([differences(pair(row), pair(zero)) for row in changes])
            report['results'][name] = dict(steps=len(ids), precision_difference=agreement,
                original_rk_summary=old['rk_summary'], original_native_summary=old['native_summary'],
                reverse_rk_summary=summarize(rk_second, reference),
                reverse_native_summary=summarize(native_first, reference), change_summary=delta,
                per_step_maximum_change=per_step, all_order_identities_exact=True,
                last_step_change_exact_zero=True, diagnostic_stability_passed=(
                    delta['position_metres'] < 1e-6 and delta['velocity_m_per_s'] < 1e-12),
                costs=costs, seconds=perf_counter()-stamp)
            for key, rows in (('reverse70', transported[70]), ('reverse100', transported[100]),
                    ('reverse_rk_increments', rk_second), ('reverse_native_increments', native_first),
                    ('rk_order_change', changes)):
                arrays[name+'_'+key] = np.asarray([[str(x) for x in row] for row in rows])
            print(name, 'order delta', delta['position_metres'], delta['velocity_m_per_s'], flush=True)
            save()
        verify()
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.pop('active_case', None)
        report.update(complete=True, source_unchanged=True, input_unchanged=True,
            npz_sha256=sha(output.with_suffix('.npz')),
            all_diagnostic_stability_passed=all(r['diagnostic_stability_passed'] for r in report['results'].values()))
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cache', default=ROOT/CACHE, type=Path)
    args = parser.parse_args()
    report = run(args.output, args.cache)
    return 0 if report['all_diagnostic_stability_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
