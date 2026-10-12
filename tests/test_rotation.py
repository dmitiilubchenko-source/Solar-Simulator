import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from solar_simulator.rotation import (RigidFigure, angular_velocity, integrate,
    invariants, pair_field, pair_rhs, quaternion_rate, rotation_matrix)
from solar_simulator.simulation import G


def figure():
    return RigidFigure(1e15, (2e20, 2.5e20, 3e20), 1000.)


def quaternion(rotvec):
    return np.roll(Rotation.from_rotvec(rotvec).as_quat(), 1)


def test_mac_cullagh_force_torque_and_energy_derivatives():
    body, mass = figure(), 2e14
    r = np.array([12000., -8000., 5000.])
    q = quaternion([.3, -.2, .4])
    matrix = Rotation.from_quat(np.roll(q, -1)).as_matrix()
    inertia = matrix@np.diag(body.moments)@matrix.T

    def potential(displacement, rotation):
        n = displacement/np.linalg.norm(displacement)
        tensor = rotation@np.diag(body.moments)@rotation.T
        return (-G*body.mass*mass/np.linalg.norm(displacement)
            +G*mass*(3*n@tensor@n-np.trace(tensor))/(2*np.linalg.norm(displacement)**3))

    u, force, torque = pair_field(body, mass, r, q)
    assert u == pytest.approx(potential(r, matrix), rel=1e-14)
    h = .1
    gradient = np.array([(potential(r+h*axis, matrix)-potential(r-h*axis, matrix))/(2*h)
                          for axis in np.eye(3)])
    assert np.linalg.norm(force+gradient)/np.linalg.norm(force) < 1e-6
    angle = 1e-4
    orientation_gradient = np.array([(potential(r, Rotation.from_rotvec(angle*axis).as_matrix()@matrix)
        -potential(r, Rotation.from_rotvec(-angle*axis).as_matrix()@matrix))/(2*angle) for axis in np.eye(3)])
    assert np.linalg.norm(torque+orientation_gradient)/np.linalg.norm(torque) < 1e-6
    inertia_torque = 3*G*mass/np.linalg.norm(r)**3*np.cross(r/np.linalg.norm(r), inertia@(r/np.linalg.norm(r)))
    assert np.linalg.norm(torque-inertia_torque)/np.linalg.norm(torque) < 1e-14
    assert np.linalg.norm(np.cross(r, force)+torque) < np.linalg.norm(torque)*1e-12
    # Direct derivative of full H along coupled RHS, not only potential.
    state = np.concatenate((r, [1., 2., -.5], q, [1e17, -2e17, 4e17]))
    rate = pair_rhs(body, mass, state)
    dt = .01
    energy_rate = (invariants(body, state+dt*rate, mass)[0]-invariants(body, state-dt*rate, mass)[0])/(2*dt)
    work_scale = abs(force@state[3:6])+abs(torque@angular_velocity(body, q, state[10:]))
    assert abs(energy_rate)/work_scale < 1e-6


def test_mass_distribution_independent_far_field_limit():
    # Six equal masses at +/- axes. Direct Newtonian sum gives an independent
    # potential/force/torque; Q2 errors must fall as (size/distance)^2 relative
    # to the nonspherical contribution (next surviving even moment is order 4).
    points = np.concatenate((np.diag([600., 450., 300.]), -np.diag([600., 450., 300.])))
    mass, target = 1e15, 2e14
    second = mass/6*(points.T@points)
    moments = np.trace(second)-np.diag(second)
    body = RigidFigure(mass, tuple(moments), 600.)
    q = quaternion([.3, -.2, .4])
    rotation = Rotation.from_quat(np.roll(q, -1)).as_matrix()
    points = points@rotation.T
    errors = []
    for distance in [6000., 12000., 24000., 48000.]:
        r = distance*np.array([.8, .48, .36])  # unit vector
        deltas = r-points
        lengths = np.linalg.norm(deltas, axis=1)
        forces = G*(mass/6)*target*deltas/lengths[:, None]**3  # on source elements
        exact_u = -G*(mass/6)*target*np.sum(1/lengths)
        exact_f, exact_t = -np.sum(forces, axis=0), np.sum(np.cross(points, forces), axis=0)
        u, f, torque = pair_field(body, target, r, q)
        monopole = -G*mass*target/distance
        correction = f+G*mass*target*r/distance**3
        errors.append([abs(u-exact_u)/abs(u-monopole),
            np.linalg.norm(f-exact_f)/np.linalg.norm(correction),
            np.linalg.norm(torque-exact_t)/np.linalg.norm(torque)])
    errors = np.array(errors)
    assert np.all(errors[1:] < errors[:-1]*.3)
    # Original 40-radius check failed; keep this limit visible instead of
    # claiming the Q2 approximation is accurate to 0.2% at that separation.
    assert errors[2, 2] > .002
    assert np.max(errors[-1]) < .002


