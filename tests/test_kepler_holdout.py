import numpy as np

from scripts.assess_kepler_holdout import holdout_fixture
from scripts.assess_kepler_phase import fixture
from scripts.assess_sandbox_planets import states


def test_signed_permutation_preserves_existing_float_initial_components_exactly():
    seed,_=fixture(.95)
    rotated,times=holdout_fixture(.95,0.,True)
    original=states(seed.bodies)
    expected=original[:,[1,2,0,4,5,3]]*np.array([1.,-1.,-1.,1.,-1.,-1.])
    np.testing.assert_array_equal(states(rotated.bodies),expected)
    assert len(times)==82 and times[0]==0 and times[-1]>0


def test_unrotated_holdouts_preserve_original_seed_and_include_all_old_epochs():
    for eccentricity in (0.,.5,.95):
        old,old_times=fixture(eccentricity)
        new,times=holdout_fixture(eccentricity,0.,False)
        np.testing.assert_array_equal(states(new.bodies),states(old.bodies))
        assert set(old_times)<=set(times)
        assert np.all(np.diff(times)>0) and times[-1]==old_times[-1]
