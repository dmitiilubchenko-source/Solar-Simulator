"""Predeclared canonical PN/spin model audit, independent gradient RK45 oracle."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.pn_spin_model import Parameters, rhs, invariants, exact_so
from scripts.independent_pn_spin import rhs as independent_rhs, gradient


def normalized_difference(first, second, scales):
    if first.shape != second.shape or first.ndim != 2 or first.shape[1] != 9:
        raise ValueError('Mismatched reference state grids')
    if not np.all(np.isfinite(first)) or not np.all(np.isfinite(second)):
        raise ValueError('Nonfinite reference states')
    blocks = np.linalg.norm((first-second).reshape(-1, 3, 3), axis=2)/scales
    return dict(position=float(blocks[:, 0].max()), momentum=float(blocks[:, 1].max()),
                spin=float(blocks[:, 2].max()), maximum=float(blocks.max()))


def audit():
    output = ROOT/'docs/pn-spin-validation.json'
    if output.exists():
        raise FileExistsError('Preserve original PN/spin audit')
    policy = json.loads((ROOT/'scripts/pn-spin-policy.json').read_text(encoding='utf-8'))
    paths = ['scripts/pn-spin-policy.json', 'scripts/pn_spin_model.py', 'scripts/independent_pn_spin.py',
             'scripts/assess_pn_spin.py', 'tests/test_pn_spin_model.py',
             'src/solar_simulator/relativity.py', 'src/solar_simulator/nbody_rotation.py']
    sha = lambda path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    hashes = {path: sha(path) for path in paths}
    parameters = Parameters(policy['mass1'], policy['mass2'], policy['c'])
    axis, eccentricity = policy['semimajor_axis'], policy['eccentricity']
    radius = axis*(1-eccentricity)
    kepler_speed = np.sqrt(parameters.total*(1+eccentricity)/radius)
    initial = np.r_[[radius, 0., 0.], [0., parameters.reduced*kepler_speed, 0.], policy['initial_spin']]
    period = 2*np.pi*np.sqrt(axis**3/parameters.total)
    times = np.linspace(0., policy['orbits']*period, policy['samples'])
    scales = np.linalg.norm(initial.reshape(3, 3), axis=1)
    if np.any(scales <= 0):
        raise ValueError('Audit requires nonzero initial r/p/S scales')
    directory = ROOT/'.tools/rotation55'; directory.mkdir(parents=True, exist_ok=True)
    jobs = {}; elapsed = {}
    def integrate(name, field, rtol, atol, grid, only_so=False):
        print(name, 'started', flush=True); start = time.perf_counter()
        solution = solve_ivp(field, (0., float(grid[-1])), initial,
            method='DOP853' if name.startswith('production') or only_so else 'RK45',
            rtol=rtol, atol=atol*np.repeat(scales, 3),
            max_step=period*policy['max_step_over_period'] if not only_so else period,
            t_eval=grid)
        if not solution.success or not np.all(np.isfinite(solution.y)) or len(solution.t) != len(grid):
            raise ValueError(f'Failed/invalid job: {name}')
        elapsed[name] = time.perf_counter()-start
        jobs[name] = dict(state=solution.y.T, times=solution.t, nfev=solution.nfev)
        print(name, round(elapsed[name], 2), 'seconds', flush=True)
        return solution.y.T
    primary = integrate('production', lambda t, y: rhs(t, y, parameters),
        policy['production_rtol'], policy['production_atol'], times)
    references = [integrate(f'reference-{i}', lambda t, y: independent_rhs(t, y,
        parameters.mass1, parameters.mass2, parameters.c), tol,
        tol*policy['reference_atol_over_rtol'], times) for i, tol in enumerate(policy['reference_rtols'])]
    inv = [invariants(state, parameters) for state in primary]
    energy = np.array([v[0] for v in inv]); angular = np.array([v[1] for v in inv]); spin = np.array([v[2] for v in inv])
    difference = normalized_difference(primary, references[-1], scales)
    uncertainty = normalized_difference(references[0], references[1], scales)
    so_times = np.linspace(0., policy['SO_exact_duration_periods']*period, 129)
    so_numeric = integrate('SO-exact-flow', lambda t, y: rhs(t, y, parameters, only_so=True),
        policy['production_rtol'], policy['production_atol'], so_times, only_so=True)
    so_exact = np.array([exact_so(initial, t, parameters) for t in so_times])
    so_difference = normalized_difference(so_numeric, so_exact, scales)
    orbital = np.cross(so_numeric[:, :3], so_numeric[:, 3:6])
    exchanged = orbital-orbital[0]+so_numeric[:, 6:]-initial[6:]
    coefficient = parameters.spin_coefficient/np.linalg.norm(initial[:3])**3
    initial_l = np.cross(initial[:3], initial[3:6]); initial_j = initial_l+initial[6:]
    wrong_spin = np.array([Rotation.from_rotvec(coefficient*t*initial_l).apply(initial[6:]) for t in so_times])
    wrong_j = initial_l+wrong_spin
    rng = np.random.default_rng(55); gradient_errors = []
    for _ in range(16):
        state = np.r_[rng.normal(size=3), rng.normal(size=3)*.05, rng.normal(size=3)*.003]
        g = gradient(state, parameters.mass1, parameters.mass2, parameters.c)
        expected = np.r_[g[3:6], -g[:3], np.cross(g[6:], state[6:])].reshape(3, 3)
        actual = rhs(0., state, parameters).reshape(3, 3)
        gradient_errors.extend(np.linalg.norm(actual-expected, axis=1)/np.linalg.norm(expected, axis=1))
    metrics = dict(energy_relative=float(np.max(abs(energy-energy[0]))/abs(energy[0])),
        angular_momentum_relative=float(np.linalg.norm(angular-angular[0], axis=1).max()/np.linalg.norm(angular[0])),
        spin_norm_relative=float(np.max(abs(spin-spin[0]))/spin[0]),
        reference_difference=difference['maximum'], reference_uncertainty=uncertainty['maximum'],
        SO_exact_difference=so_difference['maximum'],
        SO_exchange_relative=float(np.linalg.norm(exchanged, axis=1).max()/scales[2]),
        negative_control_J_drift_minimum=float(np.linalg.norm(wrong_j-initial_j, axis=1).max()/np.linalg.norm(initial_j)),
        hamiltonian_gradient_relative=float(max(gradient_errors)))
    for path, digest in hashes.items():
        if sha(path) != digest:
            raise ValueError(f'Source changed while executing: {path}')
    failures = [key for key, limit in policy['criteria'].items()
                if (metrics[key] <= limit if key.endswith('_minimum') else metrics[key] >= limit)]
    arrays = directory/'pn-spin-trajectories.npz'
    if arrays.exists():
        raise FileExistsError('Preserve trajectory archive')
    np.savez_compressed(arrays, **{f'{name}-{key}': value for name, job in jobs.items()
                                  for key, value in job.items()}, SO_exact=so_exact, wrong_spin=wrong_spin)
    result = dict(model=policy['model'], policy=policy, code_sha256=hashes,
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        initial_state=initial.tolist(), scaling_r_p_S=scales.tolist(), period=period,
        sample_times=times.tolist(), metrics=metrics, failed_criteria=failures, passed=not failures,
        reference_components=difference, reference_uncertainty_components=uncertainty,
        SO_exact_components=so_difference, job_elapsed_seconds=elapsed,
        orbital_and_spin_exchange_norm=float(np.linalg.norm(orbital[-1]-orbital[0])),
        initial_velocity=rhs(0., initial, parameters)[:3].tolist(),
        initial_newtonian_p_over_mu=(initial[3:6]/parameters.reduced).tolist(),
        trajectory_archive_local_path=str(arrays.relative_to(ROOT)), trajectory_archive_sha256=sha(arrays),
        future_ephemerides_called=False, runtime_model_changed=False)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(metrics, 'failed criteria', failures, flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if audit()['passed'] else 1)
