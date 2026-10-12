"""Solar constants, independent potential/apsidal advance, and mixed checkpoints."""
from dataclasses import replace
import hashlib
from importlib.resources import files
import json
from math import cos,radians,sin

import numpy as np
import pytest
from solar_simulator.ephemerides import solar_system
from solar_simulator.experiment import preset,create_experiment,advance,reset
from solar_simulator.oblateness import (SOLAR_PROFILE_SHA256,solar_j2,sun_earth_moon_quadrupoles,
    prepare,acceleration,FixedJ2,PrescribedQuadrupole)
from solar_simulator.simulation import AU,G
from solar_simulator.storage import save,load,to_document
from solar_simulator.vector3 import Vector3
from scripts.fetch_solar_profile import solar_pole


def test_offline_solar_profile_uses_de441_radius_and_unnormalized_j2():
    raw=files('solar_simulator.data').joinpath('solar-j2-20261008.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==SOLAR_PROFILE_SHA256
    data=json.loads(raw)
    assert data['coefficient']==2.1961391516529825e-7
    assert data['reference_radius_metres']==696000000
    assert data['pole_ra_degrees']==286.13 and data['pole_dec_degrees']==63.87
    for resolved in (False,True):
        bodies,origin=solar_system(resolved_moon=resolved)
        figure=solar_j2(bodies,origin)[0]
        assert isinstance(figure,FixedJ2) and figure.body=='Sun'
        assert figure.coefficient==data['coefficient'] and np.linalg.norm(figure.axis)==pytest.approx(1)


def test_solar_pole_parser_uses_data_blocks_and_correct_rotation():
    source=b'BODY10_POLE_RA = (0 0 0)\n\\begindata\nBODY10_POLE_RA = (90 0 0)\nBODY10_POLE_DEC = (0 0 0)\n\\begintext'
    axis,ra,dec=solar_pole(source)
    epsilon=radians(84381.448/3600)
    assert np.allclose(axis,[0,cos(epsilon),-sin(epsilon)],rtol=0,atol=1e-16)
    assert ra==90 and dec==0
    with pytest.raises(ValueError,match='constant'):
        solar_pole(source.replace(b'(90 0 0)',b'(90 .01 0)'))
    with pytest.raises(ValueError,match='one'):
        solar_pole(source.replace(b'BODY10_POLE_DEC',b'BODY11_POLE_DEC'))


def test_solar_profile_tampering_is_rejected(monkeypatch):
    import importlib.resources
    raw=files('solar_simulator.data').joinpath('solar-j2-20261008.json').read_bytes()+b' '
    class Resource:
        def joinpath(self,name):
            return self
        def read_bytes(self):
            return raw
    bodies,origin=solar_system()
    monkeypatch.setattr(importlib.resources,'files',lambda name:Resource())
    with pytest.raises(ValueError,match='профиль'):
        solar_j2(bodies,origin)


@pytest.mark.parametrize('changed',['epoch','dataset','gm','names','origin'])
def test_solar_factory_rejects_incompatible_origin(changed):
    bodies,origin=solar_system(resolved_moon=True)
    if changed=='epoch':
        origin=replace(origin,epoch_jd_tdb=origin.epoch_jd_tdb+1)
    if changed=='dataset':
        origin=replace(origin,dataset_sha256='0'*64)
    if changed=='gm':
        origin=replace(origin,gm_sha256='0'*64)
    if changed=='names':
        bodies=bodies[:-1]
    if changed=='origin':
        origin=None
    with pytest.raises(ValueError,match='solar-j2'):
        solar_j2(bodies,origin)


def test_solar_field_matches_independent_complex_potential_gradient_and_reaction():
    bodies,origin=solar_system()
    figure=solar_j2(bodies,origin)[0]
    axis=np.array(figure.axis)
    r=.4*AU*np.array([.3,-.8,.6])
    pair=[replace(bodies[0],position=Vector3(0,0,0)),replace(bodies[1],position=Vector3(*r))]
    masses=np.array([b.mass for b in pair])
    actual=acceleration(np.array([[0.,0.,0.],r]),masses,prepare(pair,(figure,)))
    def potential(value):
        radius2=value@value
        return G*masses[0]*masses[1]*figure.coefficient*figure.reference_radius**2*(
            3*(value@axis)**2-radius2)/(2*radius2**2.5)
    gradient=[]
    for component in range(3):
        value=r.astype(complex); value[component]+=1e-4j
        gradient.append(potential(value).imag/1e-4)
    expected=-np.array(gradient)/masses[1]
    assert np.allclose(actual[1],expected,rtol=2e-14,atol=1e-28)
    assert np.linalg.norm(actual[0]*masses[0]+actual[1]*masses[1])<np.linalg.norm(actual[1]*masses[1])*3e-16


def test_solar_j2_equatorial_precession_against_analytic_solution():
    from scripts.assess_solar_j2 import equatorial_precession
    bodies,origin=solar_system()
    result=equatorial_precession(solar_j2(bodies,origin)[0],orbits=3)
    assert result['relative_error']<.01
    assert abs(result['newtonian_spurious_radians_per_orbit'])<result['expected_radians_per_orbit']*.01


def test_fixed_and_prescribed_figures_share_v8_checkpoint_and_resume(tmp_path):
    initial=preset('solar-system-moon')
    figures=sun_earth_moon_quadrupoles(initial.bodies,initial.origin)
    assert isinstance(figures[0],FixedJ2) and all(isinstance(f,PrescribedQuadrupole) for f in figures[1:])
    settings=replace(initial.settings,physics='eih-1pn',figures=figures,relative_pair=('Earth','Moon'),
                     position_atol=1e-5,velocity_atol=1e-11)
    initial=create_experiment(initial.bodies,settings,origin=initial.origin)
    partial=advance(initial,24)
    save(partial,tmp_path/'solar.json')
    restored=load(tmp_path/'solar.json')
    assert restored.settings.figures==figures and restored.orientation_work==partial.orientation_work
    doc=to_document(restored)
    from solar_simulator.storage import SCHEMA_VERSION
    assert doc['schema_version']==SCHEMA_VERSION and 'kind' not in doc['settings']['figures'][0]
    resumed=advance(restored,24)
    whole=advance(initial,48)
    assert max(a.position.distance_to(b.position) for a,b in zip(whole.bodies,resumed.bodies))<.01
    assert reset(resumed).orientation_work==0 and reset(resumed).settings.figures==figures


@pytest.mark.parametrize('name,profile,count',[('solar-system','solar-j2',1),('solar-system-moon','sun-earth-moon-q2',3)])
def test_cli_creates_solar_profiles(tmp_path,capsys,name,profile,count):
    from solar_simulator.cli import main
    path=tmp_path/'solar.json'
    assert main(['new',name,str(path),'--physics','eih-1pn','--figures',profile])==0
    state=load(path)
    assert len(state.settings.figures)==count and state.settings.figures[0].body=='Sun'
    assert json.loads(capsys.readouterr().out)['orbital_angular_momentum_conserved'] is False


def test_cli_rejects_solar_profile_for_unpinned_teaching_scenario(tmp_path):
    from solar_simulator.cli import main
    path=tmp_path/'invalid.json'
    with pytest.raises(SystemExit) as error:
        main(['new','sun-earth',str(path),'--figures','solar-j2'])
    assert error.value.code==2 and not path.exists()
