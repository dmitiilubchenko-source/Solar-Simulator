"""Independent potential, Hessian and torque checks of the fixedJ2 contract."""
from dataclasses import replace
from decimal import Decimal,localcontext

import numpy as np
import pytest

from scripts.fixed_j2_ias import (model,entries,potential,figure_force,pn_response,
    full_force,reference,balances,validate,ias_trajectory)
from scripts.ias15_reference import load_library
from scripts.ias15_eih import configured,integrate_checked
from scripts.newton_year import ROOT
from scripts.assess_sandbox_planets import states
from solar_simulator.oblateness import acceleration,prepare,orbital_torque,FixedJ2,PrescribedQuadrupole
from solar_simulator.native_forces import prepare as native_prepare
from solar_simulator.relativity import C
from solar_simulator.simulation import G
from solar_simulator.orientation import PROFILE_SHA256


@pytest.fixture
def library():
    directory = ROOT/'.tools/ias15165/dependency'
    if not directory.is_dir():
        pytest.importorskip('rebound',reason='Optional research library absent')
        return load_library()
    return load_library(directory)


@pytest.mark.parametrize('case',['newton_one','newton_two','eih_two'])
def test_tensor_complex_step_gradient_reaction_torque_and_full_callback(case):
    seed,_,_ = model(case);q = states(seed.bodies);m = np.array([b.mass for b in seed.bodies])
    fig = entries(seed);field = figure_force(q[:,:3],m,fig)
    native_field = acceleration(q[:,:3],m,prepare(seed.bodies,seed.settings.figures))
    scale = np.linalg.norm(field,axis=1).max()
    assert np.linalg.norm(field-native_field,axis=1).max()/scale<5e-13
    gradient = np.zeros_like(field)
    for i in range(len(m)):
        for k in range(3):
            p = q[:,:3].astype(complex);p[i,k] += 1e-12j
            gradient[i,k] = potential(p,m,fig).imag/1e-12
    assert np.linalg.norm(field+gradient/m[:,None],axis=1).max()/scale<5e-13
    forces = m[:,None]*field
    assert np.linalg.norm(forces.sum(axis=0))/np.linalg.norm(forces,axis=1).sum()<5e-13
    torque = np.cross(q[:,:3],forces).sum(axis=0)
    actual = orbital_torque(seed.bodies,seed.settings.figures)
    torque_scale = np.linalg.norm(q[1,:3]-q[0,:3])*np.linalg.norm(forces,axis=1).sum()
    assert np.linalg.norm(torque-[actual.x,actual.y,actual.z])/torque_scale<5e-13
    point = native_prepare(m)(q[:,:3],q[:,3:],C if case=='eih_two' else None)
    np.testing.assert_allclose(full_force(seed)(q[:,:3],q[:,3:]),point+field,rtol=5e-13,atol=1e-12)


def test_pn_response_from_decimal70_mixed_derivative_of_scalar_action():
    p = np.array([[-1.,.2,.3],[1.,.3,-.2],[.5,-1.1,.1]])
    v = np.array([[.1,.4,.1],[-.4,.1,.3],[.2,-.3,-.2]])
    b = np.array([[.2,-.3,.1],[.4,.2,-.1],[-.1,.2,.3]])
    m = np.array([2.,.7,.4])
    with localcontext() as context:
        context.prec = 70
        D = lambda x:Decimal(str(x))
        pp,vv,bb = [[[D(x) for x in row] for row in array] for array in (p,v,b)]
        mm = [D(x) for x in m]
        dot = lambda a,b:sum(x*y for x,y in zip(a,b))
        def lag1(vel):
            value = sum(mm[i]*dot(vel[i],vel[i])**2/8 for i in range(3))
            for i in range(3):
                u = Decimal(0)
                for j in range(3):
                    if i==j:continue
                    r = [x-y for x,y in zip(pp[i],pp[j])];radius = dot(r,r).sqrt();n = [x/radius for x in r]
                    u += mm[j]/radius
                    if i<j:
                        value += mm[i]*mm[j]/(2*radius)*(3*(dot(vel[i],vel[i])+dot(vel[j],vel[j]))
                            -7*dot(vel[i],vel[j])-dot(n,vel[i])*dot(n,vel[j]))
                value -= mm[i]*u*u/2
            return value/Decimal(1000)**2
        h,epsilon = Decimal('1e-10'),Decimal('1e-18')
        expected = np.zeros_like(v)
        for i in range(3):
            for k in range(3):
                terms = []
                for a,c in ((1,1),(1,-1),(-1,1),(-1,-1)):
                    vel = [[vv[j][l]+a*h*bb[j][l] for l in range(3)] for j in range(3)]
                    vel[i][k] += c*epsilon
                    terms.append(a*c*lag1(vel))
                expected[i,k] = float(sum(terms)/(4*h*epsilon))
    actual = pn_response(p,v,m,b,g=1.,c=1000.)
    assert np.linalg.norm(actual-expected)/np.linalg.norm(expected)<1e-10


