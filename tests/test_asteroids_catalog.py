"""All 343 asteroid masses use the shared immutable supplement contract."""
from dataclasses import replace
from importlib.resources import files
import hashlib,json
import numpy as np
import pytest
from solar_simulator.perturbers import (solar_system_asteroids_full,solar_system_asteroids_catalog,
    ASTEROIDS_CATALOG_SPEC,decode_body_dataset,figure_parent_origin)
from solar_simulator.ephemerides import solar_system
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.experiment import preset,advance,reset
from solar_simulator.storage import save,load,to_document,from_document
from scripts.assess_resolved_moon import states
from scripts.build_asteroid_catalog_dataset import document


def test_runtime_catalogue_preserves_all_original_values_and_source_is_reproducible():
    parent,parent_origin=solar_system_asteroids_full();bodies,origin=solar_system_asteroids_catalog()
    assert len(bodies)==354 and len({b.name for b in bodies})==354
    assert np.array_equal(states(parent),states(bodies[:27]))
    def unchanged(b): return (b.name,b.mass,b.radius,b.spin.x,b.spin.y,b.spin.z)
    assert [unchanged(b) for b in parent]==[unchanged(b) for b in bodies[:27]]
    assert all(b.mass>0 and b.radius==0 and b.spin.magnitude()==0 for b in bodies)
    raw=files('solar_simulator.data').joinpath(ASTEROIDS_CATALOG_SPEC.filename).read_bytes()
    assert len(raw)>100000 and hashlib.sha256(raw).hexdigest()==origin.dataset_sha256
    assert raw==(json.dumps(document(),indent=2,allow_nan=False)+'\n').encode()
    assert json.loads(raw)['base_origin']['dataset_sha256']==parent_origin.dataset_sha256
    assert len(ASTEROIDS_CATALOG_SPEC.identities)==327
    assert [b.name for b in bodies[27:]]==[n for _,n in ASTEROIDS_CATALOG_SPEC.identities]
    _,root=solar_system(resolved_moon=True)
    assert figure_parent_origin(origin)==root
    assert sun_earth_moon_quadrupoles(bodies,origin)==sun_earth_moon_quadrupoles(parent,parent_origin)
    with pytest.raises(ValueError): sun_earth_moon_quadrupoles(bodies,parent_origin)


@pytest.mark.parametrize('change',['parent','mass','duplicate_id','order','missing','future','gm','size'])
def test_catalogue_contract_rejects_incompatible_documents(change):
    data=json.loads(files('solar_simulator.data').joinpath(ASTEROIDS_CATALOG_SPEC.filename).read_bytes())
    if change=='parent': data['base_origin']['dataset_sha256']='0'*64
    if change=='mass': data['bodies'][0]['gm_m3_s2']=float('nan')
    if change=='duplicate_id': data['bodies'][1]['id']=data['bodies'][0]['id']
    if change=='order': data['bodies'].reverse()
    if change=='missing': data['bodies'].pop()
    if change=='future': data['bodies'][0]['states']=[]
    if change=='gm': data['gm_sha256']='0'*64
    raw=json.dumps(data).encode()
    if change=='size': raw+=b' '*(8192+1024*len(ASTEROIDS_CATALOG_SPEC.identities))
    with pytest.raises(ValueError): decode_body_dataset(raw,ASTEROIDS_CATALOG_SPEC)


def test_pinned_asset_corruption_is_rejected_before_any_dynamics(monkeypatch):
    import solar_simulator.perturbers as module
    from types import SimpleNamespace
    raw=files('solar_simulator.data').joinpath(ASTEROIDS_CATALOG_SPEC.filename).read_bytes()
    monkeypatch.setattr(module,'files',lambda _:SimpleNamespace(joinpath=lambda _:SimpleNamespace(read_bytes=lambda:raw+b' ')))
    with pytest.raises(ValueError,match='закрепл'): module._load_supplement(ASTEROIDS_CATALOG_SPEC)


def test_full_catalogue_cli_checkpoint_resumes_and_retains_exact_lineage(tmp_path,capsys):
    pytest.importorskip('solar_native')
    from solar_simulator.cli import main
    file=tmp_path/'all.json'
    assert main(['new','solar-system-asteroids-catalog',str(file),'--backend','rust','--physics','eih-1pn',
        '--figures','sun-earth-moon-q2','--relative-pair','Earth','Moon','--rtol','3e-14',
        '--position-atol','1e-5','--velocity-atol','1e-11'])==0
    assert json.loads(capsys.readouterr().out)['bodies']==354
    initial=load(file)
    whole=advance(initial,4)
    save(advance(initial,2),file);restored=load(file);resumed=advance(restored,2)
    assert len(resumed.bodies)==354 and resumed.origin==initial.origin and resumed.settings==initial.settings
    assert resumed.orientation_work!=0
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(whole.bodies)[:,:3],axis=1))<.02
    assert reset(resumed).origin==initial.origin and reset(resumed).time==0
    bad=to_document(restored);bad['origin']['gm_sha256']='0'*64
    with pytest.raises(ValueError): from_document(bad)


def test_full_catalogue_uses_both_existing_newton_kernels():
    pytest.importorskip('solar_native')
    a=preset('solar-system-asteroids-catalog',backend='rust')
    python=advance(replace(a,settings=replace(a.settings,backend='python')),1)
    rust=advance(a,1)
    assert len(rust.bodies)==354 and rust.origin==a.origin
    assert np.max(np.abs(states(rust.bodies)-states(python.bodies)))<.001


def test_published_annual_report_meets_separate_numerical_checks():
    from pathlib import Path
    from scripts.assess_relative_coordinates import REFERENCE_SHA256
    from scripts.assess_solar_j2 import PLANET_REFERENCE_SHA256
    data=json.loads(Path('docs/asteroids-catalog-validation.json').read_text(encoding='utf-8'))
    bodies,origin=solar_system_asteroids_catalog()
    assert data['checks_passed'] is True and data['dataset_sha256']==origin.dataset_sha256
    assert data['gm_sha256']==origin.gm_sha256 and data['samples']==45 and data['duration_seconds']==31557600
    assert data['reference_sha256']['pair']==REFERENCE_SHA256
    assert data['reference_sha256']['planets']==PLANET_REFERENCE_SHA256
    assert len(data['variants']['all_343']['asteroids'])==343 and len(data['increment_by_original_body'])==27
    for name in ('numerical_agreement','tighter_numerical_agreement','tolerance_sensitivity','independent_reference_convergence'):
        row=data[name]
        assert 0<=row['all_bodies']['maximum_position_metres']<1
        assert 0<=row['moon_relative_to_earth']['maximum_position_metres']<.1
        assert 0<=row['all_bodies']['maximum_velocity_m_per_s']<1e-6
    assert data['variants']['all_343']['maximum_relative_energy_budget_residual']<1e-10
    assert data['options']['backend']=='rust' and data['options']['relative_pair']==['Earth','Moon']
