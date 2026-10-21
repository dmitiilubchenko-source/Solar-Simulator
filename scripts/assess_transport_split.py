"""Fixed ordered nonlinear split on native nodes; not a unique cause attribution."""
import argparse
from decimal import Decimal as D
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_kepler_phase import ROOT, differences, maximum
from scripts.assess_rust_adaptive import provenance
from scripts.kepler_shadow import exact_elapsed
from scripts.kepler_transport import (
    sha, public_path, load_public_inputs, accepted_nodes, flow, exact_difference, exact_sum, summarize,
)

PROTOCOL = 'docs/rust-transport-split-protocol.md'
CACHE = 'docs/rust-transport-validation.json'


def load_transport(path, root=ROOT):
    root, path = Path(root).resolve(), Path(path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Transport cache must be inside project')
    report = json.loads(path.read_text(encoding='utf-8'))
    if (report.get('protocol') != 'docs/rust-transport-protocol.md' or not report.get('complete')
            or not report.get('source_unchanged') or not report.get('input_unchanged')
            or report.get('runtime_modified') is not False or report.get('production_eligible') is not False
            or report.get('telescoping_is_identity') is not True or len(report.get('results', {})) != 9):
        raise ValueError('Require complete349 diagnostic transport')
    archive = public_path(root, report['sample_archive']) if 'sample_archive' in report else path.with_suffix('.npz')
    inputs = {**report['input_sha256'], path.relative_to(root).as_posix(): sha(path),
              archive.relative_to(root).as_posix(): report['npz_sha256']}
    for name, expected in {**report['source_sha256'], **inputs}.items():
        if sha(public_path(root, name)) != expected:
            raise ValueError('Changed transport source/input: '+name)
    with np.load(archive, allow_pickle=False) as data:
        values = {key: data[key].copy() for key in data.files}
    return report, values, inputs


def split_increments(native_transport, middle):
    if len(native_transport) != len(middle)+1 or not middle:
        raise ValueError('Split node counts differ')
    rk = [exact_difference(w, z) for z, w in zip(native_transport, middle)]
    native = [exact_difference(z, w) for z, w in zip(native_transport[1:], middle)]
    for i, (a, b) in enumerate(zip(rk, native)):
        if exact_sum([a, b]) != exact_difference(native_transport[i+1], native_transport[i]):
            raise ArithmeticError('Ordered split identity failed')
    return rk, native


def run(output, cache_path=ROOT/CACHE):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous transport split')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    old_report, transported, inputs = load_transport(cache_path)
    receipts, public, public_hashes = load_public_inputs()
    local_report, coarse_report, _ = receipts
    local, coarse, _ = public
    inputs.update(public_hashes)
    if set(old_report['results']) != set(local_report['results']):
        raise ValueError('All nine transport cases required')
    sources = {**old_report['source_sha256'], PROTOCOL: sha(ROOT/PROTOCOL),
               'scripts/assess_transport_split.py': sha(Path(__file__))}
    def verify():
        for name, expected in {**sources, **inputs}.items():
            if sha(public_path(ROOT, name)) != expected:
                raise ValueError('Changed split source/input: '+name)
    verify()
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, production_eligible=False, runtime_modified=False,
        ordered_split=True, unique_causal_attribution=False, global_error_bound=False,
        source_sha256=sources, input_sha256=inputs, provenance=snapshot, results={})
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
            states, elapsed, times, indices = accepted_nodes(case)
            if (states.astype('>f8').tobytes() != transported[name+'_native'].astype('>f8').tobytes()
                    or not np.array_equal(times, transported[name+'_native_times'])
                    or not np.array_equal(indices, transported[name+'_attempt_indices'])
                    or tuple(map(D, transported[name+'_elapsed'])) != elapsed):
                raise ValueError('Native350 sequence differs from349')
            decode = lambda array: [tuple(map(D, row)) for row in array]
            nodes = decode(transported[name+'_transport100'])
            expected_increments = decode(transported[name+'_increments'])
            shadow = decode(case['shadow80'][indices])
            exact_step = decode(case['flow100'][indices])
            remaining = [exact_elapsed(F(elapsed[-1])-F(t)) for t in elapsed[1:]]
            mu = D(coarse_report['results'][name]['mu_exact'])
            middle, costs = {}, {}
            for precision in (70, 100):
                tick = perf_counter()
                middle[precision] = []
                for i, (state, dt) in enumerate(zip(shadow, remaining)):
                    middle[precision].append(flow(state, mu, dt, precision))
                    if i % 100 == 0:
                        print(name, 'middle', precision, 'step', i, flush=True)
                costs['middle'+str(precision)] = perf_counter()-tick
            pair = lambda y: (y[:3], y[3:])
            agreement = maximum([differences(pair(a), pair(b)) for a, b in zip(middle[70], middle[100])])
            tick = perf_counter()
            semigroup = []
            for i, (state, dt) in enumerate(zip(exact_step, remaining)):
                semigroup.append(flow(state, mu, dt, 100))
                if i % 100 == 0:
                    print(name, 'semigroup', 'step', i, flush=True)
            costs['semigroup100'] = perf_counter()-tick
            composition = maximum([differences(pair(a), pair(b)) for a, b in zip(semigroup, nodes[:-1])])
            if any(r['position_metres'] >= 1e-20 or r['velocity_m_per_s'] >= 1e-26 for r in (agreement, composition)):
                raise ArithmeticError('Split precision/semigroup check failed')
            rk, native = split_increments(nodes, middle[100])
            if [exact_sum([a, b]) for a, b in zip(rk, native)] != expected_increments:
                raise ArithmeticError('Split differs from349 increments')
            rk_total, native_total = exact_sum(rk), exact_sum(native)
            target = tuple(map(D, old['transported_summary']['total_vector']))
            if exact_sum([rk_total, native_total]) != target:
                raise ArithmeticError('Split total differs from349')
            reference = tuple(map(D, coarse[name+'_prepared_oracle100'][-1]))
            report['results'][name] = dict(steps=len(indices), precision_difference=agreement,
                semigroup_difference=composition, rk_summary=summarize(rk, reference),
                native_summary=summarize(native, reference),
                original_total=old['transported_summary'], all_split_identities_exact=True,
                costs=costs, seconds=perf_counter()-stamp)
            for key, values in (('middle70', middle[70]), ('middle100', middle[100]),
                    ('semigroup100', semigroup), ('rk_increments', rk), ('native_increments', native)):
                arrays[name+'_'+key] = np.asarray([[str(x) for x in row] for row in values])
            print(name, 'RK', report['results'][name]['rk_summary']['signed_parallel_metres'],
                  'native', report['results'][name]['native_summary']['signed_parallel_metres'], flush=True)
            save()
        verify()
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.pop('active_case', None)
        report.update(complete=True, source_unchanged=True, input_unchanged=True,
            npz_sha256=sha(output.with_suffix('.npz')))
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
    run(args.output, args.cache)


if __name__ == '__main__':
    main()
