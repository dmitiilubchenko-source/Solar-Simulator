"""Independent canonical two-form, Hamiltonian derivative and geometry checks."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.relative_canonical import Pair, from_cartesian, to_cartesian, rhs, invariants
from scripts.independent_relative_canonical import gradients, matrix_rhs, scalar
from scripts.rigid_pn_model import Parameters, hamiltonian, rhs as cartesian_rhs
from scripts.nbody_pn_spin import Parameters as PointParameters
from solar_simulator.rotation import RigidFigure


P = Parameters(PointParameters((.3, .7, .05), float(np.sqrt(1e5))),
               RigidFigure(.3, (.002, .0025, .003), .15), 0)
Q = np.roll(Rotation.from_rotvec([.3, -.2, .4]).as_quat(), 1)
Y = np.r_[np.array([[[.56, 0., 0.], [-.24, 0., 0.], [3.5, .4, .6]],
                   [[0., .257, 0.], [0., -.257, 0.], [-.003, .025, .004]],
                   [[.003, -.004, .002], [-.002, .001, .003], [.0002, .0003, -.0001]]]).ravel(), Q]


def test_orbital_transformation_preserves_symplectic_two_form_and_one_form():
    for indices in [(0, 1), (2, 0), (1, 2)]:
        pair = Pair(P.orbital.masses, *indices); n = 9
        baseline = np.r_[np.zeros(27), Q]
        transform = np.column_stack([from_cartesian(baseline+np.eye(31)[i], pair)[:18] for i in range(18)])
        symplectic = np.block([[np.zeros((n,n)), np.eye(n)], [-np.eye(n), np.zeros((n,n))]])
        assert np.linalg.norm(transform.T@symplectic@transform-symplectic) < 2e-15
        rng = np.random.default_rng(62); dx = rng.normal(size=(3,3))
        z = from_cartesian(Y, pair); b = Y[:-4].reshape(3,3,3); zb = z[:-4].reshape(3,3,3)
        tangent = baseline.copy(); tangent[:9] = dx.ravel()
        dz = from_cartesian(tangent, pair)[:9].reshape(3,3)
        assert abs(np.sum(b[1]*dx)-np.sum(zb[1]*dz)) < 2e-15


def test_roundtrip_H_P_J_and_untouched_spin_orientation():
    pair = Pair(P.orbital.masses, 2, 0); z = from_cartesian(Y, pair)
    assert np.max(abs(to_cartesian(z,pair)-Y)) < 1e-15
    assert np.array_equal(z[18:].view(np.uint64),Y[18:].view(np.uint64))
    h,p,j = invariants(z,P,pair); b = Y[:-4].reshape(3,3,3)
    assert abs(h-hamiltonian(Y,P)) < 2e-15
    assert np.linalg.norm(p-b[1].sum(axis=0)) < 1e-16
    assert np.linalg.norm(j-(np.cross(b[0],b[1])+b[2]).sum(axis=0)) < 1e-15


def test_independent_full_H_and_body_Euler_derivatives_on_24_states():
    pair = Pair(P.orbital.masses,0,1); rotation = Rotation.from_quat(np.roll(Q,-1)).as_matrix()
    rng = np.random.default_rng(62)
    for _ in range(24):
        state = Y.copy(); b = state[:-4].reshape(3,3,3)
        for block,scale in enumerate([.05,.005,.0001]): b[block] += rng.normal(size=(3,3))*scale
        z = from_cartesian(state,pair); actual = rhs(0,z,P,pair); s = z[:-4].reshape(3,3,3)[2]
        g = gradients(z[:-4],rotation,P.orbital.masses,P.orbital.c,P.figure.moments,0,0,1).reshape(3,3,3)
        assert abs(scalar(z[:-4],rotation,P.orbital.masses,P.orbital.c,P.figure.moments,0,0,1)-invariants(z,P,pair)[0]) < 2e-15
        assert np.max(np.linalg.norm(actual[:18].reshape(2,3,3)-np.stack([g[1],-g[0]]),axis=-1)) < 1e-13
        start = np.r_[z[:-4],rotation.ravel()]; start[18:21] = rotation.T@s[0]
        df = matrix_rhs(0,start,P.orbital.masses,P.orbital.c,P.figure.moments,0,0,1)
        derivative = df[:27].reshape(3,3,3).copy(); dr = df[27:].reshape(3,3)
        derivative[2,0] = dr@(rotation.T@s[0])+rotation@derivative[2,0]
        scales = np.linalg.norm(actual[:-4].reshape(3,3,3),axis=-1)
        assert np.all(scales>0)
        assert np.max(np.linalg.norm(derivative-actual[:-4].reshape(3,3,3),axis=-1)/scales) < 1e-10


def test_huge_origin_does_not_destroy_relative_force_geometry():
    pair = Pair((.3,.7),0,1)
    params = Parameters(PointParameters(pair.masses,1e6),P.figure,0)
    z = np.r_[np.array([[[0.,0.,0.],[.25,.5,1.]],[[0.,.01,0.],[0.,.02,0.]],[[.003,0.,0.],[0.,0.,0.]]]).ravel(),Q]
    shifted = z.copy(); shifted[:3] = 2.**54
    assert np.array_equal(to_cartesian(shifted,pair,anchored=True),to_cartesian(z,pair,anchored=True))
    assert np.array_equal(rhs(0,shifted,params,pair),rhs(0,z,params,pair))
    absolute = to_cartesian(shifted,pair)
    assert not np.array_equal(absolute[:6].reshape(2,3)[1]-absolute[:3],z[3:6])
    with pytest.raises(ValueError,match='Coincident'):cartesian_rhs(0,absolute,params)


def test_wrong_momentum_coordinate_transform_is_detected():
    pair = Pair(P.orbital.masses,0,1); z = from_cartesian(Y,pair)
    bad = z.copy(); b = Y[:-4].reshape(3,3,3); a,d = pair.fractions
    bad[9:12] = a*b[1,0]+d*b[1,1]; bad[12:15] = b[1,1]-b[1,0]
    assert abs(invariants(bad,P,pair)[0]-invariants(z,P,pair)[0]) > 1e-3


def test_explicit_domain_and_layout_rejections():
    for args in [((.3,.7),0,0),((.3,-.7),0,1),((.3,.7),True,1),((.3,.7),0,2)]:
        with pytest.raises(ValueError):Pair(*args)
    pair = Pair(P.orbital.masses,0,1)
    for value in [Y[:-1],np.full(31,np.nan)]:
        with pytest.raises(ValueError):from_cartesian(value,pair)
    with pytest.raises(ValueError,match='masses'):rhs(0,Y,P,Pair((.4,.6,.05),0,1))
