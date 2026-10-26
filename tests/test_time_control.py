from scripts.release_history import ui_historical_sha
from dataclasses import replace
from math import inf, nan, nextafter

import pytest

from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.simulation import Body
from solar_simulator.storage import load, save, to_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3


def inertial(integrator="verlet", dt=3., backend="python"):
    return create_experiment([Body("free", 1e20, Vector3(5., 6., 7.), Vector3(2., -3., 4.))],
                             Settings(dt, backend=backend, integrator=integrator))


@pytest.mark.parametrize("integrator", ["verlet", "dop853"])
@pytest.mark.parametrize("backend", ["python", "rust"])
def test_target_has_analytic_free_motion_and_unchanged_settings(integrator, backend):
    if backend == "rust": pytest.importorskip("solar_native")
    original = inertial(integrator, backend=backend)
    before = to_document(original)
    state = advance_towards(original, 10.25, 2)
    assert state.time == 6.
    state = advance_towards(state, 10.25, 2)
    assert state.time == 10.25
    b = state.bodies[0]
    assert (b.position.x, b.position.y, b.position.z) == pytest.approx((25.5, -24.75, 48.), abs=1e-12)
    assert state.settings is original.settings
    assert to_document(original) == before
    assert advance_towards(state, 10.25) is state


@pytest.mark.parametrize("target", [True, "1", nan, inf, -1.])
def test_invalid_target_preserves_input(target):
    state = inertial()
    before = to_document(state)
    with pytest.raises(ValueError): advance_towards(state, target)
    assert to_document(state) == before


@pytest.mark.parametrize("count", [True, 0, -1, 2001, 1.5])
def test_packet_bound_is_validated(count):
    with pytest.raises(ValueError): advance_towards(inertial(), 10., count)


def test_backward_and_unresolved_time_are_rejected():
    state = advance(inertial(), 1)
    with pytest.raises(ValueError, match="вперёд"): advance_towards(state, 2.)
    state = replace(inertial(dt=1e-6), time=1e20)
    with pytest.raises(ValueError, match="времени"): advance_towards(state, nextafter(state.time, inf), 1)


def test_shortened_verlet_step_preserves_nominal_step_and_packet_bound(monkeypatch):
    import solar_simulator.time_control as control
    calls=[]
    def recording(state, count):
        calls.append((state.settings.dt, count))
        return advance(state, count)
    monkeypatch.setattr(control, "advance", recording)
    state=inertial()
    state=advance_towards(state, 10.25, 2)
    state=advance_towards(state, 10.25, 2)
    assert calls == [(3., 2), (3., 1), (1.25, 1)]
    assert state.time == 10.25 and state.settings.dt == 3.
    # Decimal step arithmetic must not overshoot or append a whole extra step.
    state=inertial(dt=.1)
    for _ in range(5):
        if state.time == .3: break
        state=advance_towards(state, .3, 2)
        assert state.time <= .3
    assert state.time == .3


@pytest.mark.parametrize("integrator", ["verlet", "dop853"])
def test_checkpoint_resume_matches_same_packet_sequence(tmp_path, integrator):
    state=advance_towards(inertial(integrator), 25.25, 2)
    path=tmp_path/"pause.json"; save(state,path)
    resumed=load(path)
    while state.time < 25.25:
        state=advance_towards(state,25.25,2)
        resumed=advance_towards(resumed,25.25,2)
    assert to_document(resumed) == to_document(state)


@pytest.mark.parametrize("target", [5., 10.25])
def test_contact_keeps_event_time_instead_of_requested_time(target):
    bodies=[Body("left",1.,Vector3(-5.,0.,0.),Vector3(1.,0.,0.),1.),
            Body("right",1.,Vector3(5.,0.,0.),Vector3(-1.,0.,0.),1.)]
    state=create_experiment(bodies,Settings(3.))
    state=advance_towards(state,target,2)
    assert state.halted and state.time == state.events[-1].time
    assert state.time == pytest.approx(4.,abs=1e-8)
    assert state.settings.dt == 3.
    assert advance_towards(state,target,2) is state


@pytest.mark.parametrize("profile", ["solar_sandbox", "lunar_rotation"])
@pytest.mark.parametrize("backend", ["python", "rust"])
def test_eih_figures_and_dynamic_rotation_keep_settings_and_absolute_time(profile, backend):
    if backend == "rust": pytest.importorskip("solar_native")
    from solar_simulator import application_profiles
    state=getattr(application_profiles,profile)(backend=backend)
    state=advance(state,1)
    target=state.time+12.25
    controlled=advance_towards(state,target,2)
    manual=advance(replace(state,settings=replace(state.settings,dt=12.25)),1)
    manual=replace(manual,settings=state.settings)
    assert to_document(controlled) == to_document(manual)
    assert controlled.time == target and controlled.settings is state.settings


def test_published_time_audit_matches_current_sources_and_predeclared_criteria():
    import hashlib,json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    report=json.loads((root/"docs/time-control-validation.json").read_text(encoding="utf-8"))
    assert report["checks_passed"]
    for name,digest in report["source_sha256"].items():
        assert ui_historical_sha(root,name,digest) == digest
    for row in report["results"]:
        assert row["checks_passed"] and row["partition_position_difference_metres"] < 1
        assert all(3.8 < ratio < 4.2 for ratio in row["convergence_ratios"])
        for result in row["dop853"]:
            values=result["after"]
            assert values["position_metres"] < 10 and values["velocity_m_per_s"] < 1e-5
            assert values["relative_energy_drift"] < 1e-10 and values["relative_angular_momentum_drift"] < 1e-10
            assert result["same_partition_exact"] and values["final_time_seconds"] == report["target_seconds"]
