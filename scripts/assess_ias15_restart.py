"""Predeclared nine-case IAS15 cold-restart experiment, outside runtime."""
import argparse
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import platform
import statistics
import tarfile
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_kepler_phase import ROOT, decimal_relative, differences, maximum
from scripts.assess_rust_adaptive import provenance
from scripts.ias15_reference import load_library, library_hashes, EPSILONS
from scripts.ias15_restart import MODES, bits, trajectory
from scripts.kepler_shadow import exact_elapsed
from scripts.kepler_transport import load_public_inputs, flow, sha
from solar_simulator.experiment import Settings, create_experiment
from solar_simulator.simulation import Body, G
from solar_simulator.vector3 import Vector3

PROTOCOL = 'docs/ias15-restart-protocol.md'
LIBRARY_RECEIPT = 'docs/ias15-comparison-validation.json'


def load_cases(root=ROOT):
    receipts, archives, hashes = load_public_inputs(root)
    shadow, original = receipts[1], receipts[2]
    high, native = archives[1], archives[2]
    cases = {}
    for name, row in original['results'].items():
        request = row['input_request']
        encoded = json.dumps(request, allow_nan=False).encode('utf-8')
        initial, times = np.asarray(request['states']), np.asarray(request['times'])
        expected_size = 82 if name.startswith('holdout_') else 60
        if (hashlib.sha256(encoded).hexdigest() != row['input_request_sha256']
                or hashlib.sha256(bits(initial)).hexdigest() != row['initial_sha256']
                or hashlib.sha256(bits(times)).hexdigest() != row['epochs_sha256']
                or bits(initial) != bits(native[name+'_baseline'][0])
                or bits(times) != bits(native[name+'_times'])
                or bits(times) != bits(high[name+'_times']) or len(times) != expected_size):
            raise ValueError('Changed physical IC or epoch request: '+name)
        uncertainty = shadow['results'][name]['actual_oracle_uncertainty']
        if uncertainty['position_metres'] >= 1e-6 or uncertainty['velocity_m_per_s'] >= 1e-12:
            raise ValueError('Original actual oracle uncertainty exceeds protocol')
        expected = [tuple(map(D, y)) for y in high[name+'_actual_oracle100']]
        with localcontext() as context:
            context.prec = 110
            if decimal_relative(initial) != expected[0]:
                raise ValueError('Actual oracle initial state changed')
            mu = D.from_float(G)*sum(map(D.from_float, request['masses']))
        bodies = [Body(str(i), float(mass), Vector3(*q[:3]), Vector3(*q[3:]))
                  for i, (mass, q) in enumerate(zip(request['masses'], initial))]
        # This seed is only used by existing invariant metrics, never an IAS15 recipe.
        seed = create_experiment(bodies, Settings(request['packet_dt']))
        cases[name] = dict(request=request, initial=initial, times=times, expected=expected,
            mu=mu, seed=seed, origin=row['input_request_sha256'], oracle_uncertainty=uncertainty)
    return cases, hashes


def compare(values, expected, times):
    with localcontext() as context:
        context.prec = 110
        relative = [decimal_relative(y) for y in values]
    rows = [differences((y[:3], y[3:]), (z[:3], z[3:])) for y, z in zip(relative, expected)]
    if len(relative) != len(expected) or len(times) != len(rows) or not rows:
        raise ValueError('Comparison lengths differ')
    return dict(**maximum(rows), sampled_errors=rows,
        worst_position_time_seconds=float(times[max(range(len(rows)), key=lambda i: rows[i]['position_metres'])]),
        worst_velocity_time_seconds=float(times[max(range(len(rows)), key=lambda i: rows[i]['velocity_m_per_s'])]))


