import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts import local_multipole as model
from scripts.independent_local_multipole import gradients, scalar
from solar_simulator.rotation import RigidFigure, pair_field
from solar_simulator.simulation import G


def fixture():
    c = np.diag([2e20, 2.5e20, 3e20])
    u = Rotation.from_rotvec([.4, -.3, .2]).as_matrix()
    m = u@np.diag([4e19, -1e19, -3e19])@u.T
    parameters = model.Parameters(1e15, 2e14, G, c, m, 1000.)
    q = np.roll(Rotation.from_rotvec([.3, -.2, .4]).as_quat(), 1)
    y = np.r_[[12000., -8000., 5000.], [1e14, 2e14, -5e13],
              [1e17, -2e17, 4e17], q]
    return parameters, y


def test_independent_scalar_derivatives_energy_J_and_misaligned_C_M():
    p, y = fixture(); _, r, c, m, w, force, torque, _ = model.fields(y, p)
    gradient, angles = gradients(y[:9], r, p); gx, gp, gs = gradient.reshape(3, 3)
    assert abs(model.hamiltonian(y, p)/scalar(y[:9], r, p)-1) < 1e-12
    assert np.linalg.norm(gx+force)/np.linalg.norm(force) < 1e-11
    assert np.linalg.norm(gs-w)/np.linalg.norm(w) < 1e-11
    assert np.linalg.norm(np.cross(gs, y[6:9])-angles-torque)/np.linalg.norm(torque) < 1e-11
    assert np.linalg.norm(np.cross(y[:3], force)+torque)/np.linalg.norm(torque) < 1e-12
    dh = gradient@model.rhs(0., y, p)[:9]+angles@w
    scale = abs(force@gp)+abs(torque@w)
    assert abs(dh)/scale < 1e-11
    assert np.linalg.norm(c@m-m@c) > 0
    assert not np.array_equal(model.rhs(0., y, p)[6:9], np.zeros(3))


def test_Newton_density_identity_matches_original_SI_MacCullagh():
    p, y = fixture(); c = np.asarray(p.inertia_body)
    m = np.trace(c)/3*np.eye(3)-c
    p = model.Parameters(p.figure_mass, p.point_mass, G, c, m, 1000.)
    body = RigidFigure(p.figure_mass, tuple(np.diag(c)), 1000.)
    potential, force, torque = pair_field(body, p.point_mass, y[:3], y[9:])
    actual = model.fields(y, p)
    assert abs(actual[-1]/potential-1) < 1e-12
    assert np.linalg.norm(actual[5]-force)/np.linalg.norm(force) < 1e-12
    assert np.linalg.norm(actual[6]-torque)/np.linalg.norm(torque) < 1e-12


@pytest.mark.parametrize('bad', [True, 0., -1., '1', float('nan'), float('inf')])
def test_invalid_SI_parameters_rejected(bad):
    p, _ = fixture()
    with pytest.raises(ValueError):
        model.Parameters(bad, p.point_mass, G, p.inertia_body, p.multipole_body, 1000.)


@pytest.mark.parametrize('which, tensor', [
    ('inertia', np.diag([1., 0., 2.])), ('inertia', np.diag([1., -1., 2.])),
    ('inertia', [[1., 1., 0.], [0., 1., 0.], [0., 0., 1.]]),
    ('multipole', np.eye(3)), ('multipole', np.full((3, 3), np.nan)),
    ('multipole', np.ones((2, 2)))])
def test_invalid_tensors_rejected(which, tensor):
    p, _ = fixture(); c = tensor if which == 'inertia' else p.inertia_body
    m = tensor if which == 'multipole' else p.multipole_body
    with pytest.raises(ValueError):
        model.Parameters(p.figure_mass, p.point_mass, G, c, m, 1000.)


def test_domain_raw_quaternion_and_parameter_immutability():
    p, y = fixture(); original = y.copy(); y[-1] = -0.
    raw = y[9:].copy(); model.fields(y, p)
    assert np.array_equal(y[9:].view(np.uint64), raw.view(np.uint64))
    with pytest.raises(ValueError): model.validate_initial(y, p)
    for change in ('distance', 'quaternion', 'nan'):
        bad = original.copy()
        if change == 'distance': bad[:3] = [1000., 0., 0.]
        if change == 'quaternion': bad[9:] = 0.
        if change == 'nan': bad[2] = np.nan
        with pytest.raises(ValueError): model.fields(bad, p)
    with pytest.raises(ValueError): model.fields(original[:-1], p)
    with pytest.raises(ValueError): model.fields(original, None)
    c = np.asarray(p.inertia_body).copy(); expected = c.copy()
    immutable = model.Parameters(p.figure_mass, p.point_mass, G, c, p.multipole_body, 1000.)
    c[0, 0] *= 2
    assert np.array_equal(immutable.inertia_body, expected)


def test_monopole_spherical_free_spin_and_q_sign_limit():
    p, y = fixture()
    p = model.Parameters(p.figure_mass, p.point_mass, G, 2e20*np.eye(3), np.zeros((3, 3)), 1000.)
    flow = model.rhs(0., y, p)
    assert np.array_equal(flow[6:9], np.zeros(3))
    opposite = y.copy(); opposite[9:] *= -1
    assert model.hamiltonian(opposite, p) == model.hamiltonian(y, p)
    assert np.allclose(model.rhs(0., opposite, p)[9:], -flow[9:], rtol=1e-14, atol=0)
