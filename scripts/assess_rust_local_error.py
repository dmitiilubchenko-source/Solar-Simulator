"""Independent one-step errors on every frozen337 attempt; no solver edits."""
import argparse
from decimal import Decimal as D, localcontext
import json
import math
from pathlib import Path
import platform
from time import perf_counter

import numpy as np
from scipy.integrate._ivp import dop853_coefficients as scipy_table

from scripts.assess_kepler_phase import ROOT, differences, maximum
from scripts.assess_rust_adaptive import provenance
from scripts.assess_rust_trace import sha, bits, coefficients
from scripts.audit_dop853_coefficients import SOURCE_SHA
from scripts.kepler_reference import propagate
from scripts.kepler_shadow import trace_grid, rk_step, relative_rhs

PROTOCOL = 'docs/rust-local-error-protocol.md'
TRACE = 'docs/rust-adaptive-trace-validation.json'
CACHE = 'docs/rust-adaptive-shadow-validation.json'
ORIGINAL = 'docs/rust-adaptive-prototype-validation.json'
RELATIVE = (3, 4, 5, 9, 10, 11)
METRICS = ('recorded_estimate', 'reconstructed_estimate', 'native_local_norm',
           'shadow_local_norm', 'native_position', 'native_velocity',
           'shadow_position', 'shadow_velocity', 'native_minus_shadow_position',
           'native_minus_shadow_velocity', 'oracle_precision_position',
           'oracle_precision_velocity', 'shadow_precision_position', 'shadow_precision_velocity')


def estimator_norms(e5, e3, h):
    """Independent Decimal evaluation from already normalized binary operands."""
    if (len(e5) != 12 or len(e3) != 12 or not math.isfinite(h) or h <= 0
            or not all(math.isfinite(x) for x in (*e5, *e3))):
        raise ValueError('Expected finite two-body normalized estimator operands')
    with localcontext() as context:
        context.prec = 110
        result = []
        for start in range(0, 12, 3):
            a2 = sum(D.from_float(x)**2 for x in e5[start:start+3])
            b2 = sum(D.from_float(x)**2 for x in e3[start:start+3])
            denominator = (3*(a2+D('0.01')*b2)).sqrt()
            result.append(D(0) if denominator == 0 else D.from_float(h)*a2/denominator)
        return result


def recorded_estimator(header, row, config):
    old, trial, stages = row['old'], row['trial'], row['k']
    if (len(old) != 12 or len(trial) != 12 or len(stages) != 13
            or any(len(k) != 12 for k in stages)
            or not all(math.isfinite(x) for x in (*old, *trial, *(x for k in stages for x in k)))):
        raise ValueError('Invalid two-body estimator trace shape/finiteness')
    scales, e5, e3 = [], [], []
    for i in range(12):
        atol = config['position_atol'] if i < 6 else config['velocity_atol']
        scale = atol+config['rtol']*max(abs(old[i]), abs(trial[i]))
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError('Invalid recorded scale')
        five = three = 0.
        for j in range(13):
            five += header['e5'][j]*stages[j][i]
            three += header['e3'][j]*stages[j][i]
        scales.append(scale)
        e5.append(five/scale)
        e3.append(three/scale)
    expected = max(estimator_norms(e5, e3, row['h']))
    observed = row['error']
    if not math.isfinite(observed) or observed < 0 or abs(float(expected)-observed) > 32*math.ulp(observed):
        raise ValueError('Recorded5(3) norm differs by more than32ULP')
    return scales, e5, e3, expected


def local_norm(actual, reference, scales):
    if (len(actual) != 6 or len(reference) != 6 or len(scales) != 6
            or any(not math.isfinite(x) or x <= 0 for x in scales)):
        raise ValueError('Expected six positive local scales')
    with localcontext() as context:
        context.prec = 110
        return max((sum(((actual[i]-reference[i])/D.from_float(scales[i]))**2
                        for i in range(start, start+3))/3).sqrt() for start in (0, 3))


def local_solutions(initial, h, a, b, mu):
    """Each orbit starts at this stored old, not at the previous oracle endpoint."""
    flow = {p: sum(propagate(initial[:3], initial[3:], mu, D.from_float(h), precision=p), ())
            for p in (70, 100)}
    shadow = {}
    for precision in (50, 80):
        with localcontext() as context:
            context.prec = precision
            shadow[precision] = rk_step(initial, D.from_float(h), a, b, lambda y: relative_rhs(y, mu))
    pair = lambda y: (y[:3], y[3:])
    oracle_difference = differences(pair(flow[70]), pair(flow[100]))
    shadow_difference = differences(pair(shadow[50]), pair(shadow[80]))
    if any(v['position_metres'] >= 1e-20 or v['velocity_m_per_s'] >= 1e-26
           for v in (oracle_difference, shadow_difference)):
        raise ArithmeticError('Local precision agreement failed')
    return flow, shadow, oracle_difference, shadow_difference


