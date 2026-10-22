"""Controlled reset-dt versus saved-dt research; no runtime registration."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
from time import perf_counter

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases, equal_runs, compare, decimal_relative_guard
from scripts.assess_kepler_phase import ROOT
from scripts.assess_rust_adaptive import provenance
from scripts.ias15_reference import EPSILONS, load_library, library_hashes, packet_end
from scripts.ias15_restart import bits, checkpoint, restore, simulation, snapshot, validate
from scripts.kepler_transport import sha
from scripts.replay_ias15_restart import RECEIPT, replay

PROTOCOL = 'docs/ias15-restart-step-protocol.md'
RECIPES = ('reset', 'saved-dt')


def step_sidecar(time, dt, epsilon, origin):
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError('Invalid post-packet dt')
    raw = json.dumps(dict(schema='ias15-research-step-v1', time=float(time), dt=float(dt),
                         epsilon=epsilon, origin=origin), sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    if bits(restore_step(raw, digest, time, epsilon, origin)) != bits(dt):
        raise ArithmeticError('Numerical step roundtrip changed bits')
    return raw, digest


def restore_step(raw, digest, time, epsilon, origin):
    if hashlib.sha256(raw.encode()).hexdigest() != digest:
        raise ValueError('Step sidecar SHA mismatch')
    value = json.loads(raw)
    if (set(value) != {'schema', 'time', 'dt', 'epsilon', 'origin'}
            or value['schema'] != 'ias15-research-step-v1' or value['origin'] != origin
            or bits(value['time']) != bits(time) or value['epsilon'] != epsilon
            or type(value['dt']) is not float or not np.isfinite(value['dt']) or value['dt'] <= 0):
        raise ValueError('Wrong step sidecar provenance, time or value')
    return value['dt']


def step_trajectory(request, library, epsilon, recipe, origin, *, count_forces=False):
    if recipe not in RECIPES:
        raise ValueError('Undeclared restart step recipe')
    masses, initial, times, _ = validate(request['masses'], request['states'], request['times'],
                                       request['packet_dt'], epsilon, 'every-packet')
    packet_dt = request['packet_dt']
    calls = 0
    def counter(pointer):
        nonlocal calls
        calls += 1
    sim = simulation(library, 0., masses, initial, packet_dt, epsilon, counter if count_forces else None)
    raw, digest = checkpoint(0., masses, initial, origin)
    step_raw, step_sha = step_sidecar(0., sim.dt, epsilon, origin)
    texts, hashes, step_texts, step_hashes = [raw], [digest], [step_raw], [step_sha]
    states, endpoints, used = [initial.copy()], [0.], [packet_dt/200]
    values, steps, packets = [], 0, 0
    for epoch in times:
        while sim.t < epoch:
            if packets:
                steps += int(sim.steps_done)
                clock, masses, physical = restore(texts[-1], hashes[-1], origin)
                dt = restore_step(step_texts[-1], step_hashes[-1], clock, epsilon, origin)
                sim = simulation(library, clock, masses, physical, packet_dt, epsilon, counter if count_forces else None)
                if recipe == 'saved-dt':
                    sim.dt = dt
                if bits(sim.dt) != bits(dt if recipe == 'saved-dt' else packet_dt/200):
                    raise ArithmeticError('Restart step assignment changed bits')
                used.append(float(sim.dt))
            end = packet_end(float(sim.t), float(epoch), packet_dt)
            sim.integrate(end, exact_finish_time=1)
            if sim.t != end:
                raise RuntimeError('IAS15 missed exact packet endpoint')
            physical = snapshot(sim)
            raw, digest = checkpoint(float(sim.t), masses, physical, origin)
            step_raw, step_sha = step_sidecar(float(sim.t), float(sim.dt), epsilon, origin)
            texts.append(raw)
            hashes.append(digest)
            step_texts.append(step_raw)
            step_hashes.append(step_sha)
            states.append(physical)
            endpoints.append(end)
            packets += 1
        values.append(snapshot(sim))
    stats = dict(mode='every-packet', recipe=recipe, epsilon=epsilon, packets=packets,
        simulations=packets, restart_packet_indices=list(range(1, packets)), restart_output_index=None,
        steps_done=steps+int(sim.steps_done), force_evaluations=calls if count_forces else None,
        initial_dt_seconds=packet_dt/200, physical_roundtrip_bitexact=True,
        adaptive_mode='PRS23', gravity='basic')
    arrays = dict(packet_endpoints=np.asarray(endpoints), packet_states=np.asarray(states),
        checkpoint_json=np.asarray(texts), checkpoint_sha256=np.asarray(hashes),
        step_json=np.asarray(step_texts), step_sha256=np.asarray(step_hashes), restart_used_dt=np.asarray(used))
    return np.asarray(values), stats, arrays


def run(output, library_directory, source_archive):
    output = Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous step audit')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a fresh .tools output')
    baseline_integrity = replay()
    old = json.loads((ROOT/RECEIPT).read_text(encoding='utf-8'))
    archive_path = ROOT/old['sample_archive']
    with np.load(archive_path, allow_pickle=False) as saved:
        baseline = {k:saved[k].copy() for k in saved.files}
    cases, _ = load_cases()
    library = load_library(library_directory)
    external = library_hashes(library)
    if external != old['library_files_sha256'] or sha(source_archive) != old['external_source_archive_sha256']:
        raise ValueError('Pinned REBOUND library/source archive changed')
    sources = {**old['source_sha256'], PROTOCOL:sha(ROOT/PROTOCOL),
               'scripts/assess_ias15_restart_step.py':sha(Path(__file__)),
               'scripts/replay_ias15_restart.py':sha(ROOT/'scripts/replay_ias15_restart.py')}
    inputs = {**old['input_sha256'], RECEIPT:sha(ROOT/RECEIPT), old['sample_archive']:sha(archive_path)}
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = provenance(output.parent/(output.stem+'-sources'))
    report = dict(protocol=PROTOCOL, complete=False, runtime_modified=False, production_eligible=False,
        solver='IAS15 research', source_sha256=sources, input_sha256=inputs,
        library_files_sha256=external, external_source_archive_sha256=sha(source_archive),
        baseline_integrity=baseline_integrity, provenance=snapshot, results={})
    arrays = {}
    start = perf_counter()
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    save()
    try:
        for name, case in cases.items():
            req, rows = case['request'], {}
            report['active_case'] = name
            save()
            for epsilon in EPSILONS:
                def operation(recipe, counted=False):
                    return step_trajectory(req, library, epsilon, recipe, case['origin'], count_forces=counted)
                runs, costs = {}, {recipe:[] for recipe in RECIPES}
                for recipe in RECIPES:
                    operation(recipe)
                for repeat in range(3):
                    for recipe in (RECIPES if repeat % 2 == 0 else RECIPES[::-1]):
                        tick = perf_counter()
                        result = operation(recipe)
                        costs[recipe].append(perf_counter()-tick)
                        if recipe in runs:
                            equal_runs(runs[recipe], result)
                        else:
                            runs[recipe] = result
                old_prefix = name+'__'+str(epsilon)+'__every-packet__'
                reference_stats = old['results'][name]['modes'][str(epsilon)+'__every-packet']['statistics']
                if bits(runs['reset'][0]) != bits(baseline[old_prefix+'values']):
                    raise ArithmeticError('Reset control did not reproduce353')
                for field in ('packet_endpoints', 'packet_states', 'checkpoint_json', 'checkpoint_sha256'):
                    if not np.array_equal(runs['reset'][2][field], baseline[old_prefix+field]):
                        raise ArithmeticError('Reset control checkpoint did not reproduce353')
                for recipe in RECIPES:
                    counted = operation(recipe, True)
                    equal_runs(runs[recipe], counted)
                    values, stats, artifacts = runs[recipe]
                    stats = dict(stats, force_evaluations=counted[1]['force_evaluations'])
                    if recipe == 'reset' and any(stats[k] != v for k,v in reference_stats.items()):
                        raise ArithmeticError('Reset counters differ from353')
                    if bits(artifacts['packet_endpoints']) != bits(baseline[old_prefix+'packet_endpoints']):
                        raise ArithmeticError('Step recipe changed packet grid')
                    prefix = name+'__'+str(epsilon)+'__'+recipe+'__'
                    arrays[prefix+'values'] = values
                    for field, value in artifacts.items():
                        arrays[prefix+field] = value
                    rows[str(epsilon)+'__'+recipe] = dict(statistics=stats,
                        metrics=metrics(case['seed'], case['times'], values, [(y[:3], y[3:]) for y in case['expected']]),
                        difference_from_reset=compare(values, [decimal_relative_guard(y) for y in runs['reset'][0]], case['times']),
                        difference_from_warm=compare(values, [decimal_relative_guard(y) for y in baseline[name+'__'+str(epsilon)+'__warm__values']], case['times']),
                        repeat_bitexact=True, counter_bitexact=True, seconds=costs[recipe],
                        median_seconds=statistics.median(costs[recipe]))
                    row = rows[str(epsilon)+'__'+recipe]['metrics']
                    print(name, epsilon, recipe, row['checks_passed'], row['position_metres'], row['velocity_m_per_s'], flush=True)
            report['results'][name] = rows
            save()
        for name, expected in {**sources, **inputs}.items():
            if sha(ROOT/name) != expected:
                raise ValueError('Changed step source/input: '+name)
        if library_hashes(library) != external or sha(source_archive) != report['external_source_archive_sha256']:
            raise ValueError('Changed research library/source archive')
        report.update(complete=True, source_unchanged=True, input_unchanged=True, library_unchanged=True,
            reset_control_bitexact=True, experimental_all_passed=all(
                row[str(e)+'__saved-dt']['metrics']['checks_passed'] for row in report['results'].values() for e in EPSILONS))
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
    return 0 if result['experimental_all_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
