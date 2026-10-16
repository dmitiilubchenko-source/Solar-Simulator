"""A qualified report keeps fixed criteria, independent sources and failed goals."""
import hashlib
import json
from pathlib import Path


def test_current_models_report_preserves_predeclared_order_and_failures():
    report=json.loads(Path("docs/sandbox-models-validation.json").read_text())
    assert report["duration_seconds"]==31557600 and report["samples"]==45
    assert report["numerical_checks_passed"] and not report["errors"]
    expected=["newton","eih","eih-solar-j2","eih-solar-earth-j2"]
    assert [p["name"] for p in report["results"]]==expected
    assert report["physical_goals"]["all_body_position_metres"]==10000
    assert report["physical_goals"]["lunar_relative_position_metres"]==1000
    assert report["physical_goals_passed_by_profile"]==dict(zip(expected,[False,False,False,True]))
    for path,digest in report["source_sha256"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    for profile in report["results"]:
        assert profile["reference_convergence"]["all_bodies"]["maximum_position_metres"]<1
        assert profile["reference_convergence"]["moon_relative_to_earth"]["maximum_position_metres"]<.1
        for backend,values in profile["results"].items():
            assert values["numerical_checks_passed"] and values["invariant_checks_passed"]
            assert len(values["numerical_errors"])==10
            assert all(v["position_metres"]<10 and v["velocity_m_per_s"]<1e-4 for v in values["numerical_errors"].values())
            assert values["relative_numerical_error"]["position_metres"]<.1
            for name,value in values["jpl_residuals"].items():
                assert values["physical_goal_checks"][name]==(value["position_metres"]<10000)
            assert values["physical_goal_checks"]["Moon-relative"]==(values["moon_relative_jpl"]["position_metres"]<1000)
            assert profile["production"][backend]["angular_conservation_expected"]==(not profile["figures"])
