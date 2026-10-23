"""Fixed circular basic full-state pilot; fresh research outputs only."""
import argparse
import base64
from dataclasses import replace
import json
from pathlib import Path
import platform
import struct
from time import perf_counter
import warnings
import zipfile

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases, sources as old_sources
from scripts.ias15_reference import load_library, EPSILONS, library_hashes, packet_end
from scripts.ias15_restart import simulation, snapshot, bits, trajectory, checkpoint
from scripts.ias15_full_state import (FullStateGuard, CommittedFullState, PREFIX, BUFFERS,
                                     DP7, parse, pack, numeric_fields, sha)
from scripts.kepler_transport import ROOT

PROTOCOL = 'docs/ias15-full-state-protocol.md'
LIBRARY = 'docs/native-newton-year-validation.json'


def guard_checks(guard, sim):
    """Only own unintegrated stream enters C; synthetic damaged buffers never do."""
    saved = guard.capture(sim)
    rows = []
    def reject(name, candidate, time=0.):
        create = guard._archive_create
        def forbidden(*args):
            raise AssertionError('Malformed input reached C: '+name)
        guard._archive_create = forbidden
        try:
            try:
                guard.restore(candidate, time)
            except ValueError as exc:
                rows.append(dict(name=name, rejected_before_c=True, reason=str(exc)))
            else:
                raise AssertionError('Accepted bad snapshot: '+name)
        finally:
            guard._archive_create = create
    for key, wrong in [('version', '5.2.1'), ('abi', 'other ABI'), ('origin', 'other IC'),
                       ('library_sha', 'other binary'), ('identities', ('body[1]', 'body[0]')),
                       ('digest', '0'*64)]:
        reject(key, replace(saved, **{key: wrong}))
    reject('expected-time', saved, 1.)
    raw, digest = checkpoint(0., guard.masses[::-1], snapshot(sim), guard.origin)
    reject('physical-mass-order', replace(saved, physical_json=raw, physical_sha=digest))
    header, fields = parse(saved.binary)
    for name, replacement in [('G', struct.pack('=d', sim.G*2)),
                              ('t', struct.pack('=d', 1.)),
                              ('functionpointers', struct.pack('=i', 1)),
                              ('N', struct.pack('=Q', 3))]:
        altered = dict(fields, **{name: replacement})
        raw = pack(header, altered)
        reject('binary-'+name, replace(saved, binary=raw, digest=sha(raw)))
    # Well-framed synthetic full buffers exercise structural guards before any
    # orbit. This synthetic positive preflight is NEVER given to the C reader.
    full = dict(fields)
    index = list(full).index('functionpointers')
    items = list(full.items())
    items[index:index] = [(PREFIX+k, bytes(48*(7 if k in DP7 else 1))) for k in BUFFERS]
    full = dict(items)
    full['t'] = struct.pack('=d', 1.)
    physical, physical_sha = checkpoint(1., guard.masses, snapshot(sim), guard.origin)
    raw = pack(header, full)
    synthetic = replace(saved, binary=raw, digest=sha(raw), physical_json=physical, physical_sha=physical_sha)
    guard.preflight(synthetic, 1.)
    for key in BUFFERS:
        for mutation in ('missing', 'short'):
            altered = dict(full)
            if mutation == 'missing':
                del altered[PREFIX+key]
            else:
                altered[PREFIX+key] = altered[PREFIX+key][:-8]
            raw = pack(header, altered)
            reject(mutation+'-'+key, replace(synthetic, binary=raw, digest=sha(raw)), 1.)
    # Recompute outer SHA after each structural mutation: SHA alone cannot pass.
    raw = pack(header, full)
    n = 16+len('t')+1+8
    duplicate = raw[:64]+raw[64:64+n]+raw[64:]
    reject('duplicate-field', replace(synthetic, binary=duplicate, digest=sha(duplicate)), 1.)
    import ctypes as C
    for slot, kind in sim._fields_:
        if not issubclass(kind, C._CFuncPtr):
            continue
        setattr(sim, slot, kind(lambda *args: 0))
        try:
            try:
                guard.capture(sim)
            except ValueError as exc:
                rows.append(dict(name='callback-'+slot, rejected_before_export=True, reason=str(exc)))
            else:
                raise AssertionError('Unsupported callback exported')
        finally:
            # Public setters wrap a callable and reject None. Clear only the
            # owned test simulation's actual C pointer slot.
            setattr(sim, slot, kind())
    # Inject warning bits AFTER real, valid C calls; not a claim upstream emits
    # them on the accepted pilot. Unknown 2048 must not vanish in Python mapping.
    for phase in ('_archive_create', '_initialize'):
        original = getattr(guard, phase)
        for bit in (4, 128, 2048):
            def injected(*args, original=original, bit=bit):
                result = original(*args)
                args[-1].value |= bit
                return result
            setattr(guard, phase, injected)
            try:
                try:
                    guard.restore(saved, 0.)
                except ValueError as exc:
                    rows.append(dict(name=phase+'-mask-'+str(bit), injected=True, rejected=True, reason=str(exc)))
                else:
                    raise AssertionError('C warning ignored')
            finally:
                setattr(guard, phase, original)
    restored, masks = guard.restore(saved, 0.)
    if masks != (0, 0) or numeric_fields(saved) != numeric_fields(guard.capture(restored)):
        raise AssertionError('Unintegrated positive roundtrip failed')
    original = guard._initialize
    def python_warning(*args):
        original(*args)
        warnings.warn('injected RuntimeWarning', RuntimeWarning)
    guard._initialize = python_warning
    try:
        try:
            guard.restore(saved, 0.)
        except ValueError as exc:
            rows.append(dict(name='python-RuntimeWarning', injected=True, rejected=True, reason=str(exc)))
        else:
            raise AssertionError('Python warning ignored')
    finally:
        guard._initialize = original
    return rows


