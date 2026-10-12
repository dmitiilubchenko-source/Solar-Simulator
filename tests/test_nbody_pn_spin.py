"""N-body primary-action oracle, binary limit, symmetries and retained order."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.nbody_pn_spin import Parameters, geometry, hamiltonian, rhs
from scripts.independent_nbody_pn_spin import original_hamiltonian, gradient
from scripts.pn_spin_model import Parameters as Binary, hamiltonian as binary_h, rhs as binary_rhs
from solar_simulator.relativity import eih_acceleration
from solar_simulator.simulation import G


P = Parameters((.3, .7, .05), float(np.sqrt(1e5)))
Y = np.array([[[.56, 0., 0.], [-.24, 0., 0.], [3.5, .4, .6]],
              [[0., .257, 0.], [0., -.257, 0.], [-.003, .025, .004]],
              [[.003, -.004, .002], [-.002, .001, .003], [.0002, .0003, -.0001]]]).ravel()


def test_nbody_primary_action_hamiltonian_and_derivatives():
    rng = np.random.default_rng(56)
    for _ in range(12):
        y = Y.reshape(3, 3, 3).copy()
        y[0] += rng.normal(size=(3, 3))*.05
        y[1] += rng.normal(size=(3, 3))*.005
        y[2] += rng.normal(size=(3, 3))*.0001
        y = y.ravel()
        assert hamiltonian(y, P) == pytest.approx(original_hamiltonian(y, P.masses, P.c), rel=3e-15)
        gx, gp, gs = gradient(y, P.masses, P.c).reshape(3, 3, 3)
        expected = np.stack([gp, -gx, np.cross(gs, y.reshape(3, 3, 3)[2])])
        actual = rhs(0, y, P).reshape(3, 3, 3)
        assert np.max(np.linalg.norm(actual-expected, axis=-1)/np.linalg.norm(expected, axis=-1)) < 1e-11


def test_binary_COM_limit_matches_previously_independent_model():
    r = np.array([.8, .1, -.05]); p = np.array([.01, .257, .005]); s = np.array([.003, -.004, .002])
    y = np.array([[.7*r, -.3*r], [p, -p], [s, np.zeros(3)]]).ravel()
    params = Parameters((.3, .7), P.c); binary = Binary(.3, .7, P.c)
    assert hamiltonian(y, params) == pytest.approx(binary_h(np.r_[r, p, s], binary), rel=3e-15)
    dx, dp, ds = rhs(0, y, params).reshape(3, 2, 3)
    assert np.linalg.norm(np.r_[dx[0]-dx[1], dp[0], ds[0]]-binary_rhs(0, np.r_[r, p, s], binary)) < 3e-16
    assert np.linalg.norm(dp.sum(axis=0)) < 1e-16
    assert np.array_equal(ds[1], np.zeros(3))


def test_noether_derivatives_and_missing_reaction_negative_control():
    x, p, s = Y.reshape(3, 3, 3)
    dx, dp, ds = rhs(0, Y, P).reshape(3, 3, 3)
    assert np.linalg.norm(ds) > 1e-8
    assert np.linalg.norm(dp.sum(axis=0)) < 1e-16
    assert np.linalg.norm((np.cross(dx, p)+np.cross(x, dp)+ds).sum(axis=0)) < 2e-16
    assert abs(np.dot(gradient(Y, P.masses, P.c), rhs(0, Y, P))) < 1e-15
    assert np.max(abs(np.sum(s*ds, axis=1))) < 1e-21
    wrong = rhs(0, Y, P, spin_orbit=False).reshape(3, 3, 3)
    wrong[2] = ds
    assert np.linalg.norm((np.cross(wrong[0], p)+np.cross(x, wrong[1])+ds).sum(axis=0)) > 1e-8


def test_distinct_triples_are_resolved_and_not_a_binary_sum():
    complete = original_hamiltonian(Y, P.masses, P.c)
    missing = original_hamiltonian(Y, P.masses, P.c, omit_distinct_triples=True)
    x = Y.reshape(3, 3, 3)[0]; expected = 0.
    for i in range(3):
        j, k = [a for a in range(3) if a != i]
        expected += np.prod(P.masses)/(P.c**2*np.linalg.norm(x[i]-x[j])*np.linalg.norm(x[i]-x[k]))
    assert complete-missing == pytest.approx(expected, rel=1e-9)
    assert expected > 1e-8
    g = gradient(Y, P.masses, P.c)
    bad = gradient(Y, P.masses, P.c, omit_distinct_triples=True)
    assert np.linalg.norm(g[:9]-bad[:9])/np.linalg.norm(g[:9]) > 1e-7


def test_fixed_frame_symmetries_permutations_and_newton_limit():
    a = Y.reshape(3, 3, 3); field = rhs(0, Y, P).reshape(3, 3, 3)
    matrix = Rotation.from_rotvec([.3, -.4, .2]).as_matrix()
    rotated = a@matrix.T
    assert np.linalg.norm(rhs(0, rotated.ravel(), P).reshape(3, 3, 3)-field@matrix.T) < 3e-16
    shifted = a.copy(); shifted[0] += [2., -3., 1.]
    assert np.linalg.norm(rhs(0, shifted.ravel(), P)-field.ravel()) < 6e-16
    order = [2, 0, 1]; params = Parameters(tuple(P.masses[i] for i in order), P.c)
    assert np.linalg.norm(rhs(0, a[:, order].ravel(), params).reshape(3, 3, 3)-field[:, order]) < 3e-16
    signs = np.array([1., -1., -1.])[:, None, None]
    assert np.linalg.norm(rhs(0, (a*signs).ravel(), P).reshape(3, 3, 3)+field*signs) < 1e-16
    newton = rhs(0, Y, Parameters(P.masses, 1e100)).reshape(3, 3, 3)
    assert np.allclose(newton[0], a[1]/np.array(P.masses)[:, None], rtol=0, atol=1e-16)
    assert np.allclose(newton[1]/np.array(P.masses)[:, None],
                       eih_acceleration(a[0], newton[0], np.array(P.masses)/G, c=1e100), rtol=1e-15, atol=1e-16)
    assert np.linalg.norm(newton[2]) < 1e-190


def test_three_body_spinless_acceleration_matches_EIH_through_1PN():
    y = Y.copy(); y[18:] = 0.; errors = []
    for c in [float(np.sqrt(5e4)), float(np.sqrt(1e5))]:
        params = Parameters(P.masses, c); flow = rhs(0, y, params); h = 1e-3
        velocity = lambda step: rhs(0, y+step*flow, params)[:9].reshape(3, 3)
        accel = (velocity(-2*h)-8*velocity(-h)+8*velocity(h)-velocity(2*h))/(12*h)
        reference = eih_acceleration(y[:9].reshape(3, 3), velocity(0), np.array(P.masses)/G, c=c)
        errors.append(np.linalg.norm(accel-reference))
    assert 3.8 < errors[0]/errors[1] < 4.2
    assert errors[0] < 1e-7


@pytest.mark.parametrize('fault', ['shape', 'nan', 'contact', 'field', 'spin'])
def test_explicit_research_domain_rejection(fault):
    y = Y.copy()
    if fault == 'shape': y = y[:-1]
    if fault == 'nan': y[0] = np.nan
    if fault == 'contact': y[3:6] = y[:3]
    if fault == 'field': y[9] = 100.
    if fault == 'spin': y[18] = 100.
    with pytest.raises(ValueError): geometry(y, P)


@pytest.mark.parametrize('masses,c', [((.3, 0.), 1000.), ((.3, float('inf')), 1000.),
                                    ((.3,), 1000.), ((.3, .7), 0.), ((.3, .7), float('nan'))])
def test_parameter_rejection(masses, c):
    with pytest.raises(ValueError): Parameters(masses, c)


def test_audit_comparison_retains_each_body_and_rejects_invalid_arrays():
    from scripts.assess_nbody_pn_spin import difference
    scales = np.array([[1., 1., 1e9], [1., 1., 1.], [.01, .01, .01]])
    first = np.tile(Y, (2, 1)); second = first.copy(); second[1, 0] += 1e-4
    result = difference(first, second, scales)
    assert result['maximum'] == pytest.approx(1e-4)
    assert result['per_block_body'][0][0] == pytest.approx(1e-4)
    second[0, 0] = np.nan
    with pytest.raises(ValueError): difference(first, second, scales)
    with pytest.raises(ValueError): difference(first, first[:1], scales)
    scales[0, 0] = 0.
    with pytest.raises(ValueError): difference(first, first, scales)