def restart_oracle(state, masses, times, start):
    with localcontext() as context:
        context.prec = 110
        initial = decimal_relative(state)
        mu = D.from_float(G)*sum(D.from_float(float(m)) for m in masses)
    elapsed = [exact_elapsed(F(float(t))-F(float(start))) for t in times]
    result = {p: [flow(initial, mu, t, p) for t in elapsed] for p in (70, 100)}
    precision = maximum([differences((a[:3], a[3:]), (b[:3], b[3:]))
                         for a, b in zip(result[70], result[100])])
    if precision['position_metres'] >= 1e-6 or precision['velocity_m_per_s'] >= 1e-12:
        raise ArithmeticError('Restarted oracle precision check failed')
    return result, precision


def sources():
    names = [PROTOCOL, 'scripts/ias15_restart.py', 'scripts/assess_ias15_restart.py',
        'scripts/ias15_reference.py', 'scripts/assess_ias15.py', 'scripts/assess_kepler_phase.py',
        'scripts/kepler_reference.py', 'scripts/kepler_roundoff.py', 'scripts/kepler_shadow.py',
        'scripts/kepler_transport.py', 'scripts/assess_continuous.py', 'scripts/assess_sandbox_planets.py',
        'scripts/assess_rust_adaptive.py', 'requirements/research-ias15.txt']
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    return {name: sha(ROOT/name) for name in sorted(set(names))}


def equal_runs(a, b):
    if bits(a[0]) != bits(b[0]):
        raise ArithmeticError('Repeated IAS15 physical output changed')
    for key in a[2]:
        x, y = a[2][key], b[2][key]
        if x.dtype.kind == 'f':
            same = x.shape == y.shape and bits(x) == bits(y)
        else:
            same = np.array_equal(x, y)
        if not same:
            raise ArithmeticError('Repeated checkpoint artifact changed: '+key)
    if {k:v for k,v in a[1].items() if k != 'force_evaluations'} != {k:v for k,v in b[1].items() if k != 'force_evaluations'}:
        raise ArithmeticError('Repeated IAS15 counters changed')


