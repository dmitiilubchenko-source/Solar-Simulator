"""Vectorized developer reference in body axes; never a working tensor force."""
from math import fsum
import numpy as np
from solar_simulator.oblateness import FixedJ2
from solar_simulator.orientation import earth_pole, lunar_rotation
from solar_simulator.simulation import AU


def acceleration(p, mu, figures, names, time, relative_pair=None):
    p,mu=np.asarray(p,dtype=float),np.asarray(mu,dtype=float)
    if (p.shape!=(len(mu),3) or len(names)!=len(mu) or len(set(names))!=len(names)
            or mu.ndim!=1 or np.any(mu<=0) or not np.all(np.isfinite(mu)) or not np.all(np.isfinite(p))):
        raise ValueError('Invalid reference figures geometry')
    result=np.zeros_like(p)
    for figure in figures:
        source=names.index(figure.body)
        targets=np.array([i for i in range(len(mu)) if i!=source],dtype=int)
        r=p[targets]-p[source]
        if relative_pair is not None:
            first,second,rho=relative_pair
            if source==first: r[targets==second]=rho
            elif source==second: r[targets==first]=-np.asarray(rho)
        distance=np.linalg.norm(r,axis=1)
        if np.any(distance<=figure.reference_radius/AU):
            raise ValueError('Reference quadrupole is an external field')
        n=r/distance[:,None]
        scale=mu[source]*(figure.reference_radius/AU)**2/distance**4
        if isinstance(figure,FixedJ2) or figure.body!='Moon':
            pole=np.array(figure.axis) if isinstance(figure,FixedJ2) else earth_pole(float(time))[0]
            z=n@pole
            field=1.5*figure.coefficient*scale[:,None]*((5*z*z-1)[:,None]*n-2*z[:,None]*pole)
        else:
            rotation,_=lunar_rotation(float(time))
            local=n@rotation
            x,y,z=local.T
            field=1.5*figure.coefficient*scale[:,None]*(
                (5*z*z-1)[:,None]*local-np.column_stack((np.zeros_like(z),np.zeros_like(z),2*z)))
            field+=3*figure.c22*scale[:,None]*(np.column_stack((2*x,-2*y,np.zeros_like(z)))
                -5*(x*x-y*y)[:,None]*local)
            field=field@rotation.T
        result[targets]+=field
        result[source]-=np.array([fsum(mu[targets]/mu[source]*field[:,k]) for k in range(3)])
    if not np.all(np.isfinite(result)): raise ValueError('Non-finite reference quadrupole')
    return result
