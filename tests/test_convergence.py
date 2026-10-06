from dataclasses import replace

import pytest

from solar_simulator.convergence import compare_steps
from solar_simulator.experiment import preset


@pytest.mark.parametrize("backend",["python","rust"])
def test_kepler_second_order_ratio(backend):
    if backend=="rust":
        pytest.importorskip("solar_native")
    experiment=preset("sun-earth",backend=backend)
    experiment=replace(experiment,settings=replace(experiment.settings,dt=experiment.settings.dt*20))
    result=compare_steps(experiment,200)
    assert 3.8<result["position_difference_ratio"]<4.2
    assert result["finest_position_error_estimate_metres"]>0
    assert len({v["final_time_seconds"] for v in result["runs"]})==1
    assert experiment.time==0


def test_collision_estimate_is_disabled():
    result=compare_steps(preset("spheres"),600)
    assert all(v["new_events"]==1 for v in result["runs"])
    assert result["finest_position_error_estimate_metres"] is None


def test_contact_stop_and_invalid_steps():
    experiment=preset("spheres")
    experiment=replace(experiment,settings=replace(experiment.settings,contact_mode="stop"))
    with pytest.raises(ValueError,match="остановлен"):
        compare_steps(experiment,600)
    with pytest.raises(ValueError):
        compare_steps(experiment,0)
