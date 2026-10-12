"""Receipt file/semantic/source guards, distinct from saved orbit state."""
from copy import deepcopy
import json

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

import scripts.lunar_initial_receipt as receipt
from scripts.lunar_initial_boundary import PURPOSE
from scripts.canonical_checkpoint import from_document as cartesian_document
from scripts.relative_canonical_checkpoint import from_document as relative_document
from scripts.pinned_lunar_initial import source_inputs,from_pinned_dataset
from scripts.independent_rigid_pn import gradients
from solar_simulator.spin_initial import lunar_solid_equivalent_initial


@pytest.fixture(scope='module')
def valid():return receipt.make_receipt(purpose=PURPOSE)


def resign(document):
    document['payload_sha256'] = receipt.payload_checksum({k:v for k,v in document.items() if k!='payload_sha256'})
    return document


def test_actual_json_file_roundtrip_regenerates_exact_source_contract(tmp_path,valid):
    path = tmp_path/'initial receipt.json';receipt.save_receipt(path,valid)
    loaded = receipt.load_receipt(path)
    assert receipt.canonical_text(loaded)==receipt.canonical_text(valid)
    units = valid['metadata']['orbital_input']['units_SI_similarity']
    for key,value in units.items():assert float(loaded['metadata']['orbital_input']['units_SI_similarity'][key]).hex()==float(value).hex()
    assert loaded['metadata']['boundary_contract']['physical_mapping_certified'] is False
    assert 'state' not in loaded and 'elapsed_model_time' not in loaded
    assert receipt.make_receipt(purpose=PURPOSE)['state_sha256']==loaded['state_sha256']
    for parser in [cartesian_document,relative_document]:
        with pytest.raises(ValueError):parser(loaded)


def test_regenerated_dataset_state_against_independent_full_H_derivatives():
    args = source_inputs();state,_ = from_pinned_dataset(purpose=PURPOSE);p = args['parameters']
    rotation = Rotation.from_quat(np.roll(state[-4:],-1)).as_matrix()
    g,_ = gradients(state[:-4],rotation,p.orbital.masses,p.orbital.c,p.figure.moments,p.index)
    g = g.reshape(3,10,3)
    assert np.max(np.linalg.norm(g[1]-args['velocities'],axis=1)/args['velocity_scales'])<1e-13
    _,_,_,profile = lunar_solid_equivalent_initial()
    h = np.array(profile['rotation_derivative_per_second'])@np.array(profile['rotation']).T
    w = np.array([h[2,1]-h[1,2],h[0,2]-h[2,0],h[1,0]-h[0,1]])/2*args['units'].time_s
    assert np.linalg.norm(g[2,4]-w)/args['rate_scale']<1e-13


@pytest.mark.parametrize('key',['physical','physical-type','units','order','positions','velocities','state','code','environment','extra'])
def test_recomputed_checksum_cannot_certify_changed_source_or_semantics(valid,key):
    bad = deepcopy(valid)
    if key=='physical':bad['metadata']['boundary_contract']['physical_mapping_certified']=True
    elif key=='physical-type':bad['metadata']['boundary_contract']['physical_mapping_certified']=0
    elif key=='units':bad['metadata']['orbital_input']['units_SI_similarity']['length_m']*=2
    elif key=='order':bad['metadata']['orbital_input']['body_names'].reverse()
    elif key in ['positions','velocities']:bad['metadata']['orbital_input'][key+'_model_sha256']='0'*64
    elif key=='state':bad['state_sha256']='0'*64
    elif key=='code':bad['environment']['code_sha256']['scripts/lunar_initial_receipt.py']='0'*64
    elif key=='environment':bad['environment']['numpy']='different'
    else:bad['metadata']['extra']='ignored?'
    with pytest.raises(ValueError,match='source/state/contract'):receipt.verify_receipt(resign(bad))


@pytest.mark.parametrize('mutation',['kind','schema','bool-schema','purpose','representation','unknown','checksum'])
def test_reject_unsupported_schema_and_structural_changes(valid,mutation):
    bad = deepcopy(valid)
    if mutation=='bool-schema':bad['schema']=True
    elif mutation=='schema':bad['schema']=2
    elif mutation=='unknown':bad['unknown']=1
    elif mutation=='checksum':bad['payload_sha256']='0'*64
    elif mutation=='purpose':bad['purpose']='physical'
    else:bad[mutation]='unsupported'
    with pytest.raises(ValueError):receipt.verify_receipt(bad)


def test_reject_duplicate_nonfinite_and_malformed_file_json(tmp_path):
    path = tmp_path/'bad.json'
    for raw in ['{"schema":1,"schema":1}','{"schema":NaN}','{"schema":Infinity}','{']:
        path.write_text(raw,encoding='utf-8')
        with pytest.raises(ValueError):receipt.load_receipt(path)


def test_reject_changed_loaded_source_before_rebuilding(valid,monkeypatch):
    changed = dict(receipt.LOADED_CODE_SHA);changed['scripts/lunar_initial_receipt.py']='0'*64
    monkeypatch.setattr(receipt,'LOADED_CODE_SHA',changed)
    def forbidden(*args,**kwargs):pytest.fail('Changed source reached initialization')
    monkeypatch.setattr(receipt,'from_pinned_dataset',forbidden)
    with pytest.raises(ValueError,match='source code'):receipt.verify_receipt(valid)


def test_existing_receipt_and_invalid_output_are_preserved(tmp_path,valid):
    path = tmp_path/'existing.json';path.write_bytes(b'existing')
    with pytest.raises(FileExistsError):receipt.save_receipt(path,valid)
    assert path.read_bytes()==b'existing'
    invalid = deepcopy(valid);invalid['metadata']['boundary_contract']['physical_mapping_certified']=True
    target = tmp_path/'invalid.json'
    with pytest.raises(ValueError):receipt.save_receipt(target,resign(invalid))
    assert not target.exists()
    with pytest.raises(ValueError,match='not certified'):receipt.make_receipt(purpose='physical')
