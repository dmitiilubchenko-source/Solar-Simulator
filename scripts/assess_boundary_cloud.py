"""Predeclared, fresh source-frozen local-event / SR-cloud boundary audit."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import sr_cloud as sr
from scripts import density_moments as density
from scripts import local_event_map as local
from scripts import independent_sr_reference as independent
from scripts.canonical_initial import local_spin_root
from scripts.assess_metric_spin import integrate_raw_initial, failures

POLICY = 'scripts/boundary-cloud-policy.json'
USED_POLICIES = (POLICY, 'scripts/metric-spin-policy.json')


def source_hashes():
    paths = {p for folder in ('src', 'scripts', 'tests') for p in (ROOT/folder).rglob('*.py')}
    paths.update(ROOT/name for name in USED_POLICIES)
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


LOADED_SOURCES = source_hashes()


def check_sources():
    if source_hashes() != LOADED_SOURCES: raise ValueError('Scientific sources changed since module initialization')


def cloud(policy, c):
    x = np.asarray(policy['positive_positions_m'])
    positions = np.stack([x, -x], axis=1).reshape(-1, 3)
    masses = np.repeat(policy['pair_masses_kg'], 2)
    velocities = np.cross(policy['initial_omega_per_s'], positions)
    return sr.RestCloud(masses, positions, velocities, c)


def flat_jet(t, v, c):
    rate = 1-.5*(v/c)@(v/c)
    return local.Jet(float(t), float(t*rate), v*t, v, np.zeros(3), np.zeros(3),
                     0., 0., np.eye(3), np.zeros((3, 3)), c)


def order_checks(policy):
    v = np.asarray(policy['frame_velocity_m_s']); t = 2.
    offset = np.asarray(policy['positive_positions_m'][0]); x = v*t+offset
    material = v+np.array([100., 50., 100.])
    series = dict(central_clock=[], local_time=[], local_position=[], spatial_jacobian=[], velocity=[], kinetic_spin=[])
    for c in policy['light_speeds_m_s']:
        jet = flat_jet(t, v, c); point = local.event(x, jet)
        exact_time, exact_position = independent.flat_local_event(t, x, v, c)
        exact_velocity = independent.flat_local_velocity(material, v, c)
        gamma = 1/np.sqrt(1-v@v/c**2)
        exact_spatial = np.eye(3)+gamma**2/(gamma+1)*np.outer(v/c, v/c)
        actual_velocity, _ = local.velocity(x, material, jet)
        series['central_clock'].append(abs(jet.centre_clock_rate-1/gamma))
        series['local_time'].append(abs(point.local_time-exact_time))
        series['local_position'].append(float(np.linalg.norm(point.local_position-exact_position)/policy['length_scale_m']))
        series['spatial_jacobian'].append(float(np.linalg.norm(point.position_x-exact_spatial)))
        series['velocity'].append(float(np.linalg.norm(actual_velocity-exact_velocity)/np.linalg.norm(exact_velocity)))
        system = cloud(policy, c)
        exact_spin, _, leading_spin = density.rotation_snapshot_spin(system.masses, system.positions,
                                                   policy['initial_omega_per_s'], c)
        series['kinetic_spin'].append(float(np.linalg.norm(exact_spin-leading_spin)/np.linalg.norm(exact_spin)))
    ratios = {k: [float(values[i]/values[i+1]) for i in range(len(values)-1)] for k, values in series.items()}
    event_deviation = max(abs(r-16) for k, values in ratios.items() if k != 'kinetic_spin' for r in values)
    spin_deviation = max(abs(r-16) for r in ratios['kinetic_spin'])
    return float(event_deviation), float(spin_deviation), dict(remainders=series, doubling_c_ratios=ratios)


def audit(*, work=None, output=None):
    work = Path(work or ROOT/'.tools/rotation82').resolve()
    output = Path(output or ROOT/'docs/boundary-cloud-validation.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT): raise ValueError('Outputs must be inside the project')
    if work.exists() or output.exists(): raise FileExistsError('Fresh work/output paths required')
    check_sources(); sources = source_hashes(); policy = json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    work.mkdir(parents=True); output.parent.mkdir(parents=True, exist_ok=True)
    for name in sources:
        target = work/'executed-sources'/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    start = time.perf_counter(); arrays = {}; jobs = {}; expected_initial = {}
    try:
        metrics = {key: 0. for key in list(policy['maximum'])+list(policy['minimum'])}
        c = policy['light_speeds_m_s'][0]; system = cloud(policy, c)
        v = np.asarray(policy['frame_velocity_m_s']); length = policy['length_scale_m']
        pscale = policy['momentum_scale_kg_m_s']; duration = policy['duration_s']
        grid = np.linspace(0., 1., policy['samples']); times = duration*grid; count = len(system.masses)
        matrix = sr.boost(v, c); gamma = matrix[0, 0]
        rest_events = np.c_[np.zeros(count), system.positions]
        rest_p, rest_j, _ = sr.charges(rest_events, system.momenta)
        rest_spin = sr.spatial_angular(rest_j); spin_scale = np.linalg.norm(rest_spin)
        angular_scale = np.linalg.norm(rest_j); momentum_scale = np.linalg.norm(rest_p)
        expected_p = matrix@rest_p; expected_j = matrix@rest_j@matrix.T
        root, _ = local_spin_root(sr.ETA, v/c)
        metrics['lorentz_metric_defect'] = float(np.linalg.norm(matrix.T@sr.ETA@matrix-sr.ETA))
        events = []; momenta = []; local_times = []; states = []
        for t in times:
            ee, pp, tt = sr.snapshot(float(t), v, system)
            events.append(ee); momenta.append(pp); local_times.append(tt)
            states.append(np.r_[ee[:, 1:].ravel()/length, pp[:, 1:].ravel()/pscale])
        events = np.asarray(events); momenta = np.asarray(momenta); local_times = np.asarray(local_times); states = np.asarray(states)
        initial = states[0].copy()
        def save(name, data):
            path = work/(name+'.npz'); np.savez(path, **data)
            arrays[name] = dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               shapes={k: list(np.asarray(a).shape) for k, a in data.items()})
            expected_initial[name] = np.asarray(data['initial']).copy()
        save('production', dict(u=grid, global_time_s=times, initial=initial, states=states,
                                 events=events, momenta=momenta, local_times_s=local_times))
        totals = []
        for t, ee, pp in zip(times, events, momenta):
            total_p, total_j, centroid = sr.charges(ee, pp); totals.append((total_p, total_j))
            covariant = sr.about_centre(total_j, total_p, np.r_[c*t, v*t])
            lab = sr.about_centre(total_j, total_p, np.r_[c*t, centroid])
            spin4 = sr.spin_vector(total_p, covariant)
            values = dict(common_global_time_scaled=np.max(abs(ee[:, 0]-c*t))/length,
                momentum_covariance_relative=np.linalg.norm(total_p-expected_p)/momentum_scale,
                angular_covariance_relative=np.linalg.norm(total_j-expected_j)/angular_scale,
                mass_shell_relative=np.max(abs(-np.einsum('ni,ij,nj->n', pp, sr.ETA, pp)
                    -(np.asarray(system.masses)*c)**2)/(np.asarray(system.masses)*c)**2),
                covariant_ssc_scaled=np.linalg.norm(covariant@(sr.ETA@total_p))/(angular_scale*momentum_scale),
                lab_ssc_scaled=np.linalg.norm(lab[0])/angular_scale,
                centroid_formula_scaled=np.linalg.norm(centroid-v*t-np.cross(v, rest_spin)/(c*rest_p[0]))/length,
                spin_vector_covariance_relative=np.linalg.norm(spin4-matrix@np.r_[0., rest_spin])/spin_scale,
                euclidean_spin_relative=np.linalg.norm(root@spin4[1:]-rest_spin)/spin_scale)
            for key, value in values.items(): metrics[key] = max(metrics[key], float(value))
        metrics['energy_drift_relative'] = float(max(abs(p[0]-totals[0][0][0]) for p, _ in totals)/expected_p[0])
        metrics['angular_drift_relative'] = float(max(np.linalg.norm(j-totals[0][1]) for _, j in totals)/angular_scale)
        solver_policy = dict(atol_over_rtol=policy['atol_over_rtol'], max_phase_step=policy['max_step_u'])
        def run(name, method, tolerance):
            check_sources(); tick = time.perf_counter()
            function = lambda u, z: independent.rhs(u, z, system.masses, c, duration, length, pscale)
            result, nfev = integrate_raw_initial(function, initial, grid, method, tolerance, solver_policy)
            check_sources(); save(name, dict(u=grid, global_time_s=times, initial=initial, states=result))
            jobs[name] = dict(method=method, rtol=tolerance, atol=tolerance*policy['atol_over_rtol'], nfev=nfev, seconds=time.perf_counter()-tick)
            print(f'{name}: {nfev} evaluations, {jobs[name]["seconds"]:.2f}s', flush=True)
            return result
        refs = [run('reference-'+str(i), 'RK45', tolerance) for i, tolerance in enumerate(policy['reference_rtols'])]
        tighter = run('reference-dop853', 'DOP853', policy['tighter_rtol'])
        def difference(a, b, block):
            return float(np.max(np.linalg.norm((a-b)[:, block].reshape(-1, count, 3), axis=2)))
        xyz = slice(0, 3*count); pxyz = slice(3*count, 6*count)
        metrics['reference_x_scaled'] = difference(states, refs[1], xyz)
        metrics['reference_p_scaled'] = difference(states, refs[1], pxyz)
        metrics['reference_sensitivity_x_scaled'] = difference(refs[0], refs[1], xyz)
        metrics['tighter_reference_x_scaled'] = difference(refs[1], tighter, xyz)
        d, inertia, multipole = density.mass_moments(system.masses, system.positions)
        metrics['density_pair_residual_scaled'] = float(np.linalg.norm(density.density_pair(inertia, multipole)-d)/np.linalg.norm(d))
        jet = flat_jet(0., v, c); point = local.event(system.positions[0], jet)
        a = np.linalg.inv(point.position_x)
        di, ci, _ = density.mass_moments(system.masses, np.asarray(system.positions)@a.T)
        expected_d = a@d@a.T
        metrics['affine_moment_identity_relative'] = float(np.linalg.norm(ci-(np.trace(expected_d)*np.eye(3)-expected_d))/np.linalg.norm(ci))
        metrics['naive_inertia_image_relative'] = float(np.linalg.norm(ci-a@inertia@a.T)/np.linalg.norm(ci))
        spin_exact, spin_newton, spin_leading = density.rotation_snapshot_spin(system.masses, system.positions,
                                                                    policy['initial_omega_per_s'], c)
        metrics['naive_newton_spin_relative'] = float(np.linalg.norm(spin_exact-spin_newton)/np.linalg.norm(spin_exact))
        metrics['ignored_centroid_shift_scaled'] = float(np.linalg.norm(np.cross(v, rest_spin)/(c*rest_p[0]))/length)
        metrics['wrong_metric_root_as_rotation'] = float(np.linalg.norm(root.T@root-np.eye(3)))
        material = v+np.array([100., 50., 100.]); actual, _ = local.velocity(system.positions[0], material, jet)
        wrong_velocity = (point.position_t+point.position_x@material)/point.time_t
        metrics['omitted_simultaneity_velocity_relative'] = float(np.linalg.norm(wrong_velocity-actual)/np.linalg.norm(actual))
        wrong_events = []
        for t in times:
            wrong_t = float(t/gamma); x = np.asarray(system.positions)+np.asarray(system.velocities)*wrong_t
            wrong_events.append(np.c_[np.full(count, c*wrong_t), x]@matrix.T)
        wrong_events = np.asarray(wrong_events)
        wrong_states = np.c_[wrong_events[:, :, 1:].reshape(len(times), -1)/length,
                              momenta[:, :, 1:].reshape(len(times), -1)/pscale]
        metrics['wrong_common_local_time_spread_scaled'] = float(np.max(abs(wrong_events[:, :, 0]-c*times[:, None]))/length)
        metrics['wrong_common_local_time_position_scaled'] = float(np.max(np.linalg.norm(wrong_events[:, :, 1:]-events[:, :, 1:], axis=2))/length)
        save('wrong-common-local-time', dict(u=grid, global_time_s=times, initial=wrong_states[0], states=wrong_states, events=wrong_events))
        event_dev, spin_dev, order = order_checks(policy)
        metrics['event_fourth_order_ratio_deviation'] = event_dev; metrics['spin_fourth_order_ratio_deviation'] = spin_dev
        source_copy_ok = all(hashlib.sha256((work/'executed-sources'/name).read_bytes()).hexdigest()==digest for name, digest in sources.items())
        verified = True; raw_ok = True; grid_ok = True
        for name, entry in arrays.items():
            path = ROOT/entry['path']; verified &= hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
            with np.load(path, allow_pickle=False) as saved:
                for key, shape in entry['shapes'].items():
                    verified &= list(saved[key].shape)==shape and np.all(np.isfinite(saved[key]))
                raw_ok &= np.array_equal(saved['initial'].view(np.uint64), expected_initial[name].view(np.uint64))
                raw_ok &= np.array_equal(saved['states'][0].view(np.uint64), expected_initial[name].view(np.uint64))
                grid_ok &= np.array_equal(saved['u'].view(np.uint64), grid.view(np.uint64))
                grid_ok &= np.array_equal(saved['global_time_s'].view(np.uint64), times.view(np.uint64))
        confirmations = dict(sources_preserved=source_hashes()==sources and source_copy_ok,
            arrays_reverified=bool(verified), raw_initial_preserved=bool(raw_ok), grid_preserved=bool(grid_ok),
            physical_claims_false=bool(policy['physical_lunar_mapping_certified'] is False and policy['physical_accuracy_certified'] is False))
        failed = failures(metrics, confirmations, policy)
        report = dict(changes=policy['changes'], policy=policy, sources=sources, arrays=arrays, jobs=jobs,
            rest_input=dict(masses=system.masses, positions=system.positions, velocities=system.velocities),
            rest_energy_joule=float(c*rest_p[0]), invariant_mass_kg=float(rest_p[0]/c),
            rest_spin_kg_m2_s=rest_spin.tolist(), metrics=metrics, confirmations=confirmations,
            order=order, passed=not failed, failed=failed, seconds=time.perf_counter()-start,
            environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
            physical_lunar_mapping_certified=False, physical_accuracy_certified=False,
            runtime_changed=False, old_trajectories_reused=False,
            limitations='Exact freely expanding SR particles, no rigidity/binding stress/selfgravity. Leading event map is incomplete at higher orders. Density moments use specified rest-mass weights on one slice; not PN gravity moments. No lunar inertia/time-scale/ADM-centre qualification. Fixed epochs and numerical reference sensitivity are not a rigorous error bound.')
        text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
        with (work/'report.json').open('x', encoding='utf-8') as f: f.write(text)
        with output.open('x', encoding='utf-8') as f: f.write(text)
        if failed: raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        (work/'failure.json').write_text(json.dumps(dict(passed=False, error=repr(error), sources=sources,
            arrays=arrays, jobs=jobs, metrics=locals().get('metrics', {})), indent=2)+'\n', encoding='utf-8')
        raise


if __name__ == '__main__':
    result = audit()
    print(json.dumps(dict(passed=result['passed'], metrics=result['metrics'], order=result['order']), indent=2))
