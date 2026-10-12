"""Whole SB441 group preserves the 14-body control and all saved provenance."""
from dataclasses import replace
from importlib.resources import files
import hashlib,json
import numpy as np
import pytest
from solar_simulator.perturbers import (solar_system_asteroids,solar_system_asteroids_full,
    ASTEROIDS_FULL_SPEC,decode_body_dataset,figure_parent_origin)
from solar_simulator.ephemerides import solar_system
from solar_simulator.oblateness import sun_earth_moon_quadrupoles,earth_j2
from solar_simulator.experiment import preset,advance,reset
from solar_simulator.storage import save,load,to_document,from_document
from scripts.assess_resolved_moon import states
from scripts.fetch_asteroid_data import ALL_IDENTITIES,OTHER_IDENTITIES


def test_all_sixteen_asteroids_preserve_every_parent_value_and_source_identity():
    base,parent=solar_system_asteroids();bodies,origin=solar_system_asteroids_full()
    assert len(bodies)==27 and np.array_equal(states(base),states(bodies[:14]))
    assert [(b.name,b.mass,b.radius) for b in bodies[:14]]==[(b.name,b.mass,b.radius) for b in base]
    assert [b.name for b in bodies[11:]]==[i[1] for i in ALL_IDENTITIES]
    assert len({b.name for b in bodies})==27 and all(b.mass>0 and b.radius==0 for b in bodies)
    assert ASTEROIDS_FULL_SPEC.identities==tuple((i,n) for i,n,_ in OTHER_IDENTITIES)
    raw=files('solar_simulator.data').joinpath(ASTEROIDS_FULL_SPEC.filename).read_bytes()
    doc=json.loads(raw)
    assert hashlib.sha256(raw).hexdigest()==origin.dataset_sha256
    assert doc['base_origin']['dataset_sha256']==parent.dataset_sha256
    assert len(doc['bodies'])==13 and all('states' not in b for b in doc['bodies'])
    _,root=solar_system(resolved_moon=True)
    assert figure_parent_origin(origin)==root
    assert sun_earth_moon_quadrupoles(bodies,origin)==sun_earth_moon_quadrupoles(base,parent)
    assert earth_j2(bodies,origin)==earth_j2(base,parent)
    with pytest.raises(ValueError):sun_earth_moon_quadrupoles(bodies,parent)


@pytest.mark.parametrize('changed',['wrong_parent','duplicated_name','missing_body','future_states'])
def test_full_group_contract_rejects_conflicting_data(changed):
    doc=json.loads(files('solar_simulator.data').joinpath(ASTEROIDS_FULL_SPEC.filename).read_bytes())
    if changed=='wrong_parent':doc['base_origin']['gm_sha256']='0'*64
    if changed=='duplicated_name':doc['bodies'][1]['name']=doc['bodies'][0]['name']
    if changed=='missing_body':doc['bodies'].pop()
    if changed=='future_states':doc['bodies'][0]['states']=[]
    with pytest.raises(ValueError):decode_body_dataset(json.dumps(doc).encode(),ASTEROIDS_FULL_SPEC)


def test_cli_and_checkpoint_resume_full_twenty_seven_body_model(tmp_path,capsys):
    from solar_simulator.cli import main
    file=tmp_path/'full.json'
    assert main(['new','solar-system-asteroids-full',str(file),'--physics','eih-1pn','--figures','sun-earth-moon-q2',
        '--relative-pair','Earth','Moon','--rtol','3e-14','--position-atol','1e-5','--velocity-atol','1e-11'])==0
    assert json.loads(capsys.readouterr().out)['bodies']==27
    initial=load(file);half=advance(initial,24);save(half,file);restored=load(file)
    assert restored.origin==initial.origin and restored.settings.figures==initial.settings.figures
    assert restored.orientation_work==half.orientation_work and restored.orientation_work!=0
    resumed=advance(restored,24);whole=advance(initial,48)
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(whole.bodies)[:,:3],axis=1))<.02
    assert reset(resumed).origin==initial.origin
    bad=to_document(restored);bad['origin']['dataset_sha256']='0'*64
    with pytest.raises(ValueError):from_document(bad)


def test_generic_rust_newton_kernel_also_handles_twenty_seven_bodies():
    pytest.importorskip('solar_native')
    initial=preset('solar-system-asteroids-full',backend='rust');result=advance(initial,1)
    assert len(result.bodies)==27 and result.origin==initial.origin and result.time==3600
