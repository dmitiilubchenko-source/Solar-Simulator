import json
from pathlib import Path
import subprocess
import sys

import pytest

from solar_simulator.experiment import Settings,create_experiment
from solar_simulator.simulation import Body
from solar_simulator.storage import load,save,to_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3


def command(*args):
    return subprocess.run([sys.executable,"-X","utf8","-B","-m","solar_simulator",*map(str,args)],
                          capture_output=True,text=True,encoding="utf-8",timeout=30)


@pytest.mark.parametrize("integrator",["verlet","dop853"])
@pytest.mark.parametrize("backend",["python","rust"])
def test_actual_cli_target_matches_headless_and_preserves_input(tmp_path,integrator,backend):
    if backend=="rust":pytest.importorskip("solar_native")
    state=create_experiment([Body("free",1e20,Vector3(5.,6.,7.),Vector3(2.,-3.,4.))],
                            Settings(3.,integrator=integrator,backend=backend))
    initial=tmp_path/"initial.json";final=tmp_path/"final.json";save(state,initial)
    previous=initial.read_bytes()
    result=command("run-until",initial,final,"--time","10.25","--batch","2")
    assert result.returncode==0,result.stderr
    expected=advance_towards(advance_towards(state,10.25,2),10.25,2)
    assert to_document(load(final))==to_document(expected)
    assert json.loads(result.stdout)["time_seconds"]==10.25 and initial.read_bytes()==previous


@pytest.mark.parametrize("time",["nan","inf","-1"])
def test_invalid_target_does_not_replace_existing_output(tmp_path,time):
    state=create_experiment([Body("free",1e20,Vector3(0.,0.,0.),Vector3(0.,0.,0.))],Settings(3.))
    initial=tmp_path/"initial.json";final=tmp_path/"final.json";save(state,initial);final.write_bytes(b"keep")
    result=command("run-until",initial,final,"--time",time)
    assert result.returncode==2 and final.read_bytes()==b"keep"


def test_contact_output_distinguishes_event_time_from_target(tmp_path):
    state=create_experiment([Body("a",1.,Vector3(-5.,0.,0.),Vector3(1.,0.,0.),1.),
                             Body("b",1.,Vector3(5.,0.,0.),Vector3(-1.,0.,0.),1.)],Settings(3.))
    initial=tmp_path/"initial.json";final=tmp_path/"final.json";save(state,initial)
    result=command("run-until",initial,final,"--time","10.25","--batch","2")
    values=json.loads(result.stdout)
    assert result.returncode==0 and load(final).halted
    assert values["requested_target_seconds"]==10.25 and not values["target_reached"]
    assert values["time_seconds"]==pytest.approx(4.,abs=1e-8)


def test_qualified_profile_cli_and_legacy_inspection(tmp_path):
    from solar_simulator.application_profiles import solar_sandbox
    path=tmp_path/"solar.json";result=command("solar-sandbox",path)
    assert result.returncode==0,result.stderr
    assert to_document(load(path))==to_document(solar_sandbox())
    result=command("inspect",path)
    assert result.returncode==0 and json.loads(result.stdout)["physics"]=="eih-1pn"
