from src.motion import calculate_position


def test_calculate_position():
    result = calculate_position(10.0, 3.0, 4.0)

    assert result == 22.0

def test_position_with_zero_velocity():
    result = calculate_position(15.0, 0.0, 10.0)

    assert result == 15.0

def test_position_at_zero_time():
    result = calculate_position(42.0, 100.0, 0.0)

    assert result == 42.0
