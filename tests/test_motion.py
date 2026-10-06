from solar_simulator.motion import calculate_position


def test_calculate_position():
    result = calculate_position(10.0, 3.0, 4.0)

    assert result == 22.0

def test_position_with_zero_velocity():
    result = calculate_position(15.0, 0.0, 10.0)

    assert result == 15.0

def test_position_at_zero_time():
    result = calculate_position(42.0, 100.0, 0.0)

    assert result == 42.0

import pytest
from solar_simulator.motion import update_position, update_velocity


@pytest.mark.parametrize("dt", [-1, float("nan"), float("inf")])
def test_invalid_time_step(dt):
    with pytest.raises(ValueError):
        update_position(0, 1, 2, dt)
    with pytest.raises(ValueError):
        update_velocity(1, 2, dt)


def test_constant_acceleration_composed_steps():
    position, velocity = 10.0, 3.0
    for _ in range(4):
        position = update_position(position, velocity, -2, 0.5)
        velocity = update_velocity(velocity, -2, 0.5)
    assert position == pytest.approx(12)
    assert velocity == pytest.approx(-1)


def test_zero_step_preserves_state():
    assert update_position(10, 3, -2, 0) == 10
    assert update_velocity(3, -2, 0) == 3
