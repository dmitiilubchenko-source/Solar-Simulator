from dataclasses import replace

import pytest

from solar_simulator.diagnostics import angular_momentum
from solar_simulator.experiment import Settings, advance, create_experiment, preset
from solar_simulator.mergers import merge_contact
from solar_simulator.simulation import Body,total_energy,total_momentum,step
from solar_simulator.storage import save,load,to_document
from solar_simulator.vector3 import Vector3


def spheres():
    return [Body("a",2,Vector3(-1,0,0),Vector3(2,3,0),1,Vector3(0,0,4)),
            Body("b",3,Vector3(1,0,0),Vector3(-1,-2,0),1,Vector3(0,0,-1))]


def test_oblique_merger_conserves_mass_momentum_volume_and_angular_momentum():
    state=spheres()
    result=merge_contact(state,0,1)
    merged=result.bodies[0]
    assert merged.mass==5
    assert merged.radius**3==pytest.approx(2)
    assert merged.position.x==pytest.approx(.2)
    assert total_momentum(state).distance_to(total_momentum(result.bodies))<1e-14
    assert angular_momentum(state).distance_to(angular_momentum(result.bodies))<1e-14
    assert merged.spin.z!=0
    assert total_energy(result.bodies)+result.energy_offset==pytest.approx(total_energy(state))
    assert state[0].name=="a" and len(state)==2
    assert result.relative_kinetic_energy==pytest.approx(.5*1.2*(3**2+5**2))


@pytest.mark.parametrize("backend",["python","rust"])
def test_merge_then_continue_and_checkpoint(tmp_path,backend):
    if backend=="rust":
        pytest.importorskip("solar_native")
    original=preset("spheres",backend=backend)
    original=replace(original,settings=replace(original.settings,contact_mode="merge"))
    whole=advance(original,2000)
    assert len(whole.bodies)==1 and len(whole.events)==1
    assert whole.events[0].outcome=="merge" and whole.events[0].result=="A+B"
    assert whole.time==100
    partial=advance(original,1000)
    save(partial,tmp_path/"merge.json")
    resumed=advance(load(tmp_path/"merge.json"),1000)
    assert to_document(resumed)==to_document(whole)
    error=abs(total_energy(whole.bodies)+whole.model_energy_offset-total_energy(original.bodies))
    assert error/abs(total_energy(original.bodies))<.002
    finer=replace(original,settings=replace(original.settings,dt=.025))
    fine=advance(finer,4000)
    fine_error=abs(total_energy(fine.bodies)+fine.model_energy_offset-total_energy(original.bodies))
    assert fine_error<.4*error


def test_spin_survives_python_native_motion_and_native_diagnostics():
    native=pytest.importorskip("solar_native")
    from solar_simulator.rust_backend import evolve
    body=Body("spinning",5,Vector3(0,0,0),Vector3(1,0,0),1,Vector3(2,3,4))
    for result in (step([body],1),evolve([body],1,10)):
        assert result[0].spin.distance_to(body.spin)==0
    values=native.diagnostics([5],[[0,0,0]],[[1,0,0]],[[2,3,4]])
    assert values[2]==[2,3,4]
    with pytest.raises(ValueError):
        native.diagnostics([5],[[0,0,0]],[[1,0,0]],[[float("nan"),0,0]])
    with pytest.raises(ValueError):
        native.diagnostics([5],[[0,0,0]],[[1,0,0]],[])


def test_v1_checkpoint_migrates_without_mutating_document():
    from solar_simulator.storage import from_document
    document=to_document(preset("sun-earth"))
    document["schema_version"]=1
    del document["orientation_work"]
    del document["origin"]
    del document["model_energy_offset"]
    for key in ("integrator", "rtol", "position_atol", "velocity_atol", "physics", "figures"):
        del document["settings"][key]
    for field in ("initial","bodies"):
        for body in document[field]:
            del body["spin"]
    result=from_document(document)
    assert result.model_energy_offset==0 and result.bodies[0].spin.magnitude()==0
    assert "spin" not in document["bodies"][0]


def test_simultaneous_merge_rejected_and_invalid_geometry():
    bodies=[Body("a",1,Vector3(-4,0,0),Vector3(1,0,0),1),
            Body("b",1,Vector3(0,0,0),Vector3(0,0,0),1),
            Body("c",1,Vector3(4,0,0),Vector3(-1,0,0),1)]
    experiment=create_experiment(bodies,Settings(3,contact_mode="merge"))
    with pytest.raises(ValueError,match="Одновременное"):
        advance(experiment,1)
    with pytest.raises(ValueError):
        merge_contact(bodies,0,1)


def test_multiple_mergers_preserve_event_genealogy_and_total_angular_momentum(tmp_path):
    initial=spheres()+[Body("c",1,Vector3(10,0,0),Vector3(-5,0,0),1)]
    experiment=create_experiment(initial,Settings(.01,contact_mode="merge"))
    result=advance(experiment,500)
    assert len(result.bodies)==1 and len(result.events)==2
    assert angular_momentum(result.bodies).distance_to(angular_momentum(initial))<1e-10
    save(result,tmp_path/"history.json")
    assert to_document(load(tmp_path/"history.json"))==to_document(result)
