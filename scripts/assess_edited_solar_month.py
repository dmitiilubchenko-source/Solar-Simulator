"""Thirty-day edited Solar: frozen equations, two declared output grids."""
import argparse
from dataclasses import asdict
from importlib import import_module
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_edited_solar import CASES, fixture, oracle_check, within
from scripts.assess_sandbox_models import independent_reference, load_oracle, figure_reference
from scripts.assess_sandbox_planets import states
from scripts.edited_j2 import verify_branch, variants, legacy_trajectory, checkpoint_check
from scripts.fixed_j2_ias import dop_trajectory
from scripts.newton_year import ROOT, NAMES, hashes, agreement, errors
from solar_simulator.storage import to_document

PROTOCOL = 'docs/edited-solar-month-protocol.md'
LEVELS = ((1e-13, 1800.), (3e-14, 900.), (3e-14, 450.))
DURATION = 30 * 86400.


def epoch_grid(grid):
    if grid == 'regular':
        return np.arange(0., DURATION + 1., 21600.)
    if grid == 'shifted':
        return np.r_[0., np.arange(10800., DURATION, 21600.), DURATION]
    raise ValueError('Undeclared thirty-day grid')


def finite_states(values, times):
    if values.shape != (len(times), len(NAMES), 6) or not np.isfinite(values).all():
        raise ValueError('Nonfinite or malformed trajectory')


def reference_gate(last, initial, calls, snapshot):
    return bool(len(calls) == 3 and calls[0] < calls[1] < calls[2]
        and within(last['all_bodies'], 1., 1e-6)
        and within(last['moon_relative_to_earth'], .01, 1e-7)
        and within(initial['all_bodies'], .002, 1e-8)
        and initial['moon_relative_to_earth']['position_metres'] < .0001
        and snapshot['checks_passed'])


def candidate_metrics(values, expected):
    per_body = {name: errors(values[:, i], expected[:, i]) for i, name in enumerate(NAMES)}
    comparison = agreement(values, expected, list(NAMES))
    return dict(**comparison, per_body=per_body, checks_passed=bool(
        all(within(e, 10., 1e-4) for e in per_body.values())
        and within(comparison['moon_relative_to_earth'], .1, 1e-5)))


def endpoint_comparison(current, previous):
    """Only endpoints are common; never interpolate candidate trajectories."""
    return agreement(current[[0, -1]], previous[[0, -1]], list(NAMES))


def check_same_experiment(current, previous):
    # asdict retains tuples; a JSON receipt decodes them as lists. Compare the
    # serialized values on both sides without changing any physical parameter.
    for key in ('provenance', 'settings', 'masses_kg', 'names'):
        canonical = lambda value: json.dumps(value, sort_keys=True, allow_nan=False)
        if canonical(current[key]) != canonical(previous[key]):
            raise ValueError('Different initial experiment across grids: ' + key)


def packet_check(stats, times, expected=None):
    bounds = stats['packet_endpoints']
    if (not stats['finished'] or stats['failed'] or not bounds or bounds[-1] != times[-1]
            or not np.all(np.diff(bounds) > 0) or not set(times[1:]).issubset(bounds)
            or (expected is not None and bounds != expected)):
        raise ValueError('Failed trajectory or different packet/output grid')
    return bounds


