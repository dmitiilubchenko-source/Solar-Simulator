"""Predeclared fresh SI closed-pair and canonical basis/clock research audit."""
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
from scripts import local_multipole as model
from scripts import local_rotation_transfer as transfer
from scripts.independent_local_multipole import scalar, gradients, matrix_rhs, hat

POLICY = 'scripts/local-rotation-policy.json'


def source_hashes():
    # Broad discovery closes local project dependency coverage, including
    # imports such as spin_initial missed by an earlier manual manifest.
    paths = {p for folder in ('src', 'scripts', 'tests') for p in (ROOT/folder).rglob('*.py')}
    paths.add(ROOT/POLICY)
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


LOADED_SOURCES = source_hashes()


def check_sources():
    if source_hashes() != LOADED_SOURCES:
        raise ValueError('Scientific sources changed since audit module initialization')


def failures(metrics, confirmations, policy):
    if set(metrics) != set(policy['maximum'])|set(policy['minimum']):
        raise ValueError('Every predeclared metric must be reported exactly')
    if set(confirmations) != set(policy['required_true']):
        raise ValueError('Every predeclared confirmation must be reported exactly')
    if any(type(v) not in (int, float) or not np.isfinite(v) or v < 0 for v in metrics.values()):
        raise ValueError('Finite nonnegative real metrics required')
    if any(type(v) is not bool for v in confirmations.values()):
        raise ValueError('Strict boolean confirmations required')
    return ([k for k, v in policy['maximum'].items() if metrics[k] >= v]
            + [k for k, v in policy['minimum'].items() if metrics[k] <= v]
            + [k for k in policy['required_true'] if not confirmations[k]])


def synthetic(policy):
    u = Rotation.from_rotvec(policy['multipole_rotvec']).as_matrix()
    parameters = model.Parameters(policy['figure_mass_kg'], policy['point_mass_kg'], policy['G'],
        policy['inertia_body_kg_m2'], u@np.diag(policy['multipole_eigenvalues_kg_m2'])@u.T,
        policy['minimum_distance_m'])
    radius = policy['radius_m']; speed = np.sqrt(parameters.gravitational_constant*(parameters.figure_mass+parameters.point_mass)/radius)
    motion = speed/radius; period = 2*np.pi/motion
    rotation = Rotation.from_rotvec(policy['initial_attitude_rotvec'])
    spin = rotation.as_matrix()@np.asarray(parameters.inertia_body)@(motion*np.array(policy['initial_body_rate_over_mean_motion']))
    state = np.r_[[radius, 0., 0.], parameters.reduced_mass*speed*np.array(policy['initial_velocity_factors']),
                  spin, np.roll(rotation.as_quat(), 1)]
    model.validate_initial(state, parameters)
    scales = np.array([radius, parameters.reduced_mass*speed, np.linalg.norm(spin)])
    return parameters, state, float(period), scales


def axis_matrix(axis, angle):
    k = hat(axis)
    return np.eye(3)+np.sin(angle)*k+(1-np.cos(angle))*(k@k)


def frame_raw(t, period, policy):
    """Analytic noncommuting basis and nonlinear clock; accepts complex t."""
    u = t/period; p = policy['basis']; clock = policy['clock']
    a = np.asarray(p['axis_a']); a = a/np.linalg.norm(a)
    b = np.asarray(p['axis_b']); b = b/np.linalg.norm(b)
    def angle(suffix):
        linear, amplitude, frequency = (p[k+'_'+suffix] for k in ('linear', 'amplitude', 'frequency'))
        return (linear*u+amplitude*np.sin(frequency*u),
                (linear+amplitude*frequency*np.cos(frequency*u))/period,
                -amplitude*frequency**2*np.sin(frequency*u)/period**2)
    aa, ad, add = angle('a'); ba, bd, bdd = angle('b')
    ra = axis_matrix(a, aa); rb = axis_matrix(b, ba); basis = ra@rb
    omega = ad*a+bd*(ra@b)
    alpha = add*a+bdd*(ra@b)+bd*ad*np.cross(a, ra@b)
    amplitude, frequency = clock['amplitude_over_period'], clock['frequency_over_period']
    local_time = t+period*amplitude*np.sin(frequency*u)
    rate = 1+amplitude*frequency*np.cos(frequency*u)
    acceleration = -amplitude*frequency**2*np.sin(frequency*u)/period
    return basis, omega, alpha, local_time, rate, acceleration, a, aa, b, ba


