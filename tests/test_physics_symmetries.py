"""Инвариантность ньютоновского движения: 3D, Галилей, подобие масштабов."""
from math import cos, sin, sqrt

import pytest

from solar_simulator.experiment import advance, create_experiment, preset
from solar_simulator.simulation import Body
from solar_simulator.vector3 import Vector3


@pytest.fixture(params=["python","rust"])
def backend(request):
    if request.param=="rust":
        pytest.importorskip("solar_native")
    return request.param


def rotate(vector):
    angle=.73
    # Два независимых вращения, чтобы все три координаты были ненулевыми.
    x,y,z=vector.x,cos(angle)*vector.y-sin(angle)*vector.z,sin(angle)*vector.y+cos(angle)*vector.z
    return Vector3(cos(angle)*x+sin(angle)*z,y,-sin(angle)*x+cos(angle)*z)


def test_rotation_covariance(backend):
    original=preset("sun-earth",backend=backend,eccentricity=.6)
    tilted=create_experiment([Body(b.name,b.mass,rotate(b.position),rotate(b.velocity)) for b in original.bodies],original.settings)
    a,b=advance(original,1000),advance(tilted,1000)
    for x,y in zip(a.bodies,b.bodies):
        assert rotate(x.position).distance_to(y.position)<.1
        assert rotate(x.velocity).distance_to(y.velocity)<1e-7


def test_galilean_translation_and_boost(backend):
    original=preset("sun-earth",backend=backend)
    shift=Vector3(3e11,-2e11,4e11)
    boost=Vector3(500,-800,300)
    transformed=create_experiment([Body(b.name,b.mass,b.position.add(shift),b.velocity.add(boost)) for b in original.bodies],original.settings)
    a,b=advance(original,500),advance(transformed,500)
    for x,y in zip(a.bodies,b.bodies):
        expected=x.position.add(shift).add(boost.multiply(a.time))
        assert expected.distance_to(y.position)<.1
        assert x.velocity.add(boost).distance_to(y.velocity)<1e-7


def test_newtonian_similarity(backend):
    original=preset("earth-moon",backend=backend)
    length,mass=1e-3,1e4
    time=sqrt(length**3/mass)
    scaled=create_experiment([Body(b.name,b.mass*mass,b.position.multiply(length),
                                  b.velocity.multiply(length/time)) for b in original.bodies],
                             type(original.settings)(original.settings.dt*time,backend))
    a,b=advance(original,500),advance(scaled,500)
    for x,y in zip(a.bodies,b.bodies):
        assert x.position.multiply(length).distance_to(y.position)<1e-7
        assert x.velocity.multiply(length/time).distance_to(y.velocity)<1e-5
