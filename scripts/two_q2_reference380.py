"""Independent scaled Cartesian/R/body-momentum RK45; no production fields."""
import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation


def reference(document,times,rtol):
    """Read numerical inputs only. Return physical p/v/R/S on given epochs."""
    from solar_simulator.simulation import G
    bodies=document['bodies'];rotations=document['rotations'];count=len(bodies)
    masses=np.array([b['mass'] for b in bodies]);p=np.array([b['position'] for b in bodies]);v=np.array([b['velocity'] for b in bodies])
    weights=masses/sum(masses);center=np.sum(weights[:,None]*p,axis=0);drift=np.sum(weights[:,None]*v,axis=0)
    p-=center;v-=drift
    position_scale=max(np.linalg.norm(p,axis=1));velocity_scale=max(np.linalg.norm(v,axis=1))
    indices=[next(i for i,b in enumerate(bodies) if b['name']==s['body']) for s in rotations]
    inertias=[np.array(s['figure']['moments']) for s in rotations]
    matrices=[Rotation.from_quat(np.roll(s['quaternion'],-1)).as_matrix() for s in rotations]
    spin_scales=[np.linalg.norm(s['angular_momentum']) for s in rotations]
    orbit_size=6*count
    initial=np.r_[p.ravel()/position_scale,v.ravel()/velocity_scale,*[part
        for s,R,scale in zip(rotations,matrices,spin_scales) for part in (R.ravel(),R.T@np.array(s['angular_momentum'])/scale)]]

    def rhs(t,y):
        positions=y[:3*count].reshape(count,3)*position_scale
        velocities=y[3*count:orbit_size].reshape(count,3)*velocity_scale
        accelerations=np.zeros_like(positions);tail=[]
        for i in range(count):
            for j in range(i+1,count):
                r=positions[j]-positions[i];d=np.linalg.norm(r)
                force=G*masses[i]*masses[j]*r/d**3
                accelerations[i]+=force/masses[i];accelerations[j]-=force/masses[j]
        for k,(source,inertia,scale) in enumerate(zip(indices,inertias,spin_scales)):
            start=orbit_size+12*k;R=y[start:start+9].reshape(3,3);Pi=y[start+9:start+12]*scale
            omega=Pi/inertia;torque=np.zeros(3)
            for j in range(count):
                if j==source:continue
                r=positions[j]-positions[source];d=np.linalg.norm(r);n=r/d;body_n=R.T@n
                projection=np.dot(inertia*body_n,body_n)
                force=G*masses[j]/(2*d**4)*((15*projection-3*sum(inertia))*n-6*R@(inertia*body_n))
                accelerations[j]+=force/masses[j];accelerations[source]-=force/masses[source]
                torque+=3*G*masses[j]/d**3*np.cross(body_n,inertia*body_n)
            x,yw,z=omega;hat=np.array([[0,-z,yw],[z,0,-x],[-yw,x,0]])
            tail.extend(((R@hat).ravel(),(np.cross(Pi,omega)+torque)/scale))
        return np.r_[velocities.ravel()/position_scale,accelerations.ravel()/velocity_scale,*tail]

    solution=solve_ivp(rhs,(times[0],times[-1]),initial,method='RK45',rtol=rtol,atol=rtol*.01,max_step=50.,t_eval=times)
    if not solution.success or solution.y.shape[1]!=len(times):raise ValueError('Independent RK45 did not finish')
    positions=[];velocities=[];orientation=[];spins=[]
    for t,y in zip(times,solution.y.T):
        positions.append(y[:3*count].reshape(count,3)*position_scale+center+drift*(t-times[0]))
        velocities.append(y[3*count:orbit_size].reshape(count,3)*velocity_scale+drift)
        R=[y[orbit_size+12*k:orbit_size+12*k+9].reshape(3,3) for k in range(2)]
        orientation.append(R);spins.append([matrix@y[orbit_size+12*k+9:orbit_size+12*k+12]*spin_scales[k] for k,matrix in enumerate(R)])
    return dict(positions=np.array(positions),velocities=np.array(velocities),orientation=np.array(orientation),spins=np.array(spins),RHS=solution.nfev)


def independent_invariants(positions,velocities,matrices,spins,masses,inertias):
    """Scalar-I Hamiltonian, P/L. Never calls runtime diagnostics or Q tensors."""
    from solar_simulator.simulation import G
    E=sum(m*np.dot(v,v)/2 for m,v in zip(masses,velocities))
    P=sum((m*v for m,v in zip(masses,velocities)),start=np.zeros(3))
    L=sum((np.cross(p,m*v) for p,m,v in zip(positions,masses,velocities)),start=np.zeros(3))
    for i in range(len(masses)):
        for j in range(i+1,len(masses)):E-=G*masses[i]*masses[j]/np.linalg.norm(positions[j]-positions[i])
    for source,(R,S,I) in enumerate(zip(matrices,spins,inertias)):
        body_S=R.T@S;E+=np.dot(body_S,body_S/I)/2;L+=S
        for j in range(len(masses)):
            if source==j:continue
            r=positions[j]-positions[source];d=np.linalg.norm(r);u=R.T@(r/d)
            E+=G*masses[j]*(3*np.dot(I*u,u)-sum(I))/(2*d**3)
    return E,P,L
