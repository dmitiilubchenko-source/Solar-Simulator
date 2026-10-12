"""Fresh, source-frozen, predeclared test-gyro clock/metric/SSC audit."""
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import schwarzschild_metric as exact
from scripts import independent_schwarzschild_spin as reference
from scripts.external_metric import Sources, weak_metric, leading_clock
from scripts.metric_spin_transport import Metric, transport

POLICY = 'scripts/metric-spin-policy.json'


def source_hashes():
    paths = {p for folder in ('src', 'scripts', 'tests') for p in (ROOT/folder).rglob('*.py')}
    paths.add(ROOT/POLICY)
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


LOADED_SOURCES = source_hashes()


def check_sources():
    if source_hashes() != LOADED_SOURCES:
        raise ValueError('Scientific sources changed since module initialization')


def failures(metrics, confirmations, policy):
    if set(metrics) != set(policy['maximum'])|set(policy['minimum']):
        raise ValueError('All predeclared metrics must be reported exactly')
    if set(confirmations) != set(policy['required_true']):
        raise ValueError('All predeclared confirmations must be reported exactly')
    if any(type(v) not in (float, int) or not np.isfinite(v) or v < 0 for v in metrics.values()):
        raise ValueError('Finite nonnegative real metrics required')
    if any(type(v) is not bool for v in confirmations.values()):
        raise ValueError('Strict boolean confirmations required')
    return ([k for k, bound in policy['maximum'].items() if metrics[k] >= bound]
            +[k for k, bound in policy['minimum'].items() if metrics[k] <= bound]
            +[k for k in policy['required_true'] if not confirmations[k]])


def normmax(values):
    return float(np.max(np.linalg.norm(values, axis=(-2, -1))))


def integrate_raw_initial(function, initial, grid, method, tolerance, policy):
    """Start IVP at epoch0; request interpolation only strictly after epoch0.

    Epoch0 is the supplied raw state, not a dense-output arithmetic result
    that can replace negative zero by positive zero. No later state edits.
    """
    sol = solve_ivp(function, (grid[0], grid[-1]), initial, t_eval=grid[1:],
        method=method, rtol=tolerance, atol=tolerance*policy['atol_over_rtol'],
        max_step=policy['max_phase_step'])
    if not sol.success or not np.array_equal(sol.t, grid[1:]) or not np.all(np.isfinite(sol.y)):
        raise ValueError(f'Incomplete/nonfinite integration: {sol.message}')
    return np.vstack([initial.copy(), sol.y.T]), sol.nfev


def instantaneous(policy):
    gm = policy['gm_m3_s2']; rho = policy['isotropic_radius_m']
    metrics = {k: 0. for k in ('metric_derivative_scaled', 'circle_acceleration_relative',
        'proper_clock_analytic_absolute', 'raw_symmetry_defect', 'fourth_order_ratio_deviation',
        'weak_circle_acceleration_relative', 'omitted_root_rate_symmetry_defect')}
    remainders = dict(clock=[], root=[], geodetic=[])
    from scripts.canonical_initial import local_spin_root
    for c in policy['light_speeds_m_s']:
        x, v, a, frequency, radius = exact.circular_orbit(.37, rho, gm, c)
        supplied = exact.metric(x, gm, c); out = transport(supplied, v, c)
        metrics['circle_acceleration_relative'] = max(metrics['circle_acceleration_relative'], float(np.linalg.norm(out.acceleration-a)/np.linalg.norm(a)))
        expected_rate = np.sqrt(1-3*gm/(c**2*radius))
        metrics['proper_clock_analytic_absolute'] = max(metrics['proper_clock_analytic_absolute'], float(abs(out.proper_rate-expected_rate)))
        metrics['raw_symmetry_defect'] = max(metrics['raw_symmetry_defect'], out.symmetry_defect)
        # Independent scalar expression differentiated by complex step.
        def raw_metric(z):
            u = gm/(2*c**2*np.sqrt(z@z))
            return np.diag([-((1-u)/(1+u))**2, *([(1+u)**4]*3)])
        expected_dg = np.zeros((4, 4, 4))
        for index, axis in enumerate(np.eye(3)):
            expected_dg[index+1] = raw_metric(x+1j*1e-20*axis).imag/1e-20
        dg = np.asarray(supplied.derivative)
        metrics['metric_derivative_scaled'] = max(metrics['metric_derivative_scaled'], float(np.linalg.norm(dg-expected_dg)/np.linalg.norm(expected_dg)))
        sources = Sources([gm], [[0., 0., 0.]], [[0., 0., 0.]], [[0., 0., 0.]], c)
        clock, _ = leading_clock(x, v, a, sources)
        inverse = np.linalg.inv(supplied.covariant)
        h, _ = local_spin_root(inverse, v/c)
        series = (1-gm/(c**2*rho))*np.eye(3)-.5*np.outer(v/c, v/c)
        remainders['clock'].append(abs(clock-expected_rate))
        remainders['root'].append(float(np.linalg.norm(h-series)))
        leading_omega = 1.5*gm/(c**2*rho**3)*np.cross(x, v)
        remainders['geodetic'].append(float(np.linalg.norm(out.omega-leading_omega)/frequency))
        weak_frequency = np.sqrt(gm/(rho**3*(1+gm/(c**2*rho))))
        weak_v = weak_frequency*np.array([-x[1], x[0], 0.])
        weak_out = transport(Metric(*weak_metric(x, sources)), weak_v, c)
        weak_a = -weak_frequency**2*x
        metrics['weak_circle_acceleration_relative'] = max(metrics['weak_circle_acceleration_relative'], float(np.linalg.norm(weak_out.acceleration-weak_a)/np.linalg.norm(weak_a)))
        wrong = out.root@out.covariant_generator@np.linalg.inv(out.root)
        metrics['omitted_root_rate_symmetry_defect'] = max(metrics['omitted_root_rate_symmetry_defect'], float(np.linalg.norm(wrong+wrong.T)/np.linalg.norm(wrong)))
    ratios = {k: [v[i]/v[i+1] for i in range(len(v)-1)] for k, v in remainders.items()}
    metrics['fourth_order_ratio_deviation'] = float(max(abs(r-16) for values in ratios.values() for r in values))
    return metrics, dict(remainders=remainders, doubling_c_ratios=ratios)


