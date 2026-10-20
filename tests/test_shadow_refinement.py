from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import pytest

from scripts.assess_shadow_refinement import substep,refined_trajectory
from test_kepler_shadow import header


def test_dyadic_substeps_preserve_exact_binary_input_under_small_context():
    with localcontext() as context:
        context.prec=9
        for h in (1.1,1e-12,2e5):
            for divisor in (2,4):assert F(substep(h,divisor))*divisor==F(h)
    with pytest.raises(ValueError):substep(1.,3)
    with pytest.raises(ValueError):substep(-1.,2)


@pytest.mark.parametrize('divisor',[2,4])
def test_refinement_preserves_macro_epochs_and_decimal_clock(divisor):
    values,elapsed=refined_trajectory(tuple(map(D,(3,4,0,1,0,0))),[(1.,1.)],
        [0.,1.],header(),D(1),80,divisor)
    assert elapsed==[D(0),D(1)] and len(values)==2
    assert abs(values[-1][0]-D(4))<D('.05')
    with pytest.raises(ValueError):
        refined_trajectory(values[0],[(1.,.5)],[0.,1.],header(),D(1),80,divisor)
