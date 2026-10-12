import numpy as np
import pytest

from scripts import sr_cloud as model
from scripts.canonical_initial import local_spin_root


def fixture(c=5e4):
    x = np.array([[1200., 300., -200.], [-900., 1100., 400.], [400., -600., 1400.]])
    m = np.array([2., 3., 4.]); omega = np.array([.15, -.2, .3])
    u = np.cross(omega, x)
    return model.RestCloud(np.repeat(m, 2), np.stack([x, -x], axis=1).reshape(-1, 3),
                           np.stack([u, -u], axis=1).reshape(-1, 3), c)


def test_boost_lorentz_metric_inverse_zero_and_rest_motion():
    v = np.array([300., -400., 500.]); c = 5e4; l = model.boost(v, c)
    assert np.linalg.norm(l.T@model.ETA@l-model.ETA) < 1e-12
    assert np.linalg.norm(model.boost(-v, c)@l-np.eye(4)) < 1e-12
    assert np.array_equal(model.boost(np.zeros(3), c), np.eye(4))
    rest = np.array([c*2., 0., 0., 0.]); moving = l@rest
    assert np.allclose(c*moving[1:]/moving[0], v, rtol=1e-13)


def test_equal_time_charges_spin_centres_and_metric_root():
    cloud = fixture(); c = cloud.c; v = np.array([300., -400., 500.]); t = 2.
    zero = np.c_[np.zeros(len(cloud.masses)), cloud.positions]
    p0, j0, _ = model.charges(zero, cloud.momenta)
    spin = model.spatial_angular(j0); matrix = model.boost(v, c); gamma = matrix[0, 0]
    events, momenta, local_times = model.snapshot(t, v, cloud)
    p, j, ze = model.charges(events, momenta)
    assert np.max(abs(events[:, 0]/c-t)) < 1e-12
    local_positions = np.asarray(cloud.positions)+np.asarray(cloud.velocities)*local_times[:, None]
    # At fixed global t, DeltaT = -V.DeltaX/c². No assumed millisecond gap.
    delta_t = local_times-local_times[0]
    delta_x = local_positions-local_positions[0]
    assert np.linalg.norm(delta_t+delta_x@v/c**2)/np.linalg.norm(delta_t) < 1e-11
    assert np.linalg.norm(p-matrix@p0)/np.linalg.norm(p0) < 1e-11
    assert np.linalg.norm(j-matrix@j0@matrix.T)/np.linalg.norm(j0) < 1e-11
    e0 = c*p0[0]; centre = v*t
    assert np.linalg.norm(ze-centre-np.cross(v, spin)/e0)/np.linalg.norm(ze-centre) < 1e-11
    js = model.about_centre(j, p, np.r_[c*t, centre])
    assert np.linalg.norm(js@(model.ETA@p))/(np.linalg.norm(js)*np.linalg.norm(p)) < 1e-11
    je = model.about_centre(j, p, np.r_[c*t, ze])
    assert np.linalg.norm(je[0])/np.linalg.norm(j0) < 1e-11
    parallel = v*(v@spin)/(v@v); perpendicular = spin-parallel
    assert np.linalg.norm(model.spatial_angular(js)-(parallel+gamma*perpendicular))/np.linalg.norm(spin) < 1e-11
    assert np.linalg.norm(model.spatial_angular(je)-(parallel+perpendicular/gamma))/np.linalg.norm(spin) < 1e-11
    spin4 = model.spin_vector(p, js)
    assert np.linalg.norm(spin4-matrix@np.r_[0., spin])/np.linalg.norm(spin) < 1e-11
    assert abs(spin4@model.ETA@p)/(np.linalg.norm(spin4)*np.linalg.norm(p)) < 1e-11
    root, _ = local_spin_root(model.ETA, v/c)
    assert np.linalg.norm(root@spin4[1:]-spin)/np.linalg.norm(spin) < 1e-11
    assert np.linalg.norm(model.spin_vector(p, je)-spin4)/np.linalg.norm(spin) < 1e-11


def test_free_cloud_conservation_during_expansion_and_signed_initial_input():
    cloud = fixture(); v = np.array([300., -400., 500.]); results = []
    for t in [-2., 0., 10.]:
        events, momenta, _ = model.snapshot(t, v, cloud)
        results.append(model.charges(events, momenta)[:2])
    for p, j in results[1:]:
        assert np.linalg.norm(p-results[0][0])/np.linalg.norm(p) < 1e-12
        assert np.linalg.norm(j-results[0][1])/np.linalg.norm(j) < 1e-11
    assert np.linalg.norm(np.asarray(cloud.velocities)) > 0


@pytest.mark.parametrize('bad', [dict(masses=[-1., 1.]),
                               dict(velocities=[[5e4, 0., 0.], [-5e4, 0., 0.]]),
                               dict(velocities=[[1., 0., 0.], [0., 0., 0.]]),
                               dict(positions=[[1., 0., 0.], [0., 0., 0.]]),
                               dict(positions=[[np.nan, 0., 0.], [-1., 0., 0.]]), dict(c=True)])
def test_nonphysical_or_nonrest_cloud_rejected(bad):
    args = dict(masses=[1., 1.], positions=[[1., 0., 0.], [-1., 0., 0.]],
                velocities=[[0., 1., 0.], [0., -1., 0.]], c=5e4); args.update(bad)
    with pytest.raises(ValueError): model.RestCloud(**args)


def test_invalid_boost_spacelike_spin_and_asymmetric_tensor_rejected():
    with pytest.raises(ValueError): model.boost([5e4, 0., 0.], 5e4)
    with pytest.raises(ValueError): model.spin_vector([1., 2., 0., 0.], np.zeros((4, 4)))
    with pytest.raises(ValueError): model.spin_vector([1., 0., 0., 0.], np.eye(4))
    with pytest.raises(ValueError): model.snapshot(0., [0., 0., 0.], None)
