"""Predeclared finite mixed-H audit: quaternion/spatial vs matrix/body Euler."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.rigid_pn_model import Parameters, fields, rhs, invariants, validate_initial
from scripts.independent_rigid_pn import gradients, matrix_rhs
from scripts.assess_nbody_pn_spin import initial_state, difference as orbital_difference
from solar_simulator.rotation import RigidFigure, quaternion_rate


def attitudes(states):
    return Rotation.from_quat(states[:, -4:][:, [1, 2, 3, 0]]).as_matrix()


def convert_reference(states, count, index):
    orbit = states[:, :9*count].copy(); matrices = states[:, 9*count:].reshape(-1, 3, 3)
    spin = orbit.reshape(-1, 3, count, 3)[:, 2, index]
    spin[:] = np.einsum('tij,tj->ti', matrices, spin)
    return orbit, matrices


def compare(first_orbit, first_matrices, second_orbit, second_matrices, scales):
    if (first_matrices.shape != second_matrices.shape
            or first_matrices.shape != (len(first_orbit), 3, 3)
            or not np.all(np.isfinite(first_matrices)) or not np.all(np.isfinite(second_matrices))):
        raise ValueError('Invalid attitude grids')
    result = orbital_difference(first_orbit, second_orbit, scales)
    result['attitude_matrix'] = float(np.linalg.norm(first_matrices-second_matrices, axis=(1, 2)).max())
    result['maximum'] = max(result['maximum'], result['attitude_matrix'])
    return result


def audit():
    output = ROOT/'docs/rigid-pn-validation.json'
    if output.exists(): raise FileExistsError('Preserve original rigid/PN audit')
    policy = json.loads((ROOT/'scripts/rigid-pn-policy.json').read_text(encoding='utf-8'))
    paths = ['scripts/rigid-pn-policy.json', 'scripts/rigid_pn_model.py', 'scripts/independent_rigid_pn.py',
             'scripts/assess_rigid_pn.py', 'tests/test_rigid_pn_model.py', 'scripts/nbody_pn_spin.py',
             'scripts/independent_nbody_pn_spin.py', 'scripts/assess_nbody_pn_spin.py',
             'src/solar_simulator/rotation.py', 'src/solar_simulator/nbody_rotation.py',
             'src/solar_simulator/relativity.py']
    sha = lambda path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    hashes = {path: sha(path) for path in paths}
    count = len(policy['masses']); index = policy['figure_index']
    params = Parameters(PointParameters(tuple(policy['masses']), policy['c']),
        RigidFigure(policy['masses'][index], tuple(policy['moments']), policy['bounding_radius']), index)
    q = np.roll(Rotation.from_rotvec(policy['initial_attitude_rotvec']).as_quat(), 1)
    initial = np.r_[initial_state(policy), q]
    validate_initial(initial, params)
    scales = np.linalg.norm(initial[:-4].reshape(3, count, 3), axis=-1)
    if np.any(scales <= 0): raise ValueError('Audit requires nonzero initial per-body scales')
    start_matrix = Rotation.from_quat(np.roll(q, -1)).as_matrix()
    matrix_start = np.r_[initial[:-4], start_matrix.ravel()]
    matrix_start[6*count+3*index:6*count+3*index+3] = start_matrix.T@initial[:-4].reshape(3, count, 3)[2, index]
    times = np.linspace(0., policy['periods']*policy['nominal_period'], policy['samples'])
    jobs = {}; elapsed = {}
    def integrate(name, field, method, start_state, grid, tol, atol_ratio, matrix=False):
        print(name, 'started', flush=True); clock = time.perf_counter()
        component_scales = np.r_[np.repeat(scales.ravel(), 3), np.ones(9 if matrix else 4)]
        sol = solve_ivp(field, (float(grid[0]), float(grid[-1])), start_state, t_eval=grid,
                       method=method, rtol=tol, atol=tol*atol_ratio*component_scales,
                       max_step=policy['max_step_over_period']*policy['nominal_period'])
        if (not sol.success or sol.y.shape != (len(start_state), len(grid))
                or not np.array_equal(sol.t, grid) or not np.all(np.isfinite(sol.y))):
            raise ValueError(f'Failed/invalid mixed-H integration: {name}')
        elapsed[name] = time.perf_counter()-clock
        jobs[name] = dict(state=sol.y.T, times=sol.t, nfev=sol.nfev)
        print(name, round(elapsed[name], 2), 'seconds', flush=True)
        return sol.y.T
    prod_field = lambda t, y: rhs(t, y, params)
    primary = integrate('production', prod_field, 'DOP853', initial, times,
                        policy['production_rtol'], policy['production_atol_over_rtol'])
    ref_field = lambda t, y: matrix_rhs(t, y, params.orbital.masses, params.orbital.c,
                                       params.figure.moments, index)
    raw_refs = [integrate(f'reference-{i}', ref_field, 'RK45', matrix_start, times, tol,
                         policy['reference_atol_over_rtol'], matrix=True)
                for i, tol in enumerate(policy['reference_rtols'])]
    refs = [convert_reference(y, count, index) for y in raw_refs]
    measured = attitudes(primary)
    delta = compare(primary[:, :-4], measured, *refs[-1], scales)
    uncertainty = compare(*refs[0], *refs[1], scales)
    split = len(times)//2
    prefix = integrate('restart-prefix', prod_field, 'DOP853', initial, times[:split+1],
                       policy['production_rtol'], policy['production_atol_over_rtol'])
    # Keep the raw checkpoint q and fixed frame, without normalizing or reboosting.
    suffix = integrate('restart-suffix', prod_field, 'DOP853', prefix[-1].copy(), times[split:],
                       policy['production_rtol'], policy['production_atol_over_rtol'])
    restarted = np.vstack([prefix[:-1], suffix])
    restart = compare(primary[:, :-4], measured, restarted[:, :-4], attitudes(restarted), scales)
    signs = np.r_[np.ones(3*count), -np.ones(6*count), np.ones(4)]
    reversed_states = integrate('time-reversal', prod_field, 'DOP853', primary[-1]*signs, times,
                               policy['production_rtol'], policy['production_atol_over_rtol'])
    reversal = compare(reversed_states[:, :-4], attitudes(reversed_states),
                       (primary[::-1]*signs)[:, :-4], measured[::-1], scales)
    values = [invariants(y, params) for y in primary]
    h = np.array([v[0] for v in values]); p = np.array([v[1] for v in values]); j = np.array([v[2] for v in values])
    spin_norms = np.linalg.norm(primary[:, :-4].reshape(-1, 3, count, 3)[:, 2], axis=-1)
    point_indices = [i for i in range(count) if i != index]
    h_scale, j_scale, p_scale = abs(h[0]), np.linalg.norm(j[0]), scales[1].sum()
    if min(h_scale, j_scale, p_scale) <= 0: raise ValueError('Degenerate invariant normalization')
    gradient_errors = []; balance_errors = []; rng = np.random.default_rng(policy['gradient_seed'])
    for _ in range(policy['gradient_states']):
        y = initial.copy(); b = y[:-4].reshape(3, count, 3)
        for block, amplitude in enumerate([.05, .005, .0001]):
            b[block] += rng.normal(size=(count, 3))*amplitude
        rotation = Rotation.from_quat(np.roll(y[-4:], -1)).as_matrix()
        g, angle = gradients(y[:-4], rotation, params.orbital.masses, params.orbital.c,
                             params.figure.moments, index)
        g = g.reshape(3, count, 3)
        expected = np.stack([g[1], -g[0], np.cross(g[2], b[2])]); expected[2, index] -= angle
        actual = rhs(0., y, params)[:-4].reshape(3, count, 3)
        norms = np.linalg.norm(expected, axis=-1)
        if np.any(norms == 0): raise ValueError('Degenerate derivative comparison')
        gradient_errors.extend((np.linalg.norm(actual-expected, axis=-1)/norms).ravel())
        power = np.sum(np.linalg.norm(g, axis=-1)*np.linalg.norm(actual, axis=-1))+np.linalg.norm(angle)*np.linalg.norm(g[2, index])
        if power <= 0: raise ValueError('Degenerate balance power')
        balance_errors.append(abs(np.sum(g*actual)+np.dot(angle, g[2, index]))/power)
    g0, angle0 = gradients(initial[:-4], start_matrix, params.orbital.masses, params.orbital.c,
                          params.figure.moments, index)
    g0 = g0.reshape(3, count, 3); f0 = rhs(0., initial, params)[:-4].reshape(3, count, 3)
    _, _, omega, connection, _, qforces, torque = fields(initial, params)
    power_scale = float(np.sum(np.linalg.norm(g0, axis=-1)*np.linalg.norm(f0, axis=-1))
                        +np.linalg.norm(angle0)*np.linalg.norm(omega+connection))
    if power_scale <= 0: raise ValueError('Degenerate initial power')
    wrong_energy_rate = float(np.sum(g0*f0)+np.dot(angle0, omega))
    b0 = initial[:-4].reshape(3, count, 3)
    wrong_j_rate = (np.cross(f0[0], b0[1])+np.cross(b0[0], f0[1]-qforces)+f0[2]).sum(axis=0)
    matrices = np.concatenate([v[1] for v in refs])
    metrics = dict(energy_relative=float(abs(h-h[0]).max()/h_scale),
        momentum_scaled=float(np.linalg.norm(p-p[0], axis=1).max()/p_scale),
        angular_momentum_relative=float(np.linalg.norm(j-j[0], axis=1).max()/j_scale),
        point_spin_norm_relative=float((abs(spin_norms[:, point_indices]-spin_norms[0, point_indices])/spin_norms[0, point_indices]).max()),
        quaternion_norm=float(abs(np.linalg.norm(primary[:, -4:], axis=1)-1).max()),
        reference_difference=delta['maximum'], reference_uncertainty=uncertainty['maximum'],
        reference_rotation_orthogonality=float(np.linalg.norm(np.swapaxes(matrices, 1, 2)@matrices-np.eye(3), axis=(1, 2)).max()),
        reference_rotation_determinant=float(abs(np.linalg.det(matrices)-1).max()),
        restart_difference=restart['maximum'], time_reversal_difference=reversal['maximum'],
        hamiltonian_gradient_relative=float(max(gradient_errors)), energy_balance_scaled=float(max(balance_errors)),
        missing_attitude_SO_energy_rate_minimum=abs(wrong_energy_rate)/power_scale,
        missing_Q2_reaction_J_rate_minimum=float(np.linalg.norm(wrong_j_rate)*policy['nominal_period']/j_scale))
    if not all(np.isfinite(v) for v in metrics.values()): raise ValueError('Nonfinite audit metrics')
    for path, digest in hashes.items():
        if sha(path) != digest: raise ValueError(f'Source changed during integration: {path}')
    failures = [key for key, limit in policy['criteria'].items()
                if (metrics[key] <= limit if key.endswith('_minimum') else metrics[key] >= limit)]
    archive = ROOT/'.tools/rotation57/rigid-pn-trajectories.npz'
    if archive.exists(): raise FileExistsError('Preserve original mixed-H trajectories')
    archive.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(archive, **{f'{name}-{key}': value for name, job in jobs.items() for key, value in job.items()})
    result = dict(policy=policy, code_sha256=hashes, initial_state=initial.tolist(),
        scales_x_p_S_per_body=scales.tolist(), invariant_scales=dict(H=h_scale, J=j_scale, P=p_scale),
        sample_times=times.tolist(), metrics=metrics, passed=not failures, failed_criteria=failures,
        reference_components=delta, reference_uncertainty_components=uncertainty,
        restart_components=restart, time_reversal_components=reversal, job_elapsed_seconds=elapsed,
        nfev={name: job['nfev'] for name, job in jobs.items()},
        initial_intrinsic_omega=omega.tolist(), initial_SO_connection=connection.tolist(),
        negative_control_wrong_energy_rate=wrong_energy_rate, negative_control_power_scale=power_scale,
        negative_control_wrong_J_rate=wrong_j_rate.tolist(),
        figure_spin_norm_relative_variation=float(abs(spin_norms[:, index]-spin_norms[0, index]).max()/spin_norms[0, index]),
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        trajectory_archive_local_path=str(archive.relative_to(ROOT)), trajectory_archive_sha256=sha(archive),
        future_ephemerides_called=False, runtime_model_changed=False, checkpoint_reboosted=False,
        checkpoint_quaternion_normalized=False)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(metrics, 'failed criteria', failures, flush=True)
    return result


if __name__ == '__main__':
    sys.exit(0 if audit()['passed'] else 1)
