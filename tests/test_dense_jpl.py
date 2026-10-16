"""Dense DE441 validation rejects wrong conventions and retains prior failures."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.assess_dense_jpl import validate_reference, residuals, verified_sources
from scripts.assess_sandbox_models import load_inputs
from solar_simulator.ephemerides import RESOLVED_IDS

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("field,value", [("units","KM-S"),("initial_dataset_changed",True),
    ("physical_parameters_fitted",True),("epochs_jd_tdb",[0.])])
def test_dense_reference_rejects_incompatible_conventions(field,value):
    reference=json.loads((ROOT/"docs/qualification-grid-reference.json").read_bytes())
    initial,origin,_,_,_=load_inputs()
    grid=reference["epochs_jd_tdb"][:]
    reference[field]=value
    with pytest.raises(ValueError,match="mismatch"):
        validate_reference(reference,origin,[b.name for b in initial],RESOLVED_IDS,grid)


def test_dense_reference_rejects_wrong_frame_missing_state_and_nonfinite_values():
    reference=json.loads((ROOT/"docs/qualification-grid-reference.json").read_bytes())
    initial,origin,_,_,_=load_inputs()
    names=[b.name for b in initial]; grid=reference["epochs_jd_tdb"]
    changed=deepcopy(reference); changed["origin"]["frame"]="ICRF"
    with pytest.raises(ValueError):validate_reference(changed,origin,names,RESOLVED_IDS,grid)
    changed=deepcopy(reference); changed["bodies"][0]["states"].pop()
    with pytest.raises(ValueError):validate_reference(changed,origin,names,RESOLVED_IDS,grid)
    changed=deepcopy(reference); changed["bodies"][0]["states"][0]["position"][0]=float("nan")
    with pytest.raises(ValueError):validate_reference(changed,origin,names,RESOLVED_IDS,grid)


def test_residual_threshold_checks_relative_moon_independently():
    # Both absolute errors pass10km, but opposite errors fail the1km pair goal.
    expected=np.zeros((2,2,6)); actual=expected.copy()
    actual[1,0,0]=600.; actual[1,1,0]=-600.
    result=residuals(actual,expected,["Earth","Moon"],[1.,2.])
    assert all(row["position_goal_passed"] for row in result["jpl_residuals"].values())
    assert result["moon_relative_jpl"]["position_metres"]==1200.
    assert not result["physical_goals_passed"]


def test_changed_scientific_source_rejected(tmp_path):
    (tmp_path/"source.py").write_bytes(b"original")
    receipt=dict(source_sha256={"source.py":hashlib.sha256(b"original").hexdigest()})
    verified_sources(receipt,tmp_path)
    (tmp_path/"source.py").write_bytes(b"changed")
    with pytest.raises(ValueError,match="Source changed"):
        verified_sources(receipt,tmp_path)


def test_published_dense_audit_has_real_coverage_and_preserves_numerical_failure():
    report=json.loads((ROOT/"docs/dense-jpl-validation.json").read_bytes())
    assert report["samples"]==125 and report["duration_seconds"]==31557600
    assert report["checks_passed"] and report["jpl_new_epochs_checked"]
    assert report["raw_responses_checked"]==40 and not report["initial_states_fitted"]
    assert report["prior_numerical_failure_retained"]
    verified_sources(report)
    for path,digest in report["input_sha256"].items():
        if path.startswith(".tools/"):continue  # cache validated by the executed audit, not a clean-clone fixture.
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    for row in report["results"].values():
        assert len(row["jpl_residuals"])==10 and row["physical_goals_passed"]
        assert row["moon_relative_jpl"]["position_metres"]<1000
        assert all(r["position_metres"]<10000 for r in row["jpl_residuals"].values())
    failed=json.loads((ROOT/"docs/qualification-grid-validation.json").read_bytes())
    assert not failed["results"]["rust"]["numerical_checks_passed"]
