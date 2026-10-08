from copy import deepcopy
from dataclasses import replace
import json

import pytest

from solar_simulator.experiment import advance, preset
from solar_simulator.storage import from_document, to_document, save, load


@pytest.mark.parametrize("backend",["python","rust"])
@pytest.mark.parametrize("name",["sun-earth","spheres"])
def test_checkpoint_resume_matches_uninterrupted(tmp_path,backend,name):
    if backend == "rust":
        pytest.importorskip("solar_native")
    original = preset(name,backend=backend)
    whole = advance(original,2000)
    partial = advance(original,1000)
    file = tmp_path/"опыт.json"
    save(partial,file)
    restored = load(file)
    assert to_document(restored)==to_document(partial)
    resumed = advance(restored,1000)
    assert resumed.time == pytest.approx(whole.time,rel=1e-15)
    assert len(resumed.events)==len(whole.events)
    assert resumed.dissipated_energy==whole.dissipated_energy
    for a,b in zip(resumed.bodies,whole.bodies):
        assert a.position.distance_to(b.position)==0
        assert a.velocity.distance_to(b.velocity)==0


@pytest.mark.parametrize("field,value",[("schema_version",True),("schema_version",8),
    ("units","km"),("time",-1),("time",True),("dissipated_energy",float("nan")),
    ("halted",1),("bodies",[]),("events",[dict(first="A",second="B",time=1)])])
def test_reject_malformed_checkpoint(field,value):
    document=to_document(preset("sun-earth"))
    document[field]=value
    with pytest.raises(ValueError):
        from_document(document)


def test_missing_fields_vector_and_body_identity():
    document=to_document(preset("sun-earth"))
    variants=[]
    missing=deepcopy(document); del missing["units"]; variants.append(missing)
    vector=deepcopy(document); vector["bodies"][0]["position"]=[0,0]; variants.append(vector)
    changed=deepcopy(document); changed["bodies"][0]["mass"]*=2; variants.append(changed)
    boolean=deepcopy(document); boolean["bodies"][0]["mass"]=True; variants.append(boolean)
    for variant in variants:
        with pytest.raises(ValueError):
            from_document(variant)


@pytest.mark.parametrize("text",['{"schema_version":1,"schema_version":1}',
    '{"time":NaN}',"not json",'"string"'])
def test_bad_json(tmp_path,text):
    file=tmp_path/"bad.json"
    file.write_text(text,encoding="utf-8")
    with pytest.raises(ValueError):
        load(file)


def test_failed_atomic_replace_preserves_old_file(tmp_path,monkeypatch):
    import solar_simulator.storage as storage
    file=tmp_path/"state.json"
    save(preset("sun-earth"),file)
    before=file.read_bytes()
    def fail(*args):
        raise OSError("disk test")
    monkeypatch.setattr(storage.os,"replace",fail)
    with pytest.raises(OSError):
        save(preset("earth-moon"),file)
    assert file.read_bytes()==before
    assert list(tmp_path.glob(".solar-*.tmp"))==[]


def test_halted_checkpoint_roundtrip(tmp_path):
    experiment=preset("spheres")
    experiment=replace(experiment,settings=replace(experiment.settings,contact_mode="stop"))
    result=advance(experiment,2000)
    save(result,tmp_path/"stopped.json")
    restored=load(tmp_path/"stopped.json")
    assert restored.halted and advance(restored,10) is restored
