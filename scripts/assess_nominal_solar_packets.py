"""Qualify the unchanged nominal strict year at actual twenty-hour endpoints."""
import argparse
from dataclasses import asdict, replace
from importlib import import_module
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_dense_jpl import residuals
from scripts.assess_edited_solar import oracle_check
from scripts.assess_edited_solar_month import (LEVELS, finite_states, reference_gate,
    candidate_metrics)
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.assess_sandbox_models import independent_reference, load_oracle, figure_reference
from scripts.assess_sandbox_planets import states
from scripts.edited_j2 import legacy_trajectory, checkpoint_check
from scripts.fixed_j2_ias import dop_trajectory
from scripts.fixed_j2_year import inputs, jpl_vectors
from scripts.newton_year import ROOT, NAMES, hashes, agreement
from scripts.verify_edited_solar_packets import check_packet_boundaries
from solar_simulator.storage import to_document, from_document

PROTOCOL = 'docs/nominal-solar-packet20-protocol.md'


def versions(seed):
    """Keep nominal calendar provenance; edited_j2.variants omits Origin."""
    return {name: replace(from_document(to_document(seed)),
        settings=replace(seed.settings, backend=name)) for name in ('python', 'rust')}


def shared_epochs(packet_times, prior_times):
    """Exact intersections only, including both endpoints; never nearest epochs."""
    np.testing.assert_array_equal(packet_times, epoch_grid())
    prior_times = np.asarray(prior_times, dtype=float)
    if (prior_times.ndim != 1 or len(prior_times) < 2 or not np.isfinite(prior_times).all()
            or not np.all(np.diff(prior_times) > 0)):
        raise ValueError('Invalid prior epoch grid')
    common, a, b = np.intersect1d(packet_times, prior_times, return_indices=True)
    if len(common) != 24 or common[0] != 0. or common[-1] != packet_times[-1]:
        raise ValueError('Expected 24 exactly shared nominal/JPL epochs')
    return common, a, b


def scope_qualified(reference_passed, candidates):
    modes = {'legacy_python', 'legacy_rust', 'continuous_rust'}
    return bool(reference_passed and set(candidates) == modes and all(
        row['checks_passed'] and row['physical_goals_passed'] for row in candidates.values()))


