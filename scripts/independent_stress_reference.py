"""Independent metric gradient / stress-source spin oracles; no production imports."""
import numpy as np

from scripts.independent_fluid_reference import pressure, stress_logj_rate


def metric_komar_charge(s,c):
    """MKomar/M from a complex-step lapse gradient, not the matter integral."""
    s=np.asarray(s);step=1e-20
    lapse=(3*np.sqrt(1-2*c)-np.sqrt(1-2*c*(s+1j*step)**2))/2
    derivative=lapse.imag/step
    return s*s*np.sqrt(1-2*c*s*s)*derivative/c


def spin_log_rhs(s,state,c):
    z,logf=state
    if s==0.:
        if z!=0.:raise ValueError('Regular centre requires z=0')
        return np.zeros(2)
    rate=stress_logj_rate(s,c)
    return np.array([-z*(z+3)/s-rate*(z+4),z/s])


def normalized_profile(states,surface_state):
    z,logf=surface_state
    return np.exp(np.asarray(states)[...,1]-logf)/(1+z/3)


def direct_inertia_integrand(s,h,c):
    s=np.asarray(s);a=np.sqrt(1-2*c);u=np.sqrt(1-2*c*s*s)
    return 4*s**4*np.asarray(h)*(1+pressure(s,c))/(u*(3*a-u))


def second_order_coefficients():
    return dict(correct=212/525,paired_omission=151/315,difference=17/225)


def term_linear_coefficients():
    return dict(pressure=2/35,proper_volume=2/7,lapse=16/35,frame_profile=-16/35)