def paired(case, library, epsilon, guard, directory):
    req, times = case['request'], case['times']
    warm = simulation(library, 0., req['masses'], case['initial'], req['packet_dt'], epsilon)
    full = CommittedFullState(guard, simulation(library, 0., req['masses'], case['initial'], req['packet_dt'], epsilon))
    states, epochs, binaries, physicals = [case['initial']], [0.], {}, {}
    warm_outputs, full_outputs, last = [], [], full.current
    directory.mkdir(parents=True, exist_ok=False)
    def persist(saved, stem):
        # Each file is new. On any later failure all completed boundaries and
        # the latest warm candidate remain available, not just an exception.
        with (directory/(stem+'.bin')).open('xb') as target:
            target.write(saved.binary)
        metadata = dict(saved.__dict__)
        del metadata['binary']
        with (directory/(stem+'.json')).open('x', encoding='utf-8', newline='\n') as target:
            json.dump(metadata, target, indent=2, allow_nan=False)
    for mode, saved in [('warm', guard.capture(warm)), ('full', full.current)]:
        binaries[mode] = [base64.b64encode(saved.binary).decode('ascii')]
        physicals[mode] = [saved.physical_json]
        persist(saved, mode+'-0000')
    warm_integration = 0.
    for epoch in times:
        while warm.t < epoch:
            end = packet_end(float(warm.t), float(epoch), req['packet_dt'])
            start = perf_counter()
            warm.integrate(end, exact_finish_time=1)
            warm_integration += perf_counter()-start
            warm_saved = guard.capture(warm)
            persist(warm_saved, 'warm-'+str(len(epochs)).zfill(4))
            last = full.next(end)
            persist(last, 'full-'+str(len(epochs)).zfill(4))
            if numeric_fields(warm_saved, independent_control=True) != numeric_fields(last, independent_control=True):
                raise ArithmeticError('Warm/full packet differs: '+str(end))
            if bits(snapshot(warm)) != bits(snapshot(full.sim)):
                raise ArithmeticError('Warm/restored physical state differs')
            states.append(snapshot(warm))
            epochs.append(end)
            for mode, saved in [('warm', warm_saved), ('full', last)]:
                binaries[mode].append(base64.b64encode(saved.binary).decode('ascii'))
                physicals[mode].append(saved.physical_json)
        warm_outputs.append(snapshot(warm))
        full_outputs.append(snapshot(full.sim))
    arrays = dict(warm=np.asarray(warm_outputs), full=np.asarray(full_outputs),
        packet_states=np.asarray(states), packet_endpoints=np.asarray(epochs))
    for mode in binaries:
        arrays[mode+'_binary_base64'] = np.asarray(binaries[mode])
        arrays[mode+'_physical_json'] = np.asarray(physicals[mode])
    sizes = [len(base64.b64decode(v)) for v in binaries['full']]
    stats = dict(packets=full.packets, restored_snapshots=full.packets,
        all_packet_fields_bitexact=True, all_restored_fields_bitexact=True,
        ias15_written_fields=17, N_allocated=6, raw_c_masks=full.masks,
        stream_bytes=dict(initial=sizes[0], minimum_committed=min(sizes[1:]), maximum_committed=max(sizes[1:])),
        cost_seconds=dict(warm_integration=warm_integration, **full.cost),
        cost_scope='single paired run; reading includes strict re-export validation; not a speed benchmark')
    return arrays, stats