def frame(t, period, policy):
    b, w, alpha, local_time, rate, acceleration, a, aa, c, ca = frame_raw(t, period, policy)
    boundary = transfer.Boundary(b, hat(w)@b, float(rate), float(acceleration), alpha)
    qb_a = np.r_[np.cos(aa/2), a*np.sin(aa/2)]; qb_b = np.r_[np.cos(ca/2), c*np.sin(ca/2)]
    return boundary, transfer.quaternion_product(qb_a, qb_b), float(local_time)


def state_difference(a, b, scales, prefix):
    # Both inputs [r,p,spatial S,raw R], independent of quaternion lift.
    metrics = {}
    for index, name in enumerate(('r', 'p', 'S')):
        metrics[prefix+'_'+name+'_scaled'] = float(np.max(np.linalg.norm(a[:, index*3:index*3+3]-b[:, index*3:index*3+3], axis=1))/scales[index])
    metrics[prefix+'_R_absolute'] = float(np.max(np.linalg.norm(a[:, 9:]-b[:, 9:], axis=1)))
    return metrics


def matrix_states(states):
    matrices = np.array([Rotation.from_quat(np.roll(y[9:13], -1)).as_matrix() for y in states])
    return np.c_[states[:, :9], matrices.reshape(len(states), 9)]


def reference_states(states):
    result = states.copy(); r = states[:, 9:].reshape(-1, 3, 3)
    result[:, 6:9] = np.einsum('nij,nj->ni', r, states[:, 6:9])
    return result


def instantaneous(policy):
    parameters, initial, period, scales = synthetic(policy)
    metrics = {k: 0. for k in ('independent_H_relative', 'independent_flow_scaled', 'independent_K_flow_scaled',
        'energy_derivative_scaled', 'reaction_scaled', 'inverse_rates_scaled', 'basis_clock_derivatives_scaled')}
    rng = np.random.default_rng(policy['seed']); step = 1e-25
    for index in range(policy['random_states']):
        y = initial.copy(); y[:9] += rng.normal(size=9)*np.repeat(.03*scales, 3)
        q = np.roll(Rotation.from_rotvec(rng.normal(size=3)).as_quat(), 1); y[9:] = q
        matrix = Rotation.from_quat(np.roll(q, -1)).as_matrix()
        gradient, angles = gradients(y[:9], matrix, parameters); gx, gp, gs = gradient.reshape(3, 3)
        flow = model.rhs(0., y, parameters); expected = np.r_[gp, -gx, np.cross(gs, y[6:9])-angles]
        for j in range(3):
            value = np.linalg.norm(flow[3*j:3*j+3]-expected[3*j:3*j+3])/(scales[j]/period)
            metrics['independent_flow_scaled'] = max(metrics['independent_flow_scaled'], float(value))
        h = model.hamiltonian(y, parameters); hs = scalar(y[:9], matrix, parameters)
        metrics['independent_H_relative'] = max(metrics['independent_H_relative'], float(abs(h-hs)/abs(hs)))
        energy_rate = gradient@flow[:9]+angles@gs
        metrics['energy_derivative_scaled'] = max(metrics['energy_derivative_scaled'], float(abs(energy_rate)/(abs(h)/period)))
        reaction = np.cross(y[:3], flow[3:6])+flow[6:9]
        reaction_scale = np.linalg.norm(flow[6:9])
        metrics['reaction_scaled'] = max(metrics['reaction_scaled'], float(np.linalg.norm(reaction)/reaction_scale))
        t = float(index*policy['periods']*period/max(1, policy['random_states']-1))
        boundary, qb, _ = frame(t, period, policy); target = transfer.map_state(y, parameters, boundary, qb)
        rb = Rotation.from_quat(np.roll(target[9:], -1)).as_matrix()
        def k(z, r):
            return boundary.clock_rate*scalar(z, r, parameters)+boundary.omega@(np.cross(z[:3], z[3:6])+z[6:9])
        kg = np.array([k(target[:9]+1j*step*axis, rb).imag/step for axis in np.eye(9)])
        ka = np.array([k(target[:9], (np.eye(3)+1j*step*hat(axis))@rb).imag/step for axis in np.eye(3)])
        kx, kp, ks = kg.reshape(3, 3)
        predicted = np.r_[kp, -kx, np.cross(ks, target[6:9])-ka]
        actual = transfer.rhs(t, target, parameters, boundary)
        for j in range(3):
            value = np.linalg.norm(actual[3*j:3*j+3]-predicted[3*j:3*j+3])/(scales[j]/period)
            metrics['independent_K_flow_scaled'] = max(metrics['independent_K_flow_scaled'], float(value))
        w = boundary.clock_rate*model.fields(target, parameters)[4]+boundary.omega
        back = transfer.from_target_rates(target[:3], actual[:3], target[9:], w, parameters, boundary)
        for j in range(3):
            metrics['inverse_rates_scaled'] = max(metrics['inverse_rates_scaled'], float(np.linalg.norm(back[j*3:j*3+3]-target[j*3:j*3+3])/scales[j]))
        raw = frame_raw(t+1j*step, period, policy)
        quantities = [(raw[0].imag/step, np.asarray(boundary.basis_derivative), 1/period),
                      (raw[1].imag/step, np.asarray(boundary.basis_acceleration), 1/period**2),
                      (raw[3].imag/step, boundary.clock_rate, 1.),
                      (raw[4].imag/step, boundary.clock_acceleration, 1/period)]
        for observed, expected, scale in quantities:
            metrics['basis_clock_derivatives_scaled'] = max(metrics['basis_clock_derivatives_scaled'], float(np.linalg.norm(observed-expected)/scale))
    return metrics


