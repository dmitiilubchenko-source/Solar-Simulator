"""Protocol359: qualified RK45 caches and controlled IAS15 C/native force swap."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import statistics
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.assess_ias15_native_newton import cargo_hashes, same_array
from scripts.assess_newton_year import candidate_metrics
from scripts.assess_rust_adaptive import provenance
from scripts.assess_sandbox_planets import states
from scripts.ias15_native_newton import MODES
from scripts.ias15_reference import EPSILONS, library_hashes, load_library
from scripts.ias15_restart import bits
from scripts.kepler_transport import ROOT, sha
from scripts.native_audit import require_native
from scripts.native_newton_year import force_metrics, trajectory
from scripts.newton_year import INPUTS, LEVELS, NAMES, agreement, ias_trajectory, reference
from scripts.newton_year_cache import ARCHIVES, RECEIPT, load
from solar_simulator.native_forces import prepare

PROTOCOL = 'docs/native-newton-year-protocol.md'
NATIVE_RECEIPT = 'docs/ias15-native-newton-validation.json'
OLD_KEYS = {1e-9:'ias15_1e-9', 1e-11:'ias15_1e-11'}


def equal_runs(a, b):
    if not same_array(a[0], b[0]) or any(not same_array(a[2][k], b[2][k]) for k in a[2]):
        raise ArithmeticError('N-body arrays changed between repeats/counter runs')
    if {k:v for k,v in a[1].items() if k != 'force_evaluations'} != {k:v for k,v in b[1].items() if k != 'force_evaluations'}:
        raise ArithmeticError('N-body steps/settings changed between repeats')


def run(output, library_directory, source_archive):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous N-body qualification')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    seed, profiles, qualified, historical = load()
    library = load_library(library_directory)
    external, native = library_hashes(library), require_native()
    native['sha256'] = sha(Path(native['extension']))
    previous = json.loads((ROOT/NATIVE_RECEIPT).read_text(encoding='utf-8'))
    if (external != historical['year']['library_sha256'] or external != previous['library_files_sha256']
            or native != previous['native'] or sha(source_archive) != previous['external_source_archive_sha256']):
        raise ValueError('Changed IAS15/native binary or sdist')
    versions = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__)
    if any(any(row['environment'][k] != v for k,v in versions.items()) for row in (historical['pilot'], historical['year'])):
        raise ValueError('Changed numerical environment; do not reuse RK45 qualification silently')
    names = [PROTOCOL, 'scripts/native_newton_year.py', 'scripts/newton_year_cache.py',
        'scripts/assess_native_newton_year.py', 'scripts/replay_native_newton_year.py',
        'scripts/newton_year.py', 'scripts/assess_newton_year.py', 'scripts/assess_sandbox_planets.py',
        'scripts/ias15_native_newton.py', 'scripts/ias15_reference.py', 'scripts/ias15_restart.py',
        'scripts/native_audit.py', 'scripts/kepler_transport.py', 'scripts/assess_rust_adaptive.py',
        'tests/test_native_newton_year.py', 'tests/test_newton_year.py']
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'rust').rglob('*.rs') if 'target' not in p.parts]
    source = {name:sha(ROOT/name) for name in names}
    inputs = {name:sha(ROOT/name) for name in (*INPUTS, RECEIPT, NATIVE_RECEIPT, *ARCHIVES.values())}
    output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(protocol=PROTOCOL, solver='IAS15 C/native Newton N-body research', complete=False,
        runtime_modified=False, production_eligible=False, source_sha256=source, input_sha256=inputs,
        library_files_sha256=external, native=native, external_source_archive_sha256=sha(source_archive),
        cargo_hash_policy='cargo-crlf-to-lf-v1', cargo_lf_sha256=cargo_hashes(ROOT),
        cargo_raw_before_sha256=cargo_hashes(ROOT, raw=True), environment={**versions, 'rebound':library.__version__},
        cache_qualification=qualified, origin=asdict(seed.origin), names=list(NAMES),
        masses_kg=[b.mass for b in seed.bodies], provenance=provenance(output.parent/(output.stem+'-sources')),
        reference_recheck={}, results={}, cost={})
    arrays, start = {}, perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    save()
    try:
        q = states(seed.bodies)
        force = prepare(report['masses_kg'])(q[:, :3], q[:, 3:], None, None)
        report['initial_force'] = force_metrics(report['masses_kg'], q[:, :3], force)
        if not report['initial_force']['checks_passed']:
            raise ArithmeticError('Independent initial N-body force failed')
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            for profile, cached in profiles.items():
                report['active_profile'] = profile
                save()
                times = cached['times']
                tick = perf_counter()
                rechecked, metadata = reference(seed, times, *LEVELS[2])
                arrays[profile+'__reference_recheck'] = rechecked
                same = same_array(rechecked, cached['reference_2'])
                report['reference_recheck'][profile] = dict(bitexact=same, seconds=perf_counter()-tick,
                    metadata=metadata, values_sha256=hashlib.sha256(bits(rechecked)).hexdigest(),
                    differences=agreement(rechecked, cached['reference_2'], list(NAMES)))
                save()
                if not same:
                    raise ArithmeticError('Current RK45 reference450 does not reproduce pinned cache')
                functions, results, rows = {}, {}, {}
                for epsilon in EPSILONS:
                    old_current, old_stats = ias_trajectory(seed, times, library, epsilon, count_forces=True)
                    if not same_array(old_current, cached[OLD_KEYS[epsilon]]):
                        raise ArithmeticError('Current C control differs from175')
                    for mode in MODES:
                        key = str(epsilon)+'__'+mode
                        def operation(counted=False, epsilon=epsilon, mode=mode):
                            return trajectory(seed, times, library, epsilon, mode, counted=counted)
                        functions[key] = operation
                        result = operation()  # excluded warmup
                        counted = operation(True)
                        equal_runs(result, counted)
                        if mode == 'native' and result[1] != counted[1]:
                            raise ArithmeticError('Native callback count changed')
                        values, stats, artifacts = counted
                        if bits(values[0]) != bits(cached['initial']):
                            raise ArithmeticError('Changed candidate IC')
                        if artifacts['packet_endpoints'][1:].tolist() != old_stats['packet_endpoints']:
                            raise ArithmeticError('Different N-body packet clocks')
                        if mode == 'basic':
                            prior = historical[profile]['candidates'][OLD_KEYS[epsilon]]
                            if not same_array(values, old_current) or any(stats[k] != prior['statistics'][k]
                                    for k in ('steps_done', 'packets', 'force_evaluations')):
                                raise ArithmeticError('C control output/counters differ from175')
                        measured = candidate_metrics(values, cached['reference_2'], seed, True)
                        rows[key] = dict(metrics=measured, statistics=stats, c_control175_bitexact=mode == 'basic',
                                         repeated_bitexact=True, counter_bitexact=True)
                        prefix = profile+'__'+key+'__'
                        arrays[prefix+'values'] = values
                        arrays.update({prefix+k:v for k,v in artifacts.items()})
                        results[key] = result
                        print(profile, key, measured['checks_passed'], measured['all_bodies'], measured['moon_relative_to_earth'], flush=True)
                report['results'][profile] = rows
                save()
                costs = {k:[] for k in functions}
                for repetition in range(3):
                    order = list(functions) if repetition % 2 == 0 else list(reversed(functions))
                    for key in order:
                        tick = perf_counter()
                        value = functions[key]()
                        elapsed = perf_counter()-tick
                        equal_runs(results[key], value)
                        if results[key][1] != value[1]:
                            raise ArithmeticError('Repeated callback counters differ')
                        costs[key].append(elapsed)
                report['cost'][profile] = {k:dict(seconds=v, median_seconds=statistics.median(v)) for k,v in costs.items()}
                save()
                if profile == 'pilot' and not all(row['metrics']['checks_passed'] for row in rows.values()):
                    raise ArithmeticError('Pilot failed; year is not qualified')
            report['warnings'] = [str(w.message) for w in captured]
        if any(sha(ROOT/n) != h for n,h in {**source, **inputs}.items()):
            raise ValueError('Changed N-body source/input during run')
        report['cargo_raw_after_sha256'] = cargo_hashes(ROOT, raw=True)
        if (library_hashes(library) != external or sha(Path(native['extension'])) != native['sha256']
                or sha(source_archive) != report['external_source_archive_sha256']
                or cargo_hashes(ROOT) != report['cargo_lf_sha256']
                or report['cargo_raw_after_sha256'] != report['cargo_raw_before_sha256']):
            raise ValueError('Changed N-body native/library/build input during run')
        report.update(complete=True, source_unchanged=True, input_unchanged=True, library_unchanged=True,
            native_unchanged=True, cargo_unchanged=True, all_c_control175_bitexact=True,
            all_checks_passed=all(row['metrics']['checks_passed'] for rows in report['results'].values() for row in rows.values()))
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if arrays:
            np.savez_compressed(output.with_suffix('.npz'), **arrays)
            report['npz_sha256'] = sha(output.with_suffix('.npz'))
        if report['complete']:
            report.pop('active_profile', None)
        report['wall_seconds'] = perf_counter()-start
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--source-archive', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output, args.library, args.source_archive)
    return 0 if report['all_checks_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
