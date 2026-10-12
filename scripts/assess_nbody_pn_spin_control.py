"""Separate extended negative-control audit; never overwrite the original failure."""
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.nbody_pn_spin import Parameters, rhs, invariants


def audit():
    output = ROOT/'docs/nbody-pn-spin-control-validation.json'
    if output.exists(): raise FileExistsError('Preserve extended control audit')
    policy_path = 'scripts/nbody-pn-spin-control-policy.json'
    policy = json.loads((ROOT/policy_path).read_text(encoding='utf-8'))
    sha = lambda path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    baseline = json.loads((ROOT/policy['baseline']).read_text(encoding='utf-8'))
    if baseline['failed_criteria'] != ['negative_control_J_drift_minimum']:
        raise ValueError('Unexpected original audit failure; do not mask it')
    hashes = dict(baseline['code_sha256'])
    for path, digest in hashes.items():
        if sha(path) != digest: raise ValueError(f'Baseline source changed: {path}')
    hashes.update({path: sha(path) for path in [policy_path, policy['baseline'],
                  'scripts/assess_nbody_pn_spin_control.py']})
    array_path = baseline['trajectory_archive_local_path']
    if sha(array_path) != baseline['trajectory_archive_sha256']:
        raise ValueError('Baseline archive changed')
    hashes[array_path] = sha(array_path)
    initial = np.array(baseline['initial_state']); scales = np.array(baseline['scaling_x_p_S_per_body'])
    with np.load(ROOT/array_path, allow_pickle=False) as arrays:
        for name in ['production', 'reference-0', 'reference-1', 'missing-SO-reaction']:
            y = arrays[name+'-state']; t = arrays[name+'-times']
            if (y.shape != (len(baseline['sample_times']), len(initial))
                    or not np.array_equal(y[0], initial) or not np.all(np.isfinite(y))
                    or not np.array_equal(t, baseline['sample_times'])):
                raise ValueError('Baseline arrays/start/grid invalid')
    base_policy = baseline['policy']; count = len(base_policy['masses'])
    params = Parameters(tuple(base_policy['masses']), base_policy['c'])
    times = np.linspace(0., policy['periods']*base_policy['nominal_inner_period'], policy['samples'])
    def wrong_field(t, y):
        f = rhs(t, y, params, spin_orbit=False).reshape(3, count, 3)
        f[2] = rhs(t, y, params).reshape(3, count, 3)[2]
        return f.ravel()
    trajectories = {}; elapsed = {}
    for name, field in [('complete', lambda t, y: rhs(t, y, params)), ('missing-reaction', wrong_field)]:
        print(name, 'started', flush=True); start = time.perf_counter()
        sol = solve_ivp(field, (0., float(times[-1])), initial, t_eval=times, method='DOP853',
                       rtol=policy['rtol'], atol=policy['rtol']*policy['atol_over_rtol']*np.repeat(scales.ravel(), 3),
                       max_step=policy['max_step_over_period']*base_policy['nominal_inner_period'])
        if (not sol.success or sol.y.shape != (len(initial), len(times))
                or not np.array_equal(sol.t, times) or not np.all(np.isfinite(sol.y))):
            raise ValueError(f'Failed extended control: {name}')
        trajectories[name] = sol.y.T; elapsed[name] = time.perf_counter()-start
        print(name, round(elapsed[name], 2), 'seconds', flush=True)
    values = [invariants(y, params) for y in trajectories['complete']]
    energy = np.array([v[0] for v in values]); p = np.array([v[1] for v in values])
    j = np.array([v[2] for v in values]); spins = np.array([v[3] for v in values])
    wrong_j = np.array([invariants(y, params)[2] for y in trajectories['missing-reaction']])
    metrics = dict(energy_relative=float(abs(energy-energy[0]).max()/baseline['invariant_scales']['H']),
        momentum_scaled=float(np.linalg.norm(p-p[0], axis=1).max()/baseline['invariant_scales']['P']),
        angular_momentum_relative=float(np.linalg.norm(j-j[0], axis=1).max()/baseline['invariant_scales']['J']),
        spin_norm_relative=float((abs(spins-spins[0])/spins[0]).max()),
        negative_control_J_drift_minimum=float(np.linalg.norm(wrong_j-wrong_j[0], axis=1).max()/baseline['invariant_scales']['J']))
    if not all(np.isfinite(v) for v in metrics.values()): raise ValueError('Nonfinite extended metrics')
    failures = [key for key, limit in policy['criteria'].items()
                if (metrics[key] <= limit if key.endswith('_minimum') else metrics[key] >= limit)]
    for path, digest in hashes.items():
        if sha(path) != digest: raise ValueError(f'Source/artifact changed during extended audit: {path}')
    array_output = ROOT/'.tools/rotation56/nbody-pn-spin-control-trajectories.npz'
    if array_output.exists(): raise FileExistsError('Preserve extended trajectories')
    np.savez_compressed(array_output, times=times, **trajectories)
    wrong_s = trajectories['missing-reaction'].reshape(-1, 3, count, 3)[:, 2]
    spin_changes = wrong_s-wrong_s[0]
    result = dict(policy=policy, code_and_baseline_sha256=hashes, metrics=metrics,
        passed=not failures, failed_criteria=failures, job_elapsed_seconds=elapsed,
        individual_missing_reaction_spin_change_max=np.linalg.norm(spin_changes, axis=-1).max(axis=0).tolist(),
        total_missing_reaction_spin_change_max=float(np.linalg.norm(spin_changes.sum(axis=1), axis=1).max()),
        initial_spin_derivatives=rhs(0., initial, params).reshape(3, count, 3)[2].tolist(),
        baseline_original_passed=baseline['passed'], baseline_original_failures=baseline['failed_criteria'],
        trajectory_archive_local_path=str(array_output.relative_to(ROOT)), trajectory_archive_sha256=sha(array_output),
        future_ephemerides_called=False, runtime_model_changed=False)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    print(metrics, 'failed criteria', failures, flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if audit()['passed'] else 1)
