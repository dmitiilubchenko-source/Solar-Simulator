"""All accepted native nodes transported analytically to the frozen final time."""
import argparse
from decimal import Decimal as D, localcontext
import json
from pathlib import Path
import platform
from time import perf_counter

import numpy as np

from scripts.assess_kepler_phase import ROOT, differences, maximum, decimal_relative
from scripts.assess_rust_adaptive import provenance
from scripts.kepler_transport import (
    sha, load_public_inputs, accepted_nodes, transport_rows, exact_difference, summarize,
)

PROTOCOL = 'docs/rust-transport-protocol.md'
SOURCE_NAMES = (PROTOCOL, 'scripts/assess_rust_transport.py', 'scripts/kepler_transport.py',
    'scripts/kepler_reference.py', 'scripts/kepler_shadow.py', 'scripts/assess_kepler_phase.py',
    'scripts/assess_rust_adaptive.py')


def run(output):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous transport audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    receipts, data, inputs = load_public_inputs()
    local, coarse, original = receipts
    raw, cache, old = data
    sources = {name: sha(ROOT/name) for name in SOURCE_NAMES}
    def verify():
        for name, digest in {**sources, **inputs}.items():
            if sha(ROOT/name) != digest:
                raise ValueError('Source/input changed: '+name)
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False, production_eligible=False,
        global_error_bound=False, telescoping_is_identity=True, source_sha256=sources,
        input_sha256=inputs, provenance=snapshot,
        environment=dict(python=platform.python_version(), numpy=np.__version__), results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    save()
    try:
        for name, evidence in local['results'].items():
            stamp = perf_counter()
            case = {key[len(name)+1:]: value for key, value in raw.items() if key.startswith(name+'_')}
            states, elapsed, native_times, indices = accepted_nodes(case)
            if (len(indices) != evidence['accepted']['count'] or len(case['accepted'])-len(indices) != evidence['rejected']['count']
                    or native_times[-1] != cache[name+'_times'][-1]):
                raise ValueError('Counts or final epoch changed')
            output_clocks = dict(zip(native_times, elapsed))
            if any(str(output_clocks[float(t)]) != c for t, c in zip(cache[name+'_times'], cache[name+'_elapsed'])):
                raise ValueError('Exact338 output clocks changed')
            prepared = [tuple(map(D, row)) for row in cache[name+'_prepared_oracle100']]
            actual = [tuple(map(D, row)) for row in cache[name+'_actual_oracle100']]
            if tuple(map(D.from_float, states[0])) != prepared[0]:
                raise ValueError('Prepared initial state changed')
            mu = D(coarse['results'][name]['mu_exact'])
            transported, costs = {}, {}
            for precision in (70, 100):
                tick = perf_counter()
                transported[precision] = transport_rows(states, elapsed, mu, precision,
                    lambda i: print(name, 'precision', precision, 'node', i, flush=True))
                costs[str(precision)] = perf_counter()-tick
            pair = lambda y: (y[:3], y[3:])
            agreement = maximum([differences(pair(a), pair(b)) for a, b in zip(transported[70], transported[100])])
            alignment = differences(pair(transported[100][0]), pair(prepared[-1]))
            if any(r['position_metres'] >= 1e-20 or r['velocity_m_per_s'] >= 1e-26 for r in (agreement, alignment)):
                raise ArithmeticError('Transport precision/reference check failed')
            high = transported[100]
            if high[-1] != tuple(map(D.from_float, states[-1])):
                raise ValueError('Zero-remaining endpoint changed')
            increments = [exact_difference(b, a) for a, b in zip(high, high[1:])]
            summary = summarize(increments, prepared[-1])
            if tuple(map(D, summary['total_vector'])) != exact_difference(high[-1], high[0]):
                raise ArithmeticError('Exact telescoping identity failed')
            with localcontext() as context:
                context.prec = 110
                physical = decimal_relative(old[name+'_rust'][-1])
                clock_offset = elapsed[-1]-D.from_float(float(native_times[-1]))
            report['results'][name] = dict(nodes=len(states), accepted=len(indices),
                exact_horizon_seconds=str(elapsed[-1]), horizon_minus_nominal_seconds=str(clock_offset),
                precision_difference=agreement, initial_reference_alignment=alignment,
                final_prepared_error=differences(pair(high[-1]), pair(prepared[-1])),
                final_actual_error=differences(pair(high[-1]), pair(actual[-1])),
                physical_export_difference=differences(pair(high[-1]), pair(physical)),
                transported_summary=summary, exact_telescoping=True,
                original_rust_gate=original['results'][name]['rust']['checks_passed'],
                transport_seconds=costs, seconds=perf_counter()-stamp)
            for key, values in (('native', states), ('elapsed', list(map(str, elapsed))),
                    ('native_times', native_times), ('attempt_indices', indices),
                    ('transport70', [[str(x) for x in y] for y in transported[70]]),
                    ('transport100', [[str(x) for x in y] for y in high]),
                    ('increments', [[str(x) for x in y] for y in increments])):
                arrays[name+'_'+key] = np.asarray(values)
            print(name, 'final', report['results'][name]['final_prepared_error'],
                  'parallel', summary['absolute_parallel_fraction'], flush=True)
            save()
        verify()
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
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
    args = parser.parse_args()
    run(args.output)


if __name__ == '__main__':
    main()
