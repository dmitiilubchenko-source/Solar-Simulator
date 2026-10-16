"""Single-threaded, offline RK roundoff experiment; never a runtime backend."""
import math
from math import fsum, sqrt
from unittest.mock import patch

import numpy as np

from solar_simulator.error_control import PerBodyDOP853


def solver_class(*, accurate_sums, compensated, divisor=None, mu=None):
    """Preserve installed SciPy acceptance; substitute just its RK stage sums.

    Process-global rk_step patch is scoped to one synchronous _step_impl call.
    This factory must not be used concurrently or as a production integrator.
    """
    if accurate_sums and not hasattr(math,'sumprod'):
        raise RuntimeError('The sumprod experiment requires Python 3.12 or newer')
    class RoundoffDOP853(PerBodyDOP853):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.carry=np.zeros_like(self.y)
            self.accepted_steps=0
            self.trial_steps=0

        def _trial(self,fun,t,y,f,h,A,B,C,K):
            self.trial_steps+=1
            K[0]=f

            def weighted(stages,coefficients):
                if not accurate_sums:
                    return stages.T@coefficients
                weights=coefficients.tolist()
                return np.array([math.sumprod(column.tolist(),weights) for column in stages.T])

            def add(increment):
                if not compensated:
                    return y+increment
                return np.array([fsum((float(base),float(lost),float(delta)))
                    for base,lost,delta in zip(y,self.carry,increment)])

            for stage in range(1,len(B)):
                increment=h*weighted(K[:stage],A[stage,:stage])
                K[stage]=fun(t+h*C[stage],add(increment))
            increment=h*weighted(K[:-1],B)
            proposal=add(increment)
            self.proposed_carry=np.array([fsum((float(base),float(lost),float(delta),-float(new)))
                for base,lost,delta,new in zip(y,self.carry,increment,proposal)]) if compensated else self.carry.copy()
            K[-1]=fun(t+h,proposal)
            return proposal,K[-1].copy()

        def _step_impl(self):
            if divisor is not None:
                radius=float(np.linalg.norm(self.y[3:6]))
                self.max_step=sqrt(radius**3/mu)/divisor
            with patch('scipy.integrate._ivp.rk.rk_step',self._trial):
                success,message=super()._step_impl()
            if success:
                self.carry=self.proposed_carry.copy()
                self.accepted_steps+=1
            return success,message

    return RoundoffDOP853