def test_rotation_covariance_and_quaternion_sign():
    body, mass = figure(), 2e14
    r, q = np.array([12000., -8000., 5000.]), quaternion([.3, -.2, .4])
    u, f, torque = pair_field(body, mass, r, q)
    frame = Rotation.from_rotvec([-.5, .6, .2])
    transformed_q = np.roll((frame*Rotation.from_quat(np.roll(q, -1))).as_quat(), 1)
    u2, f2, t2 = pair_field(body, mass, frame.apply(r), transformed_q)
    assert u2 == pytest.approx(u, rel=1e-14)
    assert np.allclose(f2, frame.apply(f), rtol=1e-13)
    assert np.allclose(t2, frame.apply(torque), rtol=1e-13)
    assert np.allclose(rotation_matrix(q), rotation_matrix(-q), atol=1e-15)


def test_spherical_body_analytic_rotation_and_zero_q2():
    body = RigidFigure(1e15, (2e20,)*3, 1000.)
    omega = np.array([.2, -.1, .3])
    initial = np.concatenate(([1., 0., 0., 0.], omega*2e20))
    times = np.linspace(0, 100, 101)
    states = integrate(body, initial, times, rtol=1e-12, atol=1e-13, max_step=1.)
    expected = Rotation.from_rotvec(times[:, None]*omega).as_matrix()
    measured = np.array([rotation_matrix(y[:4]) for y in states])
    assert np.max(abs(expected-measured)) < 1e-10
    assert np.array_equal(body.quadrupole, np.zeros((3, 3)))
    assert np.array_equal(pair_field(body, 2e14, [12000, 0, 0], initial[:4])[2], np.zeros(3))


def test_pair_restart_and_time_reversal():
    body, mass = figure(), 2e14
    q = quaternion([.3, -.2, .4])
    initial = np.concatenate(([12000., 0., 0.], [0., 2., .2], q, [1e17, -2e17, 4e17]))
    times = np.linspace(0, 2000, 21)
    kwargs = dict(point_mass=mass, rtol=1e-12, atol=1e-13, max_step=50.)
    whole = integrate(body, initial, times, **kwargs)
    checkpoint = whole[10].copy()
    # Input API rejects a nonunit q: explicitly choose its equivalent unit
    # representative at restart, measure the original norm in the audit.
    checkpoint[6:10] /= np.linalg.norm(checkpoint[6:10])
    resumed = integrate(body, checkpoint, times[10:], **kwargs)
    assert np.allclose(resumed[-1], whole[-1], rtol=1e-10, atol=1e-8)
    end = whole[-1].copy()
    end[6:10] /= np.linalg.norm(end[6:10])
    end[3:6] *= -1
    end[10:] *= -1
    reversed_state = integrate(body, end, times, **kwargs)[-1]
    assert np.linalg.norm(reversed_state[:3]-initial[:3]) < 1e-7
    assert np.linalg.norm(rotation_matrix(reversed_state[6:10])-rotation_matrix(initial[6:10])) < 1e-10


@pytest.mark.parametrize("moments", [(1., 1., 3.), (0., 1., 1.), (float("nan"), 1., 1.), (1e22,)*3])
def test_invalid_inertia_rejected(moments):
    with pytest.raises(ValueError):
        RigidFigure(1e15, moments, 1000.)


def test_invalid_domain_and_initial_attitude_rejected():
    body = figure()
    with pytest.raises(ValueError):
        pair_field(body, 1., [999., 0., 0.], [1., 0., 0., 0.])
    with pytest.raises(ValueError):
        pair_field(body, -1., [12000., 0., 0.], [1., 0., 0., 0.])
    with pytest.raises(ValueError):
        integrate(body, [2., 0., 0., 0., 1., 2., 3.], [0., 1.])
    assert np.dot([1., 0., 0., 0.], quaternion_rate([1., 0., 0., 0.], np.ones(3))) == 0
