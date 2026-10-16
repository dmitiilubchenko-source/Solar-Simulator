"""Public replay fixtures work offline and reject byte and semantic corruption."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from scripts.replay_jpl import replay

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SHA = "615645e8bfd222922db520f13bebc8540da6744244084240ee9f6c2164a840dc"


@pytest.fixture
def bundle(tmp_path):
    path = ROOT/"tests/data/jpl-verification.zip"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == FIXTURE_SHA
    folder = tmp_path/"public verification"
    folder.mkdir()
    with zipfile.ZipFile(path) as archive:archive.extractall(folder)
    return folder


def modify_json(folder,name,mutation):
    document = json.loads((folder/name).read_bytes())
    mutation(document)
    (folder/name).write_text(json.dumps(document),encoding="utf-8")
    manifest = json.loads((folder/"manifest.json").read_bytes())
    manifest["files"][name] = hashlib.sha256((folder/name).read_bytes()).hexdigest()
    (folder/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")


def test_public_bundle_replays_published_values_and_preserves_prior_failure(bundle):
    result = replay(bundle)
    assert result["checks_passed"] and not result["solver_executed"]
    assert result["samples"] == 125 and result["bodies"] == 10 and result["primary_responses"] == 40
    assert result["prior_numerical_failure_retained"]
    assert result["results"]["rust_tighter"]["moon_relative_jpl"]["position_metres"] == pytest.approx(718.8247845205743,abs=1e-9)
    assert not any(p.name in {"AGENTS.md","changes.md","session-handoff.md"} or ".tools" in p.parts for p in bundle.rglob("*"))
    assert (bundle/"replay_jpl.py").read_bytes() == (ROOT/"scripts/replay_jpl.py").read_bytes()


@pytest.mark.parametrize("name",["trajectories.json","raw/horizons-10-000.json"])
def test_changed_byte_rejected_before_comparison(bundle,name):
    with (bundle/name).open("ab") as stream:stream.write(b" ")
    with pytest.raises(ValueError,match="Payload changed"):replay(bundle)


def test_missing_primary_response_rejected(bundle):
    (bundle/"raw/horizons-10-000.json").unlink()
    with pytest.raises(ValueError,match="Missing payload"):replay(bundle)


def test_manifest_cannot_read_outside_bundle(bundle):
    manifest=json.loads((bundle/"manifest.json").read_bytes())
    manifest["files"]["../../outside.json"]="0"*64
    (bundle/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(ValueError,match="Unsafe payload"):replay(bundle)


@pytest.mark.parametrize("mutation",[
    lambda d:d["origin"].update(frame="ICRF"),
    lambda d:d["epochs_jd_tdb"].__setitem__(1,d["epochs_jd_tdb"][1]+.25),
    lambda d:d["settings"]["rust_tighter"].update(rtol=1e-12),
    lambda d:d["profiles"]["rust_tighter"][0][0].__setitem__(0,0.),
    lambda d:d["profiles"].pop("python"),
])
def test_self_consistent_payload_hash_does_not_hide_wrong_trajectory_metadata(bundle,mutation):
    modify_json(bundle,"trajectories.json",mutation)
    with pytest.raises(ValueError):replay(bundle)


def test_reference_row_epoch_and_gm_checked_independently(bundle):
    modify_json(bundle,"reference.json",lambda d:d["bodies"][0]["states"][0].update(jd_tdb=0.))
    with pytest.raises(ValueError,match="row epochs"):replay(bundle)


def test_checkpoint_mass_cannot_change_without_gm_consistency(bundle):
    def mutation(document):
        document["initial"][0]["mass"] *= 2
        document["bodies"][0]["mass"] *= 2
    modify_json(bundle,"initial.json",mutation)
    with pytest.raises(ValueError,match="GM mismatch"):replay(bundle)


def test_wrong_ephemeris_in_primary_response_rejected_even_with_new_checksum(bundle):
    raw_name="raw/horizons-10-000.json"
    modify_json(bundle,raw_name,lambda d:d.update(result=d["result"].replace("DE441","DE440")))
    new_hash=hashlib.sha256((bundle/raw_name).read_bytes()).hexdigest()
    modify_json(bundle,"reference.json",lambda d:d["bodies"][0]["requests"][0].update(response_sha256=new_hash))
    with pytest.raises(ValueError,match="ephemeris"):replay(bundle)


def test_isolated_process_outside_checkout_has_no_network_or_solar_import(bundle,tmp_path):
    code='''
import importlib.util,json,pathlib,sys,numpy,socket
def deny(*args,**kwargs):raise RuntimeError("Network forbidden")
socket.socket=deny
path=pathlib.Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("offline_checker",path/"replay_jpl.py")
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
result=checker.replay(path)
assert not any(n=="solar_simulator" or n.startswith("solar_simulator.") for n in sys.modules)
assert sys.flags.isolated and result["checks_passed"] and not result["solver_executed"]
print(json.dumps({"passed":True,"isolated":sys.flags.isolated}))
'''
    env=os.environ.copy()
    env["PATH"]=str(Path(os.environ["SystemRoot"])/"System32")
    env.pop("PYTHONPATH",None);env.pop("PYTHONHOME",None)
    result=subprocess.run([sys.executable,"-X","utf8","-B","-I","-c",code,str(bundle)],
        cwd=tmp_path,env=env,capture_output=True,text=True,encoding="utf-8",timeout=30)
    assert result.returncode == 0,result.stdout+result.stderr
    assert json.loads(result.stdout)["isolated"] == 1
