"""Canonical finite physical scalars; checkpoint codecs remain strict."""
from math import isfinite

import numpy as np


def finite_number(value, name):
    """Keep builtin int/float; losslessly unwrap NumPy real scalars <=64 bits.

    bool (including numpy.bool_), arrays, complex and coercible strings are
    not physical numbers. Wider NumPy floats require an explicit caller choice.
    """
    if type(value) not in (int, float):
        if isinstance(value, np.integer) and value.dtype.kind in "iu":
            value = int(value)
        elif isinstance(value, np.floating) and value.dtype.itemsize <= 8:
            value = float(value)
        else:
            raise ValueError(f"{name}: требуется действительное число, не bool")
    try:
        finite = isfinite(value)
    except OverflowError as error:
        raise ValueError(f"{name}: число вне конечного диапазона float64") from error
    if not finite:
        raise ValueError(f"{name}: требуется конечное число")
    return value
