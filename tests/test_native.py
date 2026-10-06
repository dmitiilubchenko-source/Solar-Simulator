from concurrent.futures import ThreadPoolExecutor

import pytest

from solar_simulator.rust_backend import evolve
from solar_simulator.simulation import step, sun_earth
from solar_simulator.scenarios import earth_moon, binary_star, sun_earth_moon


@pytest.fixture
def native():
    return pytest.importorskip("solar_native", reason="Build PyO3 module: scripts/build_native.py")


@pytest.mark.parametrize("factory", [sun_earth, lambda: sun_earth(0.6), earth_moon, binary_star, sun_earth_moon])
def test_native_matches_python_and_does_not_mutate_input(native, factory):
    initial, period = factory()
    snapshot = [(b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z) for b in initial]
    expected = initial
    dt = period / 4000
    for _ in range(8000):
        expected = step(expected,dt)
    actual = evolve(initial,dt,8000)
    length = initial[-1].position.distance_to(initial[-2].position)
    speed = initial[-1].velocity.subtract(initial[-2].velocity).magnitude()
    assert max(a.position.distance_to(b.position) for a,b in zip(actual,expected)) / length < 1e-9
    assert max(a.velocity.distance_to(b.velocity) for a,b in zip(actual,expected)) / speed < 1e-9
    assert [(b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z) for b in initial] == snapshot
    assert [b.name for b in actual] == [b.name for b in initial]


@pytest.mark.parametrize("mass", [0,-1,float("nan"),float("inf")])
def test_invalid_mass(native,mass):
    with pytest.raises(ValueError):
        native.evolve([mass],[[0,0,0]],[[0,0,0]],1,1)


@pytest.mark.parametrize("dt", [0,-1,float("nan"),float("inf")])
def test_invalid_dt(native,dt):
    with pytest.raises(ValueError):
        evolve(sun_earth()[0],dt,1)


@pytest.mark.parametrize("steps", [-1,1.5,True])
def test_invalid_steps(native,steps):
    with pytest.raises(ValueError):
        evolve(sun_earth()[0],1,steps)


def test_bad_arrays_and_coincident_positions(native):
    with pytest.raises(ValueError):
        native.evolve([1,1],[[0,0,0]],[[0,0,0]],1,1)
    with pytest.raises(ValueError):
        native.evolve([1,1],[[0,0,0],[0,0,0]],[[0,0,0],[0,0,0]],1,1)
    with pytest.raises(ValueError):
        native.evolve([1],[[float("nan"),0,0]],[[0,0,0]],1,1)
    with pytest.raises(ValueError):
        native.diagnostics([],[],[])
    with pytest.raises(ValueError):
        native.evolve([1],[[0,0]],[[0,0,0]],1,1)


def test_empty_and_zero_steps(native):
    assert native.evolve([],[],[],1,0) == ([],[])
    bodies,_=sun_earth()
    actual=evolve(bodies,1,0)
    assert actual[1].position.x == bodies[1].position.x


def test_parallel_independent_calculations(native):
    initial,period=sun_earth(0.6)
    def calculate(_):
        return evolve(initial,period/4000,8000)
    with ThreadPoolExecutor(max_workers=2) as executor:
        a,b=list(executor.map(calculate,range(2)))
    assert a[1].position.distance_to(b[1].position) == 0
    assert a[1].velocity.distance_to(b[1].velocity) == 0


def test_native_diagnostics(native):
    from solar_simulator.simulation import total_energy,total_momentum,center_of_mass
    from solar_simulator.diagnostics import angular_momentum
    bodies,_=sun_earth(0.6)
    values=native.diagnostics([b.mass for b in bodies],
                             [[b.position.x,b.position.y,b.position.z] for b in bodies],
                             [[b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies])
    assert values[0] == pytest.approx(total_energy(bodies),rel=1e-13)
    for actual,function in zip(values[1:],[total_momentum,angular_momentum,center_of_mass]):
        vector=function(bodies)
        assert actual == pytest.approx([vector.x,vector.y,vector.z],rel=1e-13,abs=1e-6)
