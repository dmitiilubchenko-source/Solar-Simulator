"""Controlled nine-vs-ten-body comparison, keeping epoch, GM and 1PN fixed."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np

from solar_simulator.ephemerides import solar_system, EXPECTED_IDS
from solar_simulator.experiment import create_experiment, Settings, advance
if __package__:
    from .assess_relativity import YEAR, independent_reference
else:
    from assess_relativity import YEAR, independent_reference


def states(bodies):
    return np.array([[b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies])


def sample(bodies,origin,times,physics,*,rtol=1e-13):
    state=create_experiment(bodies,Settings(3600,integrator="dop853",physics=physics,rtol=rtol),origin=origin)
    results=[]
    for time in times:
        if time>state.time:
            state=advance(replace(state,settings=replace(state.settings,dt=float(time-state.time))),1)
        results.append(states(state.bodies))
    return np.array(results)


def errors(actual,expected):
    difference=actual-expected
    return dict(maximum_position_metres=float(np.linalg.norm(difference[...,:3],axis=-1).max()),
                maximum_velocity_m_per_s=float(np.linalg.norm(difference[...,3:],axis=-1).max()))


def main():
    initial,origin=solar_system(resolved_moon=True)
    base_initial,base_origin=solar_system()
    source=Path("docs/solar-system-moon-reference.json")
    base_path=Path("docs/solar-system-reference.json")
    doc=json.loads(source.read_text(encoding="utf-8"));base=json.loads(base_path.read_text(encoding="utf-8"))
    if (doc["dataset_sha256"]!=origin.dataset_sha256 or doc["base_dataset_sha256"]!=base_origin.dataset_sha256
            or doc["gm_sha256"]!=origin.gm_sha256
            or doc["base_reference_sha256"]!=hashlib.sha256(base_path.read_bytes()).hexdigest()
            or doc["frame"]!=origin.frame or doc["center"]!=origin.center or doc["ephemeris"]!=origin.ephemeris
            or doc["units"]!="SI" or [b["id"] for b in doc["bodies"]]!=[399,301,3]
            or [b["id"] for b in base["bodies"]]!=list(EXPECTED_IDS)):
        raise ValueError("Reference does not match pinned datasets")
    epochs=doc["epochs_jd_tdb"]
    times=(np.array(epochs)-origin.epoch_jd_tdb)*86400
    if len(times)!=45 or times[0]!=0 or times[-1]!=YEAR or np.any(np.diff(times)<=0):
        raise ValueError("Expected 45 ordered reference epochs over one year")
    expected=np.stack([np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in doc["bodies"]],axis=1)
    if any([s["jd_tdb"] for s in b["states"]]!=epochs for b in doc["bodies"]):
        raise ValueError("Inconsistent body epochs")
    names=[b.name for b in initial];earth,moon=names.index("Earth"),names.index("Moon")
    weight=initial[moon].mass/(initial[earth].mass+initial[moon].mass)
    reference,consistency=independent_reference(initial,times)
    actual=sample(initial,origin,times,"eih-1pn")
    tighter=sample(initial,origin,times,"eih-1pn",rtol=3e-14)
    newton=sample(initial,origin,times,"newtonian")
    old=sample(base_initial,base_origin,times,"eih-1pn")
    barycentre=actual[:,earth]+weight*(actual[:,moon]-actual[:,earth])
    lunar_relative=actual[:,moon]-actual[:,earth]
    expected_relative=expected[:,1]-expected[:,0]
    dense=times<=32*86400
    annual=np.array([epochs.index(jd) for jd in base["epochs_jd_tdb"]])
    rows=[]
    old_names=[b.name for b in base_initial]
    for b in base["bodies"]:
        predicted=barycentre[annual] if b["id"]==3 else actual[annual,names.index(b["name"])]
        expected_year=np.array([s["position"]+s["velocity"] for s in b["states"]])
        rows.append(dict(name=b["name"],nine_body_jpl=errors(old[annual,old_names.index(b["name"])],expected_year),
            ten_body_jpl=errors(predicted,expected_year)))
    numerical=[dict(name=b.name,agreement=errors(actual[:,i],reference[:,i])) for i,b in enumerate(initial)]
    passed=all(row["agreement"]["maximum_position_metres"]<10
               and row["agreement"]["maximum_velocity_m_per_s"]<1e-4 for row in numerical)
    report=dict(physics="eih-1pn",epoch_jd_tdb=origin.epoch_jd_tdb,duration_seconds=YEAR,samples=len(times),
        dataset_sha256=origin.dataset_sha256,reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        independent_reference_position_consistency_metres=consistency,numerical_agreement=numerical,
        tolerance_sensitivity=errors(actual,tighter),annual_comparison=rows,
        resolved_pair=dict(earth=errors(actual[:,earth],expected[:,0]),moon=errors(actual[:,moon],expected[:,1]),
            barycentre=errors(barycentre,expected[:,2]),moon_relative_to_earth=errors(lunar_relative,expected_relative),
            first_32_days_relative=errors(lunar_relative[dense],expected_relative[dense])),
        newtonian_pair=dict(earth=errors(newton[:,earth],expected[:,0]),moon=errors(newton[:,moon],expected[:,1]),
            barycentre=errors(newton[:,earth]+weight*(newton[:,moon]-newton[:,earth]),expected[:,2]),
            moon_relative_to_earth=errors(newton[:,moon]-newton[:,earth],expected_relative)),
        checks_passed=passed,limitation="45 sampled epochs, not a global bound. Earth and Moon are spherical point masses; no oblateness, spin, tides, asteroids or other resolved moons.")
    Path("docs/moon-validation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,allow_nan=False),flush=True)
    if not passed:
        raise RuntimeError("Resolved Moon numerical agreement targets failed")


if __name__=="__main__":
    main()
