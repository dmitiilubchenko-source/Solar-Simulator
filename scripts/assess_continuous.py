"""Independent checks and paired cost of explicitly selected DOP853 continuation."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from math import cos, sin, sqrt, pi, fsum, dist
from pathlib import Path
import statistics
from time import perf_counter
from unittest.mock import patch

import numpy as np

from scripts.assess_sandbox_planets import states, errors
from scripts.profile_catalog import scientific
from solar_simulator.cli import report
from solar_simulator.continuous import ContinuousRun
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.simulation import Body, G, AU, SUN_MASS, EARTH_MASS
from solar_simulator.storage import load, save, to_document
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[1]


def invariant_rows(bodies):
    p,v,m = states(bodies)[:,:3],states(bodies)[:,3:],np.array([b.mass for b in bodies])
    energy=fsum(.5*mass*fsum(x*x for x in velocity) for mass,velocity in zip(m,v))
    energy+=fsum(-G*m[i]*m[j]/dist(p[i],p[j]) for i in range(len(m)) for j in range(i+1,len(m)))
    linear=np.array([fsum(m*v[:,k]) for k in range(3)])
    angular=np.array([fsum(m*(p[:,(k+1)%3]*v[:,(k+2)%3]-p[:,(k+2)%3]*v[:,(k+1)%3])) for k in range(3)])
    return energy,linear,angular


def kepler(tight=False,legacy=False):
    axis=np.array([1.,2.,-1.]);axis/=np.linalg.norm(axis)
    tangent=np.cross(axis,np.array([0.,1.,1.]));tangent/=np.linalg.norm(tangent)
    rate=sqrt(G*(SUN_MASS+EARTH_MASS)/AU**3)
    period=2*pi/rate
    fraction=EARTH_MASS/(SUN_MASS+EARTH_MASS)
    offset,drift=np.array([3e9,-2e9,1e9]),np.array([75.,-50.,25.])
    times=np.unique(np.concatenate((np.linspace(0,2*period,51),
        period*np.array([.0001,.001,.01,.999,1.0001,1.001,1.01,1.999,1.9999]))))
    results={}
    for e in (0.,.5,.95):
        relative=AU*(1-e)*axis
        velocity=AU*rate*sqrt((1+e)/(1-e))*tangent
        bodies=[Body("A",SUN_MASS,Vector3(*(offset-fraction*relative)),Vector3(*(drift-fraction*velocity))),
                Body("B",EARTH_MASS,Vector3(*(offset+(1-fraction)*relative)),Vector3(*(drift+(1-fraction)*velocity)))]
        initial_energy,initial_p,initial_l=invariant_rows(bodies)
        p_scale=sum(b.mass*b.velocity.magnitude() for b in bodies)
        rows={}
        for rtol in (1e-12,3e-14):
            state=create_experiment(bodies,Settings(period/50,backend="rust",integrator="dop853",
                relative_pair=("A","B"),rtol=rtol,
                position_atol=1e-7 if tight else 1e-3,velocity_atol=1e-13 if tight else 1e-9))
            session=None if legacy else ContinuousRun(state,float(times[-1]))
            current=state
            maximum_p=maximum_v=energy_drift=angular_drift=linear_drift=0.
            for time in times:
                if legacy:
                    current=(advance(replace(state,settings=replace(state.settings,dt=float(time))),1)
                             if time>0 else state)
                while current.time < time:
                    current=session.next(1,until=float(time))
                assert current.time==time
                mean=(rate*time)%(2*pi)
                lo,hi=mean-e,mean+e
                for _ in range(90):
                    middle=(lo+hi)/2
                    if middle-e*sin(middle)<mean:lo=middle
                    else:hi=middle
                anomaly=(lo+hi)/2
                expected_p=AU*((cos(anomaly)-e)*axis+sqrt(1-e*e)*sin(anomaly)*tangent)
                expected_v=AU*rate/(1-e*cos(anomaly))*(-sin(anomaly)*axis+sqrt(1-e*e)*cos(anomaly)*tangent)
                actual=states(current.bodies)[1]-states(current.bodies)[0]
                maximum_p=max(maximum_p,dist(actual[:3],expected_p))
                maximum_v=max(maximum_v,dist(actual[3:],expected_v))
                energy,linear,angular=invariant_rows(current.bodies)
                energy_drift=max(energy_drift,abs(energy-initial_energy)/abs(initial_energy))
                angular_drift=max(angular_drift,np.linalg.norm(angular-initial_l)/np.linalg.norm(initial_l))
                linear_drift=max(linear_drift,np.linalg.norm(linear-initial_p)/p_scale)
            passed=(maximum_p<.1 and maximum_v<1e-6 and max(energy_drift,angular_drift,linear_drift)<1e-10)
            rows[str(rtol)]=dict(position_metres=maximum_p,velocity_m_per_s=maximum_v,
                relative_energy_drift=energy_drift,relative_angular_drift=angular_drift,
                scaled_momentum_drift=linear_drift,checks_passed=passed,
                **(session.statistics if session else dict(legacy_from_same_initial_per_epoch=True)))
        results[str(e)]=rows
        print("Kepler",e,rows,flush=True)
    return dict(samples=len(times),periods=2,results=results,tight_absolute_tolerances=tight,legacy_restart=legacy,
        checks_passed=all(row["3e-14"]["checks_passed"] for row in results.values()),
        loose_level_is_sensitivity_only=True)


def trajectory(seed,times,mode,diagnostics=False):
    session=ContinuousRun(seed,float(times[-1])) if mode=="continuous" else None
    current=seed
    values=[]
    packets=0
    for time in times:
        while current.time < time:
            current=(session.next(20,until=float(time)) if session else
                advance(replace(current,settings=replace(seed.settings,dt=min(seed.settings.dt,
                    (float(time)-current.time)/20))),20))
            # Retain original dt metadata when the final interval is fractional.
            current=replace(current,settings=seed.settings)
            packets+=1
            if diagnostics:report(current)
        assert current.time==time
        values.append(states(current.bodies))
    return np.array(values),current,(session.statistics if session else dict(packets=packets))


def catalog(output):
    seed=scientific("solar-system-asteroids-catalog")
    times=np.arange(11,dtype=float)*72000.
    initial=to_document(seed)
    before,_,_=trajectory(seed,times,"restart")
    after,last,stats=trajectory(seed,times,"continuous")
    repeat,_,_=trajectory(seed,times,"continuous")
    assert np.array_equal(after,repeat) and to_document(seed)==initial
    differences=errors(after,before)
    names=[b.name for b in seed.bodies];e,m=names.index("Earth"),names.index("Moon")
    relative=errors(after[:,m]-after[:,e],before[:,m]-before[:,e])
    per_body={name:errors(after[:,i],before[:,i]) for i,name in enumerate(names)}
    passed=(all(v["position_metres"]<.1 and v["velocity_m_per_s"]<1e-6 for v in per_body.values())
            and relative["position_metres"]<.01 and relative["velocity_m_per_s"]<1e-6)
    path=output.with_name(output.stem+"-pause.json")
    if path.exists():raise FileExistsError("Preserve checkpoint")
    session=ContinuousRun(seed,float(times[-1]))
    for _ in range(5):paused=session.next()
    save(paused,path)
    fresh=ContinuousRun(load(path),float(times[-1]))
    while not fresh.finished:resumed=fresh.next()
    resumed_difference=errors(states(resumed.bodies),states(last.bodies))
    resumed_pair=errors((states(resumed.bodies)[m]-states(resumed.bodies)[e])[None,:],
                        (states(last.bodies)[m]-states(last.bodies)[e])[None,:])
    restart_passed=(resumed_difference["position_metres"]<.1 and resumed_difference["velocity_m_per_s"]<1e-6
        and resumed_pair["position_metres"]<.01 and resumed_pair["velocity_m_per_s"]<1e-6)
    cost={}
    for diagnostics in (False,True):
        raw={mode:[] for mode in ("restart","continuous")}
        for mode in raw:trajectory(seed,times,mode,diagnostics)
        for iteration in range(3):
            for mode in (("restart","continuous") if iteration%2==0 else ("continuous","restart")):
                start=perf_counter();values,_,_=trajectory(seed,times,mode,diagnostics)
                elapsed=perf_counter()-start
                np.testing.assert_array_equal(values,before if mode=="restart" else after)
                raw[mode].append(elapsed)
        key="physics_with_report" if diagnostics else "physics"
        cost[key]={mode:dict(raw_seconds=samples,median_seconds=statistics.median(samples)) for mode,samples in raw.items()}
    cost_gain=1-cost["physics_with_report"]["continuous"]["median_seconds"]/cost["physics_with_report"]["restart"]["median_seconds"]
    np.savez_compressed(output.with_suffix(".npz"),times=times,restart=before,continuous=after)
    # Count old RHS in a separate un-timed run.
    from solar_simulator import accuracy
    rhs=[];original=accuracy.solve_ivp
    def observed(*a,**kw):
        result=original(*a,**kw);rhs.append(result.nfev);return result
    with patch("solar_simulator.accuracy.solve_ivp",observed):trajectory(seed,times,"restart")
    return dict(settings=asdict(seed.settings),origin=asdict(seed.origin),samples=len(times),
        duration_seconds=float(times[-1]),same_output_times=True,per_body_agreement=per_body,
        relative_agreement=relative,numerical_agreement_passed=passed,resume_difference=resumed_difference,
        resume_relative_difference=resumed_pair,resume_check_passed=restart_passed,
        cost=cost,cost_gain=cost_gain,required_cost_gain=.15,cost_check_passed=cost_gain>=.15,
        rhs_calls=dict(restart=sum(rhs),continuous=stats["rhs_calls"]),
        model_energy_residual=abs(report(last)["energy_budget_residual_joules"])/abs(report(last)["energy_joules"]),
        checks_passed=passed and restart_passed and cost_gain>=.15,
        independent_trajectory_reference=False,physics_fitted=False)


def year(output):
    from scripts.assess_dense_jpl import verified_sources,validate_reference,residuals
    from solar_simulator.ephemerides import RESOLVED_IDS
    strict=json.loads((ROOT/"docs/strict-profile-validation.json").read_bytes())
    verified_sources(strict)
    cache=ROOT/".tools/qualification138/production139.npz"
    assert hashlib.sha256(cache.read_bytes()).hexdigest()==strict["cache_sha256"]
    seed=load(ROOT/"docs/solar-sandbox-strict-checkpoint.json")
    names=[b.name for b in seed.bodies]
    with np.load(cache,allow_pickle=False) as data:
        times,reference,old=[data[k].copy() for k in ("times","reference","rust_tighter")]
    assert np.array_equal(old[0],states(seed.bodies))
    start=perf_counter();actual,final,statistics_=trajectory(seed,times,"continuous")
    elapsed=perf_counter()-start
    numeric={name:errors(actual[:,i],reference[:,i]) for i,name in enumerate(names)}
    e,m=names.index("Earth"),names.index("Moon")
    relative=errors(actual[:,m]-actual[:,e],reference[:,m]-reference[:,e])
    numeric_passed=(all(v["position_metres"]<10 and v["velocity_m_per_s"]<1e-4 for v in numeric.values())
        and relative["position_metres"]<.1 and relative["velocity_m_per_s"]<1e-5)
    np.savez_compressed(output.with_suffix(".npz"),times=times,continuous=actual)
    # Load primary JPL data only after free integration, no fitting.
    dense=json.loads((ROOT/"docs/qualification-grid-reference.json").read_bytes())
    grid=dense["epochs_jd_tdb"]
    assert np.array_equal(times,(np.array(grid)-seed.origin.epoch_jd_tdb)*86400)
    expected=validate_reference(dense,seed.origin,names,RESOLVED_IDS,grid)
    from scripts.fetch_ephemerides import parse_result
    for body in dense["bodies"]:
        rows=[];offset=0
        for request in body["requests"]:
            path=ROOT/".tools/qualification144/jpl-batches"/f"horizons-{body['id']}-{offset:03d}.json"
            raw=path.read_bytes()
            assert hashlib.sha256(raw).hexdigest()==request["response_sha256"]
            rows.extend(parse_result(json.loads(raw),body["id"],request["epochs_jd_tdb"]))
            offset+=len(request["epochs_jd_tdb"])
        assert rows==body["states"]
    jpl=residuals(actual,expected,names,grid)
    return dict(settings=asdict(seed.settings),origin=asdict(seed.origin),samples=len(times),
        numerical_errors=numeric,relative_numerical_error=relative,numerical_checks_passed=numeric_passed,
        reference_cache_sha256=strict["cache_sha256"],reference_uncertainty=json.loads(
            (ROOT/"docs/qualification-grid-validation.json").read_bytes())["reference_convergence"],
        **jpl,**statistics_,wall_seconds=elapsed,model_energy_residual=abs(report(final)["energy_budget_residual_joules"])/abs(report(final)["energy_joules"]),
        checks_passed=numeric_passed and jpl["physical_goals_passed"],legacy_difference=errors(actual,old))


def reference(output,duration,levels):
    from scripts.assess_relative_coordinates import independent_reference
    from scripts.assess_sandbox_models import load_oracle,figure_reference
    seed=scientific("solar-system-asteroids-catalog")
    times=np.linspace(0.,duration,11)
    start=perf_counter()
    expected,convergence=independent_reference(seed.bodies,seed.settings.figures,times,
        levels=levels,cache_name=str(output.with_suffix("").relative_to(ROOT/".tools")),
        acceleration_function=load_oracle(),figure_acceleration_function=figure_reference)
    elapsed=perf_counter()-start
    actual,_,stats=trajectory(seed,times,"continuous")
    names=[b.name for b in seed.bodies];e,m=names.index("Earth"),names.index("Moon")
    numeric={name:errors(actual[:,i],expected[:,i]) for i,name in enumerate(names)}
    relative=errors(actual[:,m]-actual[:,e],expected[:,m]-expected[:,e])
    passed=(all(v["position_metres"]<10 and v["velocity_m_per_s"]<1e-4 for v in numeric.values())
        and relative["position_metres"]<.1 and relative["velocity_m_per_s"]<1e-5)
    return dict(duration_seconds=duration,settings=asdict(seed.settings),origin=asdict(seed.origin),
        levels=levels,reference_convergence=convergence,numerical_errors=numeric,
        relative_numerical_error=relative,wall_seconds=elapsed,checks_passed=passed,**stats)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case",choices=("kepler","kepler-tight","kepler-legacy","kepler-legacy-tight",
        "catalog","year","pilot","reference"))
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if output.exists() or output.with_suffix(".npz").exists():raise FileExistsError("Preserve previous audit")
    output.parent.mkdir(parents=True,exist_ok=True)
    from scripts.assess_sandbox_models import source_hashes
    sources=source_hashes()
    for name in ("src/solar_simulator/continuous.py","scripts/assess_continuous.py"):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    import scipy
    installed={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        ROOT/".venv/Lib/site-packages/scipy/integrate/_ivp/rk.py",
        ROOT/".venv/Lib/site-packages/scipy/integrate/_ivp/base.py")}
    if args.case.startswith("kepler"):
        result=kepler(tight="tight" in args.case,legacy="legacy" in args.case)
    elif args.case=="catalog":result=catalog(output)
    elif args.case=="year":result=year(output)
    else:result=reference(output,7200. if args.case=="pilot" else 720000.,
        ((1e-13,1800.),(3e-14,900.)))
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in sources.items())
    receipt=dict(protocol="docs/continuous-integration-protocol.md",case=args.case,source_sha256=sources,
        installed_scipy_source_sha256=installed,scipy=scipy.__version__,result=result)
    with output.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(receipt,stream,ensure_ascii=False,indent=2,allow_nan=False,default=json_scalar);stream.write("\n")
    print("Saved",output,"checks_passed",result["checks_passed"],flush=True)
    if not result["checks_passed"]:raise SystemExit(1)


def json_scalar(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError("Unsupported JSON scalar: "+type(value).__name__)


if __name__=="__main__":main()
