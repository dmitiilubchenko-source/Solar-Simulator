"""Independent analytic expectations after changing the primary mass."""
import pytest
from scripts.assess_sandbox_branch import initial, sample


@pytest.mark.parametrize("backend", ["python", "rust"])
def test_double_mass_branch_follows_independent_kepler_ellipse(backend):
    if backend == "rust":
        pytest.importorskip("solar_native")
    _, _, branch = initial(backend, "dop853")
    result = sample(branch.child)
    assert result["position_metres"] < 10
    assert result["velocity_m_per_s"] < 1e-5
    assert result["relative_energy_drift"] < 1e-10
    assert result["relative_angular_momentum_drift"] < 1e-10
