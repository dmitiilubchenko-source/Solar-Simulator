"""Isolate the solar J2 contribution on the unchanged DE441 benchmark."""
from dataclasses import replace
import hashlib
import json
from math import atan2,pi
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from solar_simulator.accuracy import evolve_accurate
from solar_simulator.ephemerides import solar_system
from solar_simulator.oblateness import solar_j2,earth_moon_quadrupoles,SOLAR_PROFILE_SHA256
from solar_simulator.simulation import AU
from solar_simulator.vector3 import Vector3

PLANET_REFERENCE_SHA256="aad15839a53f1c709c0e84a8202ffc4f9b6d13837f2bdeed2d28abb4c2ed6995"
BENCHMARK_OPTIONS = dict(relative_pair=["Earth", "Moon"], rtol=1e-13,
    position_atol_metres=1e-5, velocity_atol_m_per_s=1e-11,
    tighter=dict(rtol=3e-14, position_atol_metres=1e-6, velocity_atol_m_per_s=1e-12),
    independent_method="RK45 in AU/year", independent_atol=1e-17,
    independent_levels=[dict(rtol=1e-13, maximum_step_seconds=1800.),
                        dict(rtol=3e-14, maximum_step_seconds=900.)])

if __package__:
    from .assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from .assess_relativity import YEAR,mercury_pair
    from .assess_orientation import sample
    from .assess_oblateness import pair_errors
    from .assess_resolved_moon import errors,states
else:
    from assess_relative_coordinates import independent_reference,relative_states,REFERENCE_SHA256
    from assess_relativity import YEAR,mercury_pair
    from assess_orientation import sample
    from assess_oblateness import pair_errors
    from assess_resolved_moon import errors,states


def equatorial_precession(figure,*,orbits=5):
    """Isolated Newtonian equatorial orbit: analytic J2 apsidal advance."""
    bodies,period,_=mercury_pair()
    axis=np.array(figure.axis)
    u=np.cross(np.array([1.,0.,0.]),axis); u/=np.linalg.norm(u)
    w=np.cross(axis,u)
    def rotate(v):
        return Vector3(*map(float,v.x*u+v.y*w+v.z*axis))
    bodies=[replace(b,position=rotate(b.position),velocity=rotate(b.velocity)) for b in bodies]
    a,e=.38709893*AU,.20563
    expected=3*pi*figure.coefficient*(figure.reference_radius/a)**2/(1-e*e)**2
    def radial(state):
        return state[1].position.subtract(state[0].position).dot(state[1].velocity.subtract(state[0].velocity))
    measured=[]
    for figures in ((),(figure,)):
        state=bodies
        angles=[0.]
        def evolve(value,duration):
            return evolve_accurate(value,float(duration),figures=figures,relative_pair=("Sun","Mercury"),
                rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)
        for _ in range(orbits*32+4):
            previous=state
            state=evolve(previous,period/32)
            if radial(previous)<0<radial(state):
                t=brentq(lambda t: radial(evolve(previous,t)) if t>0 else radial(previous),0,period/32,xtol=1e-8)
                event=evolve(previous,t)
                point=event[1].position.subtract(event[0].position)
                r=np.array([point.x,point.y,point.z])
                angles.append(atan2(r@w,r@u))
        if len(angles)<orbits+1:
            raise RuntimeError("Pericentres not found")
        measured.append(float(np.diff(angles[:orbits+1]).mean()))
    result=dict(orbits=orbits,expected_radians_per_orbit=expected,
        newtonian_spurious_radians_per_orbit=measured[0],solar_j2_radians_per_orbit=measured[1],
        measured_increment_radians_per_orbit=measured[1]-measured[0])
    result["relative_error"]=abs((measured[1]-measured[0])/expected-1)
    if result["relative_error"]>.01:
        raise RuntimeError(f"Solar J2 analytic precession failed: {result}")
    return result


def planetary_errors(actual,initial,times,document):
    names=[b.name for b in initial]
    expected_times=(np.array(document["epochs_jd_tdb"])-document["epochs_jd_tdb"][0])*86400
    indices=[int(np.flatnonzero(times==t)[0]) for t in expected_times]
    result={}
    for record in document["bodies"]:
        if record["name"]=="Earth-Moon":
            e,m=names.index("Earth"),names.index("Moon")
            fraction=initial[m].mass/(initial[e].mass+initial[m].mass)
            values=actual[:,e]+fraction*(actual[:,m]-actual[:,e])
        else:
            values=actual[:,names.index(record["name"])]
        expected=np.array([s["position"]+s["velocity"] for s in record["states"]])
        result[record["name"]]=errors(values[indices],expected)
    return result