def test_axis_reversal_and_exterior_guards():
    seed,times,_ = model('newton_one');q = states(seed.bodies);m = np.array([b.mass for b in seed.bodies])
    original = seed.settings.figures[0]
    reverse = replace(original,axis=tuple(-x for x in original.axis))
    changed = replace(seed,settings=replace(seed.settings,figures=(reverse,)))
    np.testing.assert_array_equal(figure_force(q[:,:3],m,entries(seed)),figure_force(q[:,:3],m,entries(changed)))
    p = q[:,:3].copy();p[1] = p[0]+np.array([original.reference_radius*.5,0,0])
    with pytest.raises(ValueError):full_force(seed)(p,q[:,3:])
    with pytest.raises(ValueError,match='Inside'):figure_force(p,m,entries(seed))
    prescribed = PrescribedQuadrupole('Earth',.001,1e6,0.,'earth-de441',PROFILE_SHA256)
    with pytest.raises(ValueError,match='fixed J2 only'):
        validate(replace(seed,settings=replace(seed.settings,figures=(prescribed,))),times)


def test_actual_figure_radius_failure_is_not_swallowed_by_ctypes(library,capsys):
    seed,_,_ = model('newton_one');q = states(seed.bodies);m = [b.mass for b in seed.bodies]
    bad = q[:,:3].copy();bad[1] = bad[0]+np.array([seed.settings.figures[0].reference_radius*.5,0,0])
    force = full_force(seed)
    sim,callback = configured(q,m,library,1e-9,.01,lambda p,v:force(bad,v))
    with pytest.raises(RuntimeError,match='no output committed') as caught:
        integrate_checked(sim,callback,.1)
    assert isinstance(caught.value.__cause__,ValueError)
    assert 'Exception ignored' not in capsys.readouterr().err


def test_newton_torque_budget_against_independent_short_reference():
    seed,_,period = model('newton_one');times = np.linspace(0,period/4,9)
    values,budget,_ = reference(seed,times,3e-14,period/800)
    row = balances(values,budget,seed)
    assert max(row['corrected'].values())<1e-9
    assert row['raw']['angular']>1e-6
    assert row['single_axis_angular_projection']<1e-9


@pytest.mark.parametrize('direction,coefficient',[(np.array([1.,0.,0.]),-1.5),(np.array([0.,0.,1.]),3.)])
def test_equatorial_and_polar_analytic_field(direction,coefficient):
    seed,_,_ = model('newton_one');m = np.array([b.mass for b in seed.bodies]);f = seed.settings.figures[0]
    radius = 8e7;p = np.array([np.zeros(3),radius*direction])
    actual = figure_force(p,m,entries(seed))
    expected = coefficient*G*m[0]*f.coefficient*f.reference_radius**2/radius**4*direction
    np.testing.assert_allclose(actual[1],expected,rtol=5e-13,atol=0)
    np.testing.assert_allclose(actual[0],-m[1]/m[0]*expected,rtol=5e-13,atol=0)


def test_tensor_force_covariance_under_rotation_and_translation():
    seed,_,_ = model('newton_two');q = states(seed.bodies);m = np.array([b.mass for b in seed.bodies]);fig = entries(seed)
    rotation = np.array([[0.,-1.,0.],[.6,0.,-.8],[.8,0.,.6]])
    changed = tuple((i,r,rotation@tensor@rotation.T) for i,r,tensor in fig)
    actual = figure_force(q[:,:3]@rotation.T+np.array([9e8,-5e8,3e8]),m,changed)
    expected = figure_force(q[:,:3],m,fig)@rotation.T
    assert np.linalg.norm(actual-expected,axis=1).max()/np.linalg.norm(expected,axis=1).max()<5e-13


def test_mixed_bookkeeping_does_not_require_constant_raw_noether():
    seed,_,period = model('eih_two');times = np.linspace(0,period/4,9)
    values,budget,_ = reference(seed,times,3e-14,period/800)
    row = balances(values,budget,seed)
    assert max(row['corrected'].values())<1e-9
    assert row['source_integrals']['pn2']['energy']>0
    assert row['source_integrals']['pn_q2']['energy']>0
