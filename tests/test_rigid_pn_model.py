"""Independent full-H variations, Poisson closure and limiting rigid dynamics."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.nbody_pn_spin import Parameters as PointParameters, rhs as point_rhs
from scripts.rigid_pn_model import Parameters, fields, rhs, hamiltonian, invariants, validate_initial
from scripts.independent_rigid_pn import gradients, scalar_hamiltonian, hat, matrix_rhs
from solar_simulator.rotation import RigidFigure, pair_rhs
from solar_simulator.simulation import G


P = Parameters(PointParameters((.3, .7, .05), float(np.sqrt(1e5))),
               RigidFigure(.3, (.002, .0025, .003), .15), 0)
Q = np.roll(Rotation.from_rotvec([.3, -.2, .4]).as_quat(), 1)
Y = np.r_[np.array([[[.56, 0., 0.], [-.24, 0., 0.], [3.5, .4, .6]],
                   [[0., .257, 0.], [0., -.257, 0.], [-.003, .025, .004]],
                   [[.003, -.004, .002], [-.002, .001, .003], [.0002, .0003, -.0001]]]).ravel(), Q]


def oracle(state, params=P):
    r = Rotation.from_quat(np.roll(state[-4:], -1)).as_matrix()
    g, angle = gradients(state[:-4], r, params.orbital.masses, params.orbital.c,
                         params.figure.moments, params.index)
    return r, g.reshape(3, len(params.orbital.masses), 3), angle


def test_complete_hamiltonian_and_cotangent_rotation_derivatives():
    rng = np.random.default_rng(57)
    for _ in range(12):
        y = Y.copy(); b = y[:-4].reshape(3, 3, 3)
        for block, scale in enumerate([.05, .005, .0001]):
            b[block] += rng.normal(size=(3, 3))*scale
        r, g, angle = oracle(y)
        assert hamiltonian(y, P) == pytest.approx(scalar_hamiltonian(y[:-4], r,
            P.orbital.masses, P.orbital.c, P.figure.moments, 0), rel=3e-15)
        expected = np.stack([g[1], -g[0], np.cross(g[2], b[2])]); expected[2, 0] -= angle
        actual = rhs(0., y, P)[:-4].reshape(3, 3, 3)
        assert np.max(np.linalg.norm(actual-expected, axis=-1)/np.linalg.norm(expected, axis=-1)) < 1e-10
        # Body-Euler representation is different and transformed back explicitly.
        matrix_state = np.r_[y[:-4], r.ravel()]; matrix_state[18:21] = r.T@b[2, 0]
        df = matrix_rhs(0., matrix_state, P.orbital.masses, P.orbital.c, P.figure.moments, 0)
        converted = df[:27].reshape(3, 3, 3).copy()
        converted[2, 0] = df[27:].reshape(3, 3)@(r.T@b[2, 0])+r@converted[2, 0]
        assert np.max(np.linalg.norm(converted-actual, axis=-1)/np.linalg.norm(actual, axis=-1)) < 1e-10
        assert np.linalg.norm(df[27:].reshape(3, 3)-hat(g[2, 0])@r) < 1e-14


def test_H_P_J_balance_and_two_detectable_wrong_combinations():
    r, g, angle = oracle(Y); b = Y[:-4].reshape(3, 3, 3)
    flow = rhs(0., Y, P); f = flow[:-4].reshape(3, 3, 3)
    rate = np.sum(g*f)+np.dot(angle, g[2, 0])
    assert abs(rate) < 1e-15
    assert np.linalg.norm(f[1].sum(axis=0)) < 1e-16
    assert np.linalg.norm((np.cross(f[0], b[1])+np.cross(b[0], f[1])+f[2]).sum(axis=0)) < 1e-15
    _, _, omega, connection, _, forces, torque = fields(Y, P)
    assert np.linalg.norm(connection) > 1e-6
    wrong_energy_rate = np.sum(g*f)+np.dot(angle, omega)
    assert abs(wrong_energy_rate) > 1e-10
    assert wrong_energy_rate == pytest.approx(-np.dot(angle, connection), rel=1e-8)
    bad_dp = f[1]-forces  # Remove Q2 orbital reactions but retain figure torque.
    assert np.linalg.norm((np.cross(f[0], b[1])+np.cross(b[0], bad_dp)+f[2]).sum(axis=0)) > 1e-5
    # The figure's spin length is NOT a point-spin Casimir after adding q/Q2.
    assert abs(np.dot(b[2, 0], f[2, 0])) > 1e-8


def test_attitude_SO_connection_even_when_initial_figure_spin_is_zero():
    y = Y.copy(); y[18:21] = 0.
    r, g, angle = oracle(y); flow = rhs(0., y, P)
    assert np.linalg.norm(flow[-4:]) > 1e-6
    h = 1e-5
    r_plus = Rotation.from_quat(np.roll(y[-4:]+h*flow[-4:], -1)).as_matrix()
    r_minus = Rotation.from_quat(np.roll(y[-4:]-h*flow[-4:], -1)).as_matrix()
    assert np.linalg.norm((r_plus-r_minus)/(2*h)-hat(g[2, 0])@r) < 1e-10


def test_spherical_figure_has_zero_Q2_and_constant_body_spin_derivative():
    params = Parameters(P.orbital, RigidFigure(.3, (.0025,)*3, .15), 0)
    y, r, omega, connection, energy, force, torque = fields(Y, params)
    assert energy == 0 and np.array_equal(force, np.zeros((3, 3))) and np.array_equal(torque, np.zeros(3))
    assert np.allclose(rhs(0., y, params)[:-4], point_rhs(0., y[:-4], params.orbital), rtol=0, atol=1e-16)
    f = rhs(0., y, params)[:-4].reshape(3, 3, 3)
    # For a sphere omega x S is identically zero. Cancel it analytically,
    # before adding tiny SO to intrinsic omega and losing float64 digits.
    assert np.linalg.norm(r.T@(f[2, 0]-np.cross(connection, y[18:21]))) < 1e-18


def test_newtonian_pair_limit_matches_existing_SI_rigid_equations():
    orbit = PointParameters((.3, .7), 1e100)
    params = Parameters(orbit, P.figure, 0)
    blocks = Y[:-4].reshape(3, 3, 3)[:, :2].copy(); y = np.r_[blocks.ravel(), Q]
    flow = rhs(0., y, params); f = flow[:-4].reshape(3, 2, 3)
    physical_figure = RigidFigure(.3/G, tuple(v/G for v in P.figure.moments), .15)
    pair_state = np.r_[blocks[0, 1]-blocks[0, 0], blocks[1, 1]/.7-blocks[1, 0]/.3, Q, blocks[2, 0]/G]
    reference = pair_rhs(physical_figure, .7/G, pair_state)
    assert np.linalg.norm(f[0, 1]-f[0, 0]-reference[:3]) < 1e-16
    assert np.linalg.norm(f[1, 1]/.7-f[1, 0]/.3-reference[3:6]) < 1e-15
    assert np.linalg.norm(flow[-4:]-reference[6:10]) < 1e-15
    assert np.linalg.norm(f[2, 0]-G*reference[10:]) < 1e-17


def test_frame_covariance_translation_permutation_sign_and_time_reversal():
    matrix = Rotation.from_rotvec([-.4, .3, .2]); b = Y[:-4].reshape(3, 3, 3)
    rotated_q = np.roll((matrix*Rotation.from_quat(np.roll(Q, -1))).as_quat(), 1)
    rotated = np.r_[(b@matrix.as_matrix().T).ravel(), rotated_q]
    f = rhs(0., Y, P)[:-4].reshape(3, 3, 3)
    assert np.linalg.norm(rhs(0., rotated, P)[:-4].reshape(3, 3, 3)-f@matrix.as_matrix().T) < 1e-15
    assert hamiltonian(rotated, P) == pytest.approx(hamiltonian(Y, P), rel=3e-15)
    shifted = Y.copy(); shifted[:-4].reshape(3, 3, 3)[0] += [2., -3., 1.]
    assert np.linalg.norm(rhs(0., shifted, P)-rhs(0., Y, P)) < 1e-15
    order = [2, 0, 1]; params = Parameters(PointParameters(tuple(P.orbital.masses[i] for i in order), P.orbital.c), P.figure, 1)
    permuted = np.r_[b[:, order].ravel(), Q]
    assert np.linalg.norm(rhs(0., permuted, params)[:-4].reshape(3, 3, 3)-f[:, order]) < 1e-15
    changed_q = Y.copy(); changed_q[-4:] *= -1
    assert np.array_equal(rhs(0., changed_q, P)[:-4], rhs(0., Y, P)[:-4])
    assert np.array_equal(rhs(0., changed_q, P)[-4:], -rhs(0., Y, P)[-4:])
    signs = np.r_[np.ones(9), -np.ones(18), np.ones(4)]
    assert np.linalg.norm(rhs(0., Y*signs, P)+rhs(0., Y, P)*signs) < 1e-15


@pytest.mark.parametrize('fault', ['shape','nan','q','contact','internal-speed'])
def test_research_state_rejection(fault):
    y = Y.copy()
    if fault == 'shape': y = y[:-1]
    if fault == 'nan': y[-1] = np.nan
    if fault == 'q': y[-4:] = 0.
    if fault == 'contact': y[3:6] = y[:3]+[.1, 0, 0]
    if fault == 'internal-speed': y[18] = .1
    with pytest.raises(ValueError): fields(y, P)


@pytest.mark.parametrize('index,figure', [(True, P.figure), (3, P.figure), (1, P.figure)])
def test_index_or_mass_mismatch_rejected(index, figure):
    with pytest.raises(ValueError): Parameters(P.orbital, figure, index)


def test_initial_quaternion_rules_do_not_reject_RK_trial_states():
    from scipy.integrate import solve_ivp
    initial = Y.copy(); initial[-4:] *= 2
    with pytest.raises(ValueError): validate_initial(initial, P)
    validate_initial(Y, P)
    # The initial-step algorithm makes a nonunit Euler trial before integration.
    trial = Y+1e-3*rhs(0., Y, P)
    assert abs(np.linalg.norm(trial[-4:])-1) > 1e-8
    assert np.all(np.isfinite(rhs(0., trial, P)))
    solution = solve_ivp(lambda t, y: rhs(t, y, P), (0., .2), Y,
                         method='DOP853', rtol=1e-11, atol=1e-13)
    assert solution.success
    assert abs(np.linalg.norm(solution.y[-4:, -1])-1) < 1e-9