def main():
    source=Path("docs/solar-system-moon-reference.json")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=REFERENCE_SHA256:
        raise ValueError("Pinned JPL pair reference changed")
    pair=json.loads(source.read_text())
    planets_source=Path("docs/solar-system-reference.json")
    if hashlib.sha256(planets_source.read_bytes()).hexdigest()!=PLANET_REFERENCE_SHA256:
        raise ValueError("Pinned JPL planet reference changed")
    planets=json.loads(planets_source.read_text())
    initial,origin=solar_system(resolved_moon=True)
    _,other_origin=solar_system()
    if (planets["dataset_sha256"]!=other_origin.dataset_sha256 or planets["units"]!="SI"
            or planets["frame"]!=origin.frame or planets["center"]!=origin.center
            or planets["ephemeris"]!=origin.ephemeris or planets["epochs_jd_tdb"][0]!=origin.epoch_jd_tdb):
        raise ValueError("Planet reference does not match the benchmark")
    times=(np.array(pair["epochs_jd_tdb"])-origin.epoch_jd_tdb)*86400
    expected=np.stack([np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in pair["bodies"]],axis=1)
    base=earth_moon_quadrupoles(initial,origin)
    solar=solar_j2(initial,origin)
    models={"without_solar_j2":(base,{}),"solar_j2":(solar+base,{}),
        "solar_j2_tighter":(solar+base,dict(rtol=3e-14,position_atol=1e-6,velocity_atol=1e-12))}
    values,measurements={},{}
    for name,(figures,options) in models.items():
        actual,diagnostics=sample(initial,origin,times,figures,relative_pair=("Earth","Moon"),
            **dict(dict(position_atol=1e-5,velocity_atol=1e-11),**options))
        values[name]=actual
        measurements[name]=dict(pair=pair_errors(actual,expected,initial,times),
            planets=planetary_errors(actual,initial,times,planets),**diagnostics)
        print(name,measurements[name]["pair"],flush=True)
    precession=equatorial_precession(solar[0])
    print("Solar J2 analytic precession",precession,flush=True)
    reference,convergence=independent_reference(initial,solar+base,times,
        levels=((1e-13,1800.),(3e-14,900.)),cache_name="solar-j2-reference-progress")
    actual=values["solar_j2"]
    agreement=errors(actual,reference)
    relative_agreement=errors(relative_states(actual,initial),relative_states(reference,initial))
    def differences(a,b):
        return dict(all_bodies=errors(a,b),moon_relative_to_earth=errors(relative_states(a,initial),relative_states(b,initial)))
    passed=agreement["maximum_position_metres"]<1 and relative_agreement["maximum_position_metres"]<.1
    report=dict(physics="EIH 1PN + prescribed Earth/Moon J2/C22 + fixed solar J2",epoch_jd_tdb=origin.epoch_jd_tdb,
        duration_seconds=YEAR,samples=len(times),dataset_sha256=origin.dataset_sha256,
        pair_reference_sha256=REFERENCE_SHA256,planet_reference_sha256=hashlib.sha256(planets_source.read_bytes()).hexdigest(),
        solar_profile_sha256=SOLAR_PROFILE_SHA256,options=BENCHMARK_OPTIONS,variants=measurements,
        solar_j2_increment=differences(values["solar_j2"],values["without_solar_j2"]),
        tolerance_sensitivity=differences(values["solar_j2"],values["solar_j2_tighter"]),
        independent_reference_convergence=convergence,numerical_agreement=agreement,
        moon_relative_numerical_agreement=relative_agreement,analytic_equatorial_precession=precession,
        checks_passed=passed,
        limitation="Only solar J2 added; fixed solar pole and reaction, no solar spin/relativistic spin terms/mass loss, higher harmonics, asteroids, tides, quad/quad or mixed figure/1PN terms. Lunar orientation still prescribed. Local tolerances and sampled numerical agreement are not global error bounds.")
    Path("docs/solar-j2-validation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    np.savez_compressed(".tools/solar-j2-states.npz",times=times,reference=reference,**values)
    print("checks_passed",passed,"independent agreement",agreement,relative_agreement,flush=True)
    if not passed:
        raise RuntimeError("Solar J2 independent agreement failed")


if __name__=="__main__":
    main()
