import numpy as np
import pytest

from solar_simulator.impacts import resolve_contact
from solar_simulator.contacts import run_until_contact
from solar_simulator.diagnostics import angular_momentum
from solar_simulator.simulation import Body,G,total_energy,total_momentum
from solar_simulator.vector3 import Vector3


@pytest.fixture(params=["python","rust"])
def backend(request):
    if request.param=="rust":
        pytest.importorskip("solar_native")
    return request.param


def pair(masses=(1,1)):
    return [Body("a",masses[0],Vector3(-1,0,0),Vector3(2,0,0),1),
            Body("b",masses[1],Vector3(1,0,0),Vector3(-1,0,0),1)]


def test_equal_mass_elastic_exchange(backend):
    bodies=pair()
    result=resolve_contact(bodies,0,1,backend=backend)
    assert result.bodies[0].velocity.x==pytest.approx(-1)
    assert result.bodies[1].velocity.x==pytest.approx(2)
    assert result.dissipated_energy==0
    assert bodies[0].velocity.x==2
    assert result.bodies[0].name=="a" and result.bodies[0].radius==1


def test_unequal_mass_analytic_solution(backend):
    result=resolve_contact(pair((1,3)),0,1,backend=backend)
    assert result.bodies[0].velocity.x==pytest.approx(-2.5)
    assert result.bodies[1].velocity.x==pytest.approx(0.5)
    assert result.impulse==pytest.approx(4.5)


@pytest.mark.parametrize("e",[0,0.4,1])
def test_energy_budget_and_normal_velocity(backend,e):
    bodies=pair((1,3))
    result=resolve_contact(bodies,0,1,e,backend=backend)
    relative=result.bodies[1].velocity.x-result.bodies[0].velocity.x
    assert relative==pytest.approx(3*e,abs=1e-14)
    assert result.dissipated_energy==pytest.approx(0.5*0.75*(1-e*e)*9)
    assert total_energy(result.bodies)+result.dissipated_energy==pytest.approx(total_energy(bodies),rel=1e-13)
    assert total_momentum(result.bodies).distance_to(total_momentum(bodies))<1e-13


def test_separating_and_tangential_motion(backend):
    result=resolve_contact(pair(),0,1,backend=backend)
    again=resolve_contact(result.bodies,0,1,backend=backend)
    assert again.impulse==0 and again.dissipated_energy==0
    a,b=pair()
    a=Body(a.name,a.mass,a.position,Vector3(2,3,0),a.radius)
    b=Body(b.name,b.mass,b.position,Vector3(-1,-2,0),b.radius)
    result=resolve_contact([a,b],0,1,backend=backend)
    assert result.bodies[0].velocity.y==3
    assert result.bodies[1].velocity.y==-2


def test_detect_then_resolve(backend):
    bodies=[Body("a",1/G,Vector3(-5,0,0),Vector3(0,0,0),1),
            Body("b",1/G,Vector3(5,0,0),Vector3(0,0,0),1)]
    contact=run_until_contact(bodies,0.1,1000,backend=backend)
    event=contact.contact
    result=resolve_contact(contact.bodies,event.first,event.second,0.5,backend=backend)
    assert result.bodies[0].velocity.x<0 and result.bodies[1].velocity.x>0
    assert total_energy(result.bodies)+result.dissipated_energy==pytest.approx(total_energy(contact.bodies),rel=1e-13)


@pytest.mark.parametrize("e",[-1,1.1,float("nan"),float("inf")])
def test_invalid_restitution(backend,e):
    with pytest.raises(ValueError):
        resolve_contact(pair(),0,1,e,backend=backend)


@pytest.mark.parametrize("indices",[(0,0),(-1,1),(0,2),(True,1)])
def test_invalid_pair(backend,indices):
    with pytest.raises(ValueError):
        resolve_contact(pair(),*indices,backend=backend)


@pytest.mark.parametrize("distance",[0,1.5,3])
def test_undefined_or_noncontact_geometry(backend,distance):
    a,b=pair()
    b=Body(b.name,b.mass,Vector3(a.position.x+distance,0,0),b.velocity,b.radius)
    with pytest.raises(ValueError):
        resolve_contact([a,b],0,1,backend=backend)


def test_oblique_impacts_conserve_angular_momentum_and_match_native():
    pytest.importorskip("solar_native")
    rng=np.random.default_rng(2026)
    for _ in range(50):
        normal=rng.normal(size=3)
        normal/=np.linalg.norm(normal)
        shift=rng.normal(size=3)*30
        mass1,mass2=10**rng.uniform(-3,5,size=2)
        v1=rng.normal(size=3)*3
        tangent=rng.normal(size=3)
        tangent-=normal*np.dot(tangent,normal)
        closing=float(rng.uniform(0.1,5))
        v2=v1-closing*normal+tangent
        bodies=[Body("a",float(mass1),Vector3(*shift),Vector3(*v1),1),
                Body("b",float(mass2),Vector3(*(shift+2*normal)),Vector3(*v2),1)]
        e=float(rng.uniform(0,1))
        python=resolve_contact(bodies,0,1,e)
        rust=resolve_contact(bodies,0,1,e,backend="rust")
        for result in [python,rust]:
            momentum_scale=sum(b.mass*b.velocity.magnitude() for b in bodies)
            angular_scale=sum(b.position.cross(b.velocity).magnitude()*b.mass for b in bodies)
            energy_scale=sum(0.5*b.mass*b.velocity.dot(b.velocity) for b in bodies)
            assert total_momentum(result.bodies).distance_to(total_momentum(bodies))<1e-12*momentum_scale
            assert angular_momentum(result.bodies).distance_to(angular_momentum(bodies))<1e-12*angular_scale
            assert abs(total_energy(result.bodies)+result.dissipated_energy-total_energy(bodies))<1e-12*energy_scale
        assert max(a.velocity.distance_to(b.velocity) for a,b in zip(python.bodies,rust.bodies))<1e-11
