from copy import deepcopy
from dataclasses import replace
import hashlib
import subprocess
import sys

import numpy as np
import pytest

from scripts import lunar_research as research
from scripts.canonical_checkpoint import canonical_text,from_document as cartesian_document
from scripts.pinned_lunar_initial import from_pinned_dataset,source_inputs
from scripts.relative_canonical import from_cartesian
from scripts.relative_canonical_checkpoint import from_document as relative_document
from scripts.run_lunar_research import main


@pytest.fixture
def experiment():
    return research.create(purpose='conditional-research')


def resign(document):
    payload = {k:v for k,v in document.items() if k!='payload_sha256'}
    document['payload_sha256'] = hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest()
    return document


def test_actual_source_to_relative_checkpoint_bitwise_roundtrip(experiment,tmp_path):
    state, info = from_pinned_dataset(purpose='conditional-research'); cp = experiment.checkpoint
    expected = from_cartesian(state,cp.pair)
    assert np.array_equal(np.array(cp.initial).view(np.uint64),expected.view(np.uint64))
    assert np.array_equal(expected[60:].view(np.uint64),state[60:].view(np.uint64))
    assert cp.metadata['provenance']['physical_mapping_certified'] is False
    assert experiment.receipt['metadata']==info
    research.save(tmp_path/'lunar input.json',experiment); restored = research.load(tmp_path/'lunar input.json')
    assert restored==experiment
    for loader in [cartesian_document,relative_document]:
        with pytest.raises(ValueError): loader(research.to_document(experiment))


@pytest.mark.parametrize('mutation',['initial','mass','inertia','pair','names','frame','units','claim','source','receipt'])
def test_recomputed_checksums_cannot_change_initial_contract(experiment,mutation):
    document = research.to_document(experiment); cp = document['checkpoint']
    if mutation=='initial':
        cp['initial']['coordinate_slots'][0][0] += 1e-5
        cp['state']['coordinate_slots'][0][0] += 1e-5
    elif mutation=='mass': cp['parameters']['masses'][0] *= 1.0001
    elif mutation=='inertia': cp['parameters']['figure']['moments'][0] *= 1.0001
    elif mutation=='pair': cp['representation']['pair_indices'] = [0,4]
    elif mutation=='names': cp['body_names'][0] = 'replacement Sun'
    elif mutation=='frame': cp['metadata']['frame']['name'] = 'different axes'
    elif mutation=='units': cp['metadata']['units']['length_m'] *= 2
    elif mutation=='claim': cp['metadata']['provenance']['physical_mapping_certified'] = 0
    elif mutation=='source': cp['metadata']['provenance']['sources'].pop()
    else:
        document['initial_receipt']['metadata']['boundary_contract']['physical_mapping_certified'] = True
        resign(document['initial_receipt'])
    resign(cp)
    with pytest.raises(ValueError): research.from_document(resign(document))


@pytest.mark.parametrize('mutation',['schema','kind','unknown','checksum','negative-atol','wrong-method'])
def test_structure_and_unsupported_controls(experiment,mutation):
    d = research.to_document(experiment)
    if mutation=='schema': d['schema'] = True
    elif mutation=='kind': d['kind'] = 'legacy'
    elif mutation=='unknown': d['history'] = []
    elif mutation=='checksum':
        d['payload_sha256'] = '0'*64
        with pytest.raises(ValueError): research.from_document(d)
        return
    elif mutation=='negative-atol': d['checkpoint']['metadata']['integration']['atol'][0] = -1
    else: d['checkpoint']['metadata']['integration']['method'] = 'RK45'
    resign(d['checkpoint'])
    with pytest.raises(ValueError): research.from_document(resign(d))


def test_source_guard_runs_before_integrator(experiment,monkeypatch):
    monkeypatch.setattr(research,'source_hashes',lambda:{})
    def forbidden(*args,**kwargs): raise AssertionError('integrator must not run')
    monkeypatch.setattr(research.relative,'evolve',forbidden)
    with pytest.raises(ValueError,match='loaded lunar'): research.evolve(experiment,[0.,.01])


