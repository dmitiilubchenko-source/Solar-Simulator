"""Source receipts must reject tampering; historical failures remain visible."""
import json
from pathlib import Path
import shutil

import pytest

from scripts.accept_sandbox import ROOT, check_receipts, workflows


def test_dense_failure_retained_and_strict_profile_independently_qualified():
    failed = json.loads((ROOT/"docs/qualification-grid-validation.json").read_bytes())
    strict = json.loads((ROOT/"docs/strict-profile-validation.json").read_bytes())
    assert len(failed["epochs_jd_tdb"]) == strict["samples"] == 125
    assert failed["results"]["rust"]["relative_numerical_error"]["position_metres"] > .1
    assert not failed["checks_passed"] and strict["checks_passed"]
    assert strict["settings"]["rtol"] == 3e-14
    assert all(row["relative_numerical_error"]["position_metres"] < .1 for row in strict["results"].values())
    assert len(strict["holdout_times_seconds"]) == 9
    assert all(row["checks_passed"] for row in strict["holdout"].values())
    assert not strict["jpl_new_epochs_checked"] and not failed["jpl_coverage"]["new_epochs_checked"]
    assert check_receipts()["current_qualification_passed"]


@pytest.mark.parametrize("target", ["src/solar_simulator/oblateness.py", "docs/solar-system-moon-reference.json"])
def test_source_or_pinned_reference_change_rejected_before_acceptance(tmp_path, target):
    paths = set()
    for name in ("qualification-grid-validation.json", "strict-profile-validation.json", "sandbox-limits-validation.json"):
        paths.add("docs/"+name)
        receipt = json.loads((ROOT/"docs"/name).read_bytes())
        paths.update(receipt["source_sha256"])
    paths.update(("docs/solar-system-reference.json", "docs/solar-system-moon-reference.json",
        "docs/solar-sandbox-strict-checkpoint.json"))
    for name in paths:
        destination = tmp_path/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/name, destination)
    assert check_receipts(tmp_path)["current_qualification_passed"]
    with (tmp_path/target).open("ab") as stream:stream.write(b"\n")
    with pytest.raises(ValueError, match="changed"):
        check_receipts(tmp_path)


def test_strict_checkpoint_target_branch_export_and_continuation():
    result = workflows()
    assert result["checkpoint_continue_exact"] and result["initial_unchanged"]
    assert result["csv_rows"] == result["branch_addition_bodies"] == 11
