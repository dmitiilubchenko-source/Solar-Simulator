import numpy as np
import pytest

from scripts.canonical_initial import local_spin_root
from scripts.external_metric import Sources, weak_metric
from scripts.metric_spin_transport import Metric, christoffel, root_rate, transport


def sample():
    rng = np.random.default_rng(756)
    a = rng.normal(size=(4, 4))*.005
    g = np.diag([-1., 1., 1., 1.])+a+a.T
    dg = rng.normal(size=(4, 4, 4))*.0003
    return Metric(g, dg+dg.transpose(0, 2, 1))


def independent_connection(metric):
    # Explicit tensor formula, independent index contractions.
    g = np.asarray(metric.covariant); dg = np.asarray(metric.derivative)
    inv = np.linalg.inv(g); out = np.zeros((4, 4, 4))
    for upper in range(4):
        for first in range(4):
            for second in range(4):
                for last in range(4):
                    out[upper, first, second] += inv[upper, last]*(
                        dg[first, last, second]+dg[second, last, first]-dg[last, first, second])/2
    return out


def test_connection_metric_compatibility_and_full_covector_transport():
    metric = sample(); v = np.array([1., -2., 3.]); c = 30.
    gamma = christoffel(metric); independent = independent_connection(metric)
    assert np.linalg.norm(gamma-independent)/np.linalg.norm(independent) < 1e-12
    g = np.asarray(metric.covariant); dg = np.asarray(metric.derivative)
    for index in range(4):
        assert np.linalg.norm(dg[index]-gamma[:, index, :].T@g-g@gamma[:, index, :])/np.linalg.norm(dg[index]) < 1e-12
    out = transport(metric, v, c); beta = v/c; tangent = np.r_[1., beta]
    lower_spin = np.array([.2, -.5, .7]); spin4 = np.r_[-beta@lower_spin, lower_spin]
    spin_dot = c*np.einsum('nmr,n,r->m', independent, spin4, tangent)
    assert np.linalg.norm(out.covariant_generator@lower_spin-spin_dot[1:]) < 1e-12
    assert abs(spin_dot[0]+beta@spin_dot[1:]+out.acceleration@lower_spin/c) < 1e-12
    euclidean = out.root@lower_spin
    direct = out.root_derivative@lower_spin+out.root@spin_dot[1:]
    assert np.linalg.norm(out.generator@euclidean-direct) < 1e-12
    assert abs(euclidean@direct) < 1e-11
    assert out.symmetry_defect < 1e-10
    assert np.linalg.norm(out.generator@euclidean-np.cross(out.omega, euclidean)) < 1e-11
    assert out.proper_rate == pytest.approx(np.sqrt(-tangent@g@tangent), rel=1e-14)


def test_sylvester_root_derivative_against_independent_difference():
    metric = sample(); inv = np.linalg.inv(metric.covariant)
    dinv = np.asarray(metric.derivative)[2]; beta = np.array([.1, -.2, .05])
    dbeta = np.array([.002, -.001, .003])
    h, dh, spin_metric, dspin = root_rate(inv, dinv, beta, dbeta)
    step = 1e-4
    plus = local_spin_root(inv+step*dinv, beta+step*dbeta)[0]
    minus = local_spin_root(inv-step*dinv, beta-step*dbeta)[0]
    difference = (plus-minus)/(2*step)
    assert np.linalg.norm(dh-difference)/np.linalg.norm(dh) < 1e-7
    assert np.linalg.norm(h@dh+dh@h-dspin)/np.linalg.norm(dspin) < 1e-11
    assert np.linalg.norm(h@h-spin_metric) < 1e-12


def test_flat_boost_zero_connection_and_no_attitude_root():
    metric = Metric(np.diag([-1., 1., 1., 1.]), np.zeros((4, 4, 4)))
    out = transport(metric, [12., -4., 5.], 30.)
    assert not np.any(out.acceleration) and not np.any(out.generator)
    assert not np.any(out.root_derivative) and out.symmetry_defect == 0.
    assert np.linalg.norm(out.root.T@out.root-np.eye(3)) > .1


def test_accelerating_moving_external_metric_and_wrong_newton_acceleration():
    sources = Sources([1e12], [[0., 0., 0.]], [[19., -7., 3.]], [[.001, .002, -.003]], 1e5)
    g, dg = weak_metric([1e6, 2e6, -3e6], sources)
    out = transport(Metric(g, dg), [100., 70., -30.], sources.c)
    assert out.symmetry_defect < 1e-10
    assert np.linalg.norm(out.generator) > 0
    inv = np.linalg.inv(g); v = np.array([100., 70., -30.])
    dinv = -inv@(sources.c*dg[0]+np.einsum('i,imn->mn', v, dg[1:]))@inv
    # Deliberately inconsistent motion: beta rate omitted, must break norm.
    h, wrong_dh, _, _ = root_rate(inv, dinv, v/sources.c, np.zeros(3))
    wrong = (wrong_dh+h@out.covariant_generator)@np.linalg.inv(h)
    assert np.linalg.norm(wrong+wrong.T)/np.linalg.norm(wrong) > 1e-4


@pytest.mark.parametrize('g', [np.eye(4), np.diag([-1., -1., 1., 1.]),
                              np.diag([-1., 0., 1., 1.]), np.diag([1., -1., 1., 1.]),
                              np.full((4, 4), np.nan)])
def test_invalid_metric_rejected(g):
    with pytest.raises(ValueError):
        Metric(g, np.zeros((4, 4, 4)))


def test_asymmetric_nonfinite_derivative_spacelike_and_wrong_types_rejected():
    g = np.diag([-1., 1., 1., 1.]); dg = np.zeros((4, 4, 4)); dg[0, 1, 2] = 1.
    with pytest.raises(ValueError, match='Symmetric'):
        Metric(g, dg)
    dg[0, 2, 1] = float('inf')
    with pytest.raises(ValueError):
        Metric(g, dg)
    g[0, 1] = .1
    with pytest.raises(ValueError, match='Symmetric'):
        Metric(g, np.zeros((4, 4, 4)))
    flat = Metric(np.diag([-1., 1., 1., 1.]), np.zeros((4, 4, 4)))
    with pytest.raises(ValueError, match='Timelike'):
        transport(flat, [30., 0., 0.], 30.)
    with pytest.raises(ValueError):
        transport(flat, [False, False, False], 30.)
    with pytest.raises(ValueError):
        christoffel(g)
    with pytest.raises(ValueError):
        transport(flat, [0., 0., 0.], True)
