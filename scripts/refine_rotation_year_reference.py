"""Preserve annual baseline; tighten only the independently implemented RK45 oracle."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_rotation_year import sha, initial_setup, cached_job, pack, compare, validate_arrays
from scripts.assess_nbody_rotation import reference


def refine():
    output = ROOT / 'docs/rotation-year-reference-validation.json'
    if output.exists():
        raise FileExistsError('Preserve original refinement')
    policy_path = ROOT / 'scripts/rotation-year-reference-policy.json'
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    parent_path = ROOT / policy['parent_audit']
    parent = json.loads(parent_path.read_text(encoding='utf-8'))
    hashes = dict(parent['code_sha256'])
    hashes.update({path: sha(ROOT/path) for path in
        ('scripts/refine_rotation_year_reference.py', 'scripts/rotation-year-reference-policy.json')})
    for path, digest in hashes.items():
        if sha(ROOT/path) != digest:
            raise ValueError(f'Changed source: {path}')
    bodies, _, states, times, start = initial_setup(parent['policy']); spin = states[0]
    from solar_simulator.storage import to_document
    if json.loads(json.dumps(to_document(start))) != parent['initial_document']:
        raise ValueError('Initial checkpoint mismatch')
    if times.tolist() != parent['sample_times_seconds']:
        raise ValueError('Annual grid mismatch')
    directory = ROOT / '.tools/rotation54/year'
    def previous(name):
        path = directory/(name+'.npz'); metadata = directory/(name+'.json')
        record = json.loads(metadata.read_text(encoding='utf-8'))
        expected = parent['jobs'][name]
        if record != expected or sha(path) != expected['npz_sha256']:
            raise ValueError(f'Changed annual cache: {name}')
        context = record['context']
        if context['code_sha256'] != parent['code_sha256'] or context['policy'] != parent['policy']:
            raise ValueError('Cache source/policy mismatch')
        if context['initial_document'] != parent['initial_document'] or context['sample_times_seconds'] != times.tolist():
            raise ValueError('Cache initial state/grid mismatch')
        with np.load(path, allow_pickle=False) as archive:
            data = {key: archive[key] for key in archive.files}
        validate_arrays(data, len(times), len(bodies))
        return data
    primary = previous('production'); earlier = previous('reference-1')
    context = dict(job='independent-matrix-RK45-3e-14', policy=policy, code_sha256=hashes,
                   parent_audit_sha256=sha(parent_path), sample_times_seconds=times.tolist(),
                   initial_document=parent['initial_document'])
    refined, record = cached_job(directory, 'reference-refined', context, len(times), len(bodies),
        lambda: pack(reference(bodies, spin, times, policy['new_reference_rtol'], policy['reference_max_step'])))
    difference = compare(primary, refined, bodies, spin)
    uncertainty = compare(earlier, refined, bodies, spin)
    matrices = refined['matrices']
    metrics = dict(parent['metrics'], reference_difference=difference['maximum'],
        reference_uncertainty=uncertainty['maximum'], per_body_reference_difference=difference['per_body_maximum'],
        per_body_reference_uncertainty=uncertainty['per_body_maximum'],
        reference_matrix_orthogonality=float(np.linalg.norm(matrices.transpose(0, 2, 1)@matrices-np.eye(3), axis=(1, 2)).max()),
        reference_matrix_determinant=float(np.max(abs(np.linalg.det(matrices)-1))))
    for path, digest in hashes.items():
        if sha(ROOT/path) != digest:
            raise ValueError(f'Source changed during refinement: {path}')
    failures = [key for key, limit in parent['policy']['criteria'].items() if metrics[key] >= limit]
    result = dict(model=parent['model'], policy=policy, parent_audit_sha256=sha(parent_path),
        code_sha256=hashes, sample_times_seconds=times.tolist(), metrics=metrics,
        reference_components=difference, reference_uncertainty_components=uncertainty,
        reused_metrics='E/L/P/q/restart and descriptive DE441 values remain in unchanged parent audit',
        job=record, failed_criteria=failures, passed=not failures)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(metrics, 'failed criteria', failures, flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if refine()['passed'] else 1)
