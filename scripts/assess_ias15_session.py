"""Owned-session qualification against the frozen353 warm control."""
import argparse
import json
from pathlib import Path
import platform
import statistics
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases
from scripts.assess_kepler_phase import ROOT
from scripts.assess_rust_adaptive import provenance
from scripts.ias15_reference import EPSILONS, load_library, library_hashes
from scripts.ias15_restart import bits
from scripts.ias15_session import IAS15Session
from scripts.kepler_transport import sha
from scripts.replay_ias15_restart import RECEIPT, replay

PROTOCOL = 'docs/ias15-session-protocol.md'


def trajectory(request, library, epsilon, origin, *, count_forces=False):
    times = request['times']
    values, clocks, states, texts, digests = [], [], [], [], []
    with IAS15Session(request['masses'], request['states'], request['packet_dt'], float(times[-1]),
                      library, epsilon, origin, count_forces=count_forces) as session:
        def keep(value):
            clocks.append(value.time)
            states.append(value.state)
            texts.append(value.checkpoint_json)
            digests.append(value.checkpoint_sha256)
        keep(session.current)
        for epoch in times:
            while session.current.time < epoch:
                keep(session.next(until=float(epoch)))
            values.append(session.current.state)
    stats = session.statistics
    if not stats['closed'] or not stats['finished'] or stats['failed']:
        raise RuntimeError('Owned session did not finish and close cleanly')
    return np.asarray(values), stats, dict(packet_endpoints=np.asarray(clocks),
        packet_states=np.asarray(states), checkpoint_json=np.asarray(texts), checkpoint_sha256=np.asarray(digests))


def compare_run(a, b):
    if bits(a[0]) != bits(b[0]):
        raise ArithmeticError('Owned-session outputs changed between repeats')
    for key in a[2]:
        x, y = a[2][key], b[2][key]
        same = (x.shape == y.shape and bits(x) == bits(y)) if x.dtype.kind == 'f' else np.array_equal(x, y)
        if not same:
            raise ArithmeticError('Owned-session physical artifact changed: '+key)
    excluded = {'force_evaluations', 'attempted_force_evaluations'}
    if {k:v for k,v in a[1].items() if k not in excluded} != {k:v for k,v in b[1].items() if k not in excluded}:
        raise ArithmeticError('Owned-session counters changed')


def run(output, library_directory, source_archive):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous session qualification')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    baseline_integrity = replay()
    old = json.loads((ROOT/RECEIPT).read_text(encoding='utf-8'))
    archive_path = ROOT/old['sample_archive']
    with np.load(archive_path, allow_pickle=False) as saved:
        baseline = {key:saved[key].copy() for key in saved.files}
    cases, _ = load_cases()
    library = load_library(library_directory)
    external = library_hashes(library)
    if external != old['library_files_sha256'] or sha(source_archive) != old['external_source_archive_sha256']:
        raise ValueError('Pinned IAS15 library/source archive changed')
    source = {**old['source_sha256'], PROTOCOL:sha(ROOT/PROTOCOL),
        'scripts/ias15_session.py':sha(ROOT/'scripts/ias15_session.py'),
        'scripts/assess_ias15_session.py':sha(Path(__file__)),
        'scripts/replay_ias15_restart.py':sha(ROOT/'scripts/replay_ias15_restart.py')}
    inputs = {**old['input_sha256'], RECEIPT:sha(ROOT/RECEIPT), old['sample_archive']:sha(archive_path)}
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False, production_eligible=False,
        solver='IAS15 owned warm research session', source_sha256=source, input_sha256=inputs,
        library_files_sha256=external, external_source_archive_sha256=sha(source_archive),
        environment=dict(python=platform.python_version(), numpy=np.__version__, rebound=library.__version__),
        baseline_integrity=baseline_integrity, provenance=snapshot, results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    save()
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            for name, case in cases.items():
                report['active_case'] = name
                save()
                rows = {}
                for epsilon in EPSILONS:
                    def operation(counted=False):
                        return trajectory(case['request'], library, epsilon, case['origin'], count_forces=counted)
                    operation()  # excluded warmup
                    result, costs = None, []
                    for _ in range(3):
                        tick = perf_counter()
                        value = operation()
                        costs.append(perf_counter()-tick)
                        if result is None:
                            result = value
                        else:
                            compare_run(result, value)
                    counted = operation(True)
                    compare_run(result, counted)
                    values, stats, artifacts = counted
                    old_prefix = name+'__'+str(epsilon)+'__warm__'
                    if bits(values) != bits(baseline[old_prefix+'values']):
                        raise ArithmeticError('Owned session did not reproduce353warm')
                    for field, value in artifacts.items():
                        if value.dtype.kind == 'f':
                            same = value.shape == baseline[old_prefix+field].shape and bits(value) == bits(baseline[old_prefix+field])
                        else:
                            same = np.array_equal(value, baseline[old_prefix+field])
                        if not same:
                            raise ArithmeticError('Owned session artifact differs from353warm: '+field)
                    old_row = old['results'][name]['modes'][str(epsilon)+'__warm']
                    if (stats['simulations'] != 1 or stats['attempts'] != stats['packets']
                            or stats['attempted_force_evaluations'] != stats['force_evaluations']
                            or any(stats[k] != old_row['statistics'][k]
                                   for k in ('packets', 'steps_done', 'force_evaluations', 'simulations'))):
                        raise ArithmeticError('Owned session counters differ from353warm')
                    measured = metrics(case['seed'], case['times'], values,
                                       [(y[:3], y[3:]) for y in case['expected']])
                    if measured != old_row['metrics']:
                        raise ArithmeticError('Owned session metrics differ from353warm')
                    prefix = name+'__'+str(epsilon)+'__'
                    arrays[prefix+'values'] = values
                    for key, value in artifacts.items():
                        arrays[prefix+key] = value
                    rows[str(epsilon)] = dict(statistics=stats, metrics=measured, seconds=costs,
                        median_seconds=statistics.median(costs), warm353_bitexact=True,
                        repeated_bitexact=True, forcecounter_bitexact=True)
                    print(name, epsilon, measured['checks_passed'], measured['position_metres'],
                          measured['velocity_m_per_s'], stats['packets'], flush=True)
                report['results'][name] = rows
                save()
            report['warnings'] = [str(w.message) for w in captured]
        for name, expected in {**source, **inputs}.items():
            if sha(ROOT/name) != expected:
                raise ValueError('Changed session source/input: '+name)
        if library_hashes(library) != external or sha(source_archive) != report['external_source_archive_sha256']:
            raise ValueError('Changed IAS15 library/source archive during run')
        report.update(complete=True, source_unchanged=True, input_unchanged=True, library_unchanged=True,
            all_warm353_bitexact=True, all_checks_passed=all(
                row['metrics']['checks_passed'] for case in report['results'].values() for row in case.values()))
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if arrays:
            np.savez_compressed(output.with_suffix('.npz'), **arrays)
            report['npz_sha256'] = sha(output.with_suffix('.npz'))
        if report['complete']:
            report.pop('active_case', None)
        report['wall_seconds'] = perf_counter()-start
        save()
    return report


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
