import pytest

from solar_simulator.runner import sampled_states
from solar_simulator.simulation import Body,step,sun_earth
from solar_simulator.vector3 import Vector3


def test_sampling_has_final_remainder_and_preserves_step():
    bodies,period=sun_earth()
    snapshots=list(sampled_states(bodies,period/1000,43,every=20))
    assert [i for i,_ in snapshots]==[0,20,40,43]
    expected=bodies
    for _ in range(43):
        expected=step(expected,period/1000)
    assert snapshots[-1][1][1].position.distance_to(expected[1].position)==0


def test_rust_sampling_matches_python():
    pytest.importorskip("solar_native")
    bodies,period=sun_earth(0.6)
    a=list(sampled_states(bodies,period/4000,8000,backend="rust"))
    b=list(sampled_states(bodies,period/4000,8000))
    assert [i for i,_ in a]==[i for i,_ in b]
    assert max(x[1][1].position.distance_to(y[1][1].position) for x,y in zip(a,b))<1


def test_sampler_rejects_finite_radius():
    body=Body("a",1,Vector3(0,0,0),Vector3(0,0,0),1)
    with pytest.raises(ValueError):
        list(sampled_states([body],1,10))
