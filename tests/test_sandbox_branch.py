"""Branch semantics, archival integrity, native continuation and write failures."""
from copy import deepcopy
from dataclasses import replace
import json
import subprocess
import sys

import pytest

from solar_simulator.experiment import Settings, advance, create_experiment, preset, reset
from solar_simulator.sandbox import (branch_experiment, from_branch_document,
    load_branch, load_experiment, save_branch, to_branch_document)
from solar_simulator.simulation import Body
from solar_simulator.storage import load, save, to_document
from solar_simulator.vector3 import Vector3


@pytest.mark.parametrize("backend", ["python", "rust"])
@pytest.mark.parametrize("integrator", ["verlet", "dop853"])
def test_no_edit_branch_matches_same_partition_continuation(backend, integrator):
    if backend == "rust":
        pytest.importorskip("solar_native")
    parent = preset("binary-star", backend=backend)
    parent = replace(parent, settings=replace(parent.settings, integrator=integrator))
    parent = advance(parent, 20)
    before = to_document(parent)
    branch = branch_experiment(parent)
    assert to_document(parent) == before
    assert to_document(branch.parent) == before
    assert branch.child.time == 0 and branch.child.events == ()
    assert branch.child.origin is None and branch.changes() == []
    expected, actual = advance(parent, 10), advance(branch.child, 10)
    for a, b in zip(expected.bodies, actual.bodies):
        assert a.position.distance_to(b.position) == 0
        assert a.velocity.distance_to(b.velocity) == 0


def test_modified_jpl_start_has_detached_parent_and_new_baseline():
    parent = preset("solar-system-moon")
    before = to_document(parent)
    branch = branch_experiment(parent, replacements=(("Sun", replace(parent.bodies[0], mass=parent.bodies[0].mass*2)),))
    assert branch.parent.origin == parent.origin
    assert branch.child.origin is None
    assert branch.child.initial[0].mass == parent.bodies[0].mass*2
    assert branch.changes()[0]["name"] == "Sun"
    copy = branch.parent
    copy.bodies[0].velocity.x += 1
    branch.child.bodies[1].velocity.x += 1
    assert to_document(parent) == before
    assert to_document(branch.parent) == before
    assert branch.child.initial[1].velocity.x == parent.bodies[1].velocity.x


def test_adding_second_star_and_removing_sun_uses_generic_bodies():
    parent = preset("sun-earth")
    extra = Body("Another star", 1e30, Vector3(0, 0, 1e12), Vector3(1, 2, 3))
    branch = branch_experiment(parent, additions=(extra,), removals=("Sun",))
    assert [b.name for b in branch.child.bodies] == ["Earth", "Another star"]
    extra.position.z += 1
    assert branch.child.bodies[1].position.z == 1e12
    assert advance(branch.child, 2).time > 0
    alone = branch_experiment(parent, removals=("Sun",)).child
    evolved = advance(alone, 3)
    b = alone.bodies[0]
    expected = b.position.add(b.velocity.multiply(evolved.time))
    assert evolved.bodies[0].position.distance_to(expected) < 1e-3


def test_rename_is_explicit_and_relative_pair_is_not_silently_repaired():
    parent = preset("binary-star")
    name = parent.bodies[0].name
    body = replace(parent.bodies[0], name="Renamed")
    branch = branch_experiment(parent, replacements=((name, body),))
    assert branch.child.bodies[0].name == "Renamed"
    parent = replace(parent, settings=replace(parent.settings, integrator="dop853",
                                             relative_pair=tuple(b.name for b in parent.bodies)))
    with pytest.raises(ValueError):
        branch_experiment(parent, replacements=((name, body),))