def audit(*, work=None, output=None):
    work = Path(work or ROOT/'.tools/rotation78').resolve()
    output = Path(output or ROOT/'docs/metric-spin-validation-r3.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        raise ValueError('Audit outputs must be inside the project')
    if work.exists() or output.exists():
        raise FileExistsError('Fresh work and output paths required')
    check_sources(); sources = source_hashes()
    policy = json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    work.mkdir(parents=True); output.parent.mkdir(parents=True, exist_ok=True)
    for name in sources:
        saved = work/'executed-sources'/name
        saved.parent.mkdir(parents=True, exist_ok=True); saved.write_bytes((ROOT/name).read_bytes())
    arrays = {}; jobs = {}; start = time.perf_counter()
    try:
        metrics, order = instantaneous(policy)
        gm = policy['gm_m3_s2']; rho = policy['isotropic_radius_m']; c = policy['light_speeds_m_s'][0]
        grid = np.linspace(0., policy['orbits']*2*np.pi, policy['samples'])
        _, _, _, frequency, radius = exact.circular_orbit(0., rho, gm, c)
        expected_initial = {}
        def run(name, function, initial, method, tolerance):
            check_sources(); tick = time.perf_counter()
            states, nfev = integrate_raw_initial(function, initial, grid, method, tolerance, policy)
            check_sources()
            path = work/(name+'.npz')
            np.savez(path, phase=grid, coordinate_time_s=grid/frequency,
                     initial=initial, states=states)
            arrays[name] = dict(path=path.relative_to(ROOT).as_posix(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(), shape=list(states.shape))
            jobs[name] = dict(method=method, rtol=tolerance, atol=tolerance*policy['atol_over_rtol'],
                nfev=nfev, seconds=time.perf_counter()-tick)
            expected_initial[name] = initial.copy()
            print(f'{name}: {nfev} evaluations, {jobs[name]["seconds"]:.2f}s', flush=True)
            return states
        def production(phase, state, mode='correct'):
            x, v, *_ = exact.circular_orbit(float(phase), rho, gm, c)
            out = transport(exact.metric(x, gm, c), v, c)
            vmat = out.generator
            if mode == 'wrong-sign': vmat = -vmat
            elif mode == 'double-generator': vmat = 2*vmat
            elif mode == 'omitted-root-rate':
                vmat = out.root@out.covariant_generator@np.linalg.inv(out.root)
            elif mode != 'correct': raise ValueError('Unknown control mode')
            return np.r_[(vmat@state[:9].reshape(3, 3)).ravel()/frequency, out.proper_rate]
        initial = np.r_[np.eye(3).ravel(), 0.]
        correct = run('production', production, initial, 'DOP853', policy['production_rtol'])
        tighter = run('production-tighter', production, initial, 'DOP853', policy['tighter_rtol'])
        ref_initial = reference.initial_covectors(gm, rho, c).ravel()
        ref_matrix = reference.spherical_generator(gm, rho, c)
        refs = [run('reference-'+str(i), lambda phase, z: (ref_matrix@z.reshape(4, 3)).ravel(),
                    ref_initial, 'RK45', tolerance) for i, tolerance in enumerate(policy['reference_rtols'])]
        converted = [np.array([reference.euclidean_basis(t, z.reshape(4, 3), gm, rho, c)
                              for t, z in zip(grid, states)]) for states in refs]
        q = correct[:, :9].reshape(-1, 3, 3); qt = tighter[:, :9].reshape(-1, 3, 3)
        metrics['trajectory_agreement_absolute'] = normmax(q-converted[1])
        metrics['reference_sensitivity_absolute'] = normmax(converted[0]-converted[1])
        metrics['tighter_difference_absolute'] = normmax(q-qt)
        epsilon = gm/(c**2*radius)
        # Rationalized expression prevents loss in 1-sqrt(1-3epsilon).
        psi = 3*epsilon/(1+np.sqrt(1-3*epsilon))
        endpoints = []
        for orbit in range(policy['orbits']+1):
            angle = 2*np.pi*orbit*psi
            predicted = np.array([[np.cos(angle), -np.sin(angle), 0.],
                                  [np.sin(angle), np.cos(angle), 0.], [0., 0., 1.]])
            index = orbit*(policy['samples']-1)//policy['orbits']
            endpoints.append(np.linalg.norm(q[index]-predicted))
        metrics['endpoint_holonomy_absolute'] = float(max(endpoints))
        metrics['proper_clock_integral_scaled'] = float(np.max(abs(correct[:, 9]-np.sqrt(1-3*epsilon)*grid))/grid[-1])
        metrics['euclidean_gram_error'] = normmax(q.transpose(0, 2, 1)@q-np.eye(3))
        metrics['reference_gram_error'] = 0.; metrics['reference_ssc_error'] = 0.
        for states in refs:
            for z in states:
                gram, ssc = reference.invariants(z.reshape(4, 3), gm, rho, c)
                metrics['reference_gram_error'] = max(metrics['reference_gram_error'], float(np.linalg.norm(gram-np.eye(3))))
                metrics['reference_ssc_error'] = max(metrics['reference_ssc_error'], float(np.linalg.norm(ssc)))
        all_q = [q, qt, *converted]
        metrics['orthogonality_error'] = max(normmax(qq.transpose(0, 2, 1)@qq-np.eye(3)) for qq in all_q)
        metrics['determinant_error'] = float(max(np.max(abs(np.linalg.det(qq)-1)) for qq in all_q))
        for mode, key in [('wrong-sign', 'wrong_sign_trajectory'),
                          ('double-generator', 'double_generator_trajectory'),
                          ('omitted-root-rate', 'omitted_root_rate_trajectory')]:
            wrong = run(mode, lambda t, z, mode=mode: production(t, z, mode),
                        initial, 'DOP853', policy['production_rtol'])
            metrics[key] = normmax(wrong[:, :9].reshape(-1, 3, 3)-q)
        reverified = True; raw_preserved = True; grid_preserved = True
        for name, entry in arrays.items():
            path = ROOT/entry['path']
            reverified &= hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
            with np.load(path, allow_pickle=False) as saved:
                reverified &= (list(saved['states'].shape) == entry['shape'] and np.all(np.isfinite(saved['states'])))
                raw_preserved &= np.array_equal(saved['initial'].view(np.uint64), expected_initial[name].view(np.uint64))
                raw_preserved &= np.array_equal(saved['states'][0].view(np.uint64), expected_initial[name].view(np.uint64))
                grid_preserved &= np.array_equal(saved['phase'].view(np.uint64), grid.view(np.uint64))
                grid_preserved &= np.array_equal(saved['coordinate_time_s'].view(np.uint64), (grid/frequency).view(np.uint64))
        copies_preserved = all(hashlib.sha256((work/'executed-sources'/name).read_bytes()).hexdigest()==sha
                               for name, sha in sources.items())
        confirmations = dict(sources_preserved=source_hashes()==sources and copies_preserved,
            arrays_reverified=bool(reverified), raw_initial_preserved=bool(raw_preserved),
            grid_preserved=bool(grid_preserved), physical_claims_false=bool(
                policy['physical_lunar_mapping_certified'] is False and policy['physical_accuracy_certified'] is False))
        failed = failures(metrics, confirmations, policy)
        report = dict(changes=policy['changes'], policy=policy, sources=sources,
            arrays=arrays, jobs=jobs, metrics=metrics, confirmations=confirmations,
            order=order, coordinate_duration_s=float(grid[-1]/frequency),
            areal_radius_m=radius, circular_frequency_per_s=frequency,
            spin_holonomy_per_orbit_rad=float(2*np.pi*psi), passed=not failed, failed=failed,
            seconds=time.perf_counter()-start, environment=dict(python=platform.python_version(),
                numpy=np.__version__, scipy=scipy.__version__),
            physical_lunar_mapping_certified=False, physical_accuracy_certified=False,
            runtime_changed=False, old_trajectories_reused=False,
            limitations='Linear test spin, no spin-force feedback/extended-body inertia. Exact Schwarzschild benchmark only. Leading external clock has no epoch/offset/TDB conversion. Weak metric is incomplete beyond displayed orders. Fixed output grid and numerical reference sensitivity are not rigorous physical-error bounds.')
        text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
        with (work/'report.json').open('x', encoding='utf-8') as f: f.write(text)
        with output.open('x', encoding='utf-8') as f: f.write(text)
        if failed: raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        failure = work/'failure.json'
        if not failure.exists():
            failure.write_text(json.dumps(dict(passed=False, error=repr(error), sources=sources,
                arrays=arrays, jobs=jobs, metrics=locals().get('metrics', {}),
                confirmations=locals().get('confirmations', {})), indent=2, allow_nan=False)+'\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    result = audit()
    print(json.dumps(dict(passed=result['passed'], metrics=result['metrics'], order=result['order']), indent=2))