def run(output, library_directory, guards_only=False):
    output = Path(output).resolve()
    if not output.is_relative_to((ROOT/'.tools').resolve()) or output.exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a new output under .tools; preserve old results')
    library = load_library(library_directory)
    cases, inputs = load_cases()
    case = cases['holdout_circular']
    pinned = json.loads((ROOT/LIBRARY).read_text(encoding='utf-8'))['library_files_sha256']
    inputs[LIBRARY] = sha((ROOT/LIBRARY).read_bytes())
    for name in ('docs/ias15-restart-validation.json', 'docs/ias15-restart-samples.npz'):
        inputs[name] = sha((ROOT/name).read_bytes())
    with np.load(ROOT/'docs/ias15-restart-samples.npz', allow_pickle=False) as previous:
        old = {n: previous[n].copy() for n in previous.files if n.startswith('holdout_circular__')}
    names = [PROTOCOL, 'scripts/ias15_full_state.py', 'scripts/assess_ias15_full_state.py',
             'tests/test_ias15_full_state.py', 'scripts/replay_ias15_full_state.py', 'scripts/assess_ias15_restart.py',
             'docs/ias15-archive-source-validation.json']
    source = old_sources() | {n: sha((ROOT/n).read_bytes()) for n in names}
    output.parent.mkdir(parents=True, exist_ok=True)
    archive = output.with_name(output.stem+'-sources.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as saved_sources:
        for name in source:
            saved_sources.writestr(name, (ROOT/name).read_bytes())
    report = dict(protocol=PROTOCOL, complete=False, guards_only=guards_only,
        runtime_modified=False, production_eligible=False, case='holdout_circular',
        source_sha256=source, input_sha256=inputs, source_archive_sha256=sha(archive.read_bytes()),
        library_files_sha256=pinned, environment=dict(python=platform.python_version(),
        numpy=np.__version__, rebound=library.__version__, platform=platform.platform()),
        request=case['request'], origin=case['origin'], results={})
    arrays = {'times': case['times'], 'oracle100': np.asarray([[str(v) for v in row] for row in case['expected']])}
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    def verify():
        if any(sha((ROOT/n).read_bytes()) != digest for n, digest in (source | inputs).items()):
            raise ValueError('Executed source/input changed')
        if library_hashes(library) != pinned:
            raise ValueError('Pinned library changed during run')
    save()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            for epsilon in EPSILONS:
                req = case['request']
                guard = FullStateGuard(library, req['masses'], case['initial'], req['packet_dt'], epsilon, case['origin'], pinned)
                sim = simulation(library, 0., req['masses'], case['initial'], req['packet_dt'], epsilon)
                row = report['results'][str(epsilon)] = dict(guards=guard_checks(guard, sim), abi=guard.abi)
                save()
                if guards_only:
                    continue
                values, statistics = paired(case, library, epsilon, guard,
                    output.with_name(output.stem+'-packets')/str(epsilon))
                cold, cold_stats, cold_artifacts = trajectory(req['masses'], case['initial'], case['times'], req['packet_dt'],
                    library, epsilon, 'every-packet', case['origin'])
                values['cold'] = cold
                for key, value in cold_artifacts.items():
                    values['cold_'+key] = value
                if bits(values['packet_endpoints']) != bits(cold_artifacts['packet_endpoints']):
                    raise ArithmeticError('Cold/warm packet schedule changed')
                for current, previous in (('warm', 'warm'), ('full', 'warm'), ('cold', 'every-packet')):
                    if bits(values[current]) != bits(old['holdout_circular__'+str(epsilon)+'__'+previous+'__values']):
                        raise ArithmeticError('Previous353 output changed: '+current)
                expected = [(v[:3], v[3:]) for v in case['expected']]
                row.update(statistics=statistics, cold_statistics=cold_stats,
                    previous353_warm_cold_bitexact=True,
                    metrics={mode: metrics(case['seed'], case['times'], values[mode], expected) for mode in ('warm', 'full', 'cold')})
                row['pilot_passed'] = all(row['metrics'][mode]['checks_passed'] for mode in ('warm', 'full'))
                for key, value in values.items():
                    arrays[str(epsilon)+'__'+key] = value
                save()
                print(epsilon, 'packets', statistics['packets'], 'warm/full PASS', row['pilot_passed'],
                      'cold old-gates PASS', row['metrics']['cold']['checks_passed'], flush=True)
            if caught:
                raise ValueError('Unexpected Python warnings: '+repr([str(w.message) for w in caught]))
        verify()
        report['complete'] = True
        report['pilot_passed'] = not guards_only and all(row['pilot_passed'] for row in report['results'].values())
    except BaseException as exc:
        report['failure'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        np.savez_compressed(output.with_suffix('.npz'), **arrays)
        report['array_archive_sha256'] = sha(output.with_suffix('.npz').read_bytes())
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--guards-only', action='store_true')
    args = parser.parse_args()
    run(args.output, args.library, args.guards_only)


if __name__ == '__main__':
    main()
