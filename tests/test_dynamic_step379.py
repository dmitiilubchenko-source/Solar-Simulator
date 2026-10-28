"""Synthetic preflight, not another set of scientific trajectories."""
import numpy as np
import pytest
from scipy.integrate import solve_ivp

from scripts.dynamic_step379 import dynamic_cap,observed_solver
from solar_simulator.error_control import PerBodyDOP853


@pytest.mark.parametrize('mu,d',[ (True,32),(0.,32),(float('nan'),32),(1.,True),(1.,0)])
def test_cap_rejects_undefined_scales(mu,d):
    with pytest.raises(ValueError):dynamic_cap([3.,4.,0.],mu,d)


def test_cap_dimensions_and_rotation():
    original=dynamic_cap([3.,4.,0.],25.,32)
    assert dynamic_cap([0.,-3.,4.],25.,32)==original
    assert dynamic_cap([12.,16.,0.],25.,32)==pytest.approx(8*original)
    assert dynamic_cap([3.,4.,0.],100.,32)==pytest.approx(original/2)
    with pytest.raises(ValueError):dynamic_cap([0.,0.,0.],25.,32)


def test_disabled_instrumentation_preserves_exact_scipy_outputs_and_RHS():
    y=np.arange(1.,13.);rhs=lambda t,y:.1*y
    expected=solve_ivp(rhs,[0,5],y,method=PerBodyDOP853,rtol=3e-14,atol=1e-9)
    steps=[];trials=[];method=observed_solver(1.,None,0,steps,trials)
    actual=solve_ivp(rhs,[0,5],y,method=method,rtol=3e-14,atol=1e-9)
    assert expected.success and actual.success
    assert expected.y.tobytes()==actual.y.tobytes() and expected.t.tobytes()==actual.t.tobytes()
    assert expected.nfev==actual.nfev and len(steps)==len(actual.t)-1
    for name in ('A','B','C','E3','E5','D'):assert getattr(method,name) is getattr(PerBodyDOP853,name)


def test_cap_applies_to_internal_steps_and_uses_relative_not_COM_slot():
    y=np.zeros(12);y[:3]=[1e9,2e9,-1e9];y[3:6]=[3.,4.,0.]
    steps=[];trials=[];method=observed_solver(1.,32,0,steps,trials)
    result=solve_ivp(lambda t,y:np.zeros(12),[0,5],y,method=method,rtol=3e-14,atol=1e-9)
    assert result.success and len(steps)>5
    cap=dynamic_cap(y[3:6],1.,32)
    assert all(row[3]==cap and row[2]-row[1]<=cap+1e-14 for row in steps)
    assert any(row[-1] for row in steps)
    assert sum(row[10] for row in steps)==len(trials)
