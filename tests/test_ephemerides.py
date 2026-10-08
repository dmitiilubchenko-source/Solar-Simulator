"""Synthetic fixtures validate the importer; they are not astronomical data."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from solar_simulator.ephemerides import decode_snapshot, EXPECTED_IDS, NAMES, SOURCE_URL, GM_URL
from solar_simulator.experiment import create_experiment, Settings, advance, reset
from solar_simulator.storage import from_document, to_document
from solar_simulator.vector3 import Vector3
from scripts.fetch_ephemerides import parse_result, gm_values


def fixture_snapshot():
    return dict(schema=1,source=SOURCE_URL,gm_source=GM_URL,gm_sha256='a'*64,epoch_jd_tdb=2461321.5,
        frame='Ecliptic J2000',center='Solar System Barycenter',ephemeris='DE441',units='SI',vector_correction='NONE',
        bodies=[dict(id=body_id,name=name,gm_m3_s2=1e10,position=[i*1e10,0,0],velocity=[0,100,0])
                for i,(body_id,name) in enumerate(zip(EXPECTED_IDS,NAMES))])


def test_snapshot_origin_checkpoint_and_reset():
    data=json.dumps(fixture_snapshot()).encode()
    bodies,origin=decode_snapshot(data)
    experiment=create_experiment(bodies,Settings(60,integrator='dop853'),origin=origin)
    result=advance(experiment,2)
    restored=from_document(to_document(result))
    assert restored.origin==origin and restored.time==120
    assert reset(restored).origin==origin
    assert create_experiment(bodies,experiment.settings).origin is None  # Edited initial state loses source claim.
    assert [b.name for b in bodies]==list(NAMES)


@pytest.mark.parametrize('field,value',[('units','KM-S'),('frame','ICRF'),('center','Sun'),
    ('ephemeris','DE440'),('epoch_jd_tdb',True),('gm_sha256','bad'),('vector_correction','LT')])
def test_reject_inconsistent_metadata(field,value):
    doc=fixture_snapshot();doc[field]=value
    with pytest.raises(ValueError):
        decode_snapshot(json.dumps(doc).encode())


@pytest.mark.parametrize('field,value',[('id',399),('id',True),('gm_m3_s2',-1),('position',[0,0]),('velocity',[0,True,0])])
def test_reject_wrong_body_records(field,value):
    doc=fixture_snapshot();doc['bodies'][3][field]=value
    with pytest.raises(ValueError):
        decode_snapshot(json.dumps(doc).encode())


def test_gm_kernel_uses_system_ids_and_si_conversion():
    raw='\n'.join(f'BODY{i}_GM = ( 1.234D+04 )' for i in EXPECTED_IDS).encode()
    values=gm_values(raw)
    assert values[3]==pytest.approx(1.234e13)
    with pytest.raises(ValueError):
        gm_values(b'BODY399_GM = ( 4.0E+05 )')


def test_horizons_parser_rejects_mixed_target_frame_and_epoch():
    text='''Target body name: Earth-Moon Barycenter (3) {source: DE441}
Center body name: Solar System Barycenter (0) {source: DE441}
Output units    : KM-S
Reference frame : Ecliptic of J2000.0
Output type     : GEOMETRIC cartesian states
JDTDB, Calendar Date (TDB), X,Y,Z,VX,VY,VZ
$$SOE
2461321.5, A.D. 2026-Oct-08 00:00:00.0000, 1,2,3,4,5,6,
$$EOE'''
    payload=dict(signature=dict(version='1.3',source='NASA/JPL Horizons API'),result=text)
    state=parse_result(payload,3,[2461321.5])[0]
    assert state['position']==[1000,2000,3000] and state['velocity']==[4000,5000,6000]
    for damaged in (text.replace('DE441','DE440'),text.replace('(3)','(399)'),text.replace('KM-S','AU-D')):
        with pytest.raises(ValueError):
            parse_result(dict(signature=dict(version='1.3',source='NASA/JPL Horizons API'),result=damaged),3,[2461321.5])
    with pytest.raises(ValueError):
        parse_result(payload,3,[2461322.5])


def test_v3_checkpoint_migrates_without_fabricating_origin():
    from solar_simulator.experiment import preset
    doc=to_document(preset('sun-earth'));doc['schema_version']=3;del doc['origin']
    del doc['orientation_work']
    del doc['settings']['physics']
    del doc['settings']['figures']
    restored=from_document(doc)
    assert restored.origin is None and 'origin' not in doc


def test_offline_real_snapshot_and_source_survive_resume(tmp_path):
    from solar_simulator.ephemerides import solar_system
    from solar_simulator.experiment import preset
    from solar_simulator.storage import save,load
    bodies,origin=solar_system()
    assert len(bodies)==9 and origin.epoch_jd_tdb==2461321.5
    assert bodies[0].name=='Sun' and bodies[3].name=='Earth-Moon'
    assert origin.dataset_sha256=='6786b7c481e76383350b5c86517d9a91067f82abd9f66d07a14b262c8c3817cc'
    initial=preset('solar-system')
    assert initial.settings.integrator=='dop853' and initial.origin==origin
    partial=advance(initial,100)
    save(partial,tmp_path/'system.json')
    restored=load(tmp_path/'system.json')
    assert restored.origin==origin
    assert reset(restored).origin==origin
    resumed=advance(restored,100)
    whole=advance(initial,200)
    for a,b in zip(resumed.bodies,whole.bodies):
        assert a.position.distance_to(b.position)<100
        assert a.velocity.distance_to(b.velocity)<.001


def test_mercury_venus_aliases_are_narrowly_accepted():
    header='''Target body name: Mercury Barycenter (199) {source: DE441}
Center body name: Solar System Barycenter (0) {source: DE441}
Output units    : KM-S
Reference frame : Ecliptic of J2000.0
Output type     : GEOMETRIC cartesian states
JDTDB
$$SOE
2461321.5,date,1,2,3,4,5,6,
$$EOE'''
    payload=dict(signature=dict(version='1.3',source='NASA/JPL Horizons API'),result=header)
    assert parse_result(payload,1,[2461321.5])[0]['position']==[1000,2000,3000]
    payload['result']=header.replace('Mercury Barycenter','Venus Barycenter').replace('(199)','(299)')
    assert parse_result(payload,2,[2461321.5])[0]['position']==[1000,2000,3000]
    with pytest.raises(ValueError):
        parse_result(payload,3,[2461321.5])


def test_yearly_numerical_target_against_independent_model():
    import numpy as np
    from solar_simulator.ephemerides import solar_system
    from scripts.assess_solar_system import independent_reference,YEAR
    bodies,origin=solar_system()
    times=np.linspace(0,YEAR,13)
    expected,consistency=independent_reference(bodies,times)
    assert consistency<100
    state=create_experiment(bodies,Settings(YEAR/12,integrator='dop853'),origin=origin)
    for i in range(1,len(times)):
        state=advance(state,1)
        for j,b in enumerate(state.bodies):
            assert b.position.distance_to(Vector3(*expected[i,j,:3]))<100_000
            assert b.velocity.distance_to(Vector3(*expected[i,j,3:]))<.1
