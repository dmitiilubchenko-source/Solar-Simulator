"""KBO source integrity, no double counting, arbitrary-body kernels and restart."""
from copy import deepcopy
from dataclasses import replace
from importlib.resources import files
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
import pytest
from solar_simulator.perturbers import (solar_system_asteroids_catalog,solar_system_kuiper,
    KUIPER_SPEC,decode_body_dataset,figure_parent_origin)
from solar_simulator.ephemerides import solar_system
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.experiment import preset,advance,reset
from solar_simulator.storage import save,load,to_document,from_document
from solar_simulator.native_forces import prepare
from solar_simulator.relativity import C
from solar_simulator.simulation import G
from scripts.assess_resolved_moon import states
from scripts.fetch_kuiper_data import inputs,year_blocks,decode_year,initial_document,YEAR_MANIFEST_SHA
from scripts.build_kuiper_dataset import document,INITIAL_SHA
from scripts.independent_eih_rust import load_oracle


def source_data():
    rows,manifest,descriptors,constants=inputs()
    blocks=year_blocks(manifest)
    records=decode_year(manifest,blocks,descriptors,{r['id'] for r in rows})
    return rows,manifest,descriptors,constants,blocks,records


def test_all_thirty_initial_states_reproduce_pinned_bytes_in_common_frame():
    rows,manifest,_,constants,_,records=source_data()
    doc=initial_document(rows,manifest,constants,records)
    raw=(json.dumps(doc,indent=2,allow_nan=False)+'\n').encode('utf-8')
    assert hashlib.sha256(raw).hexdigest()==INITIAL_SHA
    assert Path('docs/kuiper-initial.json').read_bytes()==raw
    assert len(rows)==30 and {r['constant'] for r in rows}=={f'MA80{i:02d}' for i in range(1,31)}
    assert not ({r['id'] for r in rows}&{9,999,2134340})
    assert {r['name'] for r in rows}>={'Eris','Haumea','Makemake','Sedna','Quaoar'}
    assert doc['epoch_jd_tdb']==2461321.5 and doc['frame']=='Ecliptic J2000'
    assert doc['center']=='Solar System Barycenter' and doc['vector_correction']=='NONE'


@pytest.mark.parametrize('change',['tail','pointer','grid','nan','missing'])
def test_corrupt_kuiper_type_two_grid_is_rejected(change):
    rows,manifest,descriptors,_,blocks,_=source_data()
    manifest=deepcopy(manifest);blocks=dict(blocks)
    identity=rows[0]['id'];key=f'records-{identity}'
    if change=='tail':
        raw=bytearray(blocks[f'tail-{identity}']);struct.pack_into('<d',raw,8,0.)
        blocks[f'tail-{identity}']=bytes(raw)
    if change=='pointer': next(e for e in manifest['entries'] if e['role']==key)['byte_range'][0]+=8
    if change in ('grid','nan'):
        raw=bytearray(blocks[key]);struct.pack_into('<d',raw,0 if change=='grid' else 16,
            0. if change=='grid' else float('nan'));blocks[key]=bytes(raw)
    if change=='missing': blocks.pop(key)
    with pytest.raises(ValueError): decode_year(manifest,blocks,descriptors,{r['id'] for r in rows})


def test_384_body_template_preserves_every_parent_property_and_figure_lineage():
    parent,parent_origin=solar_system_asteroids_catalog();bodies,origin=solar_system_kuiper()
    assert len(bodies)==384 and len({b.name for b in bodies})==384
    assert np.array_equal(states(parent),states(bodies[:354]))
    def properties(b): return b.name,b.mass,b.radius,b.spin.x,b.spin.y,b.spin.z
    assert [properties(b) for b in parent]==[properties(b) for b in bodies[:354]]
    assert sum(b.name=='Pluto-System' for b in bodies)==1
    assert [b.name for b in bodies[354:]]==[name for _,name in KUIPER_SPEC.identities]
    assert all(b.mass>0 and b.radius==0 and b.spin.magnitude()==0 for b in bodies[354:])
    raw=files('solar_simulator.data').joinpath(KUIPER_SPEC.filename).read_bytes()
    assert raw==(json.dumps(document(),indent=2,allow_nan=False)+'\n').encode('utf-8')
    assert hashlib.sha256(raw).hexdigest()==origin.dataset_sha256
    _,root=solar_system(resolved_moon=True)
    assert figure_parent_origin(origin)==root
    assert sun_earth_moon_quadrupoles(bodies,origin)==sun_earth_moon_quadrupoles(parent,parent_origin)
    with pytest.raises(ValueError): sun_earth_moon_quadrupoles(bodies,parent_origin)


