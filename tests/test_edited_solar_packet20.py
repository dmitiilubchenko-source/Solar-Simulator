"""A GUI packet must not be shortened by an observation grid used for validation."""
import numpy as np

from scripts.assess_edited_solar_packet20 import epoch_grid, PACKET_SECONDS
from scripts.assess_edited_solar_year import epoch_grid as six_hour_grid, DURATION


def test_actual_packet_grid_has_438_twenty_hour_packets_then_six_hours():
    times = epoch_grid()
    assert len(times) == 440 and times[0] == 0. and times[-1] == DURATION
    np.testing.assert_array_equal(np.diff(times)[:-1], np.full(438, PACKET_SECONDS))
    assert np.diff(times)[-1] == 21600.
    assert times[-2] == 31536000.


def test_packet_grid_uses_exact_shared_epochs_without_nearest_time_matching():
    regular = six_hour_grid('regular')
    common, a, b = np.intersect1d(epoch_grid(), regular, return_indices=True)
    assert len(common) == 148
    np.testing.assert_array_equal(common[:-1], np.arange(0., 31536000.+1., 216000.))
    assert common[-1] == DURATION
    np.testing.assert_array_equal(epoch_grid()[a], regular[b])
    assert 72000. not in regular and 21600. not in epoch_grid()
