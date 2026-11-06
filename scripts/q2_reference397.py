"""397 output-only adaptation of frozen reference380; unchanged RK45/RHS."""
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
    return unpack_solution(solution,document,times,center,drift,position_scale,velocity_scale,spin_scales)


def unpack_solution(solution,document,times,center,drift,position_scale,velocity_scale,spin_scales):
    """Validate/unpack 6N+12K; rotations stay in their input/body-ID order.

    No projection, quaternion normalization, new dynamics or solver changes.
    The numerical output expressions below are the original380 expressions.
    """
    if not solution.success:raise ValueError('Independent RK45 did not finish')
    bodies=document['bodies'];rotations=document['rotations'];count=len(bodies);K=len(rotations)
    if count<2 or K not in (1,2):raise ValueError('Expected N>=2 and K=1 or K=2')
    names=[b['name'] for b in bodies];sources=[s['body'] for s in rotations]
    if any(type(x) is not str or not x for x in names+sources) or len(set(names))!=count or len(set(sources))!=K or any(x not in names for x in sources):raise ValueError('Invalid body/rotation identifiers')
    for s in rotations:
        if s['figure']['mass']!=bodies[names.index(s['body'])]['mass']:raise ValueError('Rotation/body mass mismatch')
    t=np.asarray(times);values=np.asarray(solution.y);recorded=np.asarray(solution.t)
    if t.ndim!=1 or len(t)<2 or not np.isfinite(t).all() or not (np.diff(t)>0).all():raise ValueError('Invalid output epochs')
    if recorded.shape!=t.shape or not np.array_equal(recorded,t):raise ValueError('Solver output epochs changed')
    if values.dtype!=np.dtype('float64') or values.shape!=(6*count+12*K,len(t)) or not np.isfinite(values).all():raise ValueError('Invalid solver state dimension/type/values')
    for value in (center,drift):
        if np.shape(value)!=(3,) or not np.isfinite(value).all():raise ValueError('Invalid output origin/drift')
    scales=np.asarray([position_scale,velocity_scale,*spin_scales])
    if len(spin_scales)!=K or not np.isfinite(scales).all() or not (scales>0).all():raise ValueError('Invalid output scales')
    orbit_size=6*count
    positions=[];velocities=[];orientation=[];spins=[]
    for t,y in zip(times,solution.y.T):
        positions.append(y[:3*count].reshape(count,3)*position_scale+center+drift*(t-times[0]))
        velocities.append(y[3*count:orbit_size].reshape(count,3)*velocity_scale+drift)
        R=[y[orbit_size+12*k:orbit_size+12*k+9].reshape(3,3) for k in range(K)]
        orientation.append(R);spins.append([matrix@y[orbit_size+12*k+9:orbit_size+12*k+12]*spin_scales[k] for k,matrix in enumerate(R)])
    result=dict(positions=np.array(positions),velocities=np.array(velocities),orientation=np.array(orientation),spins=np.array(spins),RHS=solution.nfev)
    if not all(np.isfinite(result[key]).all() for key in ('positions','velocities','orientation','spins')):raise ValueError('Nonfinite reconstructed output')
    return result
