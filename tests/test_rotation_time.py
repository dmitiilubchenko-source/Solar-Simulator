"""Compatible SI/model scaling and explicit rotating-clock boundary checks."""
import json

import numpy as np
import pytest

from scripts.assess_rotation_time import ROOT,synthetic,scaling_metrics,boundary_metrics,axis_rotation,evaluate
from scripts.rotation_time import (L_B,UniformTimeScaling,spatial_rate,rotation_boundary,
    local_rate,global_acceleration)
from scripts.canonical_initial import SIUnits
from scripts.independent_rigid_pn import hat


def policy():return json.loads((ROOT/'scripts/rotation-time-policy.json').read_text(encoding='utf-8'))


def test_full_H_scaling_independent_variations_and_wrong_inertia():
    p = policy();params,y,_ = synthetic(p);metrics,raw = scaling_metrics(p,params,y)
    assert raw and p['uniform_factors'][-1]==1-L_B
    for key,value in metrics.items():
        if key in p['minimum_metrics']:assert value>p['criteria'][key]
        else:assert value<p['criteria'][key]
    all_metrics = dict(metrics,**boundary_metrics(p),scaled_trajectory_difference=0.)
    checks,passed = evaluate(p,all_metrics,{k:True for k in p['required_true']})
    assert passed and all(type(v) is bool for v in checks.values())
    json.dumps(dict(metrics=all_metrics,checks=checks),allow_nan=False)


def test_moving_basis_and_nonuniform_clock_independent_complex_time_derivatives():
    p = policy()
    for key,value in boundary_metrics(p).items():
        if key in p['minimum_metrics']:assert value>p['criteria'][key]
        else:assert value<p['criteria'][key]


def test_common_unit_rescaling_preserves_dimensionless_values_and_raw_signed_zero_q():
    params,y,_ = synthetic(policy());y[-1] = -0.
    f = .5;s = UniformTimeScaling(f);out = s.state(y,params)
    u = SIUnits(2e30,1.5e11,6.6743e-11);us = SIUnits(f*u.mass_kg,f*u.length_m,u.gravitational_constant)
    physical_units = np.r_[np.full(9,u.length_m),np.full(9,u.momentum_kg_m_s),np.full(9,u.spin_kg_m2_s),np.ones(4)]
    new_units = np.r_[np.full(9,us.length_m),np.full(9,us.momentum_kg_m_s),np.full(9,us.spin_kg_m2_s),np.ones(4)]
    assert np.allclose(out/new_units,y/physical_units,rtol=3e-16,atol=0)
    assert us.time_s==pytest.approx(f*u.time_s,rel=2e-16)
    assert us.inertia_kg_m2==f**3*u.inertia_kg_m2
    assert np.array_equal(out[-4:].view(np.uint64),y[-4:].view(np.uint64))
    # Returned arrays do not alias input; inverse keeps signed zero in raw q.
    inverse = UniformTimeScaling(1/f).state(out,s.parameters(params))
    assert np.array_equal(inverse.view(np.uint64),y.view(np.uint64))
    out[0]+=1;assert inverse[0]==y[0]


@pytest.mark.parametrize('factor',[True,0.,-1.,float('nan'),float('inf'),1e-200,1e200,'1'])
def test_reject_invalid_or_unrepresentable_uniform_factor(factor):
    with pytest.raises(ValueError):UniformTimeScaling(factor)


def test_scaling_rejects_invalid_state_parameters_and_body_count():
    s = UniformTimeScaling(.5);params,y,_ = synthetic(policy())
    for n in [True,1,2.5]:
        with pytest.raises(ValueError):s.state_factors(n)
    with pytest.raises(ValueError):s.parameters(params.orbital)
    with pytest.raises(ValueError):s.state(y[:-1],params)
    bad = y.copy();bad[0] = float('nan')
    with pytest.raises(ValueError):s.state(bad,params)
    bad = y.copy();bad[-4:] = 0
    with pytest.raises(ValueError):s.state(bad,params)


def test_boundary_rejects_nonrotations_nontangent_derivatives_and_metric_stretch():
    identity = np.eye(3);zero = np.zeros((3,3))
    for b in [np.diag([1.,1.,-1.]),np.diag([1.+1e-6,1.,1.]),np.ones((2,2))]:
        with pytest.raises(ValueError):rotation_boundary(identity,zero,b,zero,1.)
    for d in [identity,np.full((3,3),float('nan'))]:
        with pytest.raises(ValueError):rotation_boundary(identity,zero,identity,d,1.)
        with pytest.raises(ValueError):rotation_boundary(identity,d,identity,zero,1.)
    for rate in [True,0.,-1.,float('inf'),'1']:
        with pytest.raises(ValueError):local_rate(np.ones(3),identity,zero,rate)
    with pytest.raises(ValueError):global_acceleration(np.ones(3),np.zeros(3),identity,zero,np.zeros(3),1.,float('nan'))
    with pytest.raises(ValueError):global_acceleration(np.ones(2),np.zeros(3),identity,zero,np.zeros(3),1.,0.)


def test_nonzero_local_and_basis_accelerations_include_all_four_chain_terms():
    b = axis_rotation([1.,2.,3.],.7);wb = np.array([.2,-.3,.4]);w = np.array([-.4,.1,.3])
    a = np.array([.03,.06,-.02]);ab = np.array([-.01,.02,.04]);rate = 1.3;rdot = -.07
    actual = global_acceleration(w,a,b,hat(wb)@b,ab,rate,rdot)
    # Independent differentiable path: B(t)=exp(wb*t) exp(ab*t^2/2) B(0).
    # Its spatial basis rate is wb+exp(wb*t) ab*t, with derivative ab at 0.
    def rate_path(t):
        first = axis_rotation(wb,np.linalg.norm(wb)*t)
        moving = first@axis_rotation(ab,.5*np.linalg.norm(ab)*t*t)@b
        local_time = rate*t+.5*rdot*t*t
        return wb+first@ab*t+(rate+rdot*t)*(moving@(w+a*local_time))
    expected = rate_path(1j*1e-25).imag/1e-25
    assert np.linalg.norm(actual-expected)<1e-16
    assert np.array_equal(spatial_rate(np.eye(3),np.zeros((3,3))),np.zeros(3))
