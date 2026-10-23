"""Thirty-six fresh-process basic IAS15 restarts at fixed boundaries."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from time import perf_counter
import uuid
import zipfile

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases
from scripts.assess_ias15_full_suite import CASES
from scripts.ias15_process import (ROOT, BASE, SAMPLES, POINTS, bindings, context, request_for,
                                  verify_files, sha, launch, validate_child, signature, validate_identity)
from scripts.ias15_restart import bits


def composite(ctx, indices, states):
    expected_indices = np.arange(int(indices[0]), len(ctx['ends']))
    if not np.array_equal(indices, expected_indices) or states.shape != (len(indices), 2, 6) or not np.isfinite(states).all():
        raise ValueError('Incomplete/nonfinite child continuation')
    positions = np.searchsorted(ctx['ends'], ctx['times'])
    if bits(ctx['ends'][positions]) != bits(ctx['times']):
        raise ValueError('Frozen epochs are not exact packet boundaries')
    values = ctx['warm'].copy()
    mask = positions >= indices[0]
    values[mask] = states[positions[mask]-indices[0]]
    if bits(values) != bits(ctx['warm']):
        raise ArithmeticError('New-process outputs differ from frozen warm')
    return values, mask


def measured(case, ctx, indices, states):
    values, mask = composite(ctx, indices, states)
    expected = [(v[:3], v[3:]) for v in case['expected']]
    full = metrics(case['seed'], case['times'], values, expected)
    suffix = metrics(case['seed'], case['times'][mask], values[mask], [v for v, keep in zip(expected, mask) if keep])
    return dict(composite=full, suffix=suffix)


def execute(request, directory, library_directory, outer_sha=None):
    directory.mkdir(parents=True, exist_ok=False)
    path = directory/'request.json'
    path.write_text(json.dumps(request, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    digest = sha(path.read_bytes())
    command = [sys.executable, '-X', 'utf8', '-B', '-m', 'scripts.ias15_process_worker',
               '--request', str(path), '--sha256', outer_sha or digest,
               '--library', str(Path(library_directory).resolve()), '--directory', str(directory)]
    launched = launch(command, directory, launch_id=request['launch_id'])
    result_path = directory/'result.json'
    result = json.loads(result_path.read_bytes()) if result_path.exists() else dict(complete=False, failure={'message': 'No worker result'})
    if sha(path.read_bytes()) != digest:
        raise ValueError('Request changed during child execution')
    return digest, launched, result


def run(output, library_directory):
    output = Path(output).resolve()
    directory = output.with_name(output.stem+'-workers')
    source_zip = output.with_name(output.stem+'-sources.zip')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a research .tools output')
    if any(p.exists() for p in (output, output.with_suffix('.npz'), directory, source_zip)):
        raise FileExistsError('Preserve prior process results and logs')
    sources, inputs = bindings()
    verify_files(sources | inputs)
    cases, _ = load_cases()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source_zip, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sources:
            archive.writestr(name, (ROOT/name).read_bytes())
    report = dict(protocol='docs/ias15-process-protocol.md', complete=False, runtime_modified=False,
        production_eligible=False, parent_pid=os.getpid(), source_sha256=sources, input_sha256=inputs,
        source_archive_sha256=sha(source_zip.read_bytes()), negatives={}, results={})
    arrays = {}
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    def request(ctx, point):
        return request_for(ctx, point, os.getpid(), uuid.uuid4().hex, sources, inputs)
    started = perf_counter()
    save()
    try:
        pilot = context(CASES[0], '1e-09')
        for mutation in ('outer-sha', 'abi', 'binary-sha', 'source-sha'):
            req = request(pilot, 'first')
            req = deepcopy(req)
            if mutation == 'abi':
                req['abi'] = 'unqualified ABI'
            elif mutation == 'binary-sha':
                req['digest'] = '0'*64
            elif mutation == 'source-sha':
                req['source_sha256']['scripts/ias15_process_worker.py'] = '0'*64
            digest, launched, child = execute(req, directory/('negative-'+mutation), library_directory,
                                             '0'*64 if mutation == 'outer-sha' else None)
            validate_identity(child, req, launched)
            passed = (launched['returncode'] != 0 and not launched['timed_out'] and not child['complete']
                and not child.get('c_restore_started', True) and child.get('last_committed_index') is None)
            report['negatives'][mutation] = dict(passed=passed, launched=launched, child=child, request_sha256=digest)
            save()
            if not passed:
                raise ValueError('Real negative worker was not rejected before C restore: '+mutation)
        for name in CASES:
            for epsilon in ('1e-09', '1e-11'):
                ctx = context(name, epsilon)
                for point in POINTS:
                    job = name+'__'+epsilon+'__'+point
                    row = report['results'][job] = dict(complete=False)
                    req = request(ctx, point)
                    row['request'] = req
                    try:
                        digest, launched, child = execute(req, directory/job, library_directory)
                        row.update(request_sha256=digest, launched=launched, child=child)
                        validate_child(child, req, digest, launched)
                        file = directory/job/'result.npz'
                        if sha(file.read_bytes()) != child['arrays_sha256']:
                            raise ValueError('Child array SHA mismatch')
                        with np.load(file, allow_pickle=False) as data:
                            values = {k: data[k].copy() for k in data.files}
                        if set(values) != {'indices', 'states', 'signatures'} or values['indices'][0] != req['index']:
                            raise ValueError('Wrong child array inventory/start')
                        for key, value in values.items():
                            arrays[job+'__'+key] = value
                        expected_signatures = np.asarray([signature(ctx['saved'](int(i))) for i in values['indices']])
                        if (not np.array_equal(values['signatures'], expected_signatures)
                                or child['last_committed_index'] != len(ctx['ends'])-1):
                            raise ArithmeticError('Child field signatures/last commit differ')
                        if bits(values['states']) != bits(ctx['states'][values['indices']]):
                            raise ArithmeticError('Child physical packet states differ')
                        row['metrics'] = measured(cases[name], ctx, values['indices'], values['states'])
                        row['passed'] = all(v['checks_passed'] for v in row['metrics'].values())
                        row['complete'] = True
                    except Exception as exc:
                        row['failure'] = dict(type=type(exc).__name__, message=str(exc))
                    save()
                    verify_files(sources | inputs)
                    print(job, row.get('passed', False), row.get('failure', ''), flush=True)
        report['complete'] = True
        report['all_checks_passed'] = len(report['results']) == 36 and all(r.get('passed') and r['complete'] for r in report['results'].values())
    except BaseException as exc:
        report['failure'] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        report['wall_seconds_before_packaging'] = perf_counter()-started
        with output.with_suffix('.npz').open('xb') as target:
            np.savez_compressed(target, **arrays)
        report['array_archive_sha256'] = sha(output.with_suffix('.npz').read_bytes())
        try:
            verify_files(sources | inputs)
        except BaseException as exc:
            report['complete'] = False
            report['failure'] = dict(type=type(exc).__name__, message=str(exc))
            save()
            raise
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--library', type=Path, required=True)
    args = parser.parse_args()
    run(args.output, args.library)


if __name__ == '__main__':
    main()
