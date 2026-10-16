"""Independent Kepler and balance checks of bounded target-time packets."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_sandbox_branch import PERIOD, arrays, balances, initial, kepler
from solar_simulator.experiment import advance
from solar_simulator.storage import to_document
from solar_simulator.time_control import advance_towards

ROOT=Path(__file__).resolve().parents[1]
TARGET=.731234*PERIOD


def explicit_packet(state,target,batch):
    """Old public API, with a manually specified terminal interval."""
    settings=state.settings
    remaining=target-state.time
    if settings.integrator == "dop853":
        if remaining >= settings.dt*batch:
            return advance(state,batch)
        result=advance(replace(state,settings=replace(settings,dt=remaining)),1)
    else:
        full=min(batch,int(remaining/settings.dt))
        if full: state=advance(state,full)
        if full == batch or state.time == target: return state
        result=advance(replace(state,settings=replace(settings,dt=target-state.time)),1)
    return replace(result,settings=settings)


def sample(state,batch,controlled):
    original=to_document(state)
    e0,_,j0=balances(state.bodies)
    start=perf_counter(); packets=0
    max_energy=max_angular=0.
    while state.time < TARGET:
        state=(advance_towards(state,TARGET,batch) if controlled else explicit_packet(state,TARGET,batch))
        packets+=1
        e,_,j=balances(state.bodies)
        max_energy=max(max_energy,abs(e-e0)/abs(e0))
        max_angular=max(max_angular,float(np.linalg.norm(j-j0)/np.linalg.norm(j0)))
    elapsed=perf_counter()-start
    assert state.time == TARGET
    assert to_document(state)["settings"] == original["settings"]
    p,v,_=arrays(state.bodies); r_expected,v_expected=kepler(TARGET)
    return state,dict(position_metres=float(np.linalg.norm(p[1]-p[0]-r_expected)),
                      velocity_m_per_s=float(np.linalg.norm(v[1]-v[0]-v_expected)),
                      relative_energy_drift=max_energy,relative_angular_momentum_drift=max_angular,
                      wall_seconds=elapsed,packets=packets,final_time_seconds=state.time)


def main():
    results=[]
    for backend in ("python","rust"):
        dop=[]; final_positions=[]
        for batch in (1,7,64):
            _,state,_=initial(backend,"dop853")
            old_snapshot=to_document(state)
            before,old=sample(state,batch,False)
            after,new=sample(state,batch,True)
            assert to_document(state) == old_snapshot
            exact=to_document(before) == to_document(after)
            assert exact
            p,_,_=arrays(after.bodies); final_positions.append(p[1]-p[0])
            passed=(new["position_metres"]<10 and new["velocity_m_per_s"]<1e-5
                    and new["relative_energy_drift"]<1e-10 and new["relative_angular_momentum_drift"]<1e-10)
            dop.append(dict(batch=batch,before=old,after=new,same_partition_exact=exact,checks_passed=passed))
        partition_difference=max(float(np.linalg.norm(p-final_positions[0])) for p in final_positions)
        verlet=[]
        for count in (1024,2048,4096):
            _,state,_=initial(backend,"verlet",count)
            before,old=sample(state,127,False); after,new=sample(state,127,True)
            exact=to_document(before) == to_document(after)
            assert exact
            verlet.append(dict(steps_per_period=count,before=old,after=new,same_partition_exact=exact))
        ratios=[verlet[i]["after"]["position_metres"]/verlet[i+1]["after"]["position_metres"] for i in range(2)]
        results.append(dict(backend=backend,dop853=dop,partition_position_difference_metres=partition_difference,
                            verlet=verlet,convergence_ratios=ratios,
                            checks_passed=all(r["checks_passed"] for r in dop)
                            and partition_difference<1 and all(3.8<r<4.2 for r in ratios)))
    names=["scripts/assess_time_control.py","scripts/assess_sandbox_branch.py",
           "src/solar_simulator/time_control.py","src/solar_simulator/experiment.py",
           "src/solar_simulator/accuracy.py","src/solar_simulator/simulation.py"]
    import scipy,platform
    report=dict(protocol="docs/time-control-protocol.md",units="SI",physics="newtonian-point-masses",
                target_seconds=TARGET,target_period_fraction=.731234,
                versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
                source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},
                results=results,checks_passed=all(r["checks_passed"] for r in results),
                limitations="One analytic tilted binary. No new JPL accuracy qualification. Before/after share packet partitions; different DOP853 partitions need not agree bitwise. Single wall-time observations include balances, not GUI or a speedup benchmark.")
    (ROOT/"docs/time-control-validation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,allow_nan=False))
    if not report["checks_passed"]: raise RuntimeError("Predeclared target-time criteria failed")


if __name__ == "__main__": main()
