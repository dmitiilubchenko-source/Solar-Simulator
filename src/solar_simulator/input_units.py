"""Input-only SI conversions; existing teaching masses are explicit scales.

au: IAU 2012 B2, 149597870700 m exactly. Earth/Sun scales below reuse
simulation.py; they are NOT IAU 2015 nominal GM parameters or JPL masses.
"""
from math import isfinite

from .simulation import AU, EARTH_MASS, SUN_MASS

MASS_UNITS = {'кг': 1., 'M⊕ (учеб.)': EARTH_MASS, 'M☉ (учеб.)': SUN_MASS}
LENGTH_UNITS = {'м': 1., 'км': 1000., 'au': AU}
SPEED_UNITS = {'м/с': 1., 'км/с': 1000.}


def _factor(quantity, unit):
    try:
        return {'mass': MASS_UNITS, 'length': LENGTH_UNITS, 'speed': SPEED_UNITS}[quantity][unit]
    except (KeyError, TypeError) as error:
        raise ValueError('Неизвестная величина или единица') from error


def _number(value):
    if isinstance(value, bool):
        raise ValueError('Ожидается конечное число')
    number = float(value)
    if not isfinite(number):
        raise ValueError('Ожидается конечное число')
    return number


def to_si(value, quantity, unit, *, offset=0.):
    factor = _factor(quantity, unit)
    number = _number(value)
    offset = _number(offset)
    scaled = number*factor
    result = scaled+offset
    if not isfinite(result) or not isfinite(scaled):
        raise ValueError('Переполнение преобразования в SI')
    if number != 0. and (scaled == 0. or result == offset):
        raise ValueError('Величина меньше разрешения float64 в выбранном базисе')
    return result


def from_si(value, quantity, unit, *, offset=0.):
    factor = _factor(quantity, unit)
    relative = _number(value)-_number(offset)
    result = relative/factor
    if not isfinite(relative) or not isfinite(result):
        raise ValueError('Переполнение отображения единиц')
    if relative != 0. and result == 0.:
        raise ValueError('Величина меньше разрешения отображения float64')
    return result
