"""Independent finite-H initial inversion and distinct spin/centre conventions."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.canonical_initial import (SIUnits, from_velocities_and_rate, kinematics,
    local_spin_root, leading_centre_shift, leading_centre_shift_rate)
from scripts.independent_rigid_pn import gradients
from scripts.rigid_pn_model import Parameters, rhs
from scripts.nbody_pn_spin import Parameters as PointParameters
from solar_simulator.rotation import RigidFigure


PARAMS = Parameters(PointParameters((.3, .7, .05), float(np.sqrt(1e5))),
                    RigidFigure(.3, (.002, .0025, .003), .15), 0)
BASE = np.array([[[.56, 0., 0.], [-.24, 0., 0.], [3.5, .4, .6]],
                 [[0., .257, 0.], [0., -.257, 0.], [-.003, .025, .004]],
                 [[.003, -.004, .002], [-.002, .001, .003], [.0002, .0003, -.0001]]])
Q = np.roll(Rotation.from_rotvec([.3, -.2, .4]).as_quat(), 1)


def oracle_kinematics(block, q, params=PARAMS):
    r = Rotation.from_quat(np.roll(q, -1)).as_matrix()
    g, _ = gradients(block.ravel(), r, params.orbital.masses, params.orbital.c,
                     params.figure.moments, params.index)
    g = g.reshape(3, len(params.orbital.masses), 3)
    return g[1], g[2, params.index]


def invert(block=BASE, q=Q, params=PARAMS, **options):
    v, w = oracle_kinematics(block, q, params)
    s = block[2].copy(); s[params.index] = 0.
    return from_velocities_and_rate(block[0], v, q, w, s, params,
        velocity_scales=np.linalg.norm(v, axis=1), rate_scale=np.linalg.norm(w), **options)


def test_joint_inversion_against_independent_full_H_gradients():
    rng = np.random.default_rng(58)
    for _ in range(24):
        b = BASE.copy()
        b += rng.normal(size=b.shape)*np.array([.03, .001, .0001])[:, None, None]
        q = np.roll(Rotation.random(random_state=rng).as_quat(), 1)
        actual, info = invert(b, q)
        residual = np.linalg.norm(actual[:-4].reshape(b.shape)-b, axis=-1)/np.linalg.norm(b, axis=-1)
        assert residual.max() < 1e-11
        assert info['iterations'] <= 5
        assert max(info['velocity_residual'], info['attitude_rate_residual']) < 1e-13
        v, w = oracle_kinematics(b, q)
        measured_v, measured_w = kinematics(actual, PARAMS)
        assert np.max(np.linalg.norm(measured_v-v, axis=1)/np.linalg.norm(v, axis=1)) < 1e-13
        assert np.linalg.norm(measured_w-w)/np.linalg.norm(w) < 1e-13


def test_naive_m_v_and_I_W_are_detectably_wrong():
    v, w = oracle_kinematics(BASE, Q)
    r = Rotation.from_quat(np.roll(Q, -1)).as_matrix()
    naive = BASE.copy(); naive[1] = np.array(PARAMS.orbital.masses)[:, None]*v
    naive[2, 0] = r@(np.array(PARAMS.figure.moments)*(r.T@w))
    errors = np.linalg.norm(naive-BASE, axis=-1)/np.linalg.norm(BASE, axis=-1)
    assert errors[1].max() > 1e-5
    assert errors[2, 0] > 1e-6
    nv, nw = kinematics(np.r_[naive.ravel(), Q], PARAMS)
    assert np.linalg.norm(nv-v) > 1e-6
    assert np.linalg.norm(nw-w) > 1e-6


def test_rotation_translation_permutation_sign_and_time_reversal():
    rotation = Rotation.from_rotvec([.6, -.4, .7]); r = rotation.as_matrix()
    moved = BASE@r.T; moved[0] += [.7, -.3, .2]
    q = np.roll((rotation*Rotation.from_quat(np.roll(Q, -1))).as_quat(), 1)
    actual, _ = invert(moved, -q)
    assert np.allclose(actual[:-4].reshape(moved.shape), moved, rtol=1e-11, atol=1e-14)
    assert np.array_equal(actual[-4:], -q)
    reversed_block = BASE.copy(); reversed_block[1:] *= -1
    backward, _ = invert(reversed_block)
    assert np.allclose(backward[:-4].reshape(BASE.shape), reversed_block, rtol=1e-11, atol=1e-14)
    order = [2, 0, 1]
    params = Parameters(PointParameters(tuple(PARAMS.orbital.masses[i] for i in order),
                                         PARAMS.orbital.c), PARAMS.figure, 1)
    permuted, _ = invert(BASE[:, order], Q, params)
    assert np.allclose(permuted[:-4].reshape(BASE.shape), BASE[:, order], rtol=1e-11, atol=1e-14)


def test_zero_target_velocity_and_zero_attitude_rate_have_explicit_scales():
    s = BASE[2].copy(); s[0] = 0.
    state, info = from_velocities_and_rate(BASE[0], np.zeros((3, 3)), Q, np.zeros(3),
        s, PARAMS, velocity_scales=np.ones(3), rate_scale=1.)
    v, w = kinematics(state, PARAMS)
    assert np.linalg.norm(v) < 1e-13
    assert np.linalg.norm(w) < 1e-13


def test_nonconvergence_and_invalid_boundary_inputs_are_explicit():
    with pytest.raises(ValueError, match='did not converge'):
        invert(max_iterations=1, tolerance=1e-18)
    v, w = oracle_kinematics(BASE, Q); s = BASE[2].copy(); s[0] = 0.
    args = dict(positions=BASE[0], velocities=v, quaternion=Q, attitude_rate=w,
                point_spins=s, parameters=PARAMS, velocity_scales=np.ones(3), rate_scale=1.)
    for key, value in [('quaternion', Q*1.01), ('velocities', np.full((3, 3), np.nan)),
                       ('velocity_scales', np.zeros(3)), ('rate_scale', 0.),
                       ('max_iterations', True), ('point_spins', BASE[2]),
                       ('positions', np.zeros((3, 3)))]:
        with pytest.raises(ValueError):
            from_velocities_and_rate(**dict(args, **{key: value}))


def test_metric_spin_root_flat_boost_and_covariant_SSC_norm():
    metric = np.diag([-1., 1., 1., 1.])
    beta = np.array([.2, -.1, .3]); gamma = 1/np.sqrt(1-beta@beta)
    rest = np.array([.3, .7, -.2])
    covariant = rest+(gamma-1)*beta*(beta@rest)/(beta@beta)
    time_component = -beta@covariant
    root, g = local_spin_root(metric, beta)
    assert np.linalg.norm(root@covariant-rest) < 1e-15
    assert np.linalg.norm(root@root-g) < 1e-15
    assert covariant@g@covariant == pytest.approx(rest@rest, rel=1e-15)
    assert -time_component**2+covariant@covariant == pytest.approx(rest@rest, rel=1e-15)
    assert np.linalg.det(root) == pytest.approx(1/gamma, rel=1e-15)
    assert abs(np.linalg.det(root)-1) > .01  # This is not an attitude rotation.


def test_metric_spin_weak_field_series_has_fourth_order_remainder():
    errors = []
    v = np.array([.3, -.2, .1]); potential = .7
    for c in [10., 20.]:
        metric = np.diag([-1-2*potential/c**2]+[1-2*potential/c**2]*3)
        root, _ = local_spin_root(metric, v/c)
        first = np.eye(3)-(potential*np.eye(3)+.5*np.outer(v, v))/c**2
        errors.append(np.linalg.norm(root-first))
    assert 15.9 < errors[0]/errors[1] < 16.2


@pytest.mark.parametrize('metric,beta', [
    (np.eye(4), [0, 0, 0]), (np.diag([-1., 1., 1., 1.]), [1, 0, 0]),
    (np.diag([-1., -1., 1., 1.]), [0, 0, 0]),
    (np.full((4, 4), np.nan), [0, 0, 0]),
    (np.array([[-1., .1, 0, 0], [0, 1., 0, 0], [0, 0, 1., 0], [0, 0, 0, 1.]]), [0, 0, 0])])
def test_metric_spin_domain_rejections(metric, beta):
    with pytest.raises(ValueError):
        local_spin_root(metric, beta)


def test_leading_centre_shift_sign_and_rate_independent_directional_derivative():
    y = np.r_[BASE.ravel(), Q]; flow = rhs(0., y, PARAMS)[:-4]
    shift = leading_centre_shift(y[:-4], PARAMS.orbital)
    for i, mass in enumerate(PARAMS.orbital.masses):
        expected = np.cross(BASE[2, i], BASE[1, i])/(2*mass**2*PARAMS.orbital.c**2)
        assert np.linalg.norm(shift[i]-expected) < 1e-20
    # Differentiate the bilinear scalar component with complex-step, not the helper.
    z = (BASE.ravel()+1e-25j*flow).reshape(BASE.shape)
    reference = np.cross(z[2], z[1])/(2*np.array(PARAMS.orbital.masses)[:, None]**2*PARAMS.orbital.c**2)
    measured = leading_centre_shift_rate(y[:-4], flow, PARAMS.orbital)
    assert np.linalg.norm(measured-reference.imag/1e-25) < 1e-20
    wrong = np.cross(BASE[2], flow.reshape(BASE.shape)[1])/(2*np.array(PARAMS.orbital.masses)[:, None]**2*PARAMS.orbital.c**2)
    assert np.linalg.norm(measured-wrong) > 1e-9  # Figure torque term must survive.


def test_SI_unit_similarity_and_roundtrip():
    units = SIUnits(1.988e30, 1.495978707e11, 6.6743e-11)
    assert units.gravitational_constant*units.mass_kg*units.time_s**2/units.length_m**3 == pytest.approx(1.)
    assert units.inertia_kg_m2/units.time_s == pytest.approx(units.spin_kg_m2_s)
    actual, _ = invert()
    scales = np.array([units.length_m, units.momentum_kg_m_s, units.spin_kg_m2_s])[:, None, None]
    physical = actual[:-4].reshape(BASE.shape)*scales
    assert np.allclose(physical/scales, BASE, rtol=1e-11, atol=1e-14)


@pytest.mark.parametrize('scales', [(0., 1., 1.), (1., -1., 1.), (1., 1., 0.),
                                    (float('nan'), 1., 1.), (1., 1e200, 1.)])
def test_SI_unit_rejections(scales):
    with pytest.raises(ValueError):
        SIUnits(*scales)
