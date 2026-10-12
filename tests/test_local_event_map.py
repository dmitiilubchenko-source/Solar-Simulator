import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts import local_event_map as model
from scripts.external_metric import Sources, leading_clock


def hat(v):
    x, y, z = v
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def fixture():
    basis = Rotation.from_rotvec([.2, -.4, .1]).as_matrix()
    omega = np.array([.002, -.001, .003])
    jet = model.Jet(12., 11.9, [1e5, -2e5, 3e5], [100., -200., 300.],
        [.02, -.03, .01], [.001, -.002, .003], 3e5, 12., basis, hat(omega)@basis, 5e4)
    return jet, np.asarray(jet.position)+[1000., -2500., 1400.], omega


def independent_event(x, dt, jet, omega):
    # Differentiate the scalar/polynomial coordinate definition directly.
    v0 = np.array(jet.velocity); a0 = np.array(jet.acceleration); j0 = np.array(jet.jerk)
    centre = np.array(jet.position)+v0*dt+.5*a0*dt**2+j0*dt**3/6
    v = v0+a0*dt+.5*j0*dt**2; a = a0+j0*dt
    u = jet.potential+jet.potential_rate*dt; r = x-centre
    basis = (np.eye(3)+dt*hat(omega))@jet.basis
    local_time = jet.local_epoch+jet.centre_clock_rate*dt-v@r/jet.c**2
    spatial = basis@(r+(.5*v*(v@r)+u*r+r*(a@r)-.5*a*(r@r))/jet.c**2)
    return np.r_[local_time, spatial]


def test_four_blocks_against_independent_complex_step_and_velocity_inverse():
    jet, x, omega = fixture(); out = model.event(x, jet); step = 1e-20
    time_derivative = independent_event(x, 1j*step, jet, omega).imag/step
    spatial = np.array([independent_event(x+1j*step*axis, 0., jet, omega).imag/step
                        for axis in np.eye(3)]).T
    for actual, expected in [(out.time_t, time_derivative[0]),
                             (out.position_t, time_derivative[1:]),
                             (out.time_x, spatial[0]), (out.position_x, spatial[1:])]:
        assert np.linalg.norm(actual-expected)/np.linalg.norm(expected) < 1e-11
    vg = np.array([120., -160., 330.]); local, rate = model.velocity(x, vg, jet)
    material = independent_event(x+vg*1j*step, 1j*step, jet, omega).imag/step
    assert rate == pytest.approx(material[0], rel=1e-11)
    assert np.linalg.norm(local-material[1:]/material[0])/np.linalg.norm(local) < 1e-11
    assert np.linalg.norm(model.inverse_velocity(x, local, jet)-vg)/np.linalg.norm(vg) < 1e-11
    jac = out.jacobian_ct(jet.c)
    assert jac.shape == (4, 4)
    assert np.allclose(jac[0, 1:], jet.c*out.time_x, rtol=1e-14)


def test_central_clock_from_sources_and_translation():
    sources = Sources([1e12], [[2e6, -1e6, 3e6]], [[10., -5., 7.]], [[0., 0., 0.]], 5e4)
    x = np.array([1e5, 2e5, -3e5]); v = np.array([100., -200., 300.]); a = np.array([.01, .02, -.03])
    jet = model.from_sources(12., 11.8, x, v, a, [0., 0., 0.], np.eye(3), np.zeros((3, 3)), sources)
    out = model.event(x, jet); local, rate = model.velocity(x, v, jet)
    assert rate == pytest.approx(leading_clock(x, v, a, sources)[0], rel=1e-13)
    assert out.local_time == jet.local_epoch and not np.any(out.local_position)
    assert np.linalg.norm(local) < 1e-13
    offset = np.array([1e8, -2e8, 3e8])
    translated = model.Jet(jet.global_epoch, jet.local_epoch, x+offset, v, a, jet.jerk,
                          jet.potential, jet.potential_rate, jet.basis, jet.basis_derivative, jet.c)
    assert np.allclose(model.event(x+[1000., -3000., 2000.], jet).local_position,
                       model.event(x+offset+[1000., -3000., 2000.], translated).local_position, rtol=1e-12)


def test_flat_rest_empty_limit_and_spatial_strain_not_attitude_rotation():
    jet = model.Jet(0., 0., [0., 0., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 0.],
                    0., 0., np.eye(3), np.zeros((3, 3)), 5e4)
    out = model.event([1., 2., 3.], jet)
    assert np.array_equal(out.jacobian_ct(jet.c), np.eye(4))
    assert np.array_equal(model.velocity([1., 2., 3.], [4., 5., 6.], jet)[0], [4., 5., 6.])
    moving, x, _ = fixture(); out = model.event(x, moving)
    assert np.linalg.norm(out.position_x.T@out.position_x-np.eye(3)) > 1e-4
    assert out.local_time != moving.local_epoch


@pytest.mark.parametrize('changes', [dict(local_epoch=True), dict(potential=-1.),
                                   dict(potential=float('nan')), dict(potential_rate='1'),
                                   dict(velocity=[2e4, 0., 0.]), dict(jerk=[0., np.inf, 0.]),
                                   dict(basis=np.diag([1., 1., -1.])),
                                   dict(basis_derivative=np.eye(3)), dict(c=0.)])
def test_invalid_jets_rejected(changes):
    jet, _, _ = fixture(); data = dict(jet.__dict__); data.update(changes)
    with pytest.raises(ValueError): model.Jet(**data)


def test_acceleration_extent_and_non_timelike_material_rejected():
    jet, x, _ = fixture()
    with pytest.raises(ValueError, match='extent'): model.event(x+np.array([1e10, 0., 0.]), jet)
    with pytest.raises(ValueError, match='Timelike'): model.velocity(x, [jet.c, 0., 0.], jet)
    with pytest.raises(ValueError): model.event(x, None)
