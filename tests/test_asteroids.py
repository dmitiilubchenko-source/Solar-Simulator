"""Generic additions, SB441 units/boundaries, lineage and resumed 14-body physics."""
from dataclasses import replace
from importlib.resources import files
import json
import struct
import numpy as np
import pytest
from solar_simulator.perturbers import (solar_system_pluto,solar_system_asteroids,decode_body_dataset,
    ASTEROIDS_SPEC,figure_parent_origin,additional_names)
from solar_simulator.ephemerides import solar_system
from solar_simulator.oblateness import earth_j2,sun_earth_moon_quadrupoles
from solar_simulator.experiment import preset,advance,reset
from solar_simulator.storage import save,load,to_document,from_document
from solar_simulator.simulation import G
from scripts.assess_resolved_moon import states
from scripts.fetch_asteroid_data import heliocentric_state,decode_segments


def document():
    return json.loads(files('solar_simulator.data').joinpath(ASTEROIDS_SPEC.filename).read_bytes())


def test_shared_template_preserves_parent_and_adds_only_three_initial_states():
    base,parent=solar_system_pluto();bodies,origin=solar_system_asteroids()
    assert len(bodies)==14 and np.array_equal(states(base),states(bodies[:11]))
    assert [(b.name,b.mass,b.radius) for b in bodies[:11]]==[(b.name,b.mass,b.radius) for b in base]
    assert [b.name for b in bodies[11:]]==['Ceres','Pallas','Vesta']
    assert all(b.mass>0 and b.radius==0 and b.spin.magnitude()==0 for b in bodies[11:])
    # DE441 MA coefficients, AU/day -> SI; not the separate Dawn-fit masses.
    scale=(149597870700.)**3/86400**2
    assert [G*b.mass for b in bodies[11:]]==pytest.approx(np.array([1.396451812308107e-13,3.04711463300432e-14,3.8548000225257904e-14])*scale,rel=2e-15)
    assert document()['base_origin']['dataset_sha256']==parent.dataset_sha256
    assert all(set(b)=={'id','name','gm_m3_s2','position','velocity'} for b in document()['bodies'])
    original,original_origin=solar_system(resolved_moon=True)
    assert figure_parent_origin(origin)==original_origin
    assert additional_names(origin)=={'Pluto-System','Ceres','Pallas','Vesta'}
    assert sun_earth_moon_quadrupoles(bodies,origin)==sun_earth_moon_quadrupoles(original,original_origin)
    assert earth_j2(bodies,origin)==earth_j2(original,original_origin)
    with pytest.raises(ValueError): sun_earth_moon_quadrupoles(bodies,parent)


@pytest.mark.parametrize('field',['parent','gm','source','duplicate','id','order','future_states','boolean_mass','nan_vector','missing_velocity'])
def test_generic_contract_rejects_mismatched_asteroid_data(field):
    data=document()
    if field=='parent': data['base_origin']['dataset_sha256']='0'*64
    if field=='gm': data['gm_sha256']='0'*64
    if field=='source': data['sources'][-1]['byte_range'][0]+=1
    if field=='duplicate': data['bodies'][1]=data['bodies'][0]
    if field=='id': data['bodies'][0]['id']=True
    if field=='order': data['bodies'].reverse()
    if field=='future_states': data['bodies'][0]['states']=[]
    if field=='boolean_mass': data['bodies'][0]['gm_m3_s2']=True
    if field=='nan_vector': data['bodies'][0]['position'][0]=float('nan')
    if field=='missing_velocity': del data['bodies'][0]['velocity']
    with pytest.raises(ValueError): decode_body_dataset(json.dumps(data).encode(),ASTEROIDS_SPEC)


def test_asteroid_origin_cannot_forge_parent_figure_compatibility():
    bodies,origin=solar_system_asteroids()
    for forged in (replace(origin,gm_sha256='0'*64),replace(origin,epoch_jd_tdb=origin.epoch_jd_tdb+1)):
        with pytest.raises(ValueError): sun_earth_moon_quadrupoles(bodies,forged)
    with pytest.raises(ValueError): replace(origin,frame='J2000')
    unknown=replace(origin,dataset_sha256='0'*64)
    assert figure_parent_origin(unknown)==unknown
    with pytest.raises(ValueError): sun_earth_moon_quadrupoles(bodies,unknown)


