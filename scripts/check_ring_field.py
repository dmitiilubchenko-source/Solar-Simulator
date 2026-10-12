"""Initial field resolution at actual planets/KBOs, without orbit fitting."""
import hashlib
import json
from math import pi,fsum,sin
from pathlib import Path

import numpy as np
from scipy.integrate import quad_vec
from scipy.special import ellipk

from scripts.build_kuiper_ring import parameters,POLICY_SHA256
from scripts.assess_resolved_moon import states
from scripts.assess_asteroid_catalog import summed
from solar_simulator.kuiper_ring import solar_system_ring,MANIFEST_SHA256
from solar_simulator.native_forces import prepare
from solar_simulator.simulation import G


def uniform_field(point,radius,gm):
    """Adaptive angular integral independent of discrete point sums."""
    point=np.asarray(point,dtype=float)
    def integrand(angle):
        d=radius*np.array([np.cos(angle),np.sin(angle),0.])-point
        return gm/(2*pi)*d/np.linalg.norm(d)**3
    return quad_vec(integrand,0,2*pi,epsabs=1e-28,epsrel=1e-13)[0]


def potential(point,radius,gm):
    cylindrical=np.linalg.norm(point[:2])
    denominator=np.sqrt((radius+cylindrical)**2+point[2]**2)
    return -2*gm*ellipk(4*radius*cylindrical/denominator**2)/(pi*denominator)


def self_gravity_checks(radius,gm):
    """Exact regular-polygon radial sum, checked against native Newton pairs.

For a point at (R,0), a neighbour at angle 2*pi*k/N contributes
minus (GM/N)/(4*R**2*sin(pi*k/N)) radially. The sum grows logarithmically
as N increases: external-field convergence does not regularize self-gravity.
"""
    rows={}
    for n in (36,72,144):
        bodies,_=solar_system_ring(n);q=states(bodies);points=q[384:,:3]-q[0,:3]
        masses=np.array([b.mass for b in bodies[384:]])
        actual=prepare(masses)(points,np.zeros_like(points))
        magnitude=gm/(4*n*radius**2)*fsum(1/sin(pi*k/n) for k in range(1,n))
        expected=-magnitude*points/radius
        difference=float(np.max(np.linalg.norm(actual-expected,axis=1)))
        if difference>=magnitude*1e-12:raise RuntimeError('Regular polygon self-gravity identity failed')
        rows[str(n)]=dict(inward_acceleration_m_per_s2=magnitude,
            native_analytic_maximum_difference_m_per_s2=difference)
    return rows


def main():
    au,gm=parameters();radius=44*au
    initial,origin=solar_system_ring();q=states(initial)
    sources={}
    for n in (36,72,144):
        for phase in (0,1):
            bodies,_=solar_system_ring(n,phase);v=states(bodies)
            sources[f'{n}_{phase}']=v[384:,:3]-v[0,:3]
    results={}
    for index in list(range(11))+list(range(354,384)):
        point=q[index,:3]-q[0,:3];cylindrical=np.linalg.norm(point[:2])
        clearance=np.hypot(cylindrical-radius,point[2])
        if clearance<=radius*1e-8:raise ValueError('Thin continuous ring singularity too close for field audit')
        exact=uniform_field(point,radius,gm)
        h=min(radius*1e-5,clearance*1e-4)
        gradient=np.array([(8*(potential(point+h*np.eye(3)[i],radius,gm)-potential(point-h*np.eye(3)[i],radius,gm))
            -(potential(point+2*h*np.eye(3)[i],radius,gm)-potential(point-2*h*np.eye(3)[i],radius,gm)))/(12*h) for i in range(3)])
        gradient_error=float(np.linalg.norm(exact+gradient))
        if gradient_error>=1e-8*np.linalg.norm(exact)+1e-26:
            raise RuntimeError('Continuous quadrature/elliptic potential disagree: '+initial[index].name)
        variants={}
        for key,positions in sources.items():
            d=positions-point;distance=np.linalg.norm(d,axis=1)
            field=summed(gm/len(positions)*d/distance[:,None]**3)
            difference=float(np.linalg.norm(field-exact));scale=float(np.linalg.norm(exact))
            variants[key]=dict(vector_m_per_s2=field.tolist(),error_m_per_s2=difference,
                relative_error=difference/scale if scale>1e-25 else None,nearest_point_metres=float(distance.min()))
        results[initial[index].name]=dict(cylindrical_radius_au=float(cylindrical/au),z_au=float(point[2]/au),
            distance_to_continuous_circle_au=float(clearance/au),continuous_vector_m_per_s2=exact.tolist(),
            elliptic_gradient_error_m_per_s2=gradient_error,variants=variants)
    code=('scripts/check_ring_field.py','scripts/build_kuiper_ring.py','src/solar_simulator/kuiper_ring.py',
        'src/solar_simulator/perturbers.py','scripts/kuiper-ring-policy.json',
        'src/solar_simulator/native_forces.py','rust/solar_core/src/relativity.rs',
        'rust/solar_core/src/lib.rs','rust/solar_native/src/lib.rs')
    report=dict(schema=1,epoch_jd_tdb=origin.epoch_jd_tdb,targets=results,target_count=len(results),
        radius_metres=radius,gm_m3_s2=gm,policy_sha256=POLICY_SHA256,manifest_sha256=MANIFEST_SHA256,
        self_gravity=self_gravity_checks(radius,gm),
        checks_passed=True,code_sha256={path:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in code},
        limitations=['Initial positions only; not an annual propagated-orbit error bound.',
            'Thin continuous ring is an external-field comparator; not a regular continuum self-gravity model.',
            'Relative field error alone is not the physical orbit error or an ephemeris uncertainty.'])
    Path('docs/kuiper-ring-field-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    worst=max((value['variants']['36_0']['relative_error'] or 0,name) for name,value in results.items())
    print('Actual 41-body initial fields verified; largest 36-point relative field error',worst,flush=True)


if __name__=='__main__':main()