@pytest.mark.parametrize('change',['parent','pluto','duplicate','future','gm','missing'])
def test_runtime_kuiper_contract_rejects_wrong_lineage_and_extra_trajectory(change):
    data=document()
    if change=='parent': data['base_origin']['dataset_sha256']='0'*64
    if change=='pluto': data['bodies'][0]['id']=9
    if change=='duplicate': data['bodies'][1]=data['bodies'][0]
    if change=='future': data['bodies'][0]['states']=[]
    if change=='gm': data['gm_sha256']='0'*64
    if change=='missing': data['bodies'].pop()
    with pytest.raises(ValueError): decode_body_dataset(json.dumps(data).encode(),KUIPER_SPEC)


def test_native_384_body_eih_matches_separate_scalar_oracle_and_newton_reaction():
    pytest.importorskip('solar_native')
    bodies,_=solar_system_kuiper();q=states(bodies)
    masses=np.array([b.mass for b in bodies]);mu=masses*G
    names=[b.name for b in bodies];e,m=names.index('Earth'),names.index('Moon')
    relative=e,m,q[m,:3]-q[e,:3]
    native=prepare(masses)
    actual=native(q[:,:3],q[:,3:],C,relative)
    independent=load_oracle()(q[:,:3],q[:,3:],mu,C,relative)
    assert np.max(np.linalg.norm(actual-independent,axis=1))<3e-16
    newton=native(q[:,:3],q[:,3:],relative_pair=relative)
    momentum=np.sum(masses[:,None]*newton,axis=0)
    scale=np.sum(masses*np.linalg.norm(newton,axis=1))
    assert np.linalg.norm(momentum)/scale<2e-15
    parent_native=prepare(masses[:354])
    delta=newton[:354]-parent_native(q[:354,:3],q[:354,3:],relative_pair=relative)
    assert np.linalg.norm(delta[0])>0 and np.linalg.norm(newton[354:])>0


def test_384_body_cli_native_restart_preserves_provenance_and_error_control(tmp_path,capsys):
    pytest.importorskip('solar_native')
    from solar_simulator.cli import main
    file=tmp_path/'kuiper.json'
    assert main(['new','solar-system-kuiper',str(file),'--backend','rust','--physics','eih-1pn',
        '--figures','sun-earth-moon-q2','--relative-pair','Earth','Moon','--rtol','3e-14',
        '--position-atol','1e-7','--velocity-atol','1e-13'])==0
    assert json.loads(capsys.readouterr().out)['bodies']==384
    initial=load(file);whole=advance(initial,4)
    save(advance(initial,2),file);restored=load(file);resumed=advance(restored,2)
    assert resumed.origin==initial.origin and resumed.settings==initial.settings
    assert resumed.settings.error_control=='per-body' and resumed.orientation_work!=0
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(whole.bodies)[:,:3],axis=1))<.02
    assert reset(resumed).origin==initial.origin and reset(resumed).time==0
    bad=to_document(restored);bad['origin']['gm_sha256']='0'*64
    with pytest.raises(ValueError): from_document(bad)


def test_kuiper_uses_existing_python_and_rust_newton_kernels():
    pytest.importorskip('solar_native')
    a=preset('solar-system-kuiper',backend='rust')
    python=advance(replace(a,settings=replace(a.settings,backend='python')),1)
    rust=advance(a,1)
    assert len(rust.bodies)==384 and rust.origin==a.origin
    assert np.max(np.abs(states(rust.bodies)-states(python.bodies)))<.001


def test_published_cspice_check_covers_every_kbo_and_record_joins():
    report=json.loads(Path('docs/kuiper-source-validation.json').read_text(encoding='utf-8'))
    assert report['checks_passed'] and report['body_count']==30 and report['samples']>=3000
    assert report['manifest_sha256']==YEAR_MANIFEST_SHA and report['record_boundaries_and_neighbours_included']
    assert report['maximum_position_metres']<.01 and report['maximum_velocity_m_per_s']<1e-8
    assert {r['id'] for r in report['bodies'].values()}=={i for i,_ in KUIPER_SPEC.identities}
    for path,checksum in report['code_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==checksum


def test_force_diagnostic_preserves_complete_group_and_separates_tidal_field():
    from scripts.assess_kuiper import force_screen
    from scripts.assess_pluto import reference
    from scripts.assess_relative_coordinates import REFERENCE_SHA256
    from scripts.assess_solar_j2 import PLANET_REFERENCE_SHA256
    rows,_,_,constants,_,records=source_data()
    result=force_screen(rows,records,constants,
        reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256),
        reference('docs/solar-system-moon-reference.json',REFERENCE_SHA256))
    assert result['samples']==13 and result['mass_count']==30
    assert result['gm_m3_s2']==pytest.approx(2315402864753.5605,rel=2e-15)
    values=result['targets']
    assert 0<values['Moon-minus-Earth']['maximum_magnitude_m_per_s2']<1e-17
    assert 0<values['Earth-minus-Sun']['maximum_magnitude_m_per_s2']<values['Earth']['maximum_magnitude_m_per_s2']
    assert values['Neptune']['maximum_magnitude_m_per_s2']>values['Earth']['maximum_magnitude_m_per_s2']


