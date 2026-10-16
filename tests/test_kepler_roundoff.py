from unittest.mock import patch
import math

import numpy as np
import pytest
from scipy.integrate._ivp import rk

from scripts.kepler_roundoff import solver_class
from solar_simulator.error_control import PerBodyDOP853


def test_unmodified_stage_path_exactly_matches_installed_solver():
    def rhs(t,y):
        return np.concatenate((y[3:],-y[:3]))
    y=np.array([1.,2.,3.,.1,-.2,.3])
    original=PerBodyDOP853(rhs,0.,y,20.,rtol=3e-14,atol=1e-13)
    candidate=solver_class(accurate_sums=False,compensated=False)(rhs,0.,y,20.,rtol=3e-14,atol=1e-13)
    while original.status=='running':
        original.step();candidate.step()
        assert original.t==candidate.t and original.nfev==candidate.nfev
        np.testing.assert_array_equal(original.y,candidate.y)


@pytest.mark.parametrize('accurate_sums',[False,True])
def test_carry_retains_sub_ulp_increment_and_is_committed_only_on_accept(accurate_sums):
    if accurate_sums and not hasattr(math,'sumprod'):
        pytest.skip('sumprod experiment requires Python 3.12')
    cls=solver_class(accurate_sums=accurate_sums,compensated=True)
    y=np.array([1e16,0.,0.,1.,0.,0.])
    solver=cls(lambda t,y:np.array([1.,0.,0.,0.,0.,0.]),0.,y,1.,
               first_step=1.,rtol=3e-14,atol=1e-7)
    installed=rk.rk_step
    # Force one rejected trial, then one accepted trial, with the same start.
    with patch.object(solver,'_estimate_error_norm',side_effect=[2.,0.]):
        solver.step()
    assert solver.trial_steps==2 and solver.accepted_steps==1
    assert rk.rk_step is installed
    assert abs(solver.carry[0]-solver.t)<1e-14
    assert solver.y[0]==1e16


def test_failed_trial_does_not_commit_carry_or_leave_global_patch():
    cls=solver_class(accurate_sums=False,compensated=True)
    solver=cls(lambda t,y:np.ones(6),0.,np.ones(6),1.,rtol=3e-14,atol=1e-7)
    installed=rk.rk_step
    before=solver.carry.copy()
    with patch.object(solver,'_trial',side_effect=RuntimeError('trial failure')):
        with pytest.raises(RuntimeError,match='trial failure'):
            solver.step()
    assert solver.accepted_steps==0 and rk.rk_step is installed
    np.testing.assert_array_equal(solver.carry,before)


def test_missing_optional_sumprod_leaves_control_and_carry_available(monkeypatch):
    monkeypatch.delattr(math,'sumprod',raising=False)
    assert solver_class(accurate_sums=False,compensated=True)
    with pytest.raises(RuntimeError,match='Python 3.12'):
        solver_class(accurate_sums=True,compensated=False)
