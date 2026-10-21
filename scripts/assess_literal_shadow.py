"""Table-only Decimal sensitivity on the frozen338/339 grids; research only."""
import argparse
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import json
from pathlib import Path
import platform
from time import perf_counter

import numpy as np

from scripts.assess_kepler_phase import ROOT, differences, maximum
from scripts.assess_kepler_shadow import diagnostic_gate
from scripts.assess_rust_adaptive import provenance
from scripts.assess_rust_trace import sha
from scripts.assess_shadow_refinement import substep
from scripts.audit_dop853_coefficients import SOURCE_SHA
from scripts.kepler_shadow import rk_step, relative_rhs, exact_elapsed, invariant_drifts, trace_grid

PROTOCOL = 'docs/dop853-literal-shadow-protocol.md'
COEFFICIENTS = 'docs/dop853-coefficients-validation.json'
CACHE = 'docs/rust-adaptive-shadow-validation.json'
REFINEMENT = 'docs/rust-adaptive-refinement-validation.json'


def exact_decimal(value):
    result = D(value.numerator)/D(value.denominator)
    if F(result) != value:
        raise ArithmeticError('Coefficient does not fit exact Decimal precision')
    return result


def table_trajectory(initial, steps, times, a, b, mu, precision, divisor):
    if (precision not in (50, 80) or divisor not in (1, 2, 4) or len(times) < 2
            or times[0] != 0 or any(not np.isfinite(t) for t in times)
            or any(y <= x for x, y in zip(times, times[1:]))):
        raise ValueError('Use frozen forward epochs, precision50/80, subdivision1/2/4')
    state = tuple(initial)
    values, elapsed = [state], [D(0)]
    wanted = set(map(float, times[1:]))
    previous, clock = 0., F(0)
    with localcontext() as context:
        context.prec = precision
        ad = tuple(tuple(exact_decimal(x) for x in row) for row in a)
        bd = tuple(exact_decimal(x) for x in b)
        for next_time, h in steps:
            if not previous < next_time or h != next_time-previous:
                raise ValueError('Changed frozen macro grid')
            delta = D.from_float(h) if divisor == 1 else substep(h, divisor)
            for _ in range(divisor):
                state = rk_step(state, delta, ad, bd, lambda y: relative_rhs(y, mu))
            previous = next_time
            clock += F(h)
            if next_time in wanted:
                values.append(state)
                elapsed.append(exact_elapsed(clock))
    if len(values) != len(times) or previous != times[-1]:
        raise ValueError('Frozen grid misses an output epoch')
    return values, elapsed


