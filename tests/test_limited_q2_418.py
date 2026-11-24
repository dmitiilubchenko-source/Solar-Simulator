"""Product limit regression tests. Red on the frozen unrestricted0.4.0 base."""
from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from scripts.two_q2_fixture380 import fixture
from solar_simulator.experiment import Experiment, create_experiment, advance, reset
from solar_simulator.storage import from_document, save

MESSAGE = "не более одного"
ROOT = Path(__file__).resolve().parents[1]


def unsafe_state(*, initial_count=2, current_count=2, halted=False):
    """Deliberately bypass construction to test mutation and early-return guards."""
    bodies, rotations, settings = fixture()
    state = Experiment(bodies,bodies,settings)
    object.__setattr__(state,"initial_rotations",rotations[:initial_count])
    object.__setattr__(state,"rotations",rotations[:current_count])
    object.__setattr__(state,"halted",halted)
    return state


@pytest.mark.parametrize("field",["initial_rotations","rotations"])
@pytest.mark.parametrize("count",[2,3])
def test_constructor_and_replace_reject_unsupported_counts(field,count):
    b,r,s=fixture();groups=r+(r[0],) if count==3 else r
    with pytest.raises(ValueError,match=MESSAGE):
        Experiment(b,b,s,**{field:groups})
    plain=Experiment(b,b,s)
    with pytest.raises(ValueError,match=MESSAGE):
        replace(plain,**{field:groups})


def test_create_and_schema10_reject_before_calculation():
    b,r,s=fixture()
    with pytest.raises(ValueError,match=MESSAGE):create_experiment(b,s,rotations=r)
    raw=(ROOT/"src/solar_simulator/data/two-q2-demo380.json").read_bytes()
    with pytest.raises(ValueError,match=MESSAGE):from_document(json.loads(raw))
    assert (ROOT/"src/solar_simulator/data/two-q2-demo380.json").read_bytes()==raw


@pytest.mark.parametrize("counts",[(2,2),(2,0),(0,2),(2,1),(1,2)])
@pytest.mark.parametrize("steps,halted",[(0,False),(1,False),(1,True)])
def test_advance_guard_precedes_all_early_returns(counts,steps,halted):
    state=unsafe_state(initial_count=counts[0],current_count=counts[1],halted=halted)
    with patch("solar_simulator.nbody_rotation.solve_ivp",side_effect=AssertionError("Solver called")):
        with pytest.raises(ValueError,match=MESSAGE):advance(state,steps)


def test_direct_integrator_and_controller_reject_without_solver():
    from solar_simulator.nbody_rotation import integrate, RotationDOP853
    b,r,s=fixture()
    with patch("solar_simulator.nbody_rotation.solve_ivp",side_effect=AssertionError("Solver called")):
        with pytest.raises(ValueError,match=MESSAGE):integrate(b,r,[0.,50.])
    with pytest.raises(ValueError,match=MESSAGE):
        RotationDOP853(lambda t,y:np.zeros_like(y),0.,np.zeros(26),1.,body_count=2,rotation_count=2)


@pytest.mark.parametrize("action",["save","reset","recovery","record"])
def test_restart_recovery_and_record_reject_without_side_effects(tmp_path,action):
    from solar_simulator.recovery import save_recovery
    from solar_simulator.trajectory import record_trajectory
    state=unsafe_state()
    before=list(tmp_path.iterdir())
    with patch("solar_simulator.nbody_rotation.solve_ivp",side_effect=AssertionError("Solver called")), pytest.raises(ValueError,match=MESSAGE):
        if action=="save":save(state,tmp_path/"output.json")
        elif action=="reset":reset(state)
        elif action=="recovery":save_recovery(state,directory=tmp_path)
        else:record_trajectory(state,tmp_path/"track",50.)
    assert list(tmp_path.iterdir())==before


@pytest.mark.parametrize("command",["inspect","run","run-until","export-state","record-trajectory"])
def test_cli_load_is_a_common_boundary(tmp_path,command):
    from solar_simulator.commands import main
    raw=(ROOT/"src/solar_simulator/data/two-q2-demo380.json").read_bytes()
    source=tmp_path/"two.json";source.write_bytes(raw)
    args=[command,str(source)]
    if command!="inspect":args.append(str(tmp_path/"output"))
    if command in ("run-until","record-trajectory"):args+=["--time","50"]
    if command=="run":args+=["--steps","1"]
    with patch("solar_simulator.nbody_rotation.solve_ivp",side_effect=AssertionError("Solver called")), pytest.raises(SystemExit):
        main(args)
    assert source.read_bytes()==raw and not (tmp_path/"output").exists()


