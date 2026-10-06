import pytest

from solar_simulator.collisions import simulate_collisions
from solar_simulator.simulation import Body, G, total_energy, total_momentum
from solar_simulator.vector3 import Vector3


def body(name, x, vx, mass=1e-20):
    return Body(name,mass,Vector3(x,0,0),Vector3(vx,0,0),1)


@pytest.fixture(params=["python", "rust"])
def backend(request):
    if request.param == "rust":
        pytest.importorskip("solar_native")
    return request.param


def test_two_sequential_impacts_and_remaining_time(backend):
    state = [body("a",-4,2),body("b",0,0),body("c",4,0)]
    result = simulate_collisions(state,3,1,backend=backend)
    assert [e.time for e in result.events] == pytest.approx([1,2])
    assert [(e.first,e.second) for e in result.events] == [(0,1),(1,2)]
    assert [b.position.x for b in result.bodies] == pytest.approx([-2,2,6])
    assert [b.velocity.x for b in result.bodies] == pytest.approx([0,0,2])
    assert result.time == 3 and result.dissipated_energy == 0
    assert state[0].position.x == -4


def test_separating_touch_and_endpoint_contact(backend):
    separating = simulate_collisions([body("a",-1,-1),body("b",1,1)],1,2,backend=backend)
    assert separating.events == []
    result = simulate_collisions([body("a",-2,1),body("b",2,-1)],1,2,backend=backend)
    assert len(result.events) == 1
    assert result.events[0].time == pytest.approx(1)
    assert result.bodies[0].position.x == pytest.approx(-2)


def test_gravity_repeated_bounces_and_energy_convergence(backend):
    state = [body("a",-5,0,1/G),body("b",5,0,1/G)]
    results = [simulate_collisions(state,dt,round(100/dt),backend=backend) for dt in (.1,.05)]
    assert len(results[0].events) >= 2
    assert len(results[0].events) == len(results[1].events)
    for result in results:
        assert total_momentum(result.bodies).magnitude() < 1e-5
        assert result.bodies[0].position.distance_to(result.bodies[1].position) >= 2-1e-7
    initial = total_energy(state)
    errors = [abs(total_energy(r.bodies)-initial)/abs(initial) for r in results]
    assert errors[1] < errors[0]
    assert errors[1] < .002


def test_loss_accounting(backend):
    state = [body("a",-2,1),body("b",2,-1)]
    result = simulate_collisions(state,.25,8,restitution=.5,backend=backend)
    assert len(result.events) == 1
    assert total_energy(result.bodies)+result.dissipated_energy == pytest.approx(total_energy(state),rel=1e-12,abs=1e-40)


def test_initial_approach_and_tangency(backend):
    result = simulate_collisions([body("a",-1,1),body("b",1,-1)],1,1,backend=backend)
    assert [e.time for e in result.events] == [0]
    tangent = [body("a",-5,1),Body("b",1e-20,Vector3(5,2,0),Vector3(-1,0,0),1)]
    result = simulate_collisions(tangent,10,1,backend=backend)
    assert result.events == []


def test_zero_steps(backend):
    state = [body("a",-1,1),body("b",1,-1)]
    result = simulate_collisions(state,1,0,backend=backend)
    assert result.time == 0 and result.events == []
    for a,b in zip(result.bodies,state):
        assert a.position.distance_to(b.position) == 0
        assert a.velocity.distance_to(b.velocity) == 0
        assert (a.name,a.mass,a.radius) == (b.name,b.mass,b.radius)


def test_unsupported_contacts(backend):
    with pytest.raises(ValueError,match="Покоящийся"):
        simulate_collisions([body("a",-1,0),body("b",1,0)],1,1,backend=backend)
    with pytest.raises(ValueError,match="перекрытие"):
        simulate_collisions([body("a",0,0),body("b",1,0)],1,1,backend=backend)
    with pytest.raises(ValueError,match="Одновременный"):
        simulate_collisions([body("a",-4,1),body("b",0,0),body("c",4,-1)],3,1,backend=backend)
    with pytest.raises(RuntimeError,match="лимит"):
        simulate_collisions([body("a",-4,2),body("b",0,0),body("c",4,0)],3,1,max_events=1,backend=backend)


@pytest.mark.parametrize("options",[{"dt":0},{"dt":float("inf")},{"steps":True},
    {"steps":-1},{"restitution":-1},{"max_events":0},{"backend":"unknown"}])
def test_validation(options):
    arguments = dict(dt=1,steps=1)
    arguments.update(options)
    with pytest.raises(ValueError):
        simulate_collisions([],**arguments)