def test_no_future_orientation_provider(experiment,monkeypatch):
    import solar_simulator.orientation as orientation
    def forbidden(*args,**kwargs): raise AssertionError('future orientation must not be read')
    monkeypatch.setattr(orientation,'lunar_rotation',forbidden)
    assert research.create(purpose='conditional-research')==experiment
    end, states = research.evolve(experiment,[0.,60./source_inputs()['units'].time_s])
    assert np.array_equal(states[0].view(np.uint64),np.array(experiment.checkpoint.state).view(np.uint64))
    assert end.checkpoint.time>0


def test_new_process_command_restart_and_diagnostic_export(experiment,tmp_path):
    units = source_inputs()['units']; grid = np.linspace(0.,3600./units.time_s,17)
    full_end, full = research.evolve(experiment,grid)
    middle, first = research.evolve(experiment,grid[:9]); research.save(tmp_path/'middle.json',middle)
    command = [sys.executable,'-X','utf8','-B','scripts/run_lunar_research.py','run',
        str(tmp_path/'middle.json'),str(tmp_path/'end.json'),'--duration-seconds','1800','--samples','9',
        '--trajectory',str(tmp_path/'suffix.npz')]
    subprocess.run(command,cwd=research.ROOT,check=True,capture_output=True,text=True)
    end = research.load(tmp_path/'end.json')
    with np.load(tmp_path/'suffix.npz',allow_pickle=False) as archive: suffix = archive['states']
    joined = np.vstack([first[:-1],suffix]); cp = experiment.checkpoint
    assert np.array_equal(suffix[0].view(np.uint64),first[-1].view(np.uint64))
    assert np.array_equal(np.array(end.checkpoint.state).view(np.uint64),suffix[-1].view(np.uint64))
    assert end.receipt_json==experiment.receipt_json
    assert end.checkpoint.initial==cp.initial and end.checkpoint.metadata_json==cp.metadata_json
    # SI position criterion including the direct pair vector, no division by small components.
    assert np.linalg.norm((full[:,:30]-joined[:,:30]).reshape(-1,10,3),axis=2).max()*units.length_m < 1
    assert np.linalg.norm(full_end.checkpoint.state[-4:])==pytest.approx(1.,abs=1e-12)
    main(['export',str(tmp_path/'end.json'),str(tmp_path/'diagnostic.json')])
    from scripts.canonical_checkpoint import parse_json
    out = parse_json((tmp_path/'diagnostic.json').read_text('utf-8'))
    assert out['physical_mapping_certified'] is False and len(out['velocity_m_s'])==10
    with pytest.raises(ValueError): research.from_document(out)


def test_existing_outputs_and_invalid_purpose_are_preserved(experiment,tmp_path):
    path = tmp_path/'existing.json'; path.write_text('keep',encoding='utf-8')
    with pytest.raises(FileExistsError): research.save(path,experiment)
    with pytest.raises(ValueError): main(['init',str(path),'--purpose','conditional-research'])
    assert path.read_text('utf-8')=='keep'
    with pytest.raises(ValueError): research.create(purpose='physical')
    bad = tmp_path/'duplicate.json';bad.write_text('{"a":1,"a":2}',encoding='utf-8')
    with pytest.raises(ValueError): research.load(bad)


def test_declared_stricter_controls_do_not_change_initial_physics(experiment):
    control = deepcopy(experiment.checkpoint.metadata['integration'])
    control['rtol'] = 3e-13; control['atol'] = (np.array(control['atol'])*.03).tolist()
    strict = research.create(purpose='conditional-research',integration=control)
    assert strict.checkpoint.initial==experiment.checkpoint.initial
    assert strict.receipt_json==experiment.receipt_json
    assert strict.checkpoint.metadata['integration']==control
