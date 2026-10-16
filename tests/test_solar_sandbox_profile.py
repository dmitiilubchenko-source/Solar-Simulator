"""An explicit ready profile does not change the existing Newton default."""
from dataclasses import asdict
import json
from pathlib import Path
import pytest


@pytest.mark.parametrize("backend",["python","rust"])
def test_ready_profile_matches_qualified_initial_state_and_models(backend):
    from solar_simulator.application_profiles import solar_sandbox, scenario
    from solar_simulator.experiment import advance, reset
    from solar_simulator.storage import to_document, from_document
    if backend=="rust":pytest.importorskip("solar_native")
    original=scenario("solar-system-moon",backend=backend)
    assert original.settings.physics=="newtonian" and not original.settings.figures
    qualified=solar_sandbox(backend=backend)
    assert to_document(qualified)["initial"]==to_document(original)["initial"]
    assert qualified.origin==original.origin
    assert qualified.settings.physics=="eih-1pn" and qualified.settings.relative_pair==("Earth","Moon")
    report=json.loads(Path("docs/sandbox-models-validation.json").read_text())
    entry=next(p for p in report["results"] if p["name"]=="eih-solar-earth-j2")
    assert [asdict(f) for f in qualified.settings.figures]==[dict(f,axis=tuple(f["axis"])) for f in entry["figures"]]
    progressed=advance(from_document(to_document(qualified)),2)
    assert progressed.time==7200 and to_document(reset(progressed))==to_document(qualified)