def test_type2_analytic_derivative_seconds_units_right_boundary_and_no_extrapolation():
    records=np.zeros((2,26));records[:,0]=[10.,30.];records[:,1]=10.
    records[0,2:5]=[3.,2.,5.];records[1,2]=100.
    def value(et): return heliocentric_state(records,2451545+et/86400)
    # T0=1,T1=x,T2=2*x*x-1. At x=0: p=-2 km, dp/dt=.2 km/s.
    # JD binary rounding is ~20 microseconds here, included in this tolerance.
    assert value(10.)[:3]==pytest.approx([-2000.,0.,0.],abs=.01)
    assert value(10.)[3:]==pytest.approx([200.,0.,0.],abs=.01)
    assert value(0.)[0]==pytest.approx(6000.,abs=.01)
    # Use an exactly representable JD boundary, to test right-hand selection.
    exact=np.zeros((2,26));exact[:,0]=[43200.,129600.];exact[:,1]=43200.
    exact[0,2]=1.;exact[1,2]=2.
    assert heliocentric_state(exact,2451546)[0]==2000.
    assert heliocentric_state(exact,2451547)[0]==2000.
    for jd in (2451544.,2451548.,float('nan')):
        with pytest.raises(ValueError): heliocentric_state(exact,jd)


def daf_fixture():
    header=bytearray(1024);header[:8]=b'DAF/SPK ';struct.pack_into('<2i',header,8,2,6)
    struct.pack_into('<i',header,76,3);header[88:96]=b'LTL-IEEE'
    summary=bytearray(1024);struct.pack_into('<3d',summary,0,0.,0.,3.)
    blocks={'header':bytes(header)};entries=[]
    interval=2764800.;init=-interval*10
    low=10;high=int((31557600-init)//interval)
    for j,identity in enumerate((2000001,2000002,2000004)):
        a=100+1400000*j;z=a+26*50000+3
        struct.pack_into('<2d6i',summary,24+j*40,init,init+50000*interval,identity,10,1,2,a,z)
        blocks[f'tail-{identity}']=struct.pack('<4d',init,interval,26.,50000.)
        entries.append(dict(role=f'tail-{identity}',byte_range=[(z-4)*8,z*8-1]))
        records=np.zeros((high-low+1,26));records[:,0]=init+(np.arange(low,high+1)+.5)*interval;records[:,1]=interval/2
        blocks[f'records-{identity}']=records.astype('<f8').tobytes()
        entries.append(dict(role=f'records-{identity}',byte_range=[(a-1+low*26)*8,(a-1+(high+1)*26)*8-1]))
    blocks['summary-3']=bytes(summary)
    return dict(epoch_jd_tdb=2451545.,duration_seconds=31557600,entries=entries),blocks


def test_daf_source_addresses_centres_and_type2_intervals():
    manifest,blocks=daf_fixture()
    assert set(decode_segments(manifest,blocks))=={2000001,2000002,2000004}
    for changed in ('frame','center','cycle','tail_pointer','interval'):
        manifest,blocks=daf_fixture()
        summary=bytearray(blocks['summary-3'])
        if changed=='frame': struct.pack_into('<i',summary,48,17)
        if changed=='center': struct.pack_into('<i',summary,44,0)
        if changed=='cycle': struct.pack_into('<d',summary,0,3.)
        blocks['summary-3']=bytes(summary)
        if changed=='tail_pointer': manifest['entries'][0]['byte_range'][0]+=8
        if changed=='interval': blocks['tail-2000001']=struct.pack('<4d',0.,1.,26.,50000.)
        with pytest.raises(ValueError): decode_segments(manifest,blocks)


def test_cli_checkpoint_and_resumed_fourteen_body_physics(tmp_path,capsys):
    from solar_simulator.cli import main
    file=tmp_path/'asteroids.json'
    assert main(['new','solar-system-asteroids',str(file),'--physics','eih-1pn','--figures','sun-earth-moon-q2',
        '--relative-pair','Earth','Moon','--rtol','3e-14','--position-atol','1e-5','--velocity-atol','1e-11'])==0
    assert json.loads(capsys.readouterr().out)['bodies']==14
    initial=load(file);half=advance(initial,24);save(half,file);restored=load(file)
    assert restored.origin==initial.origin and restored.settings.figures==initial.settings.figures
    from solar_simulator.storage import SCHEMA_VERSION
    assert restored.orientation_work==half.orientation_work and to_document(restored)['schema_version']==SCHEMA_VERSION
    resumed=advance(restored,24);whole=advance(initial,48)
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(whole.bodies)[:,:3],axis=1))<.02
    assert reset(resumed).origin==initial.origin and reset(resumed).time==0
    malformed=to_document(restored);malformed['origin']['gm_sha256']='0'*64
    with pytest.raises(ValueError): from_document(malformed)


def test_shared_rust_newton_kernel_handles_fourteen_bodies():
    pytest.importorskip('solar_native')
    initial=preset('solar-system-asteroids',backend='rust')
    result=advance(initial,1)
    assert len(result.bodies)==14 and result.time==3600 and result.origin==initial.origin
