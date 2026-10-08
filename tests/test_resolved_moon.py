"""Pinned Earth/Moon source consistency, dynamics, checkpoint and UI contracts."""
from copy import deepcopy
from dataclasses import replace
from importlib.resources import files
import json

import numpy as np
import pytest

from solar_simulator.ephemerides import (solar_system, decode_snapshot, RESOLVED_DATASET_NAME,
                                         RESOLVED_IDS, RESOLVED_NAMES)
from solar_simulator.experiment import preset, create_experiment, advance, reset
from solar_simulator.simulation import G
from solar_simulator.storage import save, load, to_document
from solar_simulator.vector3 import Vector3
from scripts.fetch_ephemerides import gm_values, parse_result
from solar_simulator.cli import main


def snapshot():
    return json.loads(files("solar_simulator.data").joinpath(RESOLVED_DATASET_NAME).read_bytes())


def test_real_pair_mass_and_barycentre_match_base_without_changing_other_systems():
    resolved,origin=solar_system(resolved_moon=True)
    original,base_origin=solar_system()
    assert len(resolved)==10 and tuple(b.name for b in resolved)==RESOLVED_NAMES
    assert origin.dataset_sha256=="d58227299b10b217246aa5c63f33da51b0fd331b5c7a75bee400d577d6d1f702"
    assert origin.gm_sha256==base_origin.gm_sha256 and origin.epoch_jd_tdb==base_origin.epoch_jd_tdb
    earth,moon=resolved[3:5];emb=original[3]
    assert earth.mass+moon.mass==pytest.approx(emb.mass,rel=2e-15)
    fraction=moon.mass/(earth.mass+moon.mass)
    centre=earth.position.add(moon.position.subtract(earth.position).multiply(fraction))
    velocity=earth.velocity.add(moon.velocity.subtract(earth.velocity).multiply(fraction))
    assert centre.distance_to(emb.position)<.01
    assert velocity.distance_to(emb.velocity)<1e-8
    assert 3e8<earth.position.distance_to(moon.position)<5e8
    old={b.name:b for b in original}
    for body in resolved:
        if body.name in old:
            before=old[body.name]
            assert body.mass==before.mass and body.position.distance_to(before.position)==0
            assert body.velocity.distance_to(before.velocity)==0


@pytest.mark.parametrize("kind",["double_count","swapped","duplicate","missing","planet_centre"])
def test_layout_rejects_mixed_barycentre_and_resolved_pair(kind):
    doc=snapshot()
    if kind=="double_count":
        doc["bodies"][3]["id"]=3;doc["bodies"][3]["name"]="Earth-Moon"
    elif kind=="swapped":
        doc["bodies"][3],doc["bodies"][4]=doc["bodies"][4],doc["bodies"][3]
    elif kind=="duplicate":
        doc["bodies"][4]=deepcopy(doc["bodies"][3])
    elif kind=="missing":
        del doc["bodies"][4]
    else:
        doc["bodies"][5]["id"]=499
    with pytest.raises(ValueError):
        decode_snapshot(json.dumps(doc).encode())


def test_gm_import_requires_both_earth_and_moon():
    raw=b"BODY399_GM=(3.986D+05)\nBODY301_GM=(4.903D+03)"
    values=gm_values(raw,(399,301))
    assert values[399]==pytest.approx(3.986e14) and values[301]==pytest.approx(4.903e12)
    with pytest.raises(ValueError):
        gm_values(b"BODY3_GM=(4.035E+05)",(399,301))


def test_resolved_cli_checkpoint(tmp_path,capsys):
    initial,final=tmp_path/"moon.json",tmp_path/"moon-day.json"
    assert main(["new","solar-system-moon",str(initial),"--physics","eih-1pn"])==0
    capsys.readouterr()
    assert main(["run",str(initial),str(final),"--steps","24"])==0
    values=json.loads(capsys.readouterr().out)
    assert values["bodies"]==10 and values["physics"]=="eih-1pn"
    assert values["epoch_jd_tdb"]==2461322.5
    assert load(final).origin==load(initial).origin


def test_earth_centre_and_moon_ids_cannot_be_substituted_in_horizons_parser():
    header='''Target body name: Moon (301) {source: DE441}
Center body name: Solar System Barycenter (0) {source: DE441}
Output units    : KM-S
Reference frame : Ecliptic of J2000.0
Output type     : GEOMETRIC cartesian states
JDTDB
$$SOE
2461321.5,date,1,2,3,4,5,6,
$$EOE'''
    payload=dict(signature=dict(version="1.3",source="NASA/JPL Horizons API"),result=header)
    assert parse_result(payload,301,[2461321.5])[0]["position"]==[1000,2000,3000]
    for other in (3,399):
        with pytest.raises(ValueError):
            parse_result(payload,other,[2461321.5])


@pytest.mark.parametrize("physics",["newtonian","eih-1pn"])
def test_resolved_checkpoint_resume_and_relative_lunar_motion(tmp_path,physics):
    initial=preset("solar-system-moon")
    initial=replace(initial,settings=replace(initial.settings,physics=physics,dt=86400))
    assert len(initial.bodies)==10 and initial.origin is not None
    whole=advance(initial,32)
    partial=advance(initial,16)
    save(partial,tmp_path/"resolved.json")
    restored=load(tmp_path/"resolved.json")
    assert to_document(restored)==to_document(partial) and reset(restored).origin==initial.origin
    resumed=advance(restored,16)
    for a,b in zip(resumed.bodies,whole.bodies):
        assert a.position.distance_to(b.position)<10
        assert a.velocity.distance_to(b.velocity)<1e-4
    moon_r=whole.bodies[4].position.subtract(whole.bodies[3].position)
    initial_r=initial.bodies[4].position.subtract(initial.bodies[3].position)
    assert 3e8<moon_r.magnitude()<5e8 and moon_r.distance_to(initial_r)>1e8


def test_native_verlet_remains_available_for_resolved_scenario():
    pytest.importorskip("solar_native")
    a=preset("solar-system-moon",backend="rust")
    assert a.settings.integrator=="verlet" and a.settings.physics=="newtonian"
    b=create_experiment(a.bodies,replace(a.settings,backend="python"),origin=a.origin)
    native,python=advance(a,48),advance(b,48)
    for x,y in zip(native.bodies,python.bodies):
        assert x.position.distance_to(y.position)<.01
        assert x.velocity.distance_to(y.velocity)<1e-8


def test_resolved_month_against_independent_numerical_reference():
    from scripts.assess_relativity import independent_reference
    from scripts.assess_resolved_moon import sample
    initial,origin=solar_system(resolved_moon=True)
    times=np.arange(33,dtype=float)*86400
    expected,consistency=independent_reference(initial,times)
    assert consistency<10
    actual=sample(initial,origin,times,"eih-1pn")
    assert np.linalg.norm(actual[:,:,:3]-expected[:,:,:3],axis=2).max()<10
    assert np.linalg.norm(actual[:,:,3:]-expected[:,:,3:],axis=2).max()<1e-4