def test_git_filters_preserve_checked_scientific_code_hashes_across_windows_clone():
    paths=('scripts/fetch_kuiper_data.py','scripts/check_kuiper_data.py','scripts/assess_kuiper.py',
        'scripts/independent_anchored_reference.py','scripts/validation/eih_scalar.rs',
        'src/solar_simulator/accuracy.py','rust/solar_core/src/relativity.rs')
    for path in paths:
        original=subprocess.run(['git','hash-object','--no-filters',path],check=True,
            capture_output=True,text=True).stdout.strip()
        filtered=subprocess.run(['git','-c','core.autocrlf=true','hash-object','--path',path,path],check=True,
            capture_output=True,text=True).stdout.strip()
        assert filtered==original,path


def test_initial_absolute_reference_failure_is_preserved_without_changing_threshold():
    report=json.loads(Path('docs/kuiper-absolute-reference-validation.json').read_text(encoding='utf-8'))
    assert report['checks_passed'] is False and report['checks']['energy_budget'] is True
    assert report['checks']['reference_convergence'] is False
    assert report['independent_reference_convergence']['all_bodies']['maximum_position_metres']>.1
    assert report['numerical_agreement']['moon_relative_to_earth']['maximum_position_metres']<.02
    assert hashlib.sha256(Path('scripts/validation/kuiper_absolute_assessment.py').read_bytes()).hexdigest()==report['code_sha256']['scripts/assess_kuiper.py']


def test_published_annual_audit_matches_current_model_sources_and_fixed_criteria():
    report=json.loads(Path('docs/kuiper-validation.json').read_text(encoding='utf-8'))
    _,origin=solar_system_kuiper();parent,parent_origin=solar_system_asteroids_catalog()
    assert report['body_count']==384 and report['added_kuiper_bodies']==30
    assert report['dataset_sha256']==origin.dataset_sha256 and report['gm_sha256']==origin.gm_sha256
    assert report['base_dataset_sha256']==parent_origin.dataset_sha256
    assert report['epoch_jd_tdb']==origin.epoch_jd_tdb
    assert report['samples']==45 and report['duration_seconds']==31557600
    assert report['checks_passed'] and all(report['checks'].values())
    assert 'constant position origins' in report['reference_coordinates']
    for field in ('numerical_agreement','tighter_numerical_agreement',
                  'tolerance_sensitivity','independent_reference_convergence'):
        assert 0<report[field]['all_bodies']['maximum_position_metres']<.1
        assert 0<report[field]['moon_relative_to_earth']['maximum_position_metres']<.02
    assert set(report['increment_by_parent_body'])=={b.name for b in parent}
    for name,variant in report['variants'].items():
        assert variant['maximum_relative_energy_budget_residual']<1e-10
        assert variant['options']['relative_pair']==['Earth','Moon']
        assert variant['options']['error_control']=='per-body'
        if name=='kuiper_384':
            assert set(variant['kuiper_bodies'])=={name for _,name in KUIPER_SPEC.identities}
    for path,checksum in report['code_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==checksum
    previous=Path('docs/kuiper-absolute-reference-validation.json').read_bytes()
    assert hashlib.sha256(previous).hexdigest()==report['cache_provenance']['previous_absolute_report_sha256']


@pytest.mark.parametrize('field,value',[('dataset_sha256','0'*64),('gm_sha256','0'*64),
    ('base_dataset_sha256','0'*64),('samples',44),('duration_seconds',86400)])
def test_reuse_rejects_incompatible_production_before_reading_private_arrays(monkeypatch,field,value):
    from scripts import assess_kuiper as module
    initial,origin=solar_system_kuiper();base,parent=solar_system_asteroids_catalog()
    metadata=json.loads(Path('docs/kuiper-absolute-reference-validation.json').read_text(encoding='utf-8'))
    metadata[field]=value
    monkeypatch.setattr(module,'checked_document',lambda *args:metadata)
    with pytest.raises(ValueError,match='lineage/grid'):
        module.cached_production(initial,origin,base,parent,np.array([0.,31557600.]))


@pytest.mark.parametrize('field',['dataset_sha256','production_archive_sha256'])
def test_reuse_rejects_an_oracle_from_another_model_without_accessing_arrays(monkeypatch,field):
    from scripts import assess_kuiper as module
    initial,origin=solar_system_kuiper()
    metadata=dict(dataset_sha256=origin.dataset_sha256,production_archive_sha256=module.PRODUCTION_SHA)
    metadata[field]='0'*64
    monkeypatch.setattr(module,'checked_document',lambda *args:metadata)
    with pytest.raises(ValueError,match='lineage'):
        module.cached_reference(initial,origin,np.array([0.,31557600.]),{})