def audit(*, work=None, output=None):
    check_sources(); policy = json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    if policy['physical_lunar_mapping_certified'] is not False or policy['physical_accuracy_certified'] is not False:
        raise ValueError('Synthetic model cannot certify physical lunar mapping/accuracy')
    work = Path(work or ROOT/'.tools/rotation74').resolve()
    output = Path(output or ROOT/'docs/local-rotation-validation.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError('Project-local audit outputs required')
    if work.exists() or output.exists():
        raise FileExistsError('Fresh audit directory/report required')
    work.mkdir(parents=True); start = time.perf_counter()
    parameters, initial, period, scales = synthetic(policy)
    t = np.linspace(0., policy['periods']*period, policy['samples'])
    boundaries = [frame(float(v), period, policy) for v in t]
    local_grid = np.array([item[2] for item in boundaries])
    if np.any(np.diff(local_grid) <= 0):
        raise ValueError('Nonmonotonic local clock grid')
    metrics = instantaneous(policy); sources = dict(LOADED_SOURCES)
    h0, j0 = model.invariants(initial, parameters); scale_h = abs(h0)
    arrays = {}; jobs = []
    component_scales = np.r_[np.repeat(scales, 3), np.ones(4)]
    def run(name, fun, y0, grid, method, rtol, absolute_scales):
        check_sources(); seconds = time.perf_counter()
        result = solve_ivp(fun, (float(grid[0]), float(grid[-1])), y0, t_eval=grid,
                           method=method, rtol=rtol, atol=rtol*policy['atol_fraction']*absolute_scales,
                           max_step=period*policy['max_step_over_period'])
        if not result.success or not np.array_equal(result.t, grid) or not np.all(np.isfinite(result.y)):
            raise ValueError(name+': failed/incomplete integration')
        check_sources(); state = result.y.T
        path = work/(name+'.npz'); np.savez(path, times=grid, states=state, initial=y0)
        arrays[name] = dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), shape=list(state.shape))
        jobs.append(dict(name=name, seconds=time.perf_counter()-seconds, method=method, rtol=rtol, nfev=result.nfev))
        print(name+': completed', flush=True)
        return state
    try:
        local = run('local', lambda tt, z: model.rhs(tt, z, parameters), initial, local_grid,
                    'DOP853', policy['production_rtol'], component_scales)
        boundary0, qb0, _ = boundaries[0]; target_initial = transfer.map_state(initial, parameters, boundary0, qb0)
        def target_rhs(tt, z, mode='correct'):
            boundary, _, _ = frame(tt, period, policy)
            flow = transfer.rhs(tt, z[:13], parameters, boundary)
            wb = boundary.omega
            if mode == 'wrong-sign':
                for j in range(3): flow[3*j:3*j+3] -= 2*np.cross(wb, z[3*j:3*j+3])
                w = boundary.clock_rate*model.fields(z[:13], parameters)[4]-wb
                from solar_simulator.rotation import quaternion_rate
                flow[9:] = quaternion_rate(z[9:13], w)
            elif mode == 'missing-orbital':
                flow[:3] -= np.cross(wb, z[:3]); flow[3:6] -= np.cross(wb, z[3:6])
            elif mode == 'double-spin':
                flow[6:9] += np.cross(wb, z[6:9])
                w = boundary.clock_rate*model.fields(z[:13], parameters)[4]+2*wb
                from solar_simulator.rotation import quaternion_rate
                flow[9:] = quaternion_rate(z[9:13], w)
            else:
                if mode != 'correct': raise ValueError('Unknown negative-control mode')
            return np.r_[flow, transfer.explicit_power(z[:13], parameters, boundary)]
        target0 = np.r_[target_initial, 0.]; target_scales = np.r_[component_scales, scale_h]
        target = run('target', target_rhs, target0, t, 'DOP853', policy['production_rtol'], target_scales)
        tighter = run('target-tighter', target_rhs, target0, t, 'DOP853', policy['tighter_rtol'], target_scales)
        r0 = Rotation.from_quat(np.roll(initial[9:], -1)).as_matrix()
        independent0 = np.r_[initial[:6], r0.T@initial[6:9], r0.ravel()]
        references = [run('reference-'+str(index), lambda tt, z: matrix_rhs(tt, z, parameters),
                         independent0, local_grid, 'RK45', tolerance, np.r_[np.repeat(scales, 3), np.ones(9)])
                      for index, tolerance in enumerate(policy['reference_rtols'])]
        refs = [reference_states(s) for s in references]; target_matrix = matrix_states(target)
        mapped = np.array([transfer.map_state(y, parameters, b, qb) for y, (b, qb, _) in zip(local, boundaries)])
        pulled = np.array([transfer.map_state(y[:13], parameters, b, qb, inverse=True) for y, (b, qb, _) in zip(target, boundaries)])
        metrics.update(state_difference(matrix_states(local), refs[1], scales, 'agreement'))
        metrics.update(state_difference(refs[0], refs[1], scales, 'reference_sensitivity'))
        metrics.update(state_difference(target_matrix, matrix_states(tighter), scales, 'tighter_difference'))
        mapping_metrics = state_difference(target_matrix, matrix_states(mapped), scales, 'map_trajectory')
        pulled_agreement = state_difference(matrix_states(pulled), refs[1], scales, 'agreement')
        metrics.update(mapping_metrics)
        for key, value in pulled_agreement.items(): metrics[key] = max(metrics[key], value)
        local_hj = [model.invariants(y, parameters) for y in local]
        target_hj = [transfer.local_invariants(y[:13], parameters, b) for y, (b, _, _) in zip(target, boundaries)]
        for prefix, values in [('local', local_hj), ('target', target_hj)]:
            metrics[prefix+'_H_drift'] = float(max(abs(h-h0) for h, _ in values)/scale_h)
            jkey = 'local_J_drift' if prefix == 'local' else 'target_pulled_J_drift'
            metrics[jkey] = float(max(np.linalg.norm(j-j0) for _, j in values)/np.linalg.norm(j0))
        ks = np.array([transfer.hamiltonian(y[:13], parameters, b) for y, (b, _, _) in zip(target, boundaries)])
        metrics['target_work_ledger'] = float(np.max(np.abs(ks-ks[0]-target[:, 13]))/scale_h)
        metrics['time_dependent_K_change'] = float(np.max(np.abs(ks-ks[0]))/scale_h)
        metrics['quaternion_norm_error'] = float(max(np.max(abs(np.linalg.norm(s[:, 9:13], axis=1)-1)) for s in (local, target, tighter)))
        metrics['reference_orthogonality_error'] = 0.; metrics['reference_determinant_error'] = 0.
        for reference in references:
            rr = reference[:, 9:].reshape(-1, 3, 3)
            metrics['reference_orthogonality_error'] = max(metrics['reference_orthogonality_error'], float(np.max(np.linalg.norm(rr.transpose(0, 2, 1)@rr-np.eye(3), axis=(1, 2)))))
            metrics['reference_determinant_error'] = max(metrics['reference_determinant_error'], float(np.max(abs(np.linalg.det(rr)-1))))
        for mode, key in [('wrong-sign', 'wrong_sign_trajectory'), ('missing-orbital', 'missing_orbital_connection_trajectory'), ('double-spin', 'double_spin_connection_trajectory')]:
            wrong = run(mode, lambda tt, z, mode=mode: target_rhs(tt, z, mode), target0, t,
                        'DOP853', policy['production_rtol'], target_scales)
            differences = state_difference(matrix_states(wrong), target_matrix, scales, 'wrong')
            metrics[key] = max(differences.values())
        fields0 = model.fields(target_initial, parameters)
        w0 = boundary0.clock_rate*fields0[4]+boundary0.omega
        metrics['naive_initial_spin_scaled'] = float(np.linalg.norm(fields0[2]@w0-target_initial[6:9])/scales[2])
        confirmations = dict(source_hashes_preserved=source_hashes()==sources,
            arrays_reverified=all(hashlib.sha256((ROOT/a['path']).read_bytes()).hexdigest()==a['sha256'] for a in arrays.values()),
            raw_initial_preserved=all(np.array_equal(np.load(ROOT/arrays[name]['path'])['initial'].view(np.uint64), raw.view(np.uint64))
                                      for name, raw in [('local', initial), ('target', target0), ('reference-0', independent0), ('reference-1', independent0)]),
            clock_monotonic=bool(np.all(np.diff(local_grid)>0) and all(b.clock_rate>0 for b, _, _ in boundaries)),
            physical_claims_false=bool(policy['physical_lunar_mapping_certified'] is False and policy['physical_accuracy_certified'] is False))
        failed = failures(metrics, confirmations, policy)
        report = dict(changes=policy['changes'], model=policy['model'], policy=policy, sources=sources,
            parameters=dict(figure_mass_kg=parameters.figure_mass, point_mass_kg=parameters.point_mass,
                G=parameters.gravitational_constant, inertia_body_kg_m2=parameters.inertia_body,
                multipole_body_kg_m2=parameters.multipole_body, minimum_distance_m=parameters.minimum_distance),
            initial=initial.tolist(), scales=scales.tolist(), nominal_period_s=period,
            target_duration_s=float(t[-1]), local_duration_s=float(local_grid[-1]), samples=len(t),
            arrays=arrays, jobs=jobs, metrics=metrics, confirmations=confirmations, failed=failed, passed=not failed,
            seconds=time.perf_counter()-start, environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
            physical_lunar_mapping_certified=False, physical_accuracy_certified=False,
            future_ephemerides_read=False, old_lunar_trajectories_reused=False, runtime_changed=False,
            limitations=policy['scope']+' Fixed epoch grid; independent reference sensitivity is not a rigorous error bound; no checkpoint persistence contract.')
        text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
        with (work/'report.json').open('x', encoding='utf-8') as f: f.write(text)
        with output.open('x', encoding='utf-8') as f: f.write(text)
        if failed: raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        failure_path = work/'failure.json'
        if not failure_path.exists():
            failure_path.write_text(json.dumps(dict(passed=False, error=repr(error), sources=sources, arrays=arrays, jobs=jobs), indent=2)+'\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    result = audit()
    print(json.dumps(dict(passed=result['passed'], metrics=result['metrics']), indent=2))
