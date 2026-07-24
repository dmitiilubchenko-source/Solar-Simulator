from src.vector3 import Vector3
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
    if test_normalize == 0.0:
        raise ZeroDivisionError("Не может быть равно 0")

    vector = Vector3(3.0, 4.0, 12.0)

    result = vector.normalize()

    assert result.x == 0.23076923076923078
    assert result.y == 0.3076923076923077
    assert result.z == 0.9230769230769231

def test_distance_to() -> None:

    first = Vector3(1.0, 2.0, 3.0)
    second = Vector3(4.0, -1.0, 2.0)

    result = first.distance_to(second)

    assert result ==  4.358898943540674

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
