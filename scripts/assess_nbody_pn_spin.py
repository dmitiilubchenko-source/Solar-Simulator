"""Predeclared N-body canonical 1PN/SO audit with independent RK45 references."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.nbody_pn_spin import Parameters, rhs, invariants
from scripts.independent_nbody_pn_spin import rhs as reference_rhs, gradient


def difference(first, second, scales):
    if (scales.ndim != 2 or scales.shape[0] != 3 or np.any(scales <= 0)
            or not np.all(np.isfinite(scales))
            or first.shape != second.shape or first.ndim != 2 or first.shape[1] != scales.size*3
            or not np.all(np.isfinite(first)) or not np.all(np.isfinite(second))):
        raise ValueError('Invalid/mismatched reference trajectories')
    errors = np.linalg.norm((first-second).reshape(-1, *scales.shape, 3), axis=-1)/scales
    return dict(maximum=float(errors.max()), per_block_body=errors.max(axis=0).tolist())


def initial_state(policy):
    m = np.array(policy['masses'])
    x = np.array(policy['positions_before_translation'], dtype=float)
    p = np.array(policy['momenta_before_boost'], dtype=float)
    x -= np.sum(m[:, None]*x, axis=0)/m.sum()
    p -= m[:, None]*p.sum(axis=0)/m.sum()
    return np.stack([x, p, policy['spins']]).ravel()


def audit():
    output = ROOT/'docs/nbody-pn-spin-validation.json'
    if output.exists(): raise FileExistsError('Preserve original N-body audit')
    policy = json.loads((ROOT/'scripts/nbody-pn-spin-policy.json').read_text(encoding='utf-8'))
    paths = ['scripts/nbody-pn-spin-policy.json', 'scripts/nbody_pn_spin.py',
             'scripts/independent_nbody_pn_spin.py', 'scripts/assess_nbody_pn_spin.py',
             'tests/test_nbody_pn_spin.py', 'scripts/pn_spin_model.py',
             'src/solar_simulator/relativity.py', 'src/solar_simulator/nbody_rotation.py']
    sha = lambda path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    hashes = {path: sha(path) for path in paths}
    params = Parameters(tuple(policy['masses']), policy['c']); count = len(params.masses)
    initial = initial_state(policy); scales = np.linalg.norm(initial.reshape(3, count, 3), axis=-1)
    if np.any(scales <= 0): raise ValueError('Audit requires nonzero initial scales for all bodies/blocks')
    times = np.linspace(0., policy['periods']*policy['nominal_inner_period'], policy['samples'])
    jobs = {}; elapsed = {}
    def integrate(name, field, method, tol, atol_ratio):
        print(name, 'started', flush=True); start = time.perf_counter()
        sol = solve_ivp(field, (0., float(times[-1])), initial, t_eval=times, method=method,
                       rtol=tol, atol=tol*atol_ratio*np.repeat(scales.ravel(), 3),
                       max_step=policy['max_step_over_period']*policy['nominal_inner_period'])
        if (not sol.success or sol.y.shape != (9*count, len(times))
                or not np.array_equal(sol.t, times) or not np.all(np.isfinite(sol.y))):
            raise ValueError(f'Failed/invalid integration: {name}')
        elapsed[name] = time.perf_counter()-start
        jobs[name] = dict(state=sol.y.T, times=sol.t, nfev=sol.nfev)
        print(name, round(elapsed[name], 2), 'seconds', flush=True)
        return sol.y.T
    primary = integrate('production', lambda t, y: rhs(t, y, params), 'DOP853',
                        policy['production_rtol'], policy['production_atol_over_rtol'])
    refs = [integrate(f'reference-{i}', lambda t, y: reference_rhs(t, y, params.masses, params.c),
                     'RK45', tol, policy['reference_atol_over_rtol'])
            for i, tol in enumerate(policy['reference_rtols'])]
    def wrong_field(t, y):
        f = rhs(t, y, params, spin_orbit=False).reshape(3, count, 3)
        f[2] = rhs(t, y, params).reshape(3, count, 3)[2]
        return f.ravel()
    wrong = integrate('missing-SO-reaction', wrong_field, 'DOP853',
                      policy['production_rtol'], policy['production_atol_over_rtol'])
    values = [invariants(y, params) for y in primary]
    energy = np.array([v[0] for v in values]); momentum = np.array([v[1] for v in values])
    angular = np.array([v[2] for v in values]); spins = np.array([v[3] for v in values])
    energy_scale = abs(energy[0]); j_scale = np.linalg.norm(angular[0]); p_scale = scales[1].sum()
    if min(energy_scale, j_scale, p_scale) <= 0: raise ValueError('Degenerate invariant audit scales')
    bad_j = np.array([invariants(y, params)[2] for y in wrong])
    delta = difference(primary, refs[-1], scales); uncertainty = difference(refs[0], refs[1], scales)
    rng = np.random.default_rng(policy['gradient_seed']); gradient_errors = []
    for _ in range(policy['gradient_states']):
        y = initial.reshape(3, count, 3).copy()
        for block, amplitude in enumerate([.05, .005, .0001]):
            y[block] += rng.normal(size=(count, 3))*amplitude
        g = gradient(y.ravel(), params.masses, params.c).reshape(3, count, 3)
        expected = np.stack([g[1], -g[0], np.cross(g[2], y[2])])
        if np.any(np.linalg.norm(expected, axis=-1) == 0): raise ValueError('Degenerate gradient comparison')
        gradient_errors.extend((np.linalg.norm(rhs(0, y.ravel(), params).reshape(3, count, 3)-expected,
                                              axis=-1)/np.linalg.norm(expected, axis=-1)).ravel())
    complete = gradient(initial, params.masses, params.c)[:3*count]
    missing = gradient(initial, params.masses, params.c, omit_distinct_triples=True)[:3*count]
    metrics = dict(energy_relative=float(abs(energy-energy[0]).max()/energy_scale),
        momentum_scaled=float(np.linalg.norm(momentum-momentum[0], axis=1).max()/p_scale),
        angular_momentum_relative=float(np.linalg.norm(angular-angular[0], axis=1).max()/j_scale),
        spin_norm_relative=float((abs(spins-spins[0])/spins[0]).max()),
        reference_difference=delta['maximum'], reference_uncertainty=uncertainty['maximum'],
        hamiltonian_gradient_relative=float(max(gradient_errors)),
        negative_control_J_drift_minimum=float(np.linalg.norm(bad_j-bad_j[0], axis=1).max()/j_scale),
        missing_triple_force_relative_minimum=float(np.linalg.norm(complete-missing)/np.linalg.norm(complete)))
    if not all(np.isfinite(v) for v in metrics.values()): raise ValueError('Nonfinite metrics')
    failures = [key for key, limit in policy['criteria'].items()
                if (metrics[key] <= limit if key.endswith('_minimum') else metrics[key] >= limit)]
    for path, digest in hashes.items():
        if sha(path) != digest: raise ValueError(f'Source changed during calculation: {path}')
    arrays = ROOT/'.tools/rotation56/nbody-pn-spin-trajectories.npz'
    if arrays.exists(): raise FileExistsError('Preserve original trajectory archive')
    arrays.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(arrays, **{f'{name}-{key}': value for name, job in jobs.items() for key, value in job.items()})
    result = dict(policy=policy, code_sha256=hashes, initial_state=initial.tolist(),
        scaling_x_p_S_per_body=scales.tolist(), invariant_scales=dict(H=energy_scale, J=j_scale, P=p_scale),
        sample_times=times.tolist(), metrics=metrics, failed_criteria=failures, passed=not failures,
        reference_components=delta, reference_uncertainty_components=uncertainty,
        job_elapsed_seconds=elapsed, nfev={name: job['nfev'] for name, job in jobs.items()},
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        trajectory_archive_local_path=str(arrays.relative_to(ROOT)), trajectory_archive_sha256=sha(arrays),
        future_ephemerides_called=False, runtime_model_changed=False)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(metrics, 'failed criteria', failures, flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if audit()['passed'] else 1)
