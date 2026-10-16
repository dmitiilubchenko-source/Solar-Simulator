"""Explicit-epoch edited-Solar runner; all physics remains in frozen helpers."""
from dataclasses import asdict
from importlib import import_module
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_edited_solar import CASES, fixture, oracle_check, within
from scripts.assess_edited_solar_month import (LEVELS, finite_states, reference_gate,
    candidate_metrics, endpoint_comparison, check_same_experiment, packet_check)
from scripts.assess_sandbox_models import independent_reference, load_oracle, figure_reference
from scripts.assess_sandbox_planets import states
from scripts.edited_j2 import verify_branch, variants, legacy_trajectory, checkpoint_check
from scripts.fixed_j2_ias import dop_trajectory
from scripts.newton_year import ROOT, NAMES, hashes, agreement
from solar_simulator.storage import to_document


def validate_epochs(times):
    values = np.asarray(times, dtype=float).copy()
    if (values.ndim != 1 or len(values) < 3 or not np.isfinite(values).all()
            or values[0] != 0. or not np.all(np.diff(values) > 0)):
        raise ValueError('Finite strictly increasing epochs must start at zero')
    return values


def check_regular(report, times, sources, inputs, dependencies):
    if (not report['complete'] or not report['checks_passed'] or report['grid'] != 'regular'
            or report['epochs_seconds'] != times.tolist()
            or report['source_sha256'] != sources or report['input_sha256'] != inputs
            or report['dependency_sha256'] != dependencies):
        raise ValueError('Incompatible or unqualified regular receipt')


def cross_grid(data, old, case, modes):
    comparisons = {mode: endpoint_comparison(data[case + '_' + mode], old[case + '_' + mode])
        for mode in modes}
    comparisons['reference'] = endpoint_comparison(data[case + '_reference_2'], old[case + '_reference_2'])
    passed = all(within(comparisons[n]['all_bodies'], 10., 1e-4)
        and within(comparisons[n]['moon_relative_to_earth'], .1, 1e-5) for n in modes)
    passed = bool(passed and within(comparisons['reference']['all_bodies'], 1., 1e-6)
        and within(comparisons['reference']['moon_relative_to_earth'], .01, 1e-7))
    return comparisons, passed