def test_gui_profile_is_unavailable_and_button_removed():
    from solar_simulator.application_profiles import two_q2_demo
    with pytest.raises(ValueError,match=MESSAGE):two_q2_demo()
    source=(ROOT/"src/solar_simulator/app.py").read_text(encoding="utf-8")
    assert 'self._button(quick,"Две Q2-фигуры — учебный",self._open_two_q2)' not in source


@pytest.mark.parametrize("action",["load","replay"])
def test_trajectory_and_replay_reject_before_destination_write(tmp_path,action):
    import hashlib
    from solar_simulator.trajectory import Trajectory
    from solar_simulator.recipe import replay_trajectory
    raw=(ROOT/"src/solar_simulator/data/two-q2-demo380.json").read_bytes()
    track=tmp_path/"source";track.mkdir();(track/"frame-000000.json").write_bytes(raw)
    manifest=dict(format="solar-trajectory",schema_version=1,units="SI",
        engine="advance-towards-packets",packet_steps=1,start_time_seconds=0.,
        requested_target_seconds=50.,status="stopped",
        frames=[dict(file="frame-000000.json",time_seconds=0.,sha256=hashlib.sha256(raw).hexdigest())])
    (track/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    before={p.name:p.read_bytes() for p in track.iterdir()}
    with pytest.raises(ValueError,match=MESSAGE):
        if action=="load":Trajectory(track)
        else:replay_trajectory(track,tmp_path/"destination")
    assert before=={p.name:p.read_bytes() for p in track.iterdir()}
    assert not (tmp_path/"destination").exists()


def test_historical_tests_and_sources_remain_byte_pinned():
    from hashlib import sha256
    from zipfile import ZipFile
    from scripts.release_history import PRODUCT_LIMIT_ARCHIVE,PRODUCT_LIMIT_ARCHIVE_SHA,ui_historical_sha
    archive=ROOT/"scripts/validation/product-before418-tests.zip"
    assert sha256(archive.read_bytes()).hexdigest()=="f3a4dc88b8f7e3fc78f6c83a3598612780129c87c9ab201a7aff511ab20102c2"
    with ZipFile(archive) as z:
        manifest=json.loads(z.read("manifest.json"))
        for name,digest in manifest.items():assert sha256(z.read(name)).hexdigest()==digest
    path=ROOT/PRODUCT_LIMIT_ARCHIVE
    assert sha256(path.read_bytes()).hexdigest()==PRODUCT_LIMIT_ARCHIVE_SHA
    with ZipFile(path) as z:
        for name in z.namelist():
            expected=sha256(z.read(name)).hexdigest()
            assert ui_historical_sha(ROOT,name,expected)==expected


@pytest.mark.parametrize("damage", ["missing", "changed", "wrong_digest"])
def test_offline_source_bundle_is_complete_and_rejects_damage(tmp_path, damage):
    from hashlib import sha256
    from zipfile import ZipFile
    from scripts.release_history import (
        HISTORICAL_ARCHIVES, PRODUCT_LIMIT_ARCHIVE, ui_historical_sha,
    )
    assert PRODUCT_LIMIT_ARCHIVE in HISTORICAL_ARCHIVES
    name = "src/solar_simulator/recovery.py"
    with ZipFile(ROOT / PRODUCT_LIMIT_ARCHIVE) as z:
        expected = sha256(z.read(name)).hexdigest()
    live = tmp_path / name
    live.parent.mkdir(parents=True)
    live.write_bytes(b"a different live runtime")
    archive = tmp_path / PRODUCT_LIMIT_ARCHIVE
    archive.parent.mkdir(parents=True)
    if damage != "missing":
        archive.write_bytes((ROOT / PRODUCT_LIMIT_ARCHIVE).read_bytes())
    if damage == "changed":
        archive.write_bytes(archive.read_bytes() + b"damaged")
        with pytest.raises(ValueError, match="Changed historical source archive"):
            ui_historical_sha(tmp_path, name, expected)
    else:
        if damage == "wrong_digest": expected = "0" * 64
        assert ui_historical_sha(tmp_path, name, expected) != expected
