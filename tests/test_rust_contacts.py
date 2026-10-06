from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from solar_simulator.contacts import run_until_contact
from solar_simulator.simulation import Body,G
from solar_simulator.vector3 import Vector3


@pytest.fixture(autouse=True)
def native():
    return pytest.importorskip("solar_native")


def falling():
    return [Body("a",1/G,Vector3(-5,0,0),Vector3(0,0,0),1),
            Body("b",1/G,Vector3(5,0,0),Vector3(0,0,0),1)]


@pytest.mark.parametrize("y",[0,2,2.01])
def test_crossing_tangent_and_miss_match_python(y):
    bodies=[Body("a",1e-20,Vector3(-5,y,0),Vector3(1,0,0),1),
            Body("b",1e-20,Vector3(5,0,0),Vector3(-1,0,0),1)]
    python=run_until_contact(bodies,10,1)
    rust=run_until_contact(bodies,10,1,backend="rust")
    assert rust.time==pytest.approx(python.time,abs=1e-6)
    assert (rust.contact is None)==(python.contact is None)
    if rust.contact:
        assert (rust.contact.first,rust.contact.second)==(python.contact.first,python.contact.second)
    assert rust.bodies[0].position.distance_to(python.bodies[0].position)<1e-6
    assert rust.bodies[0].radius==1
    assert rust.bodies[0].name=="a"
    assert bodies[0].position.x==-5


def test_gravity_against_scipy_and_step_convergence():
    def rhs(t,y):
        return [y[1],-2/y[0]**2]
    def event(t,y):
        return y[0]-2
    event.terminal=True
    event.direction=-1
    reference=solve_ivp(rhs,(0,100),[10,0],events=event,rtol=1e-11,atol=1e-13,max_step=0.1)
    expected=reference.t_events[0][0]
    coarse=run_until_contact(falling(),0.5,300,backend="rust")
    fine=run_until_contact(falling(),0.25,600,backend="rust")
    python=run_until_contact(falling(),0.25,600)
    assert fine.contact is not None
    assert abs(fine.time-expected)<abs(coarse.time-expected)/2
    assert abs(fine.time-expected)/expected<0.001
    assert fine.time==pytest.approx(python.time,abs=1e-9)
    assert fine.bodies[0].position.distance_to(fine.bodies[1].position)==pytest.approx(2,abs=1e-9)


def test_initial_overlap_empty_and_zero_steps():
    a=Body("a",1,Vector3(0,0,0),Vector3(0,0,0),1)
    result=run_until_contact([a,a],1,10,backend="rust")
    assert result.time==0 and result.contact is not None
    assert run_until_contact([],1,10,backend="rust").bodies==[]
    assert run_until_contact([a],1,0,backend="rust").time==0


def test_earliest_pair():
    bodies=[Body("a",1e-20,Vector3(-5,0,0),Vector3(1,0,0),1),
            Body("b",1e-20,Vector3(5,0,0),Vector3(-1,0,0),1),
            Body("c",1e-20,Vector3(-2,0,0),Vector3(0,0,0),0.5)]
    result=run_until_contact(bodies,10,1,backend="rust")
    assert (result.contact.first,result.contact.second)==(0,2)
    assert result.time==pytest.approx(1.5)


@pytest.mark.parametrize("radius",[-1,float("nan"),float("inf")])
def test_native_rejects_radius(native,radius):
    with pytest.raises(ValueError):
        native.run_until_contact([1],[[0,0,0]],[[0,0,0]],[radius],1,1)


def test_native_rejects_radius_length(native):
    with pytest.raises(ValueError):
        native.run_until_contact([1],[[0,0,0]],[[0,0,0]],[],1,1)


def test_contact_in_three_dimensions_with_translation():
    # Детерминированные случайные направления, смещения и радиусы.
    rng=np.random.default_rng(42)
    for _ in range(40):
        direction=rng.normal(size=3)
        direction/=np.linalg.norm(direction)
        shift=rng.normal(size=3)*100
        radius=float(rng.uniform(0.1,2))
        speed=float(rng.uniform(0.2,3))
        bodies=[Body("a",1e-20,Vector3(*(shift-5*direction)),Vector3(*(speed*direction)),radius),
                Body("b",1e-20,Vector3(*(shift+5*direction)),Vector3(*(-speed*direction)),radius)]
        expected=(10-2*radius)/(2*speed)
        result=run_until_contact(bodies,10/speed,1,backend="rust")
        python=run_until_contact(bodies,10/speed,1)
        assert result.time==pytest.approx(expected,abs=1e-8)
        assert result.time==pytest.approx(python.time,abs=1e-8)


def test_parallel_contacts():
    def calculate(_):
        return run_until_contact(falling(),0.1,1000,backend="rust")
    with ThreadPoolExecutor(max_workers=2) as executor:
        a,b=list(executor.map(calculate,range(2)))
    assert a.time==b.time
    assert a.bodies[0].position.distance_to(b.bodies[0].position)==0