def run(output, *, times, grid, protocol, driver_sources, regular_receipt=None, regular_times=None):
    times = validate_epochs(times)
    if grid not in ('regular', 'shifted') or ((grid == 'shifted') != (regular_receipt is not None)):
        raise ValueError('Shifted grid requires a qualified regular receipt')
    if grid == 'shifted':
        regular_times = validate_epochs(regular_times)
        if not np.array_equal(times[[0, -1]], regular_times[[0, -1]]):
            raise ValueError('Different grid endpoint times')
    if Path.cwd().resolve() != ROOT:
        raise ValueError('Run from repository root; reference cache paths are relative')
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.tools'):
        raise ValueError('Research output must be inside project .tools')
    if any(output.with_suffix(s).exists() for s in ('.json', '.npz')):
        raise ValueError('Use fresh output; preserve previous receipts')
    cache_names = {case: output.parent.relative_to(ROOT / '.tools').as_posix()
        + '/' + output.stem + '-reference-' + case for case in CASES}
    cache_paths = {case: ROOT / '.tools' / (name + '.npz') for case, name in cache_names.items()}
    if any(p.exists() for p in cache_paths.values()):
        raise ValueError('Preserve existing reference caches')
    output.parent.mkdir(parents=True, exist_ok=True)
    prior_path = 'docs/edited-solar-month-validation.json'
    prior = json.loads((ROOT / prior_path).read_bytes())['measurements']['regular']
    if not prior['complete'] or not prior['checks_passed']:
        raise ValueError('Unqualified thirty-day predecessor')
    for group in ('source_sha256', 'input_sha256', 'dependency_sha256'):
        if hashes(prior[group]) != prior[group]:
            raise ValueError('Frozen predecessor source/input/actual dependency changed: ' + group)
    oracle = load_oracle()
    import scipy.integrate._ivp.rk as rk
    import scipy.integrate._ivp.base as base
    dependencies = hashes([ROOT / '.tools' / ('independent-eih-' + oracle.source_sha256[:16] + '.dll'),
        *(Path(import_module(n).__file__) for n in ('solar_native', 'solar_native.solar_native')),
        Path(rk.__file__), Path(base.__file__)])
    sources = hashes([*prior['source_sha256'], protocol, 'scripts/edited_solar_interval.py', *driver_sources])
    inputs = hashes([*prior['input_sha256'], prior_path])
    regular = None
    old_arrays = {}
    regular_binding = {}
    if regular_receipt is not None:
        regular_receipt = Path(regular_receipt).resolve()
        regular = json.loads(regular_receipt.read_bytes())
        check_regular(regular, regular_times, sources, inputs, dependencies)
        packet = regular_receipt.with_suffix('.npz')
        if hashes([packet]).popitem()[1] != regular['npz_sha256']:
            raise ValueError('Regular trajectory archive changed')
        regular_binding = hashes([regular_receipt, packet])
        with np.load(packet, allow_pickle=False) as data:
            old_arrays = {key: data[key].copy() for key in data.files}
    report = dict(protocol=protocol, grid=grid, epochs_seconds=times.tolist(), reference_levels=LEVELS,
        source_sha256=sources, input_sha256=inputs, dependency_sha256=dependencies,
        regular_receipt_sha256=regular_binding, scalar_oracle_source_sha256=oracle.source_sha256,
        compiler=oracle.compiler_version, cases={}, phase='references', complete=False, checks_passed=False,
        general_release=False, runtime_modified=False, jpl_comparison=False, source_integrals_verified=False)
    arrays = {}
    fixtures = {}

    def save():
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    save()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            for case in CASES:
                parent, branch, _ = fixture(case)
                seed = branch.child
                initial = states(seed.bodies)
                provenance = verify_branch(parent, branch)
                before = to_document(parent)
                fixtures[case] = (parent, branch, provenance, before)
                row = dict(provenance=provenance, settings=asdict(seed.settings),
                    masses_kg=[b.mass for b in seed.bodies], names=[b.name for b in seed.bodies],
                    oracle_snapshot=oracle_check(seed, oracle), candidates={})
                if tuple(row['names']) != NAMES:
                    raise ValueError('Wrong Solar order')
                report['cases'][case] = row
                arrays[case + '_initial'] = initial
                arrays[case + '_times'] = times
                calls = []

                def counted_figure(p, mu, figures, names, t, pair):
                    if t == 0.:
                        calls.append(0)
                    calls[-1] += 1
                    return figure_reference(p, mu, figures, names, t, pair)

                start = perf_counter()
                try:
                    expected, _ = independent_reference(seed.bodies, seed.settings.figures, times,
                        levels=LEVELS, cache_name=cache_names[case], acceleration_function=oracle,
                        figure_acceleration_function=counted_figure)
                finally:
                    row.update(reference_wall_seconds=perf_counter() - start, reference_rhs_calls=calls)
                    if cache_paths[case].exists():
                        row['reference_cache_sha256'] = hashes([cache_paths[case]]).popitem()[1]
                        with np.load(cache_paths[case], allow_pickle=False) as data:
                            np.testing.assert_array_equal(data['times'], times)
                            for key in data.files:
                                if key.startswith('level_'):
                                    arrays[case + '_reference_' + key.removeprefix('level_')] = data[key].copy()
                        save()
                for i in range(3):
                    finite_states(arrays[case + '_reference_' + str(i)], times)
                row['reference_comparisons'] = {f'{i-1}_to_{i}': agreement(
                    arrays[case + '_reference_' + str(i-1)], arrays[case + '_reference_' + str(i)], list(NAMES))
                    for i in (1, 2)}
                initial_error = agreement(expected[:1], initial[None], list(NAMES))
                ref_ok = reference_gate(row['reference_comparisons']['1_to_2'], initial_error, calls, row['oracle_snapshot'])
                row.update(reference_passed=ref_ok, reference_initial_roundtrip=initial_error,
                    samples=len(times), duration_seconds=float(times[-1]))
                if to_document(parent) != before or verify_branch(parent, branch) != provenance:
                    raise ValueError('Parent/child changed during reference')
                print(case, 'reference RHS', calls, 'passed', ref_ok, flush=True)
                save()
            report['all_references_qualified_before_candidates'] = all(r['reference_passed'] for r in report['cases'].values())
            if not report['all_references_qualified_before_candidates']:
                raise RuntimeError('Reference qualification failed; candidates not evaluated')
            report['phase'] = 'candidates'
            for case, (parent, branch, provenance, before) in fixtures.items():
                seed = branch.child
                row = report['cases'][case]
                initial = arrays[case + '_initial']
                expected = arrays[case + '_reference_2']
                versions = variants(seed)
                functions = {'legacy_python': lambda: legacy_trajectory(versions['python'], times),
                    'legacy_rust': lambda: legacy_trajectory(versions['rust'], times),
                    'continuous_rust': lambda: dop_trajectory(versions['rust'], times)}
                bounds = None
                for name, function in functions.items():
                    values, stats = function()
                    finite_states(values, times)
                    arrays[case + '_' + name] = values
                    save()
                    repeated, other = function()
                    np.testing.assert_array_equal(values, repeated)
                    np.testing.assert_array_equal(values[0], initial)
                    bounds = packet_check(stats, times, bounds)
                    packet_check(other, times, bounds)
                    measured = candidate_metrics(values, expected)
                    row['candidates'][name] = dict(**measured, statistics=stats, repeat_bitexact=True,
                        legacy_checkpoint_continue_exact=(checkpoint_check(versions[name.removeprefix('legacy_')],
                            float(times[len(times)//2])) if name.startswith('legacy_') else None))
                    print(case, name, measured['moon_relative_to_earth'], 'passed', measured['checks_passed'], flush=True)
                    save()
                durations = {name: [] for name in functions}
                for iteration in range(3):
                    for name in (list(functions) if iteration % 2 == 0 else list(reversed(functions))):
                        start = perf_counter()
                        values, stats = functions[name]()
                        elapsed = perf_counter() - start
                        np.testing.assert_array_equal(values, arrays[case + '_' + name])
                        packet_check(stats, times, bounds)
                        durations[name].append(elapsed)
                row['cost'] = {n: dict(seconds=v, median_seconds=median(v)) for n, v in durations.items()}
                if regular is not None:
                    check_same_experiment(row, regular['cases'][case])
                    np.testing.assert_array_equal(initial, old_arrays[case + '_initial'])
                    np.testing.assert_array_equal(old_arrays[case + '_times'], regular_times)
                    cross, cross_ok = cross_grid(arrays, old_arrays, case, functions)
                    row.update(cross_grid_endpoints=cross, cross_grid_passed=cross_ok)
                if to_document(parent) != before or verify_branch(parent, branch) != provenance:
                    raise ValueError('Parent/child changed during candidates')
                row.update(parent_child_preserved=True, packet_endpoints_equal=True)
                save()
            report['warnings'] = [str(w.message) for w in caught]
        if any(hashes(b) != b for b in (sources, inputs, dependencies, regular_binding)):
            raise ValueError('Source/input/actual dependency/regular receipt changed')
        report.update(phase='complete', complete=True, source_input_dependencies_unchanged=True,
            checks_passed=all(c['checks_passed'] and row.get('cross_grid_passed', True)
                for row in report['cases'].values() for c in row['candidates'].values()))
        save()
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    return report