@pytest.mark.parametrize("case", ["empty", "duplicate", "unknown", "same-edit", "overlap", "wrong-type"])
def test_bad_edits_leave_parent_unchanged(case):
    parent = preset("sun-earth")
    before = to_document(parent)
    values = {
        "empty": dict(removals=("Sun", "Earth")),
        "duplicate": dict(additions=(parent.bodies[0],)),
        "unknown": dict(removals=("Missing",)),
        "same-edit": dict(removals=("Sun",), replacements=(("Sun", parent.bodies[0]),)),
        "overlap": dict(additions=(replace(parent.bodies[0], name="Coincident"),)),
        "wrong-type": dict(additions=[parent.bodies[0]]),
    }
    with pytest.raises(ValueError):
        branch_experiment(parent, **values[case])
    assert to_document(parent) == before


def test_bundle_preserves_parent_and_resumes_child_exactly(tmp_path):
    parent = advance(preset("sun-earth"), 7)
    branch = branch_experiment(parent, replacements=(("Sun", replace(parent.bodies[0], mass=parent.bodies[0].mass*2)),))
    branch = replace(branch, child=advance(branch.child, 9))
    path = tmp_path/"ветка с пробелами.json"
    save_branch(branch, path)
    restored = load_branch(path)
    assert to_branch_document(restored) == to_branch_document(branch)
    assert to_document(load_experiment(path)) == to_document(branch.child)
    assert to_document(advance(restored.child, 5)) == to_document(advance(branch.child, 5))
    assert reset(restored.child).time == 0
    # Extracting the original does not depend on a path outside the bundle.
    original_path = tmp_path/"parent.json"
    save(restored.parent, original_path)
    assert to_document(load(original_path)) == to_document(parent)
    assert to_document(load_experiment(original_path)) == to_document(parent)


@pytest.mark.parametrize("case", ["checksum", "parent", "changes", "settings", "origin", "version", "extra"])
def test_tampered_bundle_is_rejected(case):
    document = to_branch_document(branch_experiment(preset("solar-system-moon")))
    if case == "checksum": document["parent_sha256"] = "0"*64
    if case == "parent": document["parent"]["time"] = 2
    if case == "changes": document["changes"] = [dict(name="fake")]
    if case == "settings": document["child"]["settings"]["dt"] *= 2
    if case == "origin": document["child"]["origin"] = deepcopy(document["parent"]["origin"])
    if case == "version": document["version"] = True
    if case == "extra": document["extra"] = 1
    with pytest.raises(ValueError):
        from_branch_document(document)


def test_failed_bundle_write_preserves_existing_file(tmp_path, monkeypatch):
    import solar_simulator.storage as storage
    path = tmp_path/"branch.json"
    save_branch(branch_experiment(preset("sun-earth")), path)
    before = path.read_bytes()
    def fail(*args): raise OSError("Controlled disk failure")
    monkeypatch.setattr(storage.os, "replace", fail)
    with pytest.raises(OSError):
        save_branch(branch_experiment(preset("earth-moon")), path)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob(".solar-*.tmp"))


def test_bundle_parser_rejects_duplicate_keys(tmp_path):
    path = tmp_path/"bad.json"
    path.write_text('{"version":1,"version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="Повтор"):
        load_branch(path)


def test_old_contact_editor_model_still_can_branch():
    parent = advance(preset("spheres"), 2000)
    branch = branch_experiment(parent)
    assert branch.child.events == () and branch.child.dissipated_energy == 0
    assert to_document(branch.parent) == to_document(parent)


def test_prescribed_ring_checkpoint_loads_in_fresh_process(tmp_path):
    from solar_simulator.kuiper_ring import solar_system_ring
    from solar_simulator.oblateness import sun_earth_moon_quadrupoles
    bodies, origin = solar_system_ring(36)
    parent = create_experiment(bodies, Settings(3600, integrator="dop853",
        figures=sun_earth_moon_quadrupoles(bodies, origin)), origin=origin)
    path = tmp_path/"ring.json"
    save(parent, path)
    code = '''
import sys
from solar_simulator.storage import load
assert "solar_simulator.kuiper_ring" not in sys.modules
p = load(sys.argv[1])
assert len(p.bodies) == 420 and len(p.settings.figures) == 3
'''
    result = subprocess.run([sys.executable, "-B", "-c", code, str(path)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
