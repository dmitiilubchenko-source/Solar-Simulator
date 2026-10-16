"""Optional REBOUND5.2.2 research comparison, deliberately outside runtime."""
import hashlib
import importlib
from pathlib import Path
import sys

import numpy as np

from scripts.assess_sandbox_planets import states
from solar_simulator.continuous import ContinuousRun
from solar_simulator.simulation import G

VERSION = '5.2.2'
EPSILONS = (1e-9, 1e-11)


def load_library(directory=None):
    """Import a separately installed optional library, never install implicitly."""
    directory=Path(directory).resolve() if directory is not None else None
    if directory is not None and not (directory/'rebound/__init__.py').is_file():
        raise ValueError('Explicit REBOUND directory does not contain the package')
    if directory is not None:
        sys.path.insert(0,str(directory))
    try:
        library=importlib.import_module('rebound')
    except ModuleNotFoundError as error:
        raise RuntimeError('Install optional research-ias15 requirements separately') from error
    finally:
        if directory is not None:
            sys.path.pop(0)
    if directory is not None and Path(library.__file__).resolve().parent.parent!=directory:
        raise RuntimeError('A different REBOUND import is already active')
    if library.__version__!=VERSION:
        raise RuntimeError('Research comparison requires REBOUND '+VERSION)
    return library


def library_hashes(library):
    root=Path(library.__file__).resolve().parent.parent
    files=list((root/'rebound').rglob('*.py'))+list(root.glob('librebound*'))
    files=[path for path in files if path.is_file()]
    if not any(path.suffix in ('.pyd','.so','.dll','.dylib') for path in files):
        raise RuntimeError('REBOUND shared library not found for provenance')
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def validate_input(seed,times):
    if (len(seed.bodies)!=2 or seed.time!=0 or seed.settings.physics!='newtonian'
            or seed.settings.figures or seed.rotations or seed.initial_rotations
            or seed.events or seed.halted or seed.dissipated_energy or seed.model_energy_offset
            or any(body.radius for body in seed.bodies)):
        raise ValueError('IAS15 research accepts only two Newtonian point masses at t0')
    times=np.asarray(times,dtype=float)
    if (times.ndim!=1 or len(times)<2 or times[0]!=0 or not np.all(np.isfinite(times))
            or not np.all(np.diff(times)>0)):
        raise ValueError('Expected a strictly increasing finite epoch grid starting at zero')
    if not np.isfinite(seed.settings.dt) or seed.settings.dt<=0:
        raise ValueError('Packet interval must be finite and positive')
    if not np.all(np.isfinite(states(seed.bodies))) or any(not np.isfinite(b.mass) or b.mass<=0 for b in seed.bodies):
        raise ValueError('Expected finite initial states and positive finite masses')
    return times


def packet_end(current,target,dt):
    """Same floating-point endpoint expression as ContinuousRun.next(1)."""
    end=min(current+dt,float(target)) if dt<=target-current else float(target)
    if end<=current:
        raise ValueError('Packet endpoint cannot advance at current floating precision')
    return end


def ias_trajectory(seed,times,library,epsilon,*,count_forces=False):
    times=validate_input(seed,times)
    if epsilon not in EPSILONS:
        raise ValueError('Use one of the two predeclared IAS15 epsilon levels')
    sim=library.Simulation()
    sim.G=G
    sim.integrator='ias15'
    sim.integrator.epsilon=epsilon
    sim.integrator.adaptive_mode='PRS23'
    sim.integrator.min_dt=0.
    sim.gravity='basic'
    sim.softening=0.
    sim.dt=seed.settings.dt/200
    force_calls=0
    if count_forces:
        def counter(pointer):
            nonlocal force_calls
            force_calls+=1
        sim.additional_forces=counter
    initial=states(seed.bodies)
    for body,row in zip(seed.bodies,initial):
        sim.add(m=float(body.mass),x=float(row[0]),y=float(row[1]),z=float(row[2]),
                vx=float(row[3]),vy=float(row[4]),vz=float(row[5]))
    assert (sim.G==G and sim.gravity=='basic' and sim.softening==0
        and sim.integrator.epsilon==epsilon and sim.integrator.adaptive_mode=='PRS23'
        and sim.integrator.min_dt==0 and sim.N==2)
    assert [particle.m for particle in sim.particles]==[body.mass for body in seed.bodies]
    def snapshot():
        return np.array([[p.x,p.y,p.z,p.vx,p.vy,p.vz] for p in sim.particles])
    np.testing.assert_array_equal(snapshot(),initial)
    values=[];bounds=[]
    for epoch in times:
        while sim.t<epoch:
            end=packet_end(sim.t,epoch,seed.settings.dt)
            sim.integrate(end,exact_finish_time=1)
            if sim.t!=end:
                raise RuntimeError('IAS15 did not reach the exact packet endpoint')
            bounds.append(end)
        values.append(snapshot())
    values=np.array(values)
    if not np.all(np.isfinite(values)):
        raise ValueError('Nonfinite IAS15 output')
    return values,dict(steps_done=int(sim.steps_done),packets=len(bounds),
        packet_endpoints=bounds,force_evaluations=force_calls if count_forces else None,
        epsilon=epsilon,adaptive_mode='PRS23',initial_step_seconds=seed.settings.dt/200)


def dop_trajectory(seed,times):
    times=validate_input(seed,times)
    session=ContinuousRun(seed,float(times[-1]))
    current=seed;values=[];bounds=[]
    for epoch in times:
        while current.time<epoch:
            current=session.next(1,until=float(epoch))
            bounds.append(current.time)
        values.append(states(current.bodies))
    return np.array(values),dict(**session.statistics,packet_endpoints=bounds)
