"""All nine fixed actual-IC IAS15 full-state cases; no runtime registration."""
import argparse
import json
from pathlib import Path
import platform
from time import perf_counter
import warnings
import zipfile

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_full_state import guard_checks, paired
from scripts.assess_ias15_restart import load_cases, sources as old_sources
from scripts.ias15_full_state import FullStateGuard, sha
from scripts.ias15_reference import load_library, library_hashes, EPSILONS
from scripts.ias15_restart import simulation, trajectory, bits
from scripts.kepler_transport import ROOT

CASES = ('holdout_circular', 'holdout_moderate', 'holdout_original', 'holdout_permuted',
         'holdout_apocentre', 'holdout_eccentric_phase', 'original_0.0', 'original_0.5', 'original_0.95')
PROTOCOL = 'docs/ias15-full-suite-protocol.md'
LIBRARY = 'docs/native-newton-year-validation.json'


def check_baseline(name, epsilon, values, previous):
    prefix = name+'__'+str(epsilon)+'__'
    if bits(values['packet_endpoints']) != bits(values['cold_packet_endpoints']):
        raise ArithmeticError('Current cold/warm packet schedule changed: '+name)
    for current, old in (('warm', 'warm'), ('full', 'warm'), ('cold', 'every-packet')):
        if bits(values[current]) != bits(previous[prefix+old+'__values']):
            raise ArithmeticError('Previous353 output changed: '+name+'/'+current)
    for mode in ('warm', 'every-packet'):
        if bits(values['packet_endpoints']) != bits(previous[prefix+mode+'__packet_endpoints']):
            raise ArithmeticError('Previous353 packet schedule changed: '+name)


def totals(results):
    variants = [r for case in results.values() for r in case.values()]
    complete = [r for r in variants if r.get('complete')]
    passed = {mode: sum(r['metrics'][mode]['checks_passed'] for r in complete) for mode in ('warm', 'full', 'cold')}
    return dict(attempted=len(variants), completed=len(complete), passed=passed,
        full_state_gate_passed=len(complete) == 18 and passed['warm'] == passed['full'] == 18,
        packets=sum(r['statistics']['packets'] for r in complete))


def run(output, library_directory):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use an output under .tools')
    if any(p.exists() for p in (output, output.with_suffix('.npz'), output.with_name(output.stem+'-sources.zip'),
                               output.with_name(output.stem+'-packets'))):
        raise FileExistsError('Preserve previous suite results and partial streams')
    cases, inputs = load_cases()
    if tuple(cases) != CASES:
        raise ValueError('Changed fixed nine-case inventory/order')
    library = load_library(library_directory)
    pinned = json.loads((ROOT/LIBRARY).read_bytes())['library_files_sha256']
    if library_hashes(library) != pinned:
        raise ValueError('Different pinned library')
    for name in (LIBRARY, 'docs/ias15-restart-validation.json', 'docs/ias15-restart-samples.npz',
                 'docs/ias15-full-state-validation.json', 'docs/ias15-full-state-samples.npz'):
        inputs[name] = sha((ROOT/name).read_bytes())
    with np.load(ROOT/'docs/ias15-restart-samples.npz', allow_pickle=False) as archive:
        previous = {n: archive[n].copy() for n in archive.files}
    names = (PROTOCOL, 'scripts/ias15_full_state.py', 'scripts/assess_ias15_full_state.py',
             'scripts/assess_ias15_restart.py', 'scripts/assess_ias15_full_suite.py',
             'scripts/replay_ias15_full_suite.py', 'tests/test_ias15_full_suite.py',
             'docs/ias15-archive-source-validation.json')
    source = old_sources() | {n: sha((ROOT/n).read_bytes()) for n in names}
    output.parent.mkdir(parents=True, exist_ok=True)
    source_zip = output.with_name(output.stem+'-sources.zip')
    with zipfile.ZipFile(source_zip, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in source:
            archive.writestr(name, (ROOT/name).read_bytes())
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False, production_eligible=False,
        source_sha256=source, input_sha256=inputs, library_files_sha256=pinned,
        source_archive_sha256=sha(source_zip.read_bytes()),
        environment=dict(python=platform.python_version(), numpy=np.__version__, rebound=library.__version__,
                         platform=platform.platform()),
        requests={n: cases[n]['request'] for n in CASES}, origins={n: cases[n]['origin'] for n in CASES},
        results={}, aggregate={})
    arrays = {}
    def save():
        report['aggregate'] = totals(report['results'])
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    def verify():
        for name, digest in (source | inputs).items():
            if sha((ROOT/name).read_bytes()) != digest:
                raise ValueError('Source/input changed during run: '+name)
        if library_hashes(library) != pinned:
            raise ValueError('Library changed during run')
    save()
    started = perf_counter()
    try:
        for name in CASES:
            case = cases[name]
            req, times = case['request'], case['times']
            report['results'][name] = {}
            arrays[name+'__times'] = times
            arrays[name+'__oracle100'] = np.asarray([[str(v) for v in row] for row in case['expected']])
            for epsilon in EPSILONS:
                row = report['results'][name][str(epsilon)] = dict(complete=False)
                save()
                try:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always')
                        guard = FullStateGuard(library, req['masses'], case['initial'], req['packet_dt'], epsilon, case['origin'], pinned)
                        sim = simulation(library, 0., req['masses'], case['initial'], req['packet_dt'], epsilon)
                        row.update(guards=guard_checks(guard, sim), abi=guard.abi)
                        directory = output.with_name(output.stem+'-packets')/name/str(epsilon)
                        values, statistics = paired(case, library, epsilon, guard, directory)
                        # Persist a completed pair before a possible cold/control failure.
                        for key, value in values.items():
                            arrays[name+'__'+str(epsilon)+'__'+key] = value
                        cold, cold_stats, artifacts = trajectory(req['masses'], case['initial'], times, req['packet_dt'],
                            library, epsilon, 'every-packet', case['origin'])
                        values['cold'] = cold
                        for key, value in artifacts.items():
                            values['cold_'+key] = value
                        check_baseline(name, epsilon, values, previous)
                        for key, value in values.items():
                            arrays[name+'__'+str(epsilon)+'__'+key] = value
                        expected = [(v[:3], v[3:]) for v in case['expected']]
                        row.update(statistics=statistics, cold_statistics=cold_stats, previous353_bitexact=True,
                            metrics={mode: metrics(case['seed'], times, values[mode], expected) for mode in ('warm', 'full', 'cold')})
                        if caught:
                            raise ValueError('Unexpected Python warnings: '+repr([str(w.message) for w in caught]))
                        row['complete'] = True
                except Exception as exc:
                    row['failure'] = dict(type=type(exc).__name__, message=str(exc))
                save()
                verify()
                print(name, epsilon, {m: r['checks_passed'] for m, r in row.get('metrics', {}).items()},
                      row.get('failure', ''), flush=True)
        report['complete'] = True
    except BaseException as exc:
        report['failure'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        report['wall_seconds_before_final_packaging'] = perf_counter()-started
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report['array_archive_sha256'] = sha(output.with_suffix('.npz').read_bytes())
        try:
            verify()
        except BaseException as exc:
            report['complete'] = False
            report['failure'] = dict(type=type(exc).__name__, message=str(exc))
            save()
            raise
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output, args.library)


if __name__ == '__main__':
    main()
