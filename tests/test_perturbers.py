"""Additional-body lineage, offline data and complete resumable experiments."""
from dataclasses import replace
from importlib.resources import files
import json

import numpy as np
import pytest
from solar_simulator.ephemerides import solar_system
from solar_simulator.perturbers import (solar_system_pluto,decode_supplement,figure_parent_origin,
    PLUTO_DATASET_SHA256,PLUTO_GM_SHA256,BASE_DATASET_SHA256)
from solar_simulator.oblateness import earth_j2,sun_earth_moon_quadrupoles
from solar_simulator.experiment import preset,create_experiment,advance,reset
from solar_simulator.storage import save,load,to_document,from_document
from solar_simulator.simulation import G
from scripts.assess_resolved_moon import states
from scripts.fetch_pluto_data import state,segment


def supplement():
    return json.loads(files('solar_simulator.data').joinpath('pluto-system-20261008.json').read_bytes())


def test_extension_preserves_every_base_value_and_adds_system_mass():
    base,parent=solar_system(resolved_moon=True)
    extended,origin=solar_system_pluto()
    assert np.array_equal(states(base),states(extended[:-1]))
    assert [(b.name,b.mass,b.radius) for b in base]==[(b.name,b.mass,b.radius) for b in extended[:-1]]
    assert len(extended)==11 and extended[-1].name=='Pluto-System'
    assert G*extended[-1].mass==pytest.approx(975500000000.,rel=2e-15)
    assert origin.dataset_sha256==PLUTO_DATASET_SHA256 and origin.gm_sha256==PLUTO_GM_SHA256
    assert figure_parent_origin(origin)==parent
    assert parent.dataset_sha256==BASE_DATASET_SHA256
    assert origin!=parent and not any('states' in b for b in supplement()['bodies'])


@pytest.mark.parametrize('changed',['schema','units','epoch','parent','gm_digest','source','id','count','mass','vector','boolean'])
def test_malformed_supplement_is_rejected(changed):
    doc=supplement()
    if changed=='schema': doc['schema']=True
    if changed=='units': doc['units']='KM-S'
    if changed=='epoch': doc['base_origin']['epoch_jd_tdb']+=1
    if changed=='parent': doc['base_origin']['dataset_sha256']='a'*64
    if changed=='gm_digest': doc['gm_sha256']='a'*64
    if changed=='source': doc['sources'][1]['byte_range'][0]+=1
    if changed=='id': doc['bodies'][0]['id']=999
    if changed=='count': doc['bodies']*=2
    if changed=='mass': doc['bodies'][0]['gm_m3_s2']=-1
    if changed=='vector': doc['bodies'][0]['velocity']=[0,0]
    if changed=='boolean': doc['bodies'][0]['position'][1]=True
    with pytest.raises(ValueError):
        decode_supplement(json.dumps(doc).encode())


def test_duplicate_nonfinite_and_altered_pinned_asset_rejected(monkeypatch):
    import solar_simulator.perturbers as module
    for raw in (b'{"schema":1,"schema":1}',b'{"schema":NaN}'):
        with pytest.raises(ValueError): decode_supplement(raw)
    raw=json.dumps(supplement()).encode()+b' '
    class Resource:
        def joinpath(self,name): return self
        def read_bytes(self): return raw
    monkeypatch.setattr(module,'files',lambda name:Resource())
    with pytest.raises(ValueError,match='закреплённое'):
        solar_system_pluto()


@pytest.mark.parametrize('field,value',[('gm_sha256','a'*64),('epoch_jd_tdb',2461322.5)])
def test_registered_extension_cannot_forge_figure_compatibility(field,value):
    bodies,origin=solar_system_pluto()
    with pytest.raises(ValueError,match='происхождение'):
        sun_earth_moon_quadrupoles(bodies,replace(origin,**{field:value}))
    unknown=replace(origin,dataset_sha256='a'*64)
    assert figure_parent_origin(unknown)==unknown
    with pytest.raises(ValueError):
        sun_earth_moon_quadrupoles(bodies,unknown)


def test_parent_figures_are_unchanged_and_base_origin_cannot_claim_extra_body():
    base,parent=solar_system(resolved_moon=True)
    bodies,origin=solar_system_pluto()
    assert sun_earth_moon_quadrupoles(base,parent)==sun_earth_moon_quadrupoles(bodies,origin)
    assert earth_j2(base,parent)==earth_j2(bodies,origin)
    with pytest.raises(ValueError,match='solar-j2'):
        sun_earth_moon_quadrupoles(bodies,parent)


def test_chebyshev_value_derivative_scale_endpoints_and_next_record():
    table=np.zeros((3,15),dtype=int);table[:,8]=[423,6,1]
    first=np.zeros(1018);first[:2]=[1000.,1032.];first[422:425]=[1.,2.,3.]
    second=first.copy();second[:2]=[1032.,1064.];second[422]=10.
    for x in (-1.,-.25,0.,.5):
        actual=state([first,second],table,9,1016+16*x)
        assert actual[0]==pytest.approx(1000*(1+2*x+3*(2*x*x-1)))
        assert actual[3]==pytest.approx(1000*(2+12*x)/(16*86400))
        assert np.array_equal(actual[[1,2,4,5]],np.zeros(4))
    assert segment([first,second],table,9,1032)[1]==1048
    assert state([first,second],table,9,1064)[0]==pytest.approx(15000.)
    for jd in (999.,1065.,float('nan')):
        with pytest.raises(ValueError): state([first,second],table,9,jd)


def test_cli_mixed_figures_v8_resume_reset_and_origin(tmp_path,capsys):
    from solar_simulator.cli import main
    file=tmp_path/'pluto.json'
    assert main(['new','solar-system-pluto',str(file),'--physics','eih-1pn','--figures','sun-earth-moon-q2',
        '--relative-pair','Earth','Moon','--position-atol','1e-5','--velocity-atol','1e-11'])==0
    report=json.loads(capsys.readouterr().out)
    assert report['bodies']==11 and report['origin']['dataset_sha256']==PLUTO_DATASET_SHA256
    original=load(file)
    partial=advance(original,24);save(partial,file)
    restored=load(file)
    assert restored.origin==original.origin and restored.orientation_work==partial.orientation_work
    assert restored.settings.figures==original.settings.figures and restored.settings.relative_pair==('Earth','Moon')
    from solar_simulator.storage import SCHEMA_VERSION
    assert to_document(restored)['schema_version']==SCHEMA_VERSION
    resumed=advance(restored,24);whole=advance(original,48)
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(whole.bodies)[:,:3],axis=1))<.02
    assert reset(resumed).origin==original.origin and reset(resumed).orientation_work==0
    doc=to_document(restored);doc['origin']['gm_sha256']='a'*64
    with pytest.raises(ValueError): from_document(doc)


def test_extended_newton_rust_backend_remains_available():
    pytest.importorskip('solar_native')
    initial=preset('solar-system-pluto',backend='rust')
    assert initial.settings.integrator=='verlet'
    result=advance(initial,1)
    assert len(result.bodies)==11 and result.origin==initial.origin and result.time==3600