def run(output):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous literal shadow')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    load = lambda name: json.loads((ROOT/name).read_text(encoding='utf-8'))
    cache, refinement, table = load(CACHE), load(REFINEMENT), load(COEFFICIENTS)
    if (not all(r['complete'] for r in (cache, refinement, table))
            or not table['abc_binary64_match'] or table['scipy_source_sha256'] != SOURCE_SHA
            or len(cache['results']) != 9 or set(cache['results']) != set(refinement['results'])):
        raise ValueError('Require complete pinned346/338/339 receipts and all nine cases')
    source = {**cache['source_sha256'], **refinement['source_sha256']}
    source.update({name: sha(ROOT/name) for name in (
        PROTOCOL, 'scripts/assess_literal_shadow.py', 'scripts/audit_dop853_coefficients.py')})
    if (source['scripts/audit_dop853_coefficients.py'] != table['audit_source_sha256']
            or sha(ROOT/'docs/dop853-coefficients-protocol.md') != table['protocol_sha256']):
        raise ValueError('Coefficient audit source/protocol changed')
    inputs = {**cache['input_sha256'], **refinement['input_sha256']}
    for receipt, name in ((cache, CACHE), (refinement, REFINEMENT)):
        archive = receipt['sample_archive']
        inputs[name] = sha(ROOT/name)
        inputs[archive] = receipt['npz_sha256']
    inputs[COEFFICIENTS] = sha(ROOT/COEFFICIENTS)
    def verify():
        for name, expected in {**source, **inputs}.items():
            if sha(ROOT/name) != expected:
                raise ValueError('Changed pinned source/input: '+name)
    verify()
    # Bind the exact337 receipt referred to by338 rather than guessing a raw path.
    candidates = [load(n) for n in cache['input_sha256'] if Path(n).suffix == '.json']
    traces = [r for r in candidates if r.get('protocol') == 'docs/rust-adaptive-trace-protocol.md']
    if len(traces) != 1 or set(traces[0]['results']) != set(cache['results']):
        raise ValueError('Require one matching337 trace receipt')
    trace = traces[0]
    original = load('docs/rust-adaptive-prototype-validation.json')
    with np.load(ROOT/cache['sample_archive'], allow_pickle=False) as data:
        coarse = {key: data[key].copy() for key in data.files}
    with np.load(ROOT/refinement['sample_archive'], allow_pickle=False) as data:
        refined = {key: data[key].copy() for key in data.files}
    a = tuple(tuple(map(F, row)) for row in table['decimal_literals']['a'])
    b = tuple(map(F, table['decimal_literals']['b']))
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, production_eligible=False, runtime_modified=False,
        source_sha256=source, input_sha256=inputs, provenance=snapshot,
        environment=dict(python=platform.python_version(), numpy=np.__version__), results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    save()
    try:
        for name, old in cache['results'].items():
            row = original['results'][name]
            path = ROOT/trace['results'][name]['trace_path']
            if sha(path) != trace['results'][name]['trace_sha256']:
                raise ValueError('Changed337 trace: '+name)
            header, initial, steps = trace_grid(path, row['baseline_statistics']['packet_endpoints'], row['rust_statistics'])
            times = coarse[name+'_times']
            if not np.array_equal(times, refined[name+'_times']):
                raise ValueError('Output epochs differ')
            mu = D(old['mu_exact'])
            decode = lambda values: [tuple(map(D, v)) for v in values]
            expected = {key: decode(coarse[name+'_'+key+'_oracle100']) for key in ('prepared', 'actual')}
            pair = lambda y: (y[:3], y[3:])
            variants = {}
            binary_a = tuple(tuple(F(x) for x in r) for r in header['a'])
            binary_b = tuple(map(F, header['b']))
            for divisor in (1, 2, 4):
                baseline = decode(coarse[name+'_shadow80'] if divisor == 1 else refined[f'{name}_d{divisor}_p80'])
                baseline_metrics = old if divisor == 1 else refinement['results'][name]['variants'][str(divisor)]
                for key in expected:
                    error = maximum([differences(pair(y), pair(r)) for y, r in zip(baseline, expected[key])])
                    if error != baseline_metrics[key+'_error']:
                        raise ValueError('Frozen binary error changed')
                stamp = perf_counter()
                replay, elapsed = table_trajectory(initial, steps, times, binary_a, binary_b, mu, 80, divisor)
                replay_seconds = perf_counter()-stamp
                if replay != baseline or list(map(str, elapsed)) != coarse[name+'_elapsed'].tolist():
                    raise ValueError('Binary80 replay or clock differs from338/339: '+name)
                values = {}
                stamp = perf_counter()
                for precision in (50, 80):
                    values[precision], clock = table_trajectory(initial, steps, times, a, b, mu, precision, divisor)
                    if clock != elapsed:
                        raise ValueError('Literal clock differs')
                    arrays[f'{name}_d{divisor}_p{precision}'] = np.array([[str(x) for x in y] for y in values[precision]])
                literal_seconds = perf_counter()-stamp
                convergence = maximum([differences(pair(x), pair(y)) for x, y in zip(values[50], values[80])])
                if convergence['position_metres'] >= 1e-6 or convergence['velocity_m_per_s'] >= 1e-12:
                    raise ArithmeticError('Literal precision50/80 check failed')
                drift = invariant_drifts(values[80], mu)
                summary = dict(binary80_replay_exact=True, binary80_seconds=replay_seconds,
                    literal50_80_seconds=literal_seconds, precision_difference=convergence,
                    relative_invariants=drift, macrosteps=len(steps), substeps=len(steps)*divisor,
                    baseline_prepared_error=baseline_metrics['prepared_error'],
                    baseline_actual_error=baseline_metrics['actual_error'])
                for key in expected:
                    errors = [differences(pair(y), pair(r)) for y, r in zip(values[80], expected[key])]
                    summary[key+'_error'] = maximum(errors)
                    summary['sampled_'+key+'_errors'] = errors
                    summary[key+'_diagnostic_gate'] = diagnostic_gate(maximum(errors), drift)
                variants[str(divisor)] = summary
            ratios = {quantity: [variants['1']['prepared_error'][quantity]/variants['2']['prepared_error'][quantity],
                                 variants['2']['prepared_error'][quantity]/variants['4']['prepared_error'][quantity]]
                      for quantity in ('position_metres', 'velocity_m_per_s')}
            report['results'][name] = dict(variants=variants, prepared_error_ratios=ratios,
                original_rust_gate=old['original_gate_passed'])
            for suffix in ('times', 'elapsed', 'prepared_oracle100', 'actual_oracle100'):
                arrays[name+'_'+suffix] = coarse[name+'_'+suffix]
            save()
            print(name, 'prepared ratios', ratios['position_metres'], flush=True)
        verify()
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.update(complete=True, source_unchanged=True, input_unchanged=True,
            npz_sha256=sha(output.with_suffix('.npz')),
            original_rust_passed=sum(r['original_rust_gate'] for r in report['results'].values()))
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
    report = run(args.output)
    return 0 if report['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
