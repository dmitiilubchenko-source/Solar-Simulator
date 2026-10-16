"""Independent motion/lifecycle checks for the explicitly selected session."""
from dataclasses import replace
from math import dist, fsum, hypot

import numpy as np
import pytest

from solar_simulator.continuous import ContinuousRun
from solar_simulator.experiment import Settings, create_experiment
from solar_simulator.simulation import Body
from solar_simulator.storage import load, save, to_document
from solar_simulator.vector3 import Vector3


def free():
    return create_experiment([Body("free", 1e20, Vector3(5.,6.,7.),Vector3(2.,-3.,4.))],
        Settings(3.,backend="rust",integrator="dop853"))


def test_exact_packet_endpoints_do_not_expose_future_or_mutable_buffers(tmp_path):
    initial = free()
    before = to_document(initial)
    session = ContinuousRun(initial, 10.25)
    first = session.next(2)
    assert first.time == 6. and first.bodies[0].position.distance_to(Vector3(17.,-12.,31.)) == 0.
    assert session._solver.t == 6. and session._solver.status == "finished"
    path = tmp_path/"physical.json"
    save(first,path)
    first.bodies[0] = replace(first.bodies[0], mass=7.)
    first.bodies[0].position.x = -1.  # Nor can mutable vectors in snapshots.
    first.initial.clear()
    initial.bodies.clear()   # Neither can a caller's original list.
    second = session.next(2)
    assert second.time == 10.25 and second.bodies[0].position.distance_to(Vector3(25.5,-24.75,48.)) == 0.
    assert second.bodies[0].mass == 1e20 and session.finished
    assert session._solver.t == 10.25
    assert to_document(session.next()) == to_document(second)
    restored = ContinuousRun(load(path),10.25).next(2)
    assert to_document(restored) == to_document(second)
    assert before["time"] == 0.  # Original document retained.


def test_failed_packet_preserves_committed_snapshot_and_cannot_resume(monkeypatch):
    session = ContinuousRun(free(),20.)
    first = session.next(2)
    def broken(*args):
        raise ValueError("injected force failure")
    monkeypatch.setattr(session,"_force",broken)
    with pytest.raises(ValueError, match="injected"):
        session.next()
    assert to_document(session.current) == to_document(first)
    assert session.statistics["failed"]
    with pytest.raises(RuntimeError, match="ошибкой"):
        session.next()


@pytest.mark.parametrize("change", [dict(backend="python"),dict(integrator="verlet"),
    dict(error_control="global-rms")])
def test_unsupported_models_reject_before_running(change):
    state = free()
    with pytest.raises(ValueError):
        ContinuousRun(replace(state,settings=replace(state.settings,**change)),20.)


def test_dynamic_rotation_contacts_and_other_scipy_are_explicitly_rejected(monkeypatch):
    state = free()
    with pytest.raises(ValueError,match="вращения"):
        ContinuousRun(replace(state,rotations=(object(),)),20.)
    state=replace(state,bodies=[replace(state.bodies[0],radius=1.)])
    with pytest.raises(ValueError,match="контактов"):
        ContinuousRun(state,20.)
    from solar_simulator import continuous
    monkeypatch.setattr(continuous.scipy,"__version__","future-release")
    with pytest.raises(RuntimeError,match="SciPy"):
        ContinuousRun(free(),20.)


@pytest.mark.parametrize("target", [float("nan"),float("inf"),-1.,True])
def test_bad_target_does_not_start_a_session(target):
    with pytest.raises(ValueError):
        ContinuousRun(free(),target)


def test_fractional_target_changing_packets_and_repeatability():
    seed=free()
    output=[]
    for _ in range(2):
        session=ContinuousRun(seed,100.25)
        rows=[]
        for steps in (1,2,3,4,5,6):
            rows.append(to_document(session.next(steps)))
        while not session.finished:
            rows.append(to_document(session.next(7)))
        assert session.current.time==100.25
        output.append(rows)
    assert output[0]==output[1]
    zero=ContinuousRun(seed,0.)
    assert zero.finished and to_document(zero.next())==to_document(seed)


def test_holdout_snapshots_are_exact_boundaries_and_cannot_extend_horizon():
    session=ContinuousRun(free(),100.25)
    state=session.next(20,until=10.125)
    assert state.time==session._solver.t==10.125 and not session.finished
    before=to_document(state)
    with pytest.raises(ValueError,match="превышает"):
        session.next(until=101.)
    assert to_document(session.current)==before and not session.statistics["failed"]
    assert session.next(20,until=20.375).time==20.375
    with pytest.raises(AttributeError):
        session.target=200.


def test_relative_newtonian_motion_matches_independent_analytic_circular_orbit():
    # Equal masses: relative acceleration is -2Gm/r²; rotate the orbit in 3D.
    from math import cos, sin, pi, sqrt
    from solar_simulator.simulation import G
    mass, radius = 1e20,1e7
    omega=sqrt(2*G*mass/radius**3)
    period=2*pi/omega
    axis=np.array([1.,2.,-1.]);axis/=np.linalg.norm(axis)
    tangent=np.cross(axis,np.array([0.,1.,1.]));tangent/=np.linalg.norm(tangent)
    position=axis*radius
    velocity=tangent*radius*omega
    state=create_experiment([Body("A",mass,Vector3(*(-position/2)),Vector3(*(-velocity/2))),
                            Body("B",mass,Vector3(*(position/2)),Vector3(*(velocity/2)))],
        Settings(period/50,backend="rust",integrator="dop853",rtol=3e-14,
                 relative_pair=("A","B")))
    session=ContinuousRun(state,2*period)
    values=[]
    initial_energy=-G*mass*mass/(2*radius)
    initial_l=mass*radius*radius*omega/2
    while not session.finished:
        current=session.next(1)
        a,b=current.bodies
        p=b.position.subtract(a.position);v=b.velocity.subtract(a.velocity)
        expected_p=radius*(axis*cos(omega*current.time)+tangent*sin(omega*current.time))
        expected_v=radius*omega*(-axis*sin(omega*current.time)+tangent*cos(omega*current.time))
        assert dist((p.x,p.y,p.z),expected_p)<.1
        assert dist((v.x,v.y,v.z),expected_v)<1e-6
        speed2=fsum(x*x for body in (a,b) for x in (body.velocity.x,body.velocity.y,body.velocity.z))
        energy=.5*mass*speed2-G*mass*mass/hypot(p.x,p.y,p.z)
        angular=np.cross((p.x,p.y,p.z),(v.x,v.y,v.z))*mass/2
        assert abs(energy-initial_energy)/abs(initial_energy)<1e-10
        assert abs(np.linalg.norm(angular)-initial_l)/initial_l<1e-10
        values.append(current.time)
    assert len(values)>=100
