"""Verify fresh-process evidence without importing REBOUND or integrating."""
import argparse
import json
from pathlib import Path

import numpy as np

from scripts.assess_ias15_full_suite import CASES
from scripts.assess_ias15_restart import load_cases
from scripts.assess_ias15_process import measured
from scripts.ias15_process import (ROOT, POINTS, verify_files, context, validate_context, validate_child,
                                  signature, sha, validate_identity)
from scripts.ias15_restart import bits
from scripts.release_history import ui_historical_sha

REPORT = 'docs/ias15-process-validation.json'
ARRAYS = 'docs/ias15-process-samples.npz'


def replay(root=ROOT, report_path=REPORT, arrays_path=ARRAYS):
    root = Path(root)
    if root.resolve() != ROOT.resolve():
        raise ValueError('Replay uses the current pinned project checkout')
    report = json.loads((root/report_path).read_bytes())
    expected_jobs = [n+'__'+e+'__'+p for n in CASES for e in ('1e-09', '1e-11') for p in POINTS]
    if (not report['complete'] or not report['all_checks_passed'] or report['runtime_modified']
            or report['production_eligible'] or report['protocol'] != 'docs/ias15-process-protocol.md'
            or list(report['results']) != expected_jobs):
        raise ValueError('Incomplete/unqualified process matrix')
    for name,expected in (report['source_sha256'] | report['input_sha256']).items():
        if ui_historical_sha(root,name,expected)!=expected:raise ValueError('File binding SHA mismatch: '+name)
    if sha((root/arrays_path).read_bytes()) != report['array_archive_sha256']:
        raise ValueError('Process array SHA mismatch')
    negatives = report['negatives']
    if set(negatives) != {'outer-sha', 'abi', 'binary-sha', 'source-sha'}:
        raise ValueError('Missing real negative worker')
    for row in negatives.values():
        child, launched = row['child'], row['launched']
        validate_identity(child, dict(parent_pid=report['parent_pid'], launch_id=child['launch_id']), launched)
        if (not row['passed'] or child['complete'] or child['c_restore_started']
                or child['last_committed_index'] is not None or launched['returncode'] == 0 or launched['timed_out']):
            raise ValueError('Negative worker was not rejected before C restore')
    with np.load(root/arrays_path, allow_pickle=False) as archive:
        data = {k: archive[k].copy() for k in archive.files}
    cases, _ = load_cases()
    expected_keys, records, steps = set(), 0, 0
    for name in CASES:
        for epsilon in ('1e-09', '1e-11'):
            ctx = context(name, epsilon)
            for point in POINTS:
                job = name+'__'+epsilon+'__'+point
                row = report['results'][job]
                req = row['request']
                validate_context(req, ctx)
                if (req['case'] != name or req['epsilon'] != epsilon or req['point'] != point
                        or req['parent_pid'] != report['parent_pid']
                        or req['source_sha256'] != report['source_sha256'] or req['input_sha256'] != report['input_sha256']):
                    raise ValueError('Wrong process request binding')
                digest = sha((json.dumps(req, indent=2, allow_nan=False)+'\n').encode())
                if digest != row['request_sha256']:
                    raise ValueError('Recorded wire request SHA differs')
                validate_child(row['child'], req, digest, row['launched'])
                keys = {key: job+'__'+key for key in ('indices', 'states', 'signatures')}
                expected_keys.update(keys.values())
                indices, states, signatures = (data[keys[k]] for k in ('indices', 'states', 'signatures'))
                if (indices[0] != req['index'] or not np.array_equal(indices, np.arange(req['index'], len(ctx['ends'])))
                        or states.shape != (len(indices), 2, 6) or bits(states) != bits(ctx['states'][indices])
                        or not np.array_equal(signatures, np.asarray([signature(ctx['saved'](int(i))) for i in indices]))):
                    raise ValueError('Physical continuation or complete field signatures differ')
                if measured(cases[name], ctx, indices, states) != row['metrics'] or not all(v['checks_passed'] for v in row['metrics'].values()):
                    raise ValueError('Independent composite/suffix metrics differ or failed')
                if not row['complete'] or not row['passed'] or row['child']['last_committed_index'] != len(ctx['ends'])-1:
                    raise ValueError('False last commit/PASS metadata')
                records += len(indices)
                steps += len(indices)-1
    if set(data) != expected_keys:
        raise ValueError('Process array inventory differs')
    return dict(cases=9, variants=18, positive_children=36, negative_children=4, continued_steps=steps,
                packet_records=records, arrays=len(data), all_checks_passed=True,
                independent_metrics_reproduced=True, runtime_modified=False,
                scope='offline physical/signature replay; no new child/C load/integration')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', default=REPORT)
    parser.add_argument('--arrays', default=ARRAYS)
    args = parser.parse_args()
    print(json.dumps(replay(report_path=args.report, arrays_path=args.arrays), indent=2))


if __name__ == '__main__':
    main()