def run(output, library_directory, source_archive=None):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous restart results')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    cases, inputs = load_cases()
    library = load_library(library_directory)
    external = library_hashes(library)
    receipt_path = ROOT/LIBRARY_RECEIPT
    old = json.loads(receipt_path.read_text(encoding='utf-8'))
    if external != old['library_files_sha256']:
        raise ValueError('Research library differs from pinned 5.2.2 bytes')
    inputs[LIBRARY_RECEIPT] = sha(receipt_path)
    review_name = 'docs/integrator-candidate-review.json'
    review = json.loads((ROOT/review_name).read_text(encoding='utf-8'))
    if source_archive is None:
        raise ValueError('Explicit pinned REBOUND source archive required')
    source_archive = Path(source_archive).resolve()
    archive_sha = review['sdist']['sha256']
    if sha(source_archive) != archive_sha:
        raise ValueError('REBOUND source archive SHA mismatch')
    with tarfile.open(source_archive, 'r:gz') as archive:
        for name, row in review['upstream_files'].items():
            data = archive.extractfile('rebound-5.2.2/'+name).read()
            if hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Changed pinned REBOUND source: '+name)
    inputs[review_name] = sha(ROOT/review_name)
    source = sources()
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False, production_eligible=False,
        solver='IAS15 research', model='Newtonian two point masses / SI / inertial 3D / model t0=0',
        source_sha256=source, input_sha256=inputs, library_files_sha256=external,
        external_source_archive_sha256=archive_sha,
        environment=dict(python=platform.python_version(), numpy=np.__version__, rebound=library.__version__),
        provenance=snapshot, results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    def verify():
        for name, expected in {**source, **inputs}.items():
            if sha(ROOT/name) != expected:
                raise ValueError('Changed restart source/input: '+name)
        if library_hashes(library) != external:
            raise ValueError('Changed research library during audit')
        if sha(source_archive) != archive_sha:
            raise ValueError('Changed REBOUND source archive during audit')
    save()
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            for name, case in cases.items():
                report['active_case'] = name
                save()
                req, times = case['request'], case['times']
                def operation(epsilon, mode, counted=False):
                    return trajectory(req['masses'], case['initial'], times, req['packet_dt'],
                                      library, epsilon, mode, case['origin'], count_forces=counted)
                results = {}
                arrays[name+'__times'] = times
                arrays[name+'__original_oracle100'] = np.asarray([[str(x) for x in y] for y in case['expected']])
                for epsilon in EPSILONS:
                    epsilon_key = str(epsilon)
                    runs, costs = {}, {mode:[] for mode in MODES}
                    for mode in MODES:
                        operation(epsilon, mode)  # excluded warmup
                    for repetition in range(3):
                        for mode in MODES[repetition:]+MODES[:repetition]:
                            tick = perf_counter()
                            result = operation(epsilon, mode)
                            costs[mode].append(perf_counter()-tick)
                            if mode in runs:
                                equal_runs(runs[mode], result)
                            else:
                                runs[mode] = result
                    for mode in MODES:
                        counted = operation(epsilon, mode, True)
                        equal_runs(runs[mode], counted)
                        values, stats, artifacts = runs[mode]
                        if bits(artifacts['packet_endpoints']) != bits(runs['warm'][2]['packet_endpoints']):
                            raise ArithmeticError('Restart changed packet endpoint grid')
                        stats = dict(stats, force_evaluations=counted[1]['force_evaluations'])
                        prefix = name+'__'+epsilon_key+'__'+mode+'__'
                        arrays[prefix+'values'] = values
                        for key, value in artifacts.items():
                            arrays[prefix+key] = value
                        expected = [(y[:3], y[3:]) for y in case['expected']]
                        row = dict(metrics=metrics(case['seed'], times, values, expected), statistics=stats,
                            seconds=costs[mode], median_seconds=statistics.median(costs[mode]),
                            repeat_bitexact=True, counter_bitexact=True,
                            cold_minus_warm=compare(values, [decimal_relative_guard(y) for y in runs['warm'][0]], times))
                        if mode == 'one-cold':
                            index = stats['restart_output_index']
                            if bits(values[:index+1]) != bits(runs['warm'][0][:index+1]):
                                raise ArithmeticError('One-cold prefix differs before restart')
                            oracle, precision = restart_oracle(values[index], req['masses'], times[index:], times[index])
                            for p, data in oracle.items():
                                arrays[prefix+'restart_oracle'+str(p)] = np.asarray([[str(x) for x in y] for y in data])
                            inherited = maximum([differences((a[:3], a[3:]), (b[:3], b[3:]))
                                for a, b in zip(oracle[100], case['expected'][index:])])
                            row['restart_diagnostics'] = dict(index=index, time=float(times[index]),
                                precision_difference=precision, inherited_oracle_difference=inherited,
                                post_restart_error=compare(values[index:], oracle[100], times[index:]),
                                prefix_bitexact=True)
                        results[epsilon_key+'__'+mode] = row
                        print(name, epsilon_key, mode, row['metrics']['checks_passed'],
                              row['metrics']['position_metres'], row['metrics']['velocity_m_per_s'], flush=True)
                report['results'][name] = dict(request=req, origin=case['origin'],
                    original_oracle_uncertainty=case['oracle_uncertainty'], modes=results)
                save()
            report['warnings'] = [str(w.message) for w in captured]
        verify()
        report.update(complete=True, source_unchanged=True, input_unchanged=True, library_unchanged=True,
            all_checks_passed=all(row['metrics']['checks_passed'] for case in report['results'].values()
                                  for row in case['modes'].values()))
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if arrays:
            np.savez_compressed(output.with_suffix('.npz'), **arrays)
            report['npz_sha256'] = sha(output.with_suffix('.npz'))
        report.pop('active_case', None) if report['complete'] else None
        report['wall_seconds'] = perf_counter()-start
        save()
    return report


def decimal_relative_guard(value):
    with localcontext() as context:
        context.prec = 110
        return decimal_relative(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--source-archive', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output, args.library, args.source_archive)
    return 0 if result['all_checks_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
