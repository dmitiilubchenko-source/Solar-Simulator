"""Predeclared initial-data audit; independent scalar-H derivatives and solver."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import scipy
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts.canonical_initial import (SIUnits, from_velocities_and_rate, kinematics,
    local_spin_root, leading_centre_shift, leading_centre_shift_rate)
from scripts.independent_rigid_pn import gradients
from scripts.rigid_pn_model import Parameters, fields, rhs
from scripts.nbody_pn_spin import Parameters as PointParameters
from solar_simulator.rotation import RigidFigure


def independent_kinematics(block, matrix, params):
    g, _ = gradients(block.ravel(), matrix, params.orbital.masses,
        params.orbital.c, params.figure.moments, params.index)
    g = g.reshape(block.shape)
    return g[1], g[2, params.index]


def inverse_reference(block, matrix, v, w, params, tolerance):
    """Independent least-squares inversion of original-H gradients, not RHS."""
    m = np.array(params.orbital.masses)[:, None]; a = params.index
    vs = np.linalg.norm(v, axis=1); ws = np.linalg.norm(w)
    inertia = matrix@np.diag(params.figure.moments)@matrix.T
    def unpack(z):
        b = block.copy(); b[1] = m*z[:-3].reshape(-1, 3)*vs[:, None]
        b[2, a] = inertia@(z[-3:]*ws)
        return b
    def residual(z):
        ov, ow = independent_kinematics(unpack(z), matrix, params)
        return np.r_[((ov-v)/vs[:, None]).ravel(), (ow-w)/ws]
    initial = np.r_[(v/vs[:, None]).ravel(), w/ws]
    answer = least_squares(residual, initial, xtol=tolerance, ftol=tolerance,
                           gtol=tolerance, max_nfev=100)
    if not answer.success or not np.all(np.isfinite(answer.x)):
        raise ValueError(f'Independent inverse failed: {answer.message}')
    return unpack(answer.x), float(np.linalg.norm(answer.fun)), int(answer.nfev)


def lunar_diagnostic(policy):
    """No migration: quantify corrections under explicitly conditional inputs."""
    specification = policy['lunar_diagnostic']
    sources = ['src/solar_simulator/data/solar-system-moon-20261008.json',
               'src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json']
    hashes = [hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources]
    if hashes != [specification['orbital_data_sha256'], specification['spin_profile_sha256']]:
        raise ValueError('Changed pinned lunar inputs')
    data, profile = [json.loads((ROOT/p).read_text(encoding='utf-8')) for p in sources]
    for key in ['epoch_jd_tdb', 'frame']:
        if data[key] != specification[key] or profile[key] != specification[key]:
            raise ValueError(f'Incompatible lunar {key}')
    if (data['center'] != specification['center'] or profile['source_center'] != data['center']
            or data['units'] != 'SI' or profile['units'] != 'SI'
            or profile['parent_dataset_sha256'] != hashes[0]):
        raise ValueError('Incompatible lunar provenance')
    bodies = data['bodies']; names = [b['name'] for b in bodies]
    sun, earth, a = names.index('Sun'), names.index('Earth'), names.index('Moon')
    gravitational_constant = profile['gravitational_constant_m3_kg_s2']
    units = SIUnits(bodies[sun]['gm_m3_s2']/gravitational_constant,
                    specification['length_scale_m'], gravitational_constant)
    masses = tuple(b['gm_m3_s2']/gravitational_constant/units.mass_kg for b in bodies)
    if (bodies[earth]['gm_m3_s2'] != profile['earth_gm_m3_s2']
            or bodies[a]['gm_m3_s2'] != profile['moon_gm_m3_s2']):
        raise ValueError('Lunar/Earth GM mismatch')
    params = Parameters(PointParameters(masses, specification['c_m_s']/units.velocity_m_s),
        RigidFigure(masses[a], tuple(np.array(profile['moments_kg_m2'])/units.inertia_kg_m2),
                    profile['exclusion_radius_m']/units.length_m), a)
    x = np.array([b['position'] for b in bodies])/units.length_m
    v = np.array([b['velocity'] for b in bodies])/units.velocity_m_s
    r = np.array(profile['rotation']); rd = np.array(profile['rotation_derivative_per_second'])
    hat = rd@r.T
    # Extraction uses no legacy spin conversion; verify the supplied tangent.
    if (np.linalg.norm(r.T@r-np.eye(3)) > 1e-12
            or np.linalg.norm(hat+hat.T)/np.linalg.norm(rd) > 1e-12):
        raise ValueError('Invalid pinned orientation tangent')
    w_si = np.array([hat[2, 1]-hat[1, 2], hat[0, 2]-hat[2, 0], hat[1, 0]-hat[0, 1]])/2
    q = np.roll(Rotation.from_matrix(r).as_quat(), 1)
    state, residual = from_velocities_and_rate(x, v, q, w_si*units.time_s,
        np.zeros_like(x), params, velocity_scales=np.linalg.norm(v, axis=1),
        rate_scale=np.linalg.norm(w_si)*units.time_s, tolerance=policy['production_tolerance'],
        max_iterations=policy['production_max_iterations'])
    block = state[:-4].reshape(3, len(masses), 3)
    ov, ow = independent_kinematics(block, r, params)
    _, _, intrinsic, connection, *_ = fields(state, params)
    naive_spin = r@(np.array(params.figure.moments)*(r.T@(w_si*units.time_s)))
    shifts = leading_centre_shift(state[:-4], params.orbital)*units.length_m
    flow = rhs(0., state, params)[:-4]
    shift_rates = leading_centre_shift_rate(state[:-4], flow, params.orbital)*units.velocity_m_s
    delta_velocity = (block[1]/np.array(masses)[:, None]-v)*units.velocity_m_s
    return dict(physical_mapping_certified=False, interpretation=specification['interpretation'],
        epoch_jd_tdb=data['epoch_jd_tdb'], frame=data['frame'], center=data['center'],
        units=vars(units), time_unit_s=units.time_s, input_sha256=dict(zip(sources, hashes)),
        body_names=names, residual=residual,
        gradient_velocity_relative=float(np.max(np.linalg.norm(ov-v, axis=1)/np.linalg.norm(v, axis=1))),
        gradient_rate_relative=float(np.linalg.norm(ow-w_si*units.time_s)/(np.linalg.norm(w_si)*units.time_s)),
        p_over_m_minus_input_velocity_m_s=delta_velocity.tolist(),
        initial_attitude_rate_per_s=w_si.tolist(), intrinsic_rate_per_s=(intrinsic/units.time_s).tolist(),
        SO_connection_per_s=(connection/units.time_s).tolist(),
        naive_spin_relative_error=float(np.linalg.norm(naive_spin-block[2, a])/np.linalg.norm(block[2, a])),
        canonical_spin_kg_m2_s=(block[2, a]*units.spin_kg_m2_s).tolist(),
        LO_harmonic_minus_canonical_centre_m=shifts.tolist(),
        LO_centre_rate_m_s=shift_rates.tolist(),
        state_for_model_diagnostic=state.tolist(),
        limitations=['x/R are conditional canonical-boundary surrogates, not a certified JPL transform',
                    'the LO centre shift is quantified but NOT applied to the conditional inputs',
                    'stored TDB-compatible inputs used unchanged; no TCB/TDB/proper-time conversion',
                    'no complete PN-Q2/metric inertia, core, deformation, tides, or future ephemeris fit'])


def audit():
    output = ROOT/'docs/canonical-initial-validation.json'
    if output.exists():
        raise FileExistsError('Preserve canonical initial audit')
    policy_path = ROOT/'scripts/canonical-initial-policy.json'
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    sources = ['scripts/canonical-initial-policy.json', 'scripts/canonical_initial.py',
        'scripts/assess_canonical_initial.py', 'tests/test_canonical_initial.py',
        'scripts/independent_rigid_pn.py', 'scripts/independent_nbody_pn_spin.py',
        'scripts/nbody_pn_spin.py', 'scripts/rigid_pn_model.py', 'src/solar_simulator/rotation.py']
    sha = lambda p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
    hashes = {p: sha(p) for p in sources}
    params = Parameters(PointParameters(tuple(policy['masses']), policy['c']),
        RigidFigure(policy['masses'][policy['figure_index']], tuple(policy['moments']),
                    policy['bounding_radius']), policy['figure_index'])
    metrics = {k: 0. for k in policy['criteria']}; controls = {k: 0. for k in policy['lower_bound_controls']}
    rng = np.random.default_rng(policy['seed']); results = []
    for index in range(policy['states']):
        b = np.array(policy['base_blocks'], dtype=float)
        b += rng.normal(size=b.shape)*np.array(policy['perturbation_scales'])[:, None, None]
        r = Rotation.random(random_state=rng); matrix = r.as_matrix(); q = np.roll(r.as_quat(), 1)
        v, w = independent_kinematics(b, matrix, params)
        spins = b[2].copy(); spins[params.index] = 0.
        y, residual = from_velocities_and_rate(b[0], v, q, w, spins, params,
            velocity_scales=np.linalg.norm(v, axis=1), rate_scale=np.linalg.norm(w),
            tolerance=policy['production_tolerance'], max_iterations=policy['production_max_iterations'])
        recovered = y[:-4].reshape(b.shape)
        reference, oracle_residual, calls = inverse_reference(b, matrix, v, w, params,
            policy['independent_least_squares_tolerance'])
        relative = lambda other: float(np.max(np.linalg.norm(other-b, axis=-1)/np.linalg.norm(b, axis=-1)))
        ov, ow = independent_kinematics(recovered, matrix, params)
        checks = dict(model_roundtrip_relative_max=relative(recovered),
            independent_inverse_relative_max=relative(reference),
            velocity_residual_max=residual['velocity_residual'],
            attitude_rate_residual_max=residual['attitude_rate_residual'],
            independent_gradient_velocity_relative_max=float(np.max(np.linalg.norm(ov-v, axis=1)/np.linalg.norm(v, axis=1))),
            independent_gradient_rate_relative_max=float(np.linalg.norm(ow-w)/np.linalg.norm(w)))
        flow = rhs(0., y, params)[:-4]; z = (y[:-4]+1e-25j*flow).reshape(b.shape)
        expected = (np.cross(z[2], z[1])/(2*np.array(params.orbital.masses)[:, None]**2*params.orbital.c**2)).imag/1e-25
        actual = leading_centre_shift_rate(y[:-4], flow, params.orbital)
        checks['centre_rate_relative_max'] = float(np.max(np.linalg.norm(actual-expected, axis=1)/np.linalg.norm(expected, axis=1)))
        controls['naive_m_v_error_max'] = max(controls['naive_m_v_error_max'],
            float(np.max(np.linalg.norm(np.array(params.orbital.masses)[:, None]*v-b[1], axis=1)/np.linalg.norm(b[1], axis=1))))
        naive_s = matrix@(np.array(params.figure.moments)*(matrix.T@w))
        controls['naive_I_W_error_max'] = max(controls['naive_I_W_error_max'],
            float(np.linalg.norm(naive_s-b[2, params.index])/np.linalg.norm(b[2, params.index])))
        for k, value in checks.items(): metrics[k] = max(metrics[k], value)
        results.append(dict(index=index, initial_state=np.r_[b.ravel(), q].tolist(),
            checks=checks, inverse=residual, oracle_residual=oracle_residual, oracle_calls=calls))
    metric_errors = []
    for c in policy['metric_cs']:
        potential = policy['metric_field']; v = np.array(policy['metric_velocity'])
        root, g = local_spin_root(np.diag([-1-2*potential/c**2]+[1-2*potential/c**2]*3), v/c)
        metrics['metric_square_root_relative'] = max(metrics['metric_square_root_relative'],
            float(np.linalg.norm(root@root-g)/np.linalg.norm(g)))
        approximation = np.eye(3)-(potential*np.eye(3)+.5*np.outer(v, v))/c**2
        metric_errors.append(float(np.linalg.norm(root-approximation)))
    ratio = metric_errors[0]/metric_errors[1]
    moon = lunar_diagnostic(policy)
    metrics.update(lunar_velocity_residual=moon['residual']['velocity_residual'],
        lunar_attitude_rate_residual=moon['residual']['attitude_rate_residual'],
        lunar_gradient_velocity_relative=moon['gradient_velocity_relative'],
        lunar_gradient_rate_relative=moon['gradient_rate_relative'])
    lo, hi = policy['interval_controls']['metric_fourth_order_ratio']
    passed = (all(metrics[k] < limit for k, limit in policy['criteria'].items())
              and all(controls[k] > limit for k, limit in policy['lower_bound_controls'].items())
              and lo < ratio < hi)
    if hashes != {p: sha(p) for p in sources}:
        raise ValueError('Audit sources changed while running')
    report = dict(change=58, policy=policy, numpy=np.__version__, scipy=scipy.__version__,
        metrics=metrics, lower_bound_controls=controls, metric_fourth_order_ratio=ratio,
        states=results, lunar_diagnostic=moon, passed=passed, physical_lunar_mapping_certified=False,
        code_sha256=hashes)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(dict(metrics=metrics, controls=controls, fourth_order_ratio=ratio, passed=passed), indent=2), flush=True)
    return passed


if __name__ == '__main__':
    sys.exit(0 if audit() else 1)
