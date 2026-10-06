from concurrent.futures import ThreadPoolExecutor

import pytest

from solar_simulator.collisions import simulate_collisions
from solar_simulator.simulation import G
from test_collisions import body


native = pytest.importorskip("solar_native")


def test_native_cycle_does_not_call_python_detector(monkeypatch):
    import solar_simulator.collisions as module
    def fail(*args,**kwargs):
        raise AssertionError("Python detector entered")
    monkeypatch.setattr(module,"first_contact",fail)
    result = simulate_collisions([body("a",-2,1),body("b",2,-1)],2,1,backend="rust")
    assert len(result.events) == 1


def test_full_cycle_backend_agreement_and_parallel_calls():
    state = [body("a",-5,0,1/G),body("b",5,0,1/G)]
    reference = simulate_collisions(state,.05,2000)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:simulate_collisions(state,.05,2000,backend="rust"),range(2)))
    for result in results:
        assert [e.time for e in result.events] == pytest.approx([e.time for e in reference.events],abs=1e-9)
        for a,b in zip(reference.bodies,result.bodies):
            assert a.position.distance_to(b.position)<1e-9
            assert a.velocity.distance_to(b.velocity)<1e-9


@pytest.mark.parametrize("dt",[float("nan"),0,-1])
def test_native_invalid_configuration(dt):
    with pytest.raises(ValueError):
        native.simulate_collisions([1],[[0,0,0]],[[0,0,0]],[1],dt,1,1,10)


def test_native_invalid_arrays():
    with pytest.raises(ValueError):
        native.simulate_collisions([1],[],[[0,0,0]],[1],1,1,1,10)
    with pytest.raises(ValueError):
        native.simulate_collisions([1],[[0,0,0]],[[0,0,0]],[],1,1,1,10)
