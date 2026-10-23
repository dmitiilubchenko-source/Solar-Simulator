"""One fresh same-build IAS15 restore/continuation. Not an application API."""
import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter
import warnings

from scripts.ias15_process import (ROOT, read_request, verify_files, context, validate_context, signature, sha, persist,
                                  validate_identity)


def run(request_path, request_sha, library_directory, directory):
    directory = Path(directory).resolve()
    if not directory.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Worker output must stay under .tools')
    if any((directory/n).exists() for n in ('result.json', 'result.npz', 'worker-start.json', 'packets')):
        raise FileExistsError('Preserve previous worker evidence')
    info = dict(complete=False, pid=os.getpid(), ppid=os.getppid(), os_name=os.name, c_restore_started=False,
                rebound_already_imported='rebound' in sys.modules, request_sha256=request_sha,
                last_committed_index=None, launch_id=None)
    with (directory/'worker-start.json').open('x', encoding='utf-8') as file:
        json.dump(info, file)
    indices, states, signatures = [], [], []
    try:
        metadata = json.loads(sys.stdin.readline(8192))
        info.update(launch_id=metadata['launch_id'], supervisor_pid=metadata['supervisor_pid'],
                    launched_pid=metadata['launched_pid'])
        validate_identity(info, dict(parent_pid=metadata['supervisor_pid'], launch_id=metadata['launch_id']),
                          dict(pid=metadata['launched_pid']))
        request = read_request(request_path, request_sha)
        validate_identity(info, request, dict(pid=metadata['launched_pid']))
        if info['rebound_already_imported']:
            raise ValueError('Expected a fresh direct child process')
        bindings = request['source_sha256'] | request['input_sha256']
        verify_files(bindings)
        from scripts.ias15_process import bindings as expected_bindings
        if (request['source_sha256'], request['input_sha256']) != expected_bindings():
            raise ValueError('Wrong file-binding inventory')
        ctx = context(request['case'], request['epsilon'])
        validate_context(request, ctx)
        # No optional library or C snapshot load before wire/context verification.
        import numpy as np
        from scripts.ias15_reference import load_library, library_hashes
        from scripts.ias15_full_state import FullStateGuard
        from scripts.ias15_restart import bits, snapshot
        library = load_library(library_directory)
        req, base, start = ctx['request'], ctx['base'], request['index']
        guard = FullStateGuard(library, req['masses'], req['states'], req['packet_dt'],
                               float(request['epsilon']), request['origin'], base['library_files_sha256'])
        info.update(abi=guard.abi, version=library.__version__, python=sys.version,
                    library_sha=guard.library_sha, costs=dict(reading=0., integration=0., capture=0., writing=0.))
        progress = directory/'packets'
        progress.mkdir()
        def commit(index, saved):
            tick = perf_counter()
            persist(progress, index, saved, ctx['saved'](index))
            indices.append(index)
            states.append(snapshot(sim))
            signatures.append(signature(saved))
            info['last_committed_index'] = index
            info['costs']['writing'] += perf_counter()-tick
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            tick = perf_counter()
            guard.preflight(ctx['saved'](start), float(ctx['ends'][start]))
            info['c_restore_started'] = True
            sim, masks = guard.restore(ctx['saved'](start), float(ctx['ends'][start]))
            info['costs']['reading'] += perf_counter()-tick
            info['restore_masks'] = list(masks)
            commit(start, guard.capture(sim))
            for index in range(start+1, len(ctx['ends'])):
                end = float(ctx['ends'][index])
                tick = perf_counter()
                sim.integrate(end, exact_finish_time=1)
                info['costs']['integration'] += perf_counter()-tick
                if bits(sim.t) != bits(end):
                    raise ArithmeticError('Wrong packet endpoint')
                tick = perf_counter()
                candidate = guard.capture(sim)
                info['costs']['capture'] += perf_counter()-tick
                commit(index, candidate)
            if caught:
                raise ValueError('Unexpected Python warning: '+str(caught[0].message))
        verify_files(bindings)
        if library_hashes(library) != base['library_files_sha256']:
            raise ValueError('Library changed during child execution')
        info['complete'] = True
    except Exception as exc:
        info['failure'] = dict(type=type(exc).__name__, message=str(exc))
    finally:
        # Even malformed-wire failures retain a readable result and immutable logs.
        if states:
            import numpy as np
            with (directory/'result.npz').open('xb') as target:
                np.savez_compressed(target, indices=np.asarray(indices), states=np.asarray(states),
                                    signatures=np.asarray(signatures))
            info['arrays_sha256'] = sha((directory/'result.npz').read_bytes())
        with (directory/'result.json').open('x', encoding='utf-8', newline='\n') as target:
            json.dump(info, target, indent=2, allow_nan=False)
            target.write('\n')
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.request, args.sha256, args.library, args.directory)
    if not result['complete']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
