"""Independent trajectory limits for edited systems, including high eccentricity."""
import json
from pathlib import Path

import pytest

from scripts.assess_sandbox_limits import assess


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("name", ["mass-double", "slow-velocity", "escape-velocity",
    "eccentric-095", "add-companion", "remove-primary"])
def test_edited_system_against_independent_orbit_or_free_motion(name, backend):
    # Rust is required for this project's validated desktop environment.
    result = assess(name, backend)
    assert result["checks_passed"] and result["parent_preserved"]
    if name == "escape-velocity":assert result["unbound"]
    if name == "eccentric-095":assert result["eccentricity"] == pytest.approx(.95, abs=1e-14)


def test_published_limits_do_not_claim_jpl_accuracy_for_edited_systems():
    receipt = json.loads(Path("docs/sandbox-limits-validation.json").read_bytes())
    assert receipt["checks_passed"] and len(receipt["results"]) == 12
    assert receipt["units"] == "SI" and "no Solar System/JPL accuracy claim" in receipt["limitations"]
    assert all(row["position_metres"] < 10 for row in receipt["results"])
