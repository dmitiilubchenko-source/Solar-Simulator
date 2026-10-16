"""Annual epochs retain the already qualified quarter without resampling."""
import numpy as np
import pytest

from scripts.assess_edited_solar_year import epoch_grid, DURATION
from scripts.assess_edited_solar_quarter import epoch_grid as quarter


def test_julian_year_grids_have_exact_horizon_spacing_and_common_endpoints():
    a, b = epoch_grid('regular'), epoch_grid('shifted')
    assert DURATION == 365.25 * 86400. == 31557600.
    assert len(a) == 1462 and len(b) == 1463
    np.testing.assert_array_equal(np.intersect1d(a, b), [0., DURATION])
    assert np.all(np.diff(a) == 21600.)
    assert b[1] == 10800. and b[-2] == 31546800.
    assert np.all(np.diff(b) > 0) and np.max(np.diff(b)) == 21600.


def test_quarter_overlap_uses_exact_common_times_and_distinguishes_forced_endpoint():
    for grid in ('regular', 'shifted'):
        annual, prior = epoch_grid(grid), quarter(grid)
        common, annual_indices, prior_indices = np.intersect1d(annual, prior, return_indices=True)
        np.testing.assert_array_equal(annual[annual_indices], prior[prior_indices])
        assert len(common) == 361 and common[0] == 0.
        if grid == 'regular':
            np.testing.assert_array_equal(common, prior)
            assert common[-1] == 7776000.
        else:
            np.testing.assert_array_equal(common, prior[:-1])
            assert common[-1] == 7765200. and 7776000. not in annual
            assert annual[np.searchsorted(annual, 7776000.)] == 7786800.


@pytest.mark.parametrize('grid', ('daily', 'best', ''))
def test_undeclared_annual_grid_is_rejected(grid):
    with pytest.raises(ValueError, match='Undeclared annual'):
        epoch_grid(grid)
