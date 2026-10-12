"""Predeclared 32-day conservative Sun/Earth/Moon audit; independent R/Euler RK45."""
import hashlib
import json
from pathlib import Path
import sys
from dataclasses import replace

import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from solar_simulator.ephemerides import solar_system
from solar_simulator.nbody_rotation import integrate, invariants, lunar_initial
from solar_simulator.simulation import G

POLICY = {"energy_relative":1e-8,"angular_momentum_relative":1e-8,"quaternion_norm":1e-8,
          "reference_difference":1e-7,"reference_uncertainty":1e-8,"restart_difference":1e-8}


def reference(bodies, rotation, times, rtol, max_step):
    """Other variables/field: increments, explicit Jacobi, R and body momentum.

    No production field, quaternion, coordinate transform or RHS is called.
    Forces use scalar pairs and MacCullagh's principal-inertia expression.
    """
    names=[b.name for b in bodies]; source=names.index(rotation.body); count=len(bodies)
    masses=np.array([b.mass for b in bodies]); inertia=np.array(rotation.figure.moments)
    p=np.array([[b.position.x,b.position.y,b.position.z] for b in bodies])
    v=np.array([[b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies])
    weights=masses/masses.sum();center=weights@p;drift=weights@v
    p=p-center;v=v-drift
    first,second=names.index("Earth"),names.index("Moon")
    f1=masses[first]/(masses[first]+masses[second]);f2=1-f1

    def encode(values):
        result=values.copy()
        result[first]=f1*values[first]+f2*values[second]
        result[second]=values[second]-values[first]
        return result

    def decode(values):
        result=values.copy()
        result[first]=values[first]-f2*values[second]
        result[second]=values[first]+f1*values[second]
        return result

    anchor=encode(p);vel=encode(v)
    rscale=np.repeat(np.maximum(np.linalg.norm(anchor,axis=1),1.),3)
    vscale=np.repeat(np.maximum(np.linalg.norm(vel,axis=1),1.),3)
    r0=Rotation.from_quat(np.roll(rotation.quaternion,-1)).as_matrix()
    spin=np.array(rotation.angular_momentum)
    scales=np.r_[rscale,vscale,np.ones(9),[np.linalg.norm(spin)]*3]
    initial=np.r_[np.zeros(3*count),vel.ravel(),r0.ravel(),r0.T@spin]/scales

    def rhs(t,scaled):
        y=scaled*scales
        encoded=anchor+y[:3*count].reshape(count,3)
        positions=decode(encoded)
        velocities=y[3*count:6*count].reshape(count,3)
        matrix=y[6*count:6*count+9].reshape(3,3);momentum=y[-3:];omega=momentum/inertia
        acceleration=np.zeros((count,3));torque=np.zeros(3)
        for i in range(count):
            for j in range(i+1,count):
                r=encoded[second] if (i,j)==(first,second) else positions[j]-positions[i]
                if (i,j)==(second,first):r=-encoded[second]
                d=np.linalg.norm(r)
                field=G*r/d**3
                acceleration[i]+=masses[j]*field;acceleration[j]-=masses[i]*field
        for target in range(count):
            if target==source:continue
            r=positions[target]-positions[source]
            if source==second and target==first:r=-encoded[second]
            d=np.linalg.norm(r)
            if d<=rotation.figure.bounding_radius:raise ValueError("Reference outside Q2 domain")
            n=r/d;body_n=matrix.T@n;projection=np.dot(inertia*body_n,body_n)
            force=G*masses[target]/(2*d**4)*((15*projection-3*sum(inertia))*n-6*(matrix@(inertia*body_n)))
            acceleration[target]+=force/masses[target];acceleration[source]-=force/masses[source]
            torque+=3*G*masses[target]/d**3*np.cross(body_n,inertia*body_n)
        x,yw,z=omega
        hat=np.array([[0,-z,yw],[z,0,-x],[-yw,x,0]])
        return np.r_[velocities.ravel(),encode(acceleration).ravel(),(matrix@hat).ravel(),np.cross(momentum,omega)+torque]/scales

    sol=solve_ivp(rhs,(times[0],times[-1]),initial,method="RK45",rtol=rtol,atol=rtol*.01,
        max_step=max_step,t_eval=times)
    if not sol.success or not np.all(np.isfinite(sol.y)):raise ValueError("Invalid independent reference")
    result=[]
    for t,y in zip(times,sol.y.T*scales):
        positions=decode(anchor+y[:3*count].reshape(count,3))+center+drift*(t-times[0])
        velocities=decode(y[3*count:6*count].reshape(count,3))+drift
        matrix=y[6*count:6*count+9].reshape(3,3)
        result.append((positions,velocities,matrix,matrix@y[-3:]))
    return result


def represented(snapshots):
    result=[]
    for bodies,rotations in snapshots:
        p=np.array([[b.position.x,b.position.y,b.position.z] for b in bodies])
        v=np.array([[b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies])
        s=rotations[0]
        matrix=Rotation.from_quat(np.roll(s.quaternion,-1)).as_matrix()
        result.append((p,v,matrix,np.array(s.angular_momentum)))
    return result


def internal_invariants(snapshots,times):
    """Use one fixed translating COM frame; do not hide pair drift by bulk energy."""
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    first=represented(snapshots[:1])[0]
    masses=np.array([b.mass for b in snapshots[0][0]]);weights=masses/masses.sum()
    center=weights@first[0];drift=weights@first[1]
    values=[]
    for t,(bodies,rotations) in zip(times,snapshots):
        transformed=[]
        for b in bodies:
            p=np.array([b.position.x,b.position.y,b.position.z])-center-drift*(t-times[0])
            v=np.array([b.velocity.x,b.velocity.y,b.velocity.z])-drift
            transformed.append(Body(b.name,b.mass,Vector3(*map(float,p)),Vector3(*map(float,v))))
        values.append(invariants(transformed,rotations))
    return values


def differences(a,b,bodies,rotation):
    names=[body.name for body in bodies];earth=names.index("Earth");moon=names.index("Moon")
    initial=represented([(bodies,(rotation,))])[0]
    pair_r=np.linalg.norm(initial[0][moon]-initial[0][earth]);pair_v=np.linalg.norm(initial[1][moon]-initial[1][earth])
    spin=np.linalg.norm(rotation.angular_momentum)
    rscale=max(np.linalg.norm(initial[0],axis=1));vscale=max(np.linalg.norm(initial[1],axis=1))
    metrics={"position":0.,"velocity":0.,"relative_position":0.,"relative_velocity":0.,"attitude":0.,"spin":0.}
    for x,y in zip(a,b):
        values=[np.max(np.linalg.norm(x[0]-y[0],axis=1))/rscale,
                np.max(np.linalg.norm(x[1]-y[1],axis=1))/vscale,
                np.linalg.norm((x[0][moon]-x[0][earth])-(y[0][moon]-y[0][earth]))/pair_r,
                np.linalg.norm((x[1][moon]-x[1][earth])-(y[1][moon]-y[1][earth]))/pair_v,
                np.linalg.norm(x[2]-y[2]),np.linalg.norm(x[3]-y[3])/spin]
        for key,value in zip(metrics,values):metrics[key]=max(metrics[key],float(value))
    return {"components":metrics,"maximum":max(metrics.values())}


def audit():
    base,origin=solar_system(resolved_moon=True)
    times=np.linspace(0.,32*86400.,129);rows=[];kept=[]
    for label,names in [("isolated_pair",{"Earth","Moon"}),("sun_earth_moon",{"Sun","Earth","Moon"})]:
        bodies=[b for b in base if b.name in names];rotations=lunar_initial(bodies,origin);rotation=rotations[0]
        print(label,"production",flush=True)
        kwargs=dict(rtol=1e-11,position_atol=1e-4,velocity_atol=1e-10,relative_pair=("Earth","Moon"),max_step=21600.)
        primary=integrate(bodies,rotations,times,**kwargs)
        strict_rotations=(replace(rotation,quaternion_atol=rotation.quaternion_atol*.03,momentum_atol=rotation.momentum_atol*.03),)
        strict=integrate(bodies,strict_rotations,times,**dict(kwargs,rtol=3e-13,position_atol=3e-6,velocity_atol=3e-12,max_step=10800.))
        native=integrate(bodies,rotations,times,backend="rust",**kwargs)
        print(label,"independent RK45 levels",flush=True)
        refs=[reference(bodies,rotation,times,tol,21600.) for tol in (3e-12,3e-13)]
        inv=internal_invariants(primary,times);energy=np.array([x[0] for x in inv]);l=np.array([[x[2].x,x[2].y,x[2].z] for x in inv])
        q=np.array([s[1][0].quaternion for s in primary])
        diff=differences(represented(primary),refs[-1],bodies,rotation)
        uncertainty=differences(refs[0],refs[1],bodies,rotation)
        # Actual serialization and continuation, not just a restarted solve.
        from solar_simulator.experiment import Settings,create_experiment,advance
        from solar_simulator.storage import from_document,to_document
        experiment=create_experiment(bodies,Settings(86400.,integrator="dop853",rtol=1e-11,position_atol=1e-4,
            velocity_atol=1e-10,relative_pair=("Earth","Moon")),origin=origin,rotations=rotations)
        half=advance(experiment,16);restored=from_document(to_document(half));continued=advance(restored,16)
        whole=advance(experiment,32)
        restart=differences(represented([(whole.bodies,whole.rotations)]),represented([(continued.bodies,continued.rotations)]),bodies,rotation)
        metrics={"energy_relative":float(np.max(abs(energy-energy[0]))/abs(energy[0])),
            "angular_momentum_relative":float(np.max(np.linalg.norm(l-l[0],axis=1))/np.linalg.norm(l[0])),
            "quaternion_norm":float(np.max(abs(np.linalg.norm(q,axis=1)-1))),
            "reference_difference":diff["maximum"],"reference_uncertainty":uncertainty["maximum"],
            "restart_difference":restart["maximum"]}
        rows.append(dict(name=label,body_names=[b.name for b in bodies],initial_document=to_document(experiment),
            invariant_frame="one fixed translating initial COM frame; orbital + spin energy/L",
            energy_normalization_joules=float(abs(energy[0])),angular_momentum_normalization_kg_m2_s=float(np.linalg.norm(l[0])),
            metrics=metrics,reference_components=diff,reference_uncertainty_components=uncertainty,
            production_sensitivity=differences(represented(primary),represented(strict),bodies,rotation),
            python_rust_difference=differences(represented(primary),represented(native),bodies,rotation),
            restart_components=restart,passed=all(metrics[k]<limit for k,limit in POLICY.items())))
        kept.append(primary)
        print(label,metrics,"passed",rows[-1]["passed"],flush=True)
    # Only after free production/reference runs: descriptive DE441 comparison.
    from solar_simulator.orientation import lunar_rotation
    residuals=[]
    for snapshots in kept:
        angles=[]
        for t,(_,rotations) in zip(times,snapshots):
            matrix=Rotation.from_quat(np.roll(rotations[0].quaternion,-1)).as_matrix()
            target,_=lunar_rotation(float(t))
            # Stable angular distance: independent target has tiny SO(3) roundoff.
            angles.append(float(np.linalg.norm(Rotation.from_matrix(matrix.T@target).as_rotvec())))
        residuals.append(angles)
    figure_angles=[float(np.linalg.norm(Rotation.from_matrix(x[2].T@y[2]).as_rotvec()))
        for x,y in zip(represented(kept[0]),represented(kept[1]))]
    paths=["src/solar_simulator/nbody_rotation.py","src/solar_simulator/experiment.py","src/solar_simulator/storage.py",
        "src/solar_simulator/cli.py","src/solar_simulator/convergence.py","src/solar_simulator/rotation.py",
        "src/solar_simulator/spin_initial.py","src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json",
        "src/solar_simulator/coordinates.py","src/solar_simulator/native_forces.py","tests/test_nbody_rotation.py",
        "scripts/assess_nbody_rotation.py"]
    return dict(model="Newtonian ONE rigid Q2 figure + fully interacting point masses; no EIH/tides/prescribed axes",
        policy=POLICY,epoch_jd_tdb=origin.epoch_jd_tdb,frame=origin.frame,sample_times_seconds=times.tolist(),
        production_options=kwargs,reference_rtols=[3e-12,3e-13],reference_atol_over_rtol=.01,
        comparison_after_free_runs=dict(DE441_attitude_residuals_rad=residuals,
            maxima_rad=[max(a) for a in residuals],solar_model_attitude_difference_max_rad=max(figure_angles),
            physical_accuracy_threshold=None,warning="Different physical models; no fit; adding Sun gravity and torque together does not identify each omitted effect"),
        code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},cases=rows,passed=all(r["passed"] for r in rows))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="docs/nbody-rotation-validation.json")
    path=ROOT/parser.parse_args().output
    if path.exists():raise FileExistsError("Preserve original audit; use an explicit new protocol for refinement")
    result=audit()
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    sys.exit(0 if result["passed"] else 1)
