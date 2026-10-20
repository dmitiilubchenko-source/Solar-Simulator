"""Isolated Rust DOP853/actual-IC Decimal audit; no runtime backend registration."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from time import perf_counter
from zipfile import ZipFile, ZIP_DEFLATED

import numpy as np
import scipy

from scripts.assess_ias15 import metrics
from scripts.assess_kepler_holdout import CASES, holdout_fixture, reference_rows
from scripts.assess_kepler_phase import ROOT, fixture
from scripts.assess_sandbox_planets import states
from scripts.ias15_reference import dop_trajectory, validate_input
from scripts.native_audit import require_native

PROTOCOL = 'docs/rust-adaptive-prototype-protocol.md'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    paths = list((ROOT/'rust/solar_adaptive').glob('src/*.rs'))
    paths += list((ROOT/'rust/solar_adaptive').glob('tests/*.rs'))
    paths += [ROOT/'rust/solar_adaptive'/n for n in ('Cargo.toml', 'Cargo.lock', 'LICENSE-SCIPY.txt')]
    paths += [ROOT/n for n in (PROTOCOL, 'scripts/assess_rust_adaptive.py',
        'scripts/assess_ias15.py', 'scripts/ias15_reference.py', 'scripts/kepler_reference.py',
        'scripts/assess_kepler_holdout.py', 'scripts/assess_kepler_phase.py',
        'scripts/assess_continuous.py', 'scripts/assess_sandbox_planets.py',
        'src/solar_simulator/continuous.py', 'src/solar_simulator/error_control.py',
        'src/solar_simulator/coordinates.py', 'src/solar_simulator/native_forces.py',
        'src/solar_simulator/simulation.py', 'src/solar_simulator/vector3.py',
        'rust/solar_core/src/lib.rs', 'rust/solar_core/src/relativity.rs',
        'rust/solar_core/Cargo.toml', 'rust/solar_core/Cargo.lock')]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(set(paths))}


def provenance(directory):
    """Capture dirty tracked patch and actual untracked input bytes before a run."""
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT)
    directory.mkdir(parents=True, exist_ok=False)
    patch = git('diff', '--binary', 'HEAD')
    (directory/'tracked.patch').write_bytes(patch)
    untracked = git('ls-files', '--others', '--exclude-standard', '-z').decode('utf-8').split('\0')
    bound = {}
    with ZipFile(directory/'untracked.zip', 'x', compression=ZIP_DEFLATED) as archive:
        for name in filter(None, untracked):
            path = (ROOT/name).resolve()
            if not path.is_relative_to(ROOT.resolve()):
                raise ValueError('Untracked source outside checkout')
            raw = path.read_bytes()
            bound[name] = hashlib.sha256(raw).hexdigest()
            archive.writestr(name, raw)
    return dict(commit=git('rev-parse', 'HEAD').decode().strip(),
        git_status=git('status', '--porcelain').decode(),
        tracked_patch_sha256=digest(directory/'tracked.patch'),
        untracked_archive_sha256=digest(directory/'untracked.zip'), untracked_source_sha256=bound,
        snapshot_directory=directory.relative_to(ROOT).as_posix())


def validate_response(response, times, initial, expected_endpoints):
    if response.get('complete') is not True or response.get('error') is not None:
        raise ValueError('Rust worker failed or produced incomplete evidence')
    frames = response.get('snapshots', [])
    if len(frames) != len(times) or not np.array_equal([r['time'] for r in frames], times):
        raise ValueError('Rust output epochs missing or changed')
    values = np.asarray([r['states'] for r in frames], dtype=float)
    if values.shape != (len(times), *initial.shape) or not np.isfinite(values).all():
        raise ValueError('Rust output shape or finiteness changed')
    if values[0].astype('>f8').tobytes() != initial.astype('>f8').tobytes():
        raise ValueError('Rust initial binary64 states changed in transport')
    if response.get('packet_endpoints') != expected_endpoints:
        raise ValueError('Rust packet boundaries differ from the existing method')
    if response.get('committed') != frames[-1]:
        raise ValueError('Rust committed snapshot differs from the last complete epoch')
    statistics = response.get('statistics', {})
    if (statistics.get('failed') is not False or statistics.get('packets') != len(expected_endpoints)
            or any(type(statistics.get(k)) is not int or statistics[k] < 0
                   for k in ('rhs_calls', 'accepted', 'rejected'))):
        raise ValueError('Rust statistics incomplete or failed')
    return values


def run(executable, output):
    executable, output = Path(executable).resolve(), Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous scientific results')
    if not executable.is_file():
        raise FileNotFoundError('Build the explicit research executable first')
    if not output.is_relative_to(ROOT/'.tools'):
        raise ValueError('Use a fresh project .tools output for this research run')
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    native = require_native()
    fingerprints = sources()
    binary_sha = digest(executable)
    dependency_paths = [Path(native['extension']), Path(scipy.__file__).parent/'integrate/_ivp/rk.py',
        Path(scipy.__file__).parent/'integrate/_ivp/common.py',
        Path(np.__file__).parent/'polynomial/chebyshev.py']
    dependencies = {str(p): digest(p) for p in dependency_paths}
    report = dict(protocol=PROTOCOL, complete=False, checks_passed=False, production_eligible=False,
        runtime_modified=False, model='Newtonian point masses / SI / 3D / model epochs',
        source_sha256=fingerprints, binary_sha256=binary_sha, provenance=snapshot,
        environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                         dependency_sha256=dependencies), results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    save()
    try:
        cases = [('holdout_'+name, *holdout_fixture(e, anomaly, permuted)) for name,e,anomaly,permuted in CASES]
        cases += [('original_'+str(e), *fixture(e)) for e in (0., .5, .95)]
        for label, seed, times in cases:
            validate_input(seed, times)
            initial = states(seed.bodies)
            expected, uncertainty = reference_rows(seed, times)
            stamp = perf_counter()
            baseline, statistics = dop_trajectory(seed, times)
            baseline_seconds = perf_counter()-stamp
            pair = seed.settings.relative_pair
            names = [b.name for b in seed.bodies]
            request = dict(masses=[b.mass for b in seed.bodies], states=initial.tolist(),
                relative_pair=[names.index(n) for n in pair] if pair else None,
                times=times.tolist(), packet_dt=seed.settings.dt, rtol=seed.settings.rtol,
                position_atol=seed.settings.position_atol, velocity_atol=seed.settings.velocity_atol)
            raw = json.dumps(request, allow_nan=False)
            request_bytes = raw.encode('utf-8')
            (output.parent/(output.stem+'-'+label+'-request.json')).write_bytes(request_bytes)
            stamp = perf_counter()
            child = subprocess.run([str(executable)], input=raw, text=True, capture_output=True, timeout=120, cwd=ROOT)
            process_seconds = perf_counter()-stamp
            (output.parent/(output.stem+'-'+label+'-stdout.json')).write_text(child.stdout, encoding='utf-8')
            (output.parent/(output.stem+'-'+label+'-stderr.txt')).write_text(child.stderr, encoding='utf-8')
            if child.returncode:
                raise RuntimeError(f'Rust worker exit {child.returncode}: {child.stderr}; complete output retained')
            response = json.loads(child.stdout)
            values = validate_response(response, times, initial, statistics['packet_endpoints'])
            before, after = metrics(seed, times, baseline, expected), metrics(seed, times, values, expected)
            report['results'][label] = dict(samples=len(times),
                input_request=request, input_request_sha256=hashlib.sha256(request_bytes).hexdigest(),
                initial_sha256=hashlib.sha256(initial.astype('>f8').tobytes()).hexdigest(),
                epochs_sha256=hashlib.sha256(times.astype('>f8').tobytes()).hexdigest(),
                oracle_uncertainty=uncertainty, baseline=before, rust=after,
                baseline_statistics=statistics, rust_statistics=response['statistics'],
                cost=dict(python_trajectory_seconds=baseline_seconds, rust_worker_compute_seconds=response['compute_seconds'],
                          rust_process_seconds=process_seconds, paired_benchmark=False, speed_claim=False))
            arrays[label+'_times'] = times
            arrays[label+'_baseline'] = baseline
            arrays[label+'_rust'] = values
            arrays[label+'_reference'] = np.array(expected, dtype=float)
            save()
            print(label, 'baseline', before['position_metres'], 'rust', after['position_metres'],
                  after['velocity_m_per_s'], 'PASS' if after['checks_passed'] else 'FAIL', flush=True)
        if sources() != fingerprints or digest(executable) != binary_sha or any(digest(p)!=sha for p,sha in dependencies.items()):
            raise ValueError('Audit source/binary/dependency bytes changed')
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report.update(complete=True, checks_passed=all(r['rust']['checks_passed'] for r in report['results'].values()),
                      source_unchanged=True, npz_sha256=digest(output.with_suffix('.npz')))
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.executable, args.output)
    return 0 if report['checks_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