def run(output, grid, regular_receipt=None):
    times = epoch_grid(grid)
    if Path.cwd().resolve() != ROOT:
        raise ValueError('Run from the repository root; reference caches use relative paths')
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.tools'):
        raise ValueError('Research output must be inside project .tools')
    if any(output.with_suffix(s).exists() for s in ('.json', '.npz')):
        raise ValueError('Use fresh output; preserve prior receipts')
    if (grid == 'shifted') != (regular_receipt is not None):
        raise ValueError('Only shifted grid requires the qualified regular receipt')
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_names = {case: output.parent.relative_to(ROOT / '.tools').as_posix()
        + '/' + output.stem + '-reference-' + case for case in CASES}
    cache_paths = {case: ROOT / '.tools' / (name + '.npz') for case, name in cache_names.items()}
    if any(p.exists() for p in cache_paths.values()):
        raise ValueError('Preserve existing reference caches')
    prior_path = 'docs/edited-solar-validation.json'
    prior = json.loads((ROOT / prior_path).read_bytes())['measurements']
    if not prior['complete'] or not prior['checks_passed']:
        raise ValueError('Unqualified three-day parent protocol')
    for group in ('source_sha256', 'input_sha256', 'dependency_sha256'):
        if hashes(prior[group]) != prior[group]:
            raise ValueError('Frozen pilot source/input/actual dependency changed: ' + group)
    oracle = load_oracle()
    import scipy.integrate._ivp.rk as rk
    import scipy.integrate._ivp.base as base
    dependencies = hashes([ROOT / '.tools' / ('independent-eih-' + oracle.source_sha256[:16] + '.dll'),
        *(Path(import_module(n).__file__) for n in ('solar_native', 'solar_native.solar_native')),
        Path(rk.__file__), Path(base.__file__)])
    sources = hashes([*prior['source_sha256'], PROTOCOL,
        'scripts/assess_edited_solar_month.py', 'tests/test_edited_solar_month.py'])
    inputs = hashes([*prior['input_sha256'], prior_path])
    regular = None
    regular_arrays = {}
    regular_binding = {}
    if regular_receipt is not None:
        regular_receipt = Path(regular_receipt).resolve()
        regular = json.loads(regular_receipt.read_bytes())
        if (not regular['complete'] or not regular['checks_passed'] or regular['grid'] != 'regular'
                or regular['source_sha256'] != sources or regular['input_sha256'] != inputs
                or regular['dependency_sha256'] != dependencies):
            raise ValueError('Incompatible or unqualified regular receipt')
        packet = regular_receipt.with_suffix('.npz')
        if hashes([packet]).popitem()[1] != regular['npz_sha256']:
            raise ValueError('Regular trajectory archive changed')
        regular_binding = hashes([regular_receipt, packet])
        with np.load(packet, allow_pickle=False) as data:
            regular_arrays = {k: data[k].copy() for k in data.files}
    report = dict(protocol=PROTOCOL, grid=grid, reference_levels=LEVELS,
        source_sha256=sources, input_sha256=inputs, dependency_sha256=dependencies,
        regular_receipt_sha256=regular_binding, scalar_oracle_source_sha256=oracle.source_sha256,
        compiler=oracle.compiler_version, cases={}, complete=False, checks_passed=False,
        general_release=False, runtime_modified=False, jpl_comparison=False, source_integrals_verified=False)
    arrays = {}

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
                            for i in range(len(calls)):
                                key = 'level_' + str(i)
                                if key in data:
                                    arrays[case + '_reference_' + str(i)] = data[key].copy()
                        save()
                for i in range(3):
                    finite_states(arrays[case + '_reference_' + str(i)], times)
                row['reference_comparisons'] = {f'{i-1}_to_{i}': agreement(
                    arrays[case + '_reference_' + str(i-1)], arrays[case + '_reference_' + str(i)], list(NAMES))
                    for i in (1, 2)}
                initial_error = agreement(expected[:1], initial[None], list(NAMES))
                ref_ok = reference_gate(row['reference_comparisons']['1_to_2'], initial_error, calls, row['oracle_snapshot'])
                row.update(reference_passed=ref_ok, reference_initial_roundtrip=initial_error)
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
                    measured['checks_passed'] = bool(ref_ok and measured['checks_passed'])
                    row['candidates'][name] = dict(**measured, statistics=stats, repeat_bitexact=True,
                        legacy_checkpoint_continue_exact=(checkpoint_check(versions[name.removeprefix('legacy_')],
                            float(times[len(times)//2])) if name.startswith('legacy_') else None))
                    print(case, name, measured['moon_relative_to_earth'], 'passed', measured['checks_passed'], flush=True)
                    save()
                durations = {n: [] for n in functions}
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
                    old = regular['cases'][case]
                    check_same_experiment(row, old)
                    np.testing.assert_array_equal(initial, regular_arrays[case + '_initial'])
                    np.testing.assert_array_equal(regular_arrays[case + '_times'], epoch_grid('regular'))
                    cross = {name: endpoint_comparison(arrays[case + '_' + name], regular_arrays[case + '_' + name])
                        for name in functions}
                    cross['reference'] = endpoint_comparison(expected, regular_arrays[case + '_reference_2'])
                    cross_ok = all(within(cross[n]['all_bodies'], 10., 1e-4)
                        and within(cross[n]['moon_relative_to_earth'], .1, 1e-5) for n in functions)
                    cross_ok = bool(cross_ok and within(cross['reference']['all_bodies'], 1., 1e-6)
                        and within(cross['reference']['moon_relative_to_earth'], .01, 1e-7))
                    row.update(cross_grid_endpoints=cross, cross_grid_passed=cross_ok)
                if to_document(parent) != before or verify_branch(parent, branch) != provenance:
                    raise ValueError('Parent or child changed')
                row.update(parent_child_preserved=True, packet_endpoints_equal=True,
                    samples=len(times), duration_seconds=float(times[-1]))
                save()
            report['warnings'] = [str(w.message) for w in caught]
        if any(hashes(b) != b for b in (sources, inputs, dependencies, regular_binding)):
            raise ValueError('Source/input/actual dependency/regular receipt changed')
        report.update(complete=True, source_input_dependencies_unchanged=True,
            checks_passed=all(c['checks_passed'] and row.get('cross_grid_passed', True)
                for row in report['cases'].values() for c in row['candidates'].values()))
        save()
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--grid', choices=('regular', 'shifted'), required=True)
    parser.add_argument('--regular-receipt', type=Path)
    args = parser.parse_args()
    if not run(args.output, args.grid, args.regular_receipt)['checks_passed']:
        raise RuntimeError('Thirty-day criteria failed; receipts preserved')


if __name__ == '__main__':
    main()
