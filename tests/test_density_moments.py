import numpy as np
import pytest

from scripts import density_moments as model
from tests.test_sr_cloud import fixture


def test_density_direct_particle_moments_force_potential_convention():
    cloud = fixture(); m = np.array(cloud.masses); x = np.array(cloud.positions)
    d, c, q = model.mass_moments(m, x)
    direct_c = sum(mm*(xx@xx*np.eye(3)-np.outer(xx, xx)) for mm, xx in zip(m, x))
    assert np.linalg.norm(c-direct_c)/np.linalg.norm(c) < 1e-11
    assert np.linalg.norm(model.density_pair(c, q)-d)/np.linalg.norm(d) < 1e-11
    n = np.array([.2, -.3, .4]); n /= np.linalg.norm(n)
    direct_q = sum(mm*(3*(n@xx)**2-xx@xx)/2 for mm, xx in zip(m, x))
    assert abs(1.5*(n@q@n)-direct_q)/abs(direct_q) < 1e-11


def test_nonorthogonal_image_actual_inertia_not_A_C_Atranspose():
    cloud = fixture(); d, c, q = model.mass_moments(cloud.masses, cloud.positions)
    a = np.array([[1.2, .1, 0.], [0., .9, -.2], [.15, 0., 1.1]])
    image = np.asarray(cloud.positions)@a.T
    di, ci, qi = model.mass_moments(cloud.masses, image)
    expected_d = a@d@a.T
    assert np.linalg.norm(di-expected_d)/np.linalg.norm(di) < 1e-11
    assert np.linalg.norm(ci-(np.trace(expected_d)*np.eye(3)-expected_d))/np.linalg.norm(ci) < 1e-11
    assert np.linalg.norm(ci-a@c@a.T)/np.linalg.norm(ci) > .01
    assert np.linalg.norm(qi-a@q@a.T)/np.linalg.norm(qi) > .01


def test_kinetic_spin_independent_particle_sum_and_not_constant_tensor_for_all_rates():
    cloud = fixture(); x = np.array(cloud.positions); m = np.array(cloud.masses)
    for w in [np.array([.15, -.2, .3]), np.array([-.3, .1, .2])]:
        exact, newton, leading = model.rotation_snapshot_spin(m, x, w, cloud.c)
        u = np.cross(w, x)
        direct = sum(mm*np.cross(xx, uu)/np.sqrt(1-(uu@uu)/cloud.c**2)
                     for mm, xx, uu in zip(m, x, u))
        assert np.linalg.norm(exact-direct)/np.linalg.norm(exact) < 1e-11
        assert np.linalg.norm(exact-newton)/np.linalg.norm(exact) > 1e-6
        assert np.linalg.norm(exact-leading) < np.linalg.norm(exact-newton)
    small = np.array([.15, -.2, .3]); twice = model.rotation_snapshot_spin(m, x, 2*small, cloud.c)[0]
    once = model.rotation_snapshot_spin(m, x, small, cloud.c)[0]
    assert np.linalg.norm(twice-2*once)/np.linalg.norm(twice) > 1e-6


@pytest.mark.parametrize('c,q', [(np.diag([10., 1., 1.]), np.diag([-6., 3., 3.])),
                               (np.diag([2., 3., 4.]), np.zeros((3, 3))),
                               (np.eye(3), np.eye(3)),
                               (np.full((3, 3), np.nan), np.zeros((3, 3)))])
def test_incompatible_or_nonrealizable_density_rejected(c, q):
    with pytest.raises(ValueError): model.density_pair(c, q)


def test_bad_masses_speeds_and_overflow_rejected():
    with pytest.raises(ValueError): model.mass_moments([-1.], [[1., 2., 3.]])
    with pytest.raises(ValueError): model.mass_moments([1e300], [[1e200, 0., 0.]])
    with pytest.raises(ValueError): model.rotation_snapshot_spin([1.], [[1., 0., 0.]], [0., 0., 5e4], 5e4)
