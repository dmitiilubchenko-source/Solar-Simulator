"""Isolated observer/cap for the two-body relative layout; never runtime import."""
from math import isfinite,sqrt

import numpy as np

from solar_simulator.error_control import PerBodyDOP853


def dynamic_cap(relative,mu,divisor):
    if type(mu) not in (int,float) or not isfinite(mu) or mu<=0:
        raise ValueError('Positive finite mu required')
    if type(divisor) is not int or divisor<=0:raise ValueError('Positive integer divisor required')
    rho=np.asarray(relative,dtype=float)
    if rho.shape!=(3,) or not np.isfinite(rho).all():raise ValueError('Finite relative 3-vector required')
    radius=float(np.linalg.norm(rho))
    cap=sqrt(radius**3/mu)/divisor
    if not isfinite(cap) or cap<=0:raise ValueError('Unresolved dynamical scale')
    return cap


def observed_solver(mu,divisor,packet,steps,trials,check_budget=lambda:None):
    """Only max_step changes. Trace arithmetic never feeds back into the solver.

    steps: packet,t_before,t_after,cap(0=off),rho[3],proposed_h,nfev_before,
    nfev_after,trial_count,rejected_count,proposal_exceeded_cap.
    trials: packet,global_step_index,h,error_norm. Norm>=1 is a rejection
    under the pinned SciPy _step_impl; nfev also includes initialization/dense IO.
    """
    class Observed(PerBodyDOP853):
        def __init__(self,*args,**kwargs):
            self.observed_trials=[]
            super().__init__(*args,**kwargs)
            if self.y.shape!=(12,):raise ValueError('Only two relative-coordinate bodies')

        def _estimate_error_norm(self,K,h,scale):
            value=super()._estimate_error_norm(K,h,scale)
            self.observed_trials.append((float(h),value))
            return value

        def _step_impl(self):
            check_budget()
            rho=self.y[3:6].copy()  # B slot IS rho; do not subtract encoded COM.
            cap=dynamic_cap(rho,mu,divisor) if divisor is not None else 0.
            if divisor is not None:self.max_step=cap
            before=float(self.t);proposed=float(self.h_abs);nfev=self.nfev
            self.observed_trials=[]
            result=super()._step_impl()
            for h,error in self.observed_trials:trials.append([packet,len(steps),h,error])
            if not result[0]:raise RuntimeError('Diagnostic solver failed: '+str(result[1]))
            steps.append([packet,before,float(self.t),cap,*map(float,rho),proposed,nfev,self.nfev,
                len(self.observed_trials),sum(error>=1 for _,error in self.observed_trials),int(cap>0 and proposed>cap)])
            return result
    return Observed
