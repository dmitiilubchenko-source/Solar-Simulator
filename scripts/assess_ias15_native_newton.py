"""Predeclared C/basic versus full Rust/Newton force coupling, outside runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import compare, decimal_relative_guard, equal_runs, load_cases
from scripts.assess_kepler_phase import ROOT
from scripts.assess_rust_adaptive import provenance
from scripts.ias15_native_newton import MODES, force_metrics, trajectory
from scripts.ias15_reference import EPSILONS, library_hashes, load_library
from scripts.ias15_restart import bits
from scripts.kepler_transport import sha
from scripts.native_audit import require_native
from scripts.replay_ias15_restart import RECEIPT as BASELINE, replay as replay_baseline
from solar_simulator.native_forces import prepare

PROTOCOL = 'docs/ias15-native-newton-protocol.md'


def cargo_hashes(root, *, raw=False):
    """Only Cargo metadata permits checkout EOL changes; all algorithm bytes stay exact."""
    result = {}
    for crate in ('solar_core', 'solar_native', 'solar_adaptive'):
        for filename in ('Cargo.toml', 'Cargo.lock'):
            name = 'rust/'+crate+'/'+filename
            data = (Path(root)/name).read_bytes()
            result[name] = hashlib.sha256(data if raw else data.replace(b'\r\n', b'\n')).hexdigest()
    return result


def same_array(a, b):
    return a.shape == b.shape and (bits(a) == bits(b) if a.dtype.kind == 'f' else np.array_equal(a, b))


def run(output, library_directory, source_archive):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous Newton coupling audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    baseline_integrity = replay_baseline()
    old = json.loads((ROOT/BASELINE).read_text(encoding='utf-8'))
    with np.load(ROOT/old['sample_archive'], allow_pickle=False) as saved:
        baseline = {k:saved[k].copy() for k in saved.files}
    cases, _ = load_cases()
    library = load_library(library_directory)
    external = library_hashes(library)
    if external != old['library_files_sha256'] or sha(source_archive) != old['external_source_archive_sha256']:
        raise ValueError('Pinned IAS15 library or sdist changed')
    native = require_native()
    native['sha256'] = sha(Path(native['extension']))
    names = [PROTOCOL, 'scripts/ias15_native_newton.py', 'scripts/assess_ias15_native_newton.py',
             'scripts/replay_ias15_native_newton.py', 'scripts/native_audit.py',
             'scripts/replay_ias15_restart.py', 'tests/test_ias15_native_newton.py']
    names += [p.relative_to(ROOT).as_posix() for p in (ROOT/'rust').rglob('*')
              if p.is_file() and 'target' not in p.parts and p.suffix == '.rs']
    source = {**old['source_sha256'], **{name:sha(ROOT/name) for name in names}}
    inputs = {**old['input_sha256'], BASELINE:sha(ROOT/BASELINE), old['sample_archive']:sha(ROOT/old['sample_archive'])}
    output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(protocol=PROTOCOL, solver='IAS15 Newton force coupling research', complete=False,
        runtime_modified=False, production_eligible=False, source_sha256=source, input_sha256=inputs,
        library_files_sha256=external, external_source_archive_sha256=sha(source_archive), native=native,
        cargo_hash_policy='cargo-crlf-to-lf-v1', cargo_lf_sha256=cargo_hashes(ROOT),
        cargo_raw_before_sha256=cargo_hashes(ROOT, raw=True),
        provenance=provenance(output.parent/(output.stem+'-sources')), baseline_integrity=baseline_integrity,
        environment=dict(python=platform.python_version(), numpy=np.__version__, rebound=library.__version__),
        initial_force={}, results={})
    arrays, start = {}, perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    save()
    try:
        # Finish every independent initial-force check before any trajectory.
        for name, case in cases.items():
            initial = case['initial']
            force = prepare(case['request']['masses'])(initial[:, :3], initial[:, 3:], None, None)
            report['initial_force'][name] = force_metrics(case['request']['masses'], initial, force)
        save()
        if not all(row['checks_passed'] for row in report['initial_force'].values()):
            raise ArithmeticError('Independent initial Newton force check failed')
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            for name, case in cases.items():
                report['results'][name] = {}
                for epsilon in EPSILONS:
                    controls = None
                    for mode in MODES:
                        key = str(epsilon)+'__'+mode
                        report['active_variant'] = name+'__'+key
                        save()
                        def operation():
                            return trajectory(case['request'], library, epsilon, case['origin'], mode)
                        operation()  # excluded warmup
                        result, costs = None, []
                        for _ in range(3):
                            tick = perf_counter()
                            value = operation()
                            costs.append(perf_counter()-tick)
                            if result is None:
                                result = value
                            else:
                                equal_runs(result, value)
                                if result[1] != value[1]:
                                    raise ArithmeticError('Force counters changed between repeats')
                        values, stats, artifacts = result
                        if mode == 'basic':
                            prefix = name+'__'+str(epsilon)+'__warm__'
                            if not same_array(values, baseline[prefix+'values']) or not all(
                                    same_array(value, baseline[prefix+field]) for field, value in artifacts.items()):
                                raise ArithmeticError('C control differs from353warm physical artifacts')
                            old_stats = old['results'][name]['modes'][str(epsilon)+'__warm']['statistics']
                            if any(stats[k] != old_stats[k] for k in ('packets', 'simulations', 'steps_done', 'force_evaluations')):
                                raise ArithmeticError('C control differs from353warm counters')
                            controls = values
                        measured = metrics(case['seed'], case['times'], values, [(y[:3], y[3:]) for y in case['expected']])
                        row = dict(statistics=stats, metrics=measured, seconds=costs,
                            median_seconds=statistics.median(costs), repeated_bitexact=True,
                            control353_bitexact=mode == 'basic')
                        if mode == 'native':
                            row['control_delta'] = compare(values, [decimal_relative_guard(q) for q in controls], case['times'])
                        report['results'][name][key] = row
                        prefix = name+'__'+key+'__'
                        arrays[prefix+'values'] = values
                        arrays.update({prefix+k:v for k, v in artifacts.items()})
                        save()
                        print(name, key, measured['checks_passed'], measured['position_metres'],
                              measured['velocity_m_per_s'], flush=True)
            report['warnings'] = [str(w.message) for w in captured]
        for name, expected in {**source, **inputs}.items():
            if sha(ROOT/name) != expected:
                raise ValueError('Changed Newton coupling source/input: '+name)
        if (library_hashes(library) != external or sha(source_archive) != report['external_source_archive_sha256']
                or sha(Path(native['extension'])) != native['sha256']):
            raise ValueError('Native or IAS15 binary/source archive changed during audit')
        report['cargo_raw_after_sha256'] = cargo_hashes(ROOT, raw=True)
        if (report['cargo_raw_after_sha256'] != report['cargo_raw_before_sha256']
                or cargo_hashes(ROOT) != report['cargo_lf_sha256']):
            raise ValueError('Cargo metadata changed during audit')
        report.update(complete=True, source_unchanged=True, input_unchanged=True, library_unchanged=True,
            native_unchanged=True, cargo_unchanged=True, all_control353_bitexact=True,
            all_checks_passed=all(row['metrics']['checks_passed'] for rows in report['results'].values() for row in rows.values()))
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if arrays:
            np.savez_compressed(output.with_suffix('.npz'), **arrays)
            report['npz_sha256'] = sha(output.with_suffix('.npz'))
        if report['complete']:
            report.pop('active_variant', None)
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
