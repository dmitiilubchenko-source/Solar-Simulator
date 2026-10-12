"""Internal relative error is measured without cancelling large exports."""
import numpy as np
import pytest

from scripts.assess_relative_canonical import differences
from scripts.canonical_initial import SIUnits
from scripts.relative_canonical import Pair


def test_direct_relative_error_even_below_absolute_export_resolution():
    pair = Pair((.3,.7),0,1); units = SIUnits(1.,1.,1.)
    a = np.zeros((1,18)); a[0,:3] = 2.**54; a[0,3:6] = [.25,.5,1.]
    b = a.copy(); b[0,3] += 1e-8
    r = np.eye(3)[None]
    result = differences(a,r,b,r,units,pair,0,1.)
    assert result['earth_moon_position_m'] == pytest.approx(1e-8,rel=1e-8)
    assert result['positions_per_body_m'][0] == pytest.approx(.7e-8,rel=1e-8)
    assert result['positions_per_body_m'][1] == pytest.approx(.3e-8,rel=1e-8)


def test_comparison_rejects_invalid_grids_or_zero_scale():
    pair = Pair((.3,.7),0,1); units = SIUnits(1.,1.,1.); a = np.zeros((1,18)); r = np.eye(3)[None]
    for b,matrix,scale in [(a[:,:-1],r,1.),(a,r,0.),(a,np.full((1,3,3),np.nan),1.)]:
        with pytest.raises(ValueError):differences(a,r,b,matrix,units,pair,0,scale)
