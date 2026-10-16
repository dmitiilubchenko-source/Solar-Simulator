import numpy as np
from decimal import Decimal

from scripts.assess_kepler_force_rounding import decimal_acceleration


def test_independent_force_on_exact_pythagorean_radii():
    # radius=5, mu=125: acceleration=-r exactly, no approximate norm oracle.
    np.testing.assert_array_equal(decimal_acceleration([3.,4.,0.],Decimal(125)),[-3.,-4.,0.])
    # Reflect, double radius: direction reverses and force falls by four.
    np.testing.assert_array_equal(decimal_acceleration([-6.,-8.,0.],Decimal(125)),[.75,1.,0.])


def test_decimal_force_preserves_a_three_dimensional_signed_permutation():
    p=np.array([3.,4.,12.])  # radius=13 exactly
    original=decimal_acceleration(p,Decimal(2197))
    np.testing.assert_array_equal(original,-p)
    rotated=p[[1,2,0]]*np.array([1.,-1.,-1.])
    np.testing.assert_array_equal(decimal_acceleration(rotated,Decimal(2197)),
                                  original[[1,2,0]]*np.array([1.,-1.,-1.]))
