"""Qualify one shared session lifecycle against both frozen357 force modes."""
import argparse
import json
from pathlib import Path
import platform
import statistics
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_native_newton import cargo_hashes, same_array
from scripts.assess_ias15_restart import load_cases
from scripts.assess_ias15_session import compare_run
from scripts.assess_kepler_phase import ROOT
from scripts.assess_rust_adaptive import provenance
from scripts.ias15_native_newton import MODES
from scripts.ias15_native_session import IAS15NativeSession
from scripts.ias15_reference import EPSILONS, library_hashes, load_library
from scripts.ias15_session import IAS15Session
from scripts.kepler_transport import sha
from scripts.native_audit import require_native
from scripts.replay_ias15_native_newton import RECEIPT as BASELINE, replay as replay357
from scripts.replay_ias15_session import RECEIPT as OWNED, FROZEN_SESSION, replay as replay356

PROTOCOL = 'docs/ias15-native-session-protocol.md'


def trajectory(request, library, epsilon, origin, mode, *, counted=False):
    if mode not in MODES:
        raise ValueError('Undeclared owned-session force mode')
    session_type = IAS15NativeSession if mode == 'native' else IAS15Session
    values, clocks, states, texts, digests = [], [], [], [], []
    def keep(value):
        clocks.append(value.time)
        states.append(value.state)
        texts.append(value.checkpoint_json)
        digests.append(value.checkpoint_sha256)
    with session_type(request['masses'], request['states'], request['packet_dt'], float(request['times'][-1]),
                      library, epsilon, origin, count_forces=counted) as session:
        keep(session.current)
        for epoch in request['times']:
            while session.current.time < epoch:
                keep(session.next(until=float(epoch)))
            values.append(session.current.state)
    return np.asarray(values), session.statistics, dict(packet_endpoints=np.asarray(clocks),
        packet_states=np.asarray(states), checkpoint_json=np.asarray(texts), checkpoint_sha256=np.asarray(digests))


def run(output, library_directory, source_archive):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous native-session audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    baseline_integrity = dict(coupling357=replay357(), owned356=replay356())
    old = json.loads((ROOT/BASELINE).read_text(encoding='utf-8'))
    owned = json.loads((ROOT/OWNED).read_text(encoding='utf-8'))
    with np.load(ROOT/old['sample_archive'], allow_pickle=False) as saved:
        baseline = {k:saved[k].copy() for k in saved.files}
    cases, _ = load_cases()
    library = load_library(library_directory)
    external, native = library_hashes(library), require_native()
    native['sha256'] = sha(Path(native['extension']))
    if (external != old['library_files_sha256'] or native != old['native']
            or sha(source_archive) != old['external_source_archive_sha256']
            or cargo_hashes(ROOT) != old['cargo_lf_sha256']):
        raise ValueError('Changed pinned IAS15/native/build inputs')
    names = [PROTOCOL, FROZEN_SESSION, 'scripts/ias15_session.py', 'scripts/ias15_native_session.py',
             'scripts/assess_ias15_native_session.py', 'scripts/replay_ias15_native_session.py',
             'scripts/assess_ias15_session.py', 'scripts/replay_ias15_session.py',
             'tests/test_ias15_native_session.py', 'tests/test_ias15_session.py',
             'tests/test_ias15_session_replay.py', 'tests/test_ias15_native_newton.py']
    source = {**old['source_sha256'], **{name:sha(ROOT/name) for name in names}}
    inputs = {**old['input_sha256'], BASELINE:sha(ROOT/BASELINE), OWNED:sha(ROOT/OWNED),
              old['sample_archive']:sha(ROOT/old['sample_archive']), owned['sample_archive']:sha(ROOT/owned['sample_archive'])}
    output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False, production_eligible=False,
        solver='IAS15 shared owned native research session', source_sha256=source, input_sha256=inputs,
        library_files_sha256=external, external_source_archive_sha256=sha(source_archive), native=native,
        cargo_hash_policy='cargo-crlf-to-lf-v1', cargo_lf_sha256=cargo_hashes(ROOT),
        cargo_raw_before_sha256=cargo_hashes(ROOT, raw=True), baseline_integrity=baseline_integrity,
        provenance=provenance(output.parent/(output.stem+'-sources')),
        environment=dict(python=platform.python_version(), numpy=np.__version__, rebound=library.__version__), results={})
    arrays, start = {}, perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    save()
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            for name, case in cases.items():
                report['results'][name] = {}
                for epsilon in EPSILONS:
                    for mode in MODES:
                        key = str(epsilon)+'__'+mode
                        report['active_variant'] = name+'__'+key
                        save()
                        def operation(counted=False):
                            return trajectory(case['request'], library, epsilon, case['origin'], mode, counted=counted)
                        operation()
                        result, costs = None, []
                        for _ in range(3):
                            tick = perf_counter()
                            value = operation()
                            costs.append(perf_counter()-tick)
                            if result is None:
                                result = value
                            else:
                                compare_run(result, value)
                                if result[1] != value[1]:
                                    raise ArithmeticError('Session repeat counters changed')
                        counted = operation(True)
                        compare_run(result, counted)
                        if mode == 'native' and result[1] != counted[1]:
                            raise ArithmeticError('Native force counter run changed')
                        values, stats, artifacts = counted
                        prefix = name+'__'+key+'__'
                        if not same_array(values, baseline[prefix+'values']) or not all(
                                same_array(value, baseline[prefix+field]) for field, value in artifacts.items()):
                            raise ArithmeticError('Owned native/basic session did not reproduce357 arrays')
                        old_row = old['results'][name][key]
                        if (any(stats[k] != old_row['statistics'][k] for k in
                                ('packets', 'steps_done', 'force_evaluations', 'simulations'))
                                or stats['attempts'] != stats['packets'] or stats['failed'] or not stats['closed']
                                or not stats['finished'] or stats['attempted_force_evaluations'] != stats['force_evaluations']):
                            raise ArithmeticError('Owned session counters or lifecycle differ')
                        measured = metrics(case['seed'], case['times'], values, [(y[:3], y[3:]) for y in case['expected']])
                        if measured != old_row['metrics']:
                            raise ArithmeticError('Owned session actual-IC metrics differ')
                        report['results'][name][key] = dict(metrics=measured, statistics=stats, seconds=costs,
                            median_seconds=statistics.median(costs), baseline357_bitexact=True,
                            repeated_bitexact=True, forcecounter_bitexact=True)
                        arrays[prefix+'values'] = values
                        arrays.update({prefix+k:v for k,v in artifacts.items()})
                        save()
                        print(name, key, measured['checks_passed'], measured['position_metres'], flush=True)
            report['warnings'] = [str(w.message) for w in captured]
        if any(sha(ROOT/name) != expected for name, expected in {**source, **inputs}.items()):
            raise ValueError('Changed native-session source/input')
        report['cargo_raw_after_sha256'] = cargo_hashes(ROOT, raw=True)
        if (library_hashes(library) != external or sha(source_archive) != report['external_source_archive_sha256']
                or sha(Path(native['extension'])) != native['sha256']
                or cargo_hashes(ROOT) != report['cargo_lf_sha256']
                or report['cargo_raw_after_sha256'] != report['cargo_raw_before_sha256']):
            raise ValueError('Changed external/native/build input during audit')
        report.update(complete=True, source_unchanged=True, input_unchanged=True, library_unchanged=True,
            native_unchanged=True, cargo_unchanged=True, all_baseline357_bitexact=True,
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