def run(output, raw_directory):
    if Path.cwd().resolve() != ROOT:
        raise ValueError('Run from repository root')
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.tools'):
        raise ValueError('Research output must be inside project .tools')
    cache_name = output.relative_to(ROOT / '.tools').as_posix() + '-reference'
    cache_path = ROOT / '.tools' / (cache_name + '.npz')
    if any(output.with_suffix(s).exists() for s in ('.json', '.npz')) or cache_path.exists():
        raise ValueError('Use fresh output; preserve earlier evidence')
    output.parent.mkdir(parents=True, exist_ok=True)
    seed, prior_times, prior_reference, prior_baseline, preflight = inputs()
    times = epoch_grid()
    common, a, b = shared_epochs(times, prior_times)
    prior = json.loads((ROOT / 'docs/edited-solar-month-validation.json').read_bytes())['measurements']['regular']
    for group in ('source_sha256', 'input_sha256', 'dependency_sha256'):
        if hashes(prior[group]) != prior[group]:
            raise ValueError('Frozen scientific predecessor changed: ' + group)
    oracle = load_oracle()
    import scipy.integrate._ivp.rk as rk
    import scipy.integrate._ivp.base as base
    dependencies = hashes([ROOT / '.tools' / ('independent-eih-' + oracle.source_sha256[:16] + '.dll'),
        *(Path(import_module(n).__file__) for n in ('solar_native', 'solar_native.solar_native')),
        Path(rk.__file__), Path(base.__file__)])
    sources = hashes([*prior['source_sha256'], PROTOCOL, 'scripts/assess_nominal_solar_packets.py',
        'tests/test_nominal_solar_packets.py', 'scripts/fixed_j2_year.py',
        'scripts/verify_edited_solar_packets.py'])
    bindings = hashes([*prior['input_sha256'], 'docs/edited-solar-month-validation.json',
        *preflight['inputs_sha256']])
    original = to_document(seed)
    arrays = dict(times=times, initial=states(seed.bodies))
    report = dict(protocol=PROTOCOL, complete=False, checks_passed=False, phase='reference',
        source_sha256=sources, input_sha256=bindings, dependency_sha256=dependencies,
        scalar_oracle_source_sha256=oracle.source_sha256, compiler=oracle.compiler_version,
        settings=asdict(seed.settings), origin=asdict(seed.origin), units='SI', names=list(NAMES),
        masses_kg=[body.mass for body in seed.bodies], epochs_seconds=times.tolist(),
        exact_shared_epochs_seconds=common.tolist(), preflight=preflight, reference_levels=LEVELS,
        oracle_snapshot=oracle_check(seed, oracle), candidates={}, runtime_modified=False,
        general_release=False, source_integrals_verified=False)

    def save():
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    save()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            calls = []

            def counted_figure(p, mu, figures, names, t, pair):
                if t == 0.:
                    calls.append(0)
                calls[-1] += 1
                return figure_reference(p, mu, figures, names, t, pair)

            start = perf_counter()
            try:
                expected, _ = independent_reference(seed.bodies, seed.settings.figures, times,
                    levels=LEVELS, cache_name=cache_name, acceleration_function=oracle,
                    figure_acceleration_function=counted_figure)
            finally:
                report.update(reference_wall_seconds=perf_counter() - start, reference_rhs_calls=calls)
                if cache_path.exists():
                    report['reference_cache_sha256'] = hashes([cache_path]).popitem()[1]
                    with np.load(cache_path, allow_pickle=False) as data:
                        np.testing.assert_array_equal(data['times'], times)
                        arrays.update({key: data[key].copy() for key in data.files if key.startswith('level_')})
                    save()
            for i in range(3):
                finite_states(arrays['level_' + str(i)], times)
            comparisons = {f'{i-1}_to_{i}': agreement(arrays['level_' + str(i-1)],
                arrays['level_' + str(i)], list(NAMES)) for i in (1, 2)}
            initial = agreement(expected[:1], arrays['initial'][None], list(NAMES))
            ref_ok = reference_gate(comparisons['1_to_2'], initial, calls, report['oracle_snapshot'])
            report.update(reference_passed=ref_ok, reference_comparisons=comparisons, reference_initial_roundtrip=initial)
            save()
            print('nominal reference RHS', calls, 'passed', ref_ok, flush=True)
            if not ref_ok:
                raise RuntimeError('Reference qualification failed; candidates not evaluated')
            report['phase'] = 'candidates'
            modes = versions(seed)
            functions = {'legacy_python': lambda: legacy_trajectory(modes['python'], times),
                'legacy_rust': lambda: legacy_trajectory(modes['rust'], times),
                'continuous_rust': lambda: dop_trajectory(modes['rust'], times)}
            for name, function in functions.items():
                values, stats = function()
                arrays[name] = values
                save()
                finite_states(values, times)
                np.testing.assert_array_equal(values[0], arrays['initial'])
                check_packet_boundaries(stats)
                repeated, other = function()
                np.testing.assert_array_equal(values.view(np.uint64), repeated.view(np.uint64))
                check_packet_boundaries(other)
                row = candidate_metrics(values, expected)
                row.update(statistics=stats, repeat_bitexact=True,
                    legacy_checkpoint_continue_exact=(checkpoint_check(modes[name.removeprefix('legacy_')],
                        float(times[len(times)//2])) if name.startswith('legacy_') else None))
                report['candidates'][name] = row
                print(name, row['all_bodies'], row['moon_relative_to_earth'], 'passed', row['checks_passed'], flush=True)
                save()
            durations = {name: [] for name in functions}
            for iteration in range(3):
                for name in (list(functions) if iteration % 2 == 0 else list(reversed(functions))):
                    start = perf_counter()
                    values, stats = functions[name]()
                    durations[name].append(perf_counter() - start)
                    np.testing.assert_array_equal(values.view(np.uint64), arrays[name].view(np.uint64))
                    check_packet_boundaries(stats)
            report['cost'] = {n: dict(seconds=v, median_seconds=median(v)) for n, v in durations.items()}
            # All candidate parameters and trajectories are frozen before reading JPL states.
            jpl, epochs, raw_hashes = jpl_vectors(seed, prior_times, raw_directory)
            report['jpl_raw_sha256'] = raw_hashes
            report['jpl_loaded_after_free_integration'] = True
            selected_epochs = [epochs[int(i)] for i in b]
            np.testing.assert_array_equal((np.array(selected_epochs) - seed.origin.epoch_jd_tdb) * 86400, common)
            arrays['jpl_shared'] = jpl[b]
            for name in functions:
                report['candidates'][name].update(residuals(arrays[name][a], jpl[b], list(NAMES), selected_epochs))
            report['previous_grid_diagnostics'] = {
                'reference': agreement(expected[a], prior_reference[b], list(NAMES)),
                'continuous_rust': agreement(arrays['continuous_rust'][a], prior_baseline[b], list(NAMES))}
            report['previous_grid_same_epoch_jpl'] = residuals(prior_baseline[b], jpl[b], list(NAMES), selected_epochs)
            report['warnings'] = [str(w.message) for w in caught]
        for group in (sources, bindings, dependencies, report['jpl_raw_sha256']):
            if hashes(group) != group:
                raise ValueError('Scientific source/input/actual dependency changed')
        if to_document(seed) != original:
            raise ValueError('Nominal initial experiment changed')
        inputs()
        report.update(phase='complete', complete=True, source_input_dependencies_unchanged=True,
            initial_experiment_preserved=True, checks_passed=scope_qualified(ref_ok, report['candidates']))
        save()
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    print('complete', output, 'qualified', report['checks_passed'], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--raw-cache', type=Path, required=True)
    args = parser.parse_args()
    if not run(args.output, args.raw_cache)['checks_passed']:
        raise RuntimeError('Nominal packet20 criteria failed; full evidence retained')


if __name__ == '__main__':
    main()
