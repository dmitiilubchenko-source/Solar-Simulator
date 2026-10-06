from dataclasses import replace

import pytest

from solar_simulator.experiment import Settings, advance, preset, reset


@pytest.mark.parametrize("name",["sun-earth","earth-moon","binary-star","sun-earth-moon","spheres"])
def test_presets_reset_and_unchanged_input(name):
    original = preset(name)
    result = advance(original,10)
    assert original.time == 0 and original.events == ()
    assert result.time == pytest.approx(original.settings.dt*10)
    restored = reset(result)
    assert restored.time == 0 and not restored.halted
    assert restored.bodies[0].position.distance_to(original.bodies[0].position) == 0
    restored.bodies[0].position.x += 1
    assert restored.bodies[0].position.distance_to(original.bodies[0].position) == 1


@pytest.mark.parametrize("backend",["python","rust"])
def test_stopping_contact_is_recorded_and_halts(backend):
    if backend == "rust":
        pytest.importorskip("solar_native")
    experiment = preset("spheres",backend=backend)
    experiment = replace(experiment,settings=replace(experiment.settings,contact_mode="stop"))
    result = advance(experiment,2000)
    assert result.halted and len(result.events)==1
    assert result.events[0].time == result.time
    assert result.events[0].first == "A"
    assert advance(result,2000) is result


@pytest.mark.parametrize("options",[{"dt":0},{"dt":True},{"backend":"bad"},
    {"contact_mode":"ignore"},{"restitution":float("nan")}])
def test_invalid_settings(options):
    values=dict(dt=1)
    values.update(options)
    with pytest.raises(ValueError):
        Settings(**values)


def test_invalid_steps_and_time_overflow():
    experiment = preset("sun-earth")
    with pytest.raises(ValueError):
        advance(experiment,True)
    with pytest.raises(ValueError):
        advance(replace(experiment,time=1e100),1)
