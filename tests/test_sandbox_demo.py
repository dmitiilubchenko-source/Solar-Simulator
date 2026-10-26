"""The published demo preserves failed baselines and declares measured scope."""
from scripts.release_history import ui_historical_sha
import hashlib
import json
from pathlib import Path


def test_published_demo_keeps_sources_epochs_and_predeclared_accuracy_goals():
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/"docs/sandbox-demo-validation.json").read_text(encoding="utf-8"))
    assert report["checks_passed"] and report["batch"] == 20
    assert report["duration_seconds"] == 31557600 and len(report["epochs_jd_tdb"]) == 45
    for name,digest in report["source_sha256"].items():
        assert ui_historical_sha(root,name,digest) == digest
    assert hashlib.sha256((root/"docs/sandbox-models-validation.json").read_bytes()).hexdigest() == report["before_report_sha256"]
    convergence=report["reference_convergence"]
    assert convergence["all_bodies"]["maximum_position_metres"] < 1
    assert convergence["moon_relative_to_earth"]["maximum_position_metres"] < .1
    for row in report["results"].values():
        assert row["production"]["exact_epochs"] and row["production"]["settings_preserved"]
        assert row["production"]["relative_energy_drift"] < 1e-10
        assert len(row["jpl_residuals"]) == 10
        assert all(value["position_metres"] < 10000 for value in row["jpl_residuals"].values())
        assert row["moon_relative_jpl"]["position_metres"] < 1000
        assert all(value["position_metres"] < 10 and value["velocity_m_per_s"] < 1e-4
                   for value in row["numerical_errors"].values())
        assert row["relative_numerical_error"]["position_metres"] < .1
        assert row["relative_numerical_error"]["velocity_m_per_s"] < 1e-5
