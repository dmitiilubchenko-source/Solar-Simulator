"""Independent exact coefficients, inverse bounds and representability errors."""
from math import ulp

import pytest

from solar_simulator.input_units import from_si, to_si


@pytest.mark.parametrize('value,quantity,unit,expected', [
    (1., 'length', 'au', 149597870700.), (1.25, 'length', 'км', 1250.),
    (-2.5, 'speed', 'км/с', -2500.), (2., 'mass', 'M⊕ (учеб.)', 1.19444e25),
    (2., 'mass', 'M☉ (учеб.)', 3.977e30), (1.25, 'mass', 'кг', 1.25),
])
def test_known_si_coefficients(value, quantity, unit, expected):
    assert to_si(value, quantity, unit) == expected


def test_relative_position_and_velocity_are_both_translations():
    assert to_si(-2., 'length', 'км', offset=10000.) == 8000.
    assert to_si(.5, 'speed', 'км/с', offset=-3000.) == -2500.
    assert from_si(8000., 'length', 'км', offset=10000.) == -2.
    assert from_si(-2500., 'speed', 'км/с', offset=-3000.) == .5


@pytest.mark.parametrize('quantity,unit,value', [('mass', 'M⊕ (учеб.)', 6.123456789012345e24),
    ('mass', 'M☉ (учеб.)', 1.999999999999999e30), ('length', 'au', -4.123456789012345e11),
    ('length', 'км', 1.234567890123456e7), ('speed', 'км/с', -29876.54321098765)])
def test_raw_float_inverse_error_within_two_ulp(quantity, unit, value):
    restored = to_si(from_si(value, quantity, unit), quantity, unit)
    assert abs(restored-value) <= 2*ulp(value)


@pytest.mark.parametrize('function,args,kwargs', [
    (to_si, (float('nan'), 'mass', 'кг'), {}), (to_si, (float('inf'), 'speed', 'м/с'), {}),
    (to_si, (True, 'length', 'м'), {}), (to_si, (1., 'length', 'mystery'), {}),
    (to_si, (1., 'time', 'с'), {}), (to_si, (1e308, 'length', 'au'), {}),
    (to_si, (1., 'length', 'м'), {'offset': 1e30}),
    (from_si, (1e-310, 'mass', 'M☉ (учеб.)'), {}),
    (from_si, (1e308, 'length', 'км'), {'offset': -1e308}),
    (from_si, (1., 'length', 'м'), {'offset': float('nan')}),
])
def test_invalid_or_unrepresentable_conversion_is_explicit(function, args, kwargs):
    with pytest.raises(ValueError):
        function(*args, **kwargs)