def run(output):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve prior local-error audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    load = lambda name: json.loads((ROOT/name).read_text(encoding='utf-8'))
    trace, cache, original = load(TRACE), load(CACHE), load(ORIGINAL)
    if (not trace['complete'] or not trace['all_modes_bitexact'] or not cache['complete']
            or len(trace['results']) != 9 or set(trace['results']) != set(cache['results'])):
        raise ValueError('Require complete337/338 and all nine cases')
    sources = {**trace['source_sha256'], **cache['source_sha256']}
    sources.update({name: sha(ROOT/name) for name in (PROTOCOL, 'scripts/assess_rust_local_error.py')})
    inputs = {**cache['input_sha256'], TRACE: sha(ROOT/TRACE), CACHE: sha(ROOT/CACHE)}
    coefficient_file = Path(scipy_table.__file__)
    inputs[str(coefficient_file)] = SOURCE_SHA
    def verify():
        for name, expected in {**sources, **inputs}.items():
            if sha(ROOT/name) != expected:
                raise ValueError('Changed bound source/input: '+name)
    verify()
    scipy_values = np.concatenate((scipy_table.A[:12, :12].ravel(), scipy_table.B,
                                   scipy_table.C[:12], scipy_table.E3, scipy_table.E5))
    if b''.join(map(bits, scipy_values)) != coefficients():
        raise ValueError('All194 Rust coefficients must match pinnedSciPy')
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, production_eligible=False, runtime_modified=False,
        global_error_bound=False, source_sha256=sources, input_sha256=inputs, provenance=snapshot,
        all194_coefficients_match=True, metric_columns=METRICS,
        environment=dict(python=platform.python_version(), numpy=np.__version__), results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    save()
    try:
        for name, evidence in trace['results'].items():
            stamp = perf_counter()
            old = original['results'][name]
            path = ROOT/evidence['trace_path']
            if sha(path) != evidence['trace_sha256']:
                raise ValueError('Changed337 trace')
            header, _, _ = trace_grid(path, old['baseline_statistics']['packet_endpoints'], old['rust_statistics'])
            a = tuple(tuple(D.from_float(x) for x in row) for row in header['a'])
            b = tuple(D.from_float(x) for x in header['b'])
            mu = D(cache['results'][name]['mu_exact'])
            columns = {key: [] for key in ('old', 'trial', 'flow70', 'flow100', 'shadow50', 'shadow80',
                                          'scales', 'e5', 'e3', 'times', 'accepted', 'metrics')}
            with path.open(encoding='utf-8') as stream:
                next(stream)
                for row in map(json.loads, stream):
                    if row['kind'] == 'finish':
                        break
                    scales, e5, e3, estimate = recorded_estimator(header, row, old['input_request'])
                    initial = tuple(D.from_float(row['old'][i]) for i in RELATIVE)
                    actual = tuple(D.from_float(row['trial'][i]) for i in RELATIVE)
                    flow, shadow, uncertainty, agreement = local_solutions(initial, row['h'], a, b, mu)
                    pair = lambda y: (y[:3], y[3:])
                    native_error = differences(pair(actual), pair(flow[100]))
                    shadow_error = differences(pair(shadow[80]), pair(flow[100]))
                    arithmetic = differences(pair(actual), pair(shadow[80]))
                    norm = lambda values: float(local_norm(values, flow[100], [scales[i] for i in RELATIVE]))
                    metrics = [row['error'], float(estimate), norm(actual), norm(shadow[80])]
                    for values in (native_error, shadow_error, arithmetic, uncertainty, agreement):
                        metrics.extend((values['position_metres'], values['velocity_m_per_s']))
                    columns['metrics'].append(metrics)
                    columns['old'].append([row['old'][i] for i in RELATIVE])
                    columns['trial'].append([row['trial'][i] for i in RELATIVE])
                    for label, values in (('flow70', flow[70]), ('flow100', flow[100]),
                                          ('shadow50', shadow[50]), ('shadow80', shadow[80])):
                        columns[label].append(list(map(str, values)))
                    for key, values in (('scales', scales), ('e5', e5), ('e3', e3)):
                        columns[key].append(values)
                    columns['times'].append([row['time'], row['next'], row['h']])
                    columns['accepted'].append(row['accepted'])
                    if len(columns['metrics']) % 100 == 0:
                        print(name, len(columns['metrics']), 'attempts', flush=True)
            metric = np.asarray(columns['metrics'], dtype=float)
            accepted = np.asarray(columns['accepted'], dtype=bool)
            if (int(accepted.sum()) != old['rust_statistics']['accepted']
                    or len(accepted)-int(accepted.sum()) != old['rust_statistics']['rejected']):
                raise ValueError('Attempt counts changed')
            summary = {}
            for label, mask in (('accepted', accepted), ('rejected', ~accepted)):
                values = metric[mask]
                summary[label] = dict(count=len(values),
                    maxima=dict(zip(METRICS, map(float, values.max(axis=0)))) if len(values) else {},
                    native_norm_above_one=int(np.count_nonzero(values[:, 2] > 1)),
                    shadow_norm_above_one=int(np.count_nonzero(values[:, 3] > 1)))
            report['results'][name] = dict(**summary, seconds=perf_counter()-stamp)
            for key, values in columns.items():
                arrays[name+'_'+key] = np.asarray(values)
            print(name, 'accepted', summary['accepted'], flush=True)
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
