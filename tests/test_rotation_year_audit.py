"""Guard annual audit against stale/corrupt cache and masked small-body errors."""
from copy import deepcopy
import json

import numpy as np
import pytest

from scripts.assess_rotation_year import ROOT, cached_job, compare, pack, represented, validate_arrays, initial_setup
from solar_simulator.ephemerides import solar_system
from solar_simulator.nbody_rotation import lunar_initial


def initial_arrays():
    bodies, origin = solar_system(resolved_moon=True)
    spin = lunar_initial(bodies, origin)[0]
    return bodies, spin, pack(represented([(bodies, (spin,))]))


def test_annual_initialization_roundtrips_and_has_exact_step_grid():
    from solar_simulator.storage import to_document, from_document
    policy = json.loads((ROOT/'scripts/rotation-year-policy.json').read_text())
    bodies, _, _, times, start = initial_setup(policy)
    assert len(bodies) == 10 and len(times) == 1462
    assert type(start.settings.dt) is float and start.settings.dt == 21600.
    assert start.settings.dt*sum(policy['checkpoint_steps']) == times[-1] == 31557600.
    restored = from_document(json.loads(json.dumps(to_document(start), allow_nan=False)))
    assert restored.settings == start.settings and restored.rotations == start.rotations


def test_cache_rejects_changed_context_and_corruption(tmp_path):
    bodies, _, data = initial_arrays()
    context = {"code_sha256": {"runtime": "old"}, "pair": ("Earth", "Moon")}
    cached_job(tmp_path, "trial", context, 1, len(bodies), lambda: data)
    def forbidden():
        raise AssertionError("Verified cache must not recompute")
    restored, _ = cached_job(tmp_path, "trial", context, 1, len(bodies), forbidden)
    np.testing.assert_array_equal(restored["positions"], data["positions"])
    with pytest.raises(ValueError, match="Changed/corrupt"):
        cached_job(tmp_path, "trial", {"code_sha256": {"runtime": "new"}}, 1, len(bodies), forbidden)
    with (tmp_path/"trial.npz").open("ab") as stream:
        stream.write(b"corruption")
    with pytest.raises(ValueError, match="Changed/corrupt"):
        cached_job(tmp_path, "trial", context, 1, len(bodies), forbidden)


def test_audit_rejects_nonfinite_or_truncated_samples():
    bodies, spin, data = initial_arrays()
    changed = deepcopy(data); changed["spins"][0, 0] = np.nan
    with pytest.raises(ValueError, match="spins"):
        validate_arrays(changed, 1, len(bodies))
    changed = deepcopy(data); changed["matrices"] = changed["matrices"][:0]
    with pytest.raises(ValueError, match="matrices"):
        compare(data, changed, bodies, spin)
    with pytest.raises(ValueError, match="Empty"):
        validate_arrays(data, 0, len(bodies))


def test_per_body_metric_exposes_sun_error_hidden_by_outer_planet_scale():
    bodies, spin, data = initial_arrays()
    changed = deepcopy(data); sun = [b.name for b in bodies].index("Sun")
    changed["positions"][0, sun, 0] += 1e4
    result = compare(data, changed, bodies, spin)
    assert result["components"]["position"] < 1e-7
    assert result["per_body"]["Sun"]["position_scaled"] > 1e-7
    assert result["per_body_maximum"] > 1e-7
