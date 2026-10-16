"""Counterfactual Solar ICs retain masses/frame conventions without JPL claims."""
import numpy as np
import pytest

from scripts.assess_edited_solar import CASES,fixture,oracle_check
from scripts.assess_sandbox_models import load_oracle
from scripts.assess_sandbox_planets import states
from solar_simulator.storage import to_document


@pytest.mark.parametrize('case',CASES)
def test_pilot_is_one_edit_of_the_pinned_ten_body_start(case):
    parent,branch,times=fixture(case);p,q=states(parent.bodies),states(branch.child.bodies)
    assert parent.origin is not None and branch.child.origin is None
    assert branch.child.settings==parent.settings and len(branch.changes())==1
    assert len(branch.child.bodies)==10 and times.shape==(25,) and times[-1]==259200.
    if case=='sun_mass':
        np.testing.assert_array_equal(p,q);assert branch.child.bodies[0].mass==1.25*parent.bodies[0].mass
    else:
        assert [b.mass for b in parent.bodies]==[b.mass for b in branch.child.bodies]
    unchanged=[i for i in range(10) if i!=({'sun_mass':0,'earth_position':3,'moon_velocity':4}[case])]
    np.testing.assert_array_equal(q[unchanged],p[unchanged])
    assert to_document(branch.parent)==to_document(parent)


@pytest.mark.parametrize('case',CASES)
def test_loaded_scalar_oracle_matches_independent_matrix_before_use(case):
    _,branch,_=fixture(case)
    assert oracle_check(branch.child,load_oracle())['checks_passed']
