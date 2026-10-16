"""Independent Riccati/log-F, positive vacuum integral and published series.

No production sphere/metric/map imports. Radius s is areal/R; fixed chart
choice agrees with Klioner/Soffel2014(107,113-117), not an ADM centre map.
"""
import numpy as np

from scripts.independent_conventions_reference import gauss_nodes


def centre_state(c):
    # State is now delta=w-w0 and logF; the exact origin is zero.
    return np.array([0.,-0.])


def riccati_rhs(s,state,c):
    delta,logf=state
    if s==0.:
        if delta!=0.:raise ValueError('Regular Riccati centre state required')
        return np.zeros(2)
    a=np.sqrt(1-2*c);u=np.sqrt(1-2*c*s*s);n=(3*a-u)/2;n0=(3*a-1)/2
    w0=c*(6-1/n0)/5;w=w0+delta
    a_over_s=c/(u*n)-2*c/(u*u)
    # (K(s)-K(0))/s^2 analytically rationalized; no constant subtraction.
    regular_source=12*c*c/(u*u)-c*c*(3*a-1-u)/((1+u)*u*n*n0)
    rate=s*regular_source-5*delta/s-s*w*(w+a_over_s)
    return np.array([rate,s*w])


def vacuum_basis(s,c,order=64):
    """D and two derivatives from positive integral, independent of the series."""
    t,weights=gauss_nodes(order);s=np.asarray(s)
    den=(s[...,None]-c)**2-c*c*t*t
    value=3*np.sum(weights*t*t/den,axis=-1)
    first=-6*(s-c)*np.sum(weights*t*t/den**2,axis=-1)
    second=6*np.sum(weights*t*t*(3*(s[...,None]-c)**2+c*c*t*t)/den**3,axis=-1)
    return value,first,second


def boundary(surface_state,c):
    delta,logf=surface_state;n0=(3*np.sqrt(1-2*c)-1)/2
    w=c*(6-1/n0)/5+delta;z=1+w;d,first,_=vacuum_basis(1.,c)
    gauge=(z*(1-c)-1)/(first-z*d)
    scale=(1-c+gauge*d)/np.exp(logf)
    return dict(compactness=c,scale=float(scale),residual_gauge=float(gauge))


def profile(s,states,matched):
    s=np.asarray(s);states=np.asarray(states);f=np.exp(states[...,1])
    c=matched['compactness'];n0=(3*np.sqrt(1-2*c)-1)/2
    w=c*(6-1/n0)/5+states[...,0]
    scale=matched['scale'];h=scale*s*f;first=scale*f*(1+s*s*w)
    return h,first


def published_interior(s,c,order=2):
    """Klioner/Soffel(113), correct global regular/matched normalization."""
    if type(order) is not int or order not in (1,2):raise ValueError('Published order1 or2 required')
    s=np.asarray(s)
    h=s*(1+(-1.5+.5*s*s)*c)
    first=1+(-1.5+1.5*s*s)*c
    if order==2:
        h+=s*(.25-.9*s*s+15/28*s**4)*c*c
        first+=(.25-2.7*s*s+75/28*s**4)*c*c
    return h,first


def published_exterior(s,c):
    s=np.asarray(s)
    return s-c-4/35*c*c/s**2,1+8/35*c*c/s**3
