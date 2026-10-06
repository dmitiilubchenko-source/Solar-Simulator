import pytest

from solar_simulator.contacts import first_contact,run_until_contact
from solar_simulator.simulation import Body,step
from solar_simulator.vector3 import Vector3


def pair(y=0):
    # Пренебрежимо малая гравитация: аналитическое время контакта 4 с.
    return [Body("a",1e-20,Vector3(-5,y,0),Vector3(1,0,0),1),
            Body("b",1e-20,Vector3(5,0,0),Vector3(-1,0,0),1)]


def test_contact_between_nonoverlapping_endpoints():
    result=run_until_contact(pair(),10,1)
    assert result.time == pytest.approx(4)
    assert result.contact is not None
    assert result.bodies[0].position.distance_to(result.bodies[1].position) == pytest.approx(2)


def test_initial_overlap_before_gravity():
    a=Body("a",1,Vector3(0,0,0),Vector3(0,0,0),1)
    result=run_until_contact([a,a],1,10)
    assert result.time == 0
    assert result.contact is not None


def test_near_miss_and_tangent():
    assert first_contact(pair(2.01),10) is None
    assert first_contact(pair(2),10).time == pytest.approx(5,abs=1e-6)


def test_earliest_pair_is_selected():
    bodies=pair()+[Body("c",1e-20,Vector3(-2,0,0),Vector3(0,0,0),0.5)]
    event=first_contact(bodies,10)
    assert (event.first,event.second)==(0,2)
    assert event.time == pytest.approx(1.5)


def test_radius_is_preserved_and_validated():
    assert step(pair(),1)[0].radius==1
    for radius in [-1,float("nan"),float("inf")]:
        with pytest.raises(ValueError):
            Body("a",1,Vector3(0,0,0),Vector3(0,0,0),radius)


def test_no_event_and_zero_steps():
    result=run_until_contact(pair(3),1,2)
    assert result.contact is None
    assert result.time==2
    assert run_until_contact(pair(),1,0).time==0


def test_gravitational_contact_converges_to_independent_scipy_event():
    from scipy.integrate import solve_ivp
    from solar_simulator.simulation import G
    def rhs(t,y):
        return [y[1],-2/y[0]**2]
    def event(t,y):
        return y[0]-2
    event.terminal=True
    event.direction=-1
    reference=solve_ivp(rhs,(0,100),[10,0],events=event,rtol=1e-11,atol=1e-13,max_step=0.1)
    expected=reference.t_events[0][0]
    bodies=[Body("a",1/G,Vector3(-5,0,0),Vector3(0,0,0),1),
            Body("b",1/G,Vector3(5,0,0),Vector3(0,0,0),1)]
    coarse=run_until_contact(bodies,0.5,300)
    fine=run_until_contact(bodies,0.25,600)
    assert coarse.contact is not None and fine.contact is not None
    assert abs(fine.time-expected)<abs(coarse.time-expected)/2
    assert abs(fine.time-expected)/expected<0.001
    assert fine.bodies[0].position.distance_to(fine.bodies[1].position)==pytest.approx(2)
