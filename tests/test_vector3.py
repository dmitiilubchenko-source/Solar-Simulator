import math

from solar_simulator.vector3 import Vector3
import pytest


def test_add() -> None:
    first = Vector3(1.0, 2.0, 3.0)
    second = Vector3(4.0, -1.0, 2.0)

    result = first.add(second)

    assert result.x == 5.0
    assert result.y == 1.0
    assert result.z == 5.0

def test_subtract() -> None:

    first = Vector3(1.0, 2.0, 3.0)
    second = Vector3(4.0, -1.0, 2.0)

    result = first.subtract(second)

    assert result.x == -3.0
    assert result.y == 3.0
    assert result.z == 1.0

def test_multiply() -> None:

    vector  = Vector3(1.0, 2.0, 3.0)

    result = vector.multiply(2.0)

    assert result.x == 2.0
    assert result.y == 4.0
    assert result.z == 6.0

def test_divide() -> None:

    vector = Vector3(2.0, 4.0, 6.0)

    result = vector.divide(2.0)

    assert result.x == 1.0
    assert result.y == 2.0
    assert result.z == 3.0

def test_magnitude() -> None:

    vector = Vector3(3.0, 4.0, 12.0)

    result = vector.magnitude()

    assert result == 13

def test_normalize() -> None:
    vector = Vector3(3.0, 4.0, 12.0)

    result = vector.normalize()

    assert result.x == pytest.approx(0.23076923076923078)
    assert result.y == pytest.approx(0.3076923076923077)
    assert result.z == pytest.approx(0.9230769230769231)

def test_distance_to() -> None:

    first = Vector3(1.0, 2.0, 3.0)
    second = Vector3(4.0, -1.0, 2.0)

    result = first.distance_to(second)

    assert result == pytest.approx(4.358898943540674)

def test_normalize_zero_vector() -> None:
    vector = Vector3(0.0, 0.0, 0.0)

    with pytest.raises(ZeroDivisionError):
        vector.normalize()

def test_divide_by_zero() -> None:
    vector = Vector3(1.0, 2.0, 3.0)

    with pytest.raises(ZeroDivisionError):
        vector.divide(0.0)

def test_repr() -> None:
    vector = Vector3(1.0, 2.0, 3.0)

    assert repr(vector) == "Vector3(1.0, 2.0, 3.0)"

def test_dot() -> None:
    first = Vector3(1, 2, 3)
    second = Vector3(4, 5, 6)

    result = first.dot(second)

    assert result == 32

def test_dot_with_perpendicular_vectors() -> None:
    first = Vector3(1, 0, 0)
    second = Vector3(0, 1, 0)

    result = first.dot(second)

    assert result == 0

def test_angle_to() -> None:
    first = Vector3(1, 0, 0)
    second = Vector3(0, 1, 0)

    result = first.angle_to(second)

    assert result == pytest.approx(1.5707963267948966)  # π/2

def test_cross() -> None:
    first = Vector3(1, 2, 3)
    second = Vector3(4, 5, 6)

    result = first.cross(second)

    assert result.x == -3
    assert result.y == 6
    assert result.z == -3
    assert result.dot(first) == 0
    assert result.dot(second) == 0

def test_project_onto() -> None:
    first = Vector3(3, 4, 0)
    second = Vector3(2, 0, 0)

    result = first.project_onto(second)

    assert result.x == pytest.approx(3)
    assert result.y == pytest.approx(0)
    assert result.z == pytest.approx(0)

def test_project_onto_zero_vector() -> None:
    first = Vector3(3, 4, 0)
    second = Vector3(0, 0, 0)

    with pytest.raises(ValueError):
        first.project_onto(second)

def test_rotate_2d() -> None:
    vector = Vector3(0, 1, 0)
    result = vector.rotate_2d(math.pi / 2)

    assert result.x == pytest.approx(-1.0)
    assert result.y == pytest.approx(0.0)
    assert result.z == pytest.approx(0.0)

def test_rotate_2d_with_minus_pi_over_2() -> None:
    vector = Vector3(0, 1, 0)
    result = vector.rotate_2d(-math.pi / 2)

    assert result.x == pytest.approx(1.0)
    assert result.y == pytest.approx(0.0)
    assert result.z == pytest.approx(0.0)

def test_circular_position() -> None:
    radius = 5.0
    angular_speed = math.pi / 2
    time = 2.0

    result = Vector3.circular_position(radius, angular_speed, time)

    assert result.x == pytest.approx(-5.0)
    assert result.y == pytest.approx(0.0)
    assert result.z == pytest.approx(0.0)

def test_direction_to() -> None:
    earth = Vector3(1.0, 2.0, 3.0)
    sun = Vector3(4.0, -1.0, 2.0)

    result = earth.direction_to(sun)

    assert result.x == pytest.approx(3/math.sqrt(19))
    assert result.y == pytest.approx(-3/math.sqrt(19))
    assert result.z == pytest.approx(-1/math.sqrt(19))

def test_circular_orbit_geometry() -> None:
    sun = Vector3(0, 0, 0)

    earth = Vector3.circular_position(
        radius=10,
        angular_speed=math.pi / 2,
        time=1,
    )

    assert earth.x == pytest.approx(0.0)
    assert earth.y == pytest.approx(10.0)
    assert earth.z == pytest.approx(0.0)

    dist = earth.distance_to(sun)

    assert dist == pytest.approx(10.0)

    direct = earth.direction_to(sun)

    assert direct.x == pytest.approx(0.0)
    assert direct.y == pytest.approx(-1.0)
    assert direct.z == pytest.approx(0.0)

    earth_rotated = earth.rotate_2d(math.pi / 2)
    earth_rotated_normalized = earth_rotated.normalize()

    assert earth_rotated_normalized.x == pytest.approx(-1.0)
    assert earth_rotated_normalized.y == pytest.approx(0.0)
    assert earth_rotated_normalized.z == pytest.approx(0.0)

    perpendicular_planets = earth_rotated_normalized.dot(direct)

    assert perpendicular_planets == pytest.approx(0.0)

@pytest.mark.parametrize("scale", [1.0, 1e200, 1e-200])
def test_angle_parallel_and_opposite(scale):
    vector = Vector3(scale, scale, scale)
    assert vector.angle_to(vector) == pytest.approx(0, abs=3e-8)
    assert vector.angle_to(vector.multiply(-1)) == pytest.approx(math.pi)


def test_angle_with_zero_vector():
    with pytest.raises(ValueError):
        Vector3(1, 0, 0).angle_to(Vector3(0, 0, 0))


def test_circular_position_through_instance():
    result = Vector3(0, 0, 0).circular_position(5, 0, 1)
    assert (result.x, result.y, result.z) == (5, 0, 0)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_coordinates(value):
    with pytest.raises(ValueError):
        Vector3(value, 0, 0)
