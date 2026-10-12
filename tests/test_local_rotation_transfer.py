import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts import local_multipole as model
from scripts import local_rotation_transfer as transfer
from scripts.independent_local_multipole import scalar, hat
from scripts.canonical_initial import local_spin_root
from tests.test_local_multipole import fixture


def boundary():
    rotation = Rotation.from_rotvec([.3, -.1, .5])
    b = rotation.as_matrix(); w = np.array([.03, -.02, .04])
    return transfer.Boundary(b, hat(w)@b, 1.2, -.003, [.002, -.001, .004]), np.roll(rotation.as_quat(), 1)


def test_full_canonical_generator_independent_Kgrad_and_product_rule():
    p, y = fixture(); b, qb = boundary(); target = transfer.map_state(y, p, b, qb)
    r = Rotation.from_quat(np.roll(target[9:], -1)).as_matrix()
    wb = b.omega; rate = b.clock_rate
    def k(z, matrix):
        return rate*scalar(z, matrix, p)+wb@(np.cross(z[:3], z[3:6])+z[6:9])
    gradient = []
    for axis in np.eye(9):
        gradient.append(k(target[:9]+1j*1e-25*axis, r).imag/1e-25)
    gradient = np.array(gradient).reshape(3, 3)
    angles = np.array([k(target[:9], (np.eye(3)+1j*1e-25*hat(a))@r).imag/1e-25 for a in np.eye(3)])
    gx, gp, gs = gradient
    flow = transfer.rhs(0., target, p, b)
    expected = np.r_[gp, -gx, np.cross(gs, target[6:9])-angles]
    for start, size in [(0, 3), (3, 3), (6, 3)]:
        assert np.linalg.norm(flow[start:start+size]-expected[start:start+size])/np.linalg.norm(expected[start:start+size]) < 1e-11
    local_flow = model.rhs(0., y, p); matrix = np.asarray(b.basis)
    for index in range(3):
        out = rate*matrix@local_flow[3*index:3*index+3]+np.cross(wb, target[3*index:3*index+3])
        assert np.allclose(flow[3*index:3*index+3], out, rtol=1e-12, atol=1e-12)
    # Quaternion lift derivative from Hamilton products, not qdot again.
    qb_dot = .5*transfer.quaternion_product(np.r_[0., wb], qb)
    product = transfer.quaternion_product(qb_dot, y[9:])+rate*transfer.quaternion_product(qb, local_flow[9:])
    assert np.linalg.norm(flow[9:]-product) < 1e-12
    assert abs(transfer.hamiltonian(target, p, b)/k(target[:9], r)-1) < 1e-12


def test_inverse_rates_preserve_canonical_state_and_detect_naive_spin():
    p, y = fixture(); b, qb = boundary(); target = transfer.map_state(y, p, b, qb)
    flow = transfer.rhs(0., target, p, b)
    w = b.clock_rate*model.fields(target, p)[4]+b.omega
    restored = transfer.from_target_rates(target[:3], flow[:3], target[9:], w, p, b)
    for i in range(3):
        assert np.linalg.norm(restored[3*i:3*i+3]-target[3*i:3*i+3])/np.linalg.norm(target[3*i:3*i+3]) < 1e-12
    assert np.array_equal(restored[9:].view(np.uint64), target[9:].view(np.uint64))
    c = model.fields(target, p)[2]
    assert np.linalg.norm(c@w-target[6:9])/np.linalg.norm(target[6:9]) > 1e-4
    assert np.linalg.norm(p.reduced_mass*flow[:3]-target[3:6])/np.linalg.norm(target[3:6]) > 1e-4
    recovered = transfer.map_state(target, p, b, qb, inverse=True)
    assert np.allclose(recovered, y, rtol=1e-12, atol=1e-12)


def test_work_and_total_J_not_just_spin_in_connection():
    p, y = fixture(); b, qb = boundary(); z = transfer.map_state(y, p, b, qb)
    h, j = model.invariants(z, p); flow = transfer.rhs(0., z, p, b)
    jdot = np.cross(flow[:3], z[3:6])+np.cross(z[:3], flow[3:6])+flow[6:9]
    assert np.linalg.norm(jdot-np.cross(b.omega, j))/np.linalg.norm(jdot) < 1e-12
    expected = b.clock_acceleration*h+np.asarray(b.basis_acceleration)@j
    assert transfer.explicit_power(z, p, b) == pytest.approx(expected, rel=1e-14)
    wrong = b.clock_rate*h+b.omega@z[6:9]
    assert abs(wrong-transfer.hamiltonian(z, p, b))/abs(transfer.hamiltonian(z, p, b)) > 1e-4
    h0, j0 = transfer.local_invariants(z, p, b)
    assert h0 == pytest.approx(model.invariants(y, p)[0], rel=1e-12)
    assert np.allclose(j0, model.invariants(y, p)[1], rtol=1e-12)


@pytest.mark.parametrize('bad', [True, 0., -1., '1', float('nan'), float('inf')])
def test_bad_clock_rejected(bad):
    b, _ = boundary()
    with pytest.raises(ValueError):
        transfer.Boundary(b.basis, b.basis_derivative, bad, 0., [0., 0., 0.])


def test_metric_root_reflection_nontangent_and_mismatched_quaternion_rejected():
    b, qb = boundary(); p, y = fixture()
    root, _ = local_spin_root(np.diag([-1., 1., 1., 1.]), [.1, .2, .3])
    for matrix, derivative in [(root, np.zeros((3, 3))), (np.diag([1., 1., -1.]), np.zeros((3, 3))),
                               (np.eye(3), np.eye(3))]:
        with pytest.raises(ValueError): transfer.Boundary(matrix, derivative, 1., 0., [0., 0., 0.])
    for q in ([1., 0., 0., 0.], qb*2):
        with pytest.raises(ValueError): transfer.map_state(y, p, b, q)
    with pytest.raises(ValueError): transfer.rhs(0., y, p, None)
    with pytest.raises(ValueError): transfer.map_state(y, p, b, qb, inverse=1)


def test_raw_q_norm_and_sign_are_not_projected_during_mapping():
    p, y = fixture(); b, qb = boundary(); y[9:] *= 1+1e-8
    z = transfer.map_state(y, p, b, qb)
    assert abs(np.linalg.norm(z[9:])-(1+1e-8)) < 1e-15
    assert np.allclose(transfer.map_state(y, p, b, -qb)[9:], -z[9:], rtol=1e-14, atol=0)
    with pytest.raises(ValueError): transfer.from_target_rates(z[:3], np.zeros(3), z[9:], np.zeros(3), p, b)


def test_overflowing_combined_H_flow_and_power_fail_explicitly():
    p, y = fixture()
    b = transfer.Boundary(np.eye(3), np.zeros((3, 3)), 1e308, 1e308, np.zeros(3))
    with np.errstate(over='ignore', invalid='ignore'):
        for operation in (transfer.hamiltonian, transfer.rhs, transfer.explicit_power):
            with pytest.raises(ValueError, match='Nonfinite'):
                if operation is transfer.rhs: operation(0., y, p, b)
                else: operation(y, p, b)
    with pytest.raises(ValueError):
        transfer.from_target_rates(y[:3], np.zeros(3), y[9:], np.zeros(3), None, b)


@pytest.mark.parametrize('acceleration', [True, '0', float('nan'), float('inf')])
def test_invalid_explicit_clock_acceleration_rejected(acceleration):
    with pytest.raises(ValueError):
        transfer.Boundary(np.eye(3), np.zeros((3, 3)), 1., acceleration, np.zeros(3))
