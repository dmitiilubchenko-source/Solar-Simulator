"""Read-only scalar-Lagrangian Noether observer for the395 short audit."""
import math


def eih_noether_observer(positions,velocities,masses,G,c,figures=()):
    """Legendre transform of scalar EIH Lagrangian; not Solar invariants().

    Complex-step velocity derivatives, SI, runtime-validated point-body inputs.
    Optional (source,J2,radius,axis) adds a fixed Newton J2 potential only.
    Full L is a diagnostic, not a conserved vector with an external fixed axis.
    Does not integrate or add this model to any runtime.
    """
    import numpy as np
    def array(values):
        raw=np.asarray(values,dtype=object)
        if any(type(x) not in (int,float) for x in raw.flat):raise ValueError('Builtin real input required, excluding bool')
        try:out=np.array(values,dtype=float,copy=True)
        except (OverflowError,ValueError) as e:raise ValueError('Nonfinite input') from e
        if not np.all(np.isfinite(out)):raise ValueError('Nonfinite input')
        return out
    p,v,m=array(positions),array(velocities),array(masses)
    if m.ndim!=1 or not len(m) or p.shape!=(len(m),3) or v.shape!=p.shape or np.any(m<=0):raise ValueError('Invalid observer shape/mass')
    g,speed=array([G,c])
    if g<=0 or speed<=0:raise ValueError('Positive G/c required')
    U=[0.]*len(m);pairs=[];potential=0.
    for i in range(len(m)):
        for j in range(len(m)):
            if i==j:continue
            r=p[i]-p[j];distance=np.linalg.norm(r)
            if distance==0:raise ValueError('Coincident bodies')
            U[i]+=g*m[j]/distance;pairs.append((i,j,r/distance,g*m[i]*m[j]/distance))
            if i<j:potential-=g*m[i]*m[j]/distance
    for source,j2,radius,axis in figures:
        axis=array(axis)
        if type(source) is not int or not 0<=source<len(m) or axis.shape!=(3,) or abs(np.linalg.norm(axis)-1)>1e-12 or type(j2) not in (int,float) or not math.isfinite(j2) or not 0<abs(j2)<=.01 or type(radius) not in (int,float) or not math.isfinite(radius) or radius<=0:raise ValueError('Invalid fixed J2')
        for j in range(len(m)):
            if j==source:continue
            r=p[j]-p[source];distance=np.linalg.norm(r)
            if distance<=radius:raise ValueError('Outside J2 reference sphere required')
            potential+=g*m[source]*m[j]*j2*radius**2*(3*np.dot(r/distance,axis)**2-1)/(2*distance**3)
    def lagrangian(velocity):
        speed2=[np.dot(x,x) for x in velocity]
        kinetic=sum(m[i]*speed2[i]/2 for i in range(len(m)))
        L1=sum(m[i]*speed2[i]**2/8-m[i]*U[i]**2/2 for i in range(len(m)))
        for i,j,n,coupling in pairs:L1+=coupling*(3*speed2[i]+3*speed2[j]-7*np.dot(velocity[i],velocity[j])-np.dot(n,velocity[i])*np.dot(n,velocity[j]))/4
        return kinetic-potential+L1/speed**2
    canonical=np.empty_like(v);h=1e-25
    for i in range(len(m)):
        for k in range(3):
            trial=v.astype(complex);trial[i,k]+=h*1j;canonical[i,k]=lagrangian(trial).imag/h
    return dict(E_J=float(np.sum(v*canonical)-lagrangian(v)),P_kg_m_s=np.sum(canonical,axis=0).tolist(),L_kg_m2_s=np.sum(np.cross(p,canonical),axis=0).tolist(),scope='EIH Noether through1PN plusfixedNewtonJ2; fullL not invariant withfixedaxis; omittedcross/higherorders remain')
