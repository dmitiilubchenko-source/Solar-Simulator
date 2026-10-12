from copy import deepcopy
import json

import numpy as np
import pytest

from scripts.assess_lunar_research import failures,boundary_controls,independent_kinematics,ROOT,POLICY
from scripts import lunar_research as research
from scripts.assess_rigid_pn import attitudes
from scripts.pinned_lunar_initial import source_inputs


def passing_values():
    policy = json.loads((ROOT/POLICY).read_text('utf-8'))
    metrics = {k:v/2 for k,v in policy['maximum'].items()}
    metrics.update({k:2*v for k,v in policy['minimum'].items()})
    return metrics,{k:True for k in policy['required_true']},policy


@pytest.mark.parametrize('section',['maximum','minimum','required_true'])
def test_predeclared_checks_detect_every_failed_metric(section):
    metrics,confirmations,policy = passing_values()
    assert failures(metrics,confirmations,policy)==[]
    for key in policy[section]:
        a,b = deepcopy(metrics),deepcopy(confirmations)
        if section=='required_true': b[key] = False
        else: a[key] = policy[section][key]
        assert failures(a,b,policy)==[key]


@pytest.mark.parametrize('mutation',['missing','unknown','nan','boolmetric','boolconfirmation'])
def test_report_cannot_drop_or_hide_metrics(mutation):
    a,b,p = passing_values();key = next(iter(a))
    if mutation=='missing': a.pop(key)
    elif mutation=='unknown': a['unreported'] = 0.
    elif mutation=='nan': a[key] = float('nan')
    elif mutation=='boolmetric': a[key] = False
    else: b[next(iter(b))] = 1
    with pytest.raises(ValueError): failures(a,b,p)


def test_independent_actual_boundary_and_wrong_mapping_controls():
    experiment = research.create(purpose='conditional-research');args = source_inputs();cp = experiment.checkpoint
    v,w,_ = independent_kinematics(np.array(cp.state),attitudes(np.array([cp.state]))[0],cp.parameters,cp.pair)
    assert (np.linalg.norm(v-args['velocities'],axis=1)/args['velocity_scales']).max()<1e-13
    from solar_simulator.spin_initial import lunar_solid_equivalent_initial
    _,_,_,profile = lunar_solid_equivalent_initial();r = np.array(profile['rotation']);rd = np.array(profile['rotation_derivative_per_second'])
    omega = sum((np.cross(r[:,i],rd[:,i]) for i in range(3)),np.zeros(3))/2*args['units'].time_s
    assert np.linalg.norm(w-omega)/args['rate_scale']<1e-13
    controls = boundary_controls(experiment); policy = passing_values()[2]
    assert set(controls)==set(policy['minimum'])
    assert all(controls[k]>limit for k,limit in policy['minimum'].items())


@pytest.mark.parametrize('consumer',['receipt','evolve'])
def test_real_disk_loader_edit_is_rejected_before_initialization_or_flow(tmp_path,monkeypatch,consumer):
    import shutil
    from scripts import lunar_initial_receipt as receipt
    experiment = research.create(purpose='conditional-research')
    for name in research.SOURCES:
        target = tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(research.ROOT/name,target)
    monkeypatch.setattr(research,'ROOT',tmp_path);monkeypatch.setattr(receipt,'ROOT',tmp_path)
    assert research.source_hashes()==research.LOADED_SOURCE_SHA
    assert receipt.code_hashes()==receipt.LOADED_CODE_SHA
    target = tmp_path/'src/solar_simulator/spin_initial.py'
    target.write_bytes(target.read_bytes()+b'\n# isolated disk mutation\n')
    def forbidden(*args,**kwargs): raise AssertionError('initialization/integrator must not run')
    monkeypatch.setattr(receipt,'from_pinned_dataset',forbidden)
    monkeypatch.setattr(research.relative,'evolve',forbidden)
    with pytest.raises(ValueError,match='loaded'):
        if consumer=='receipt': receipt.verify_receipt(experiment.receipt)
        else: research.evolve(experiment,[0.,.01])


def test_pre_fix_receipt_missing_loader_hash_is_explicitly_rejected():
    from scripts import lunar_initial_receipt as receipt
    document = receipt.make_receipt(purpose='conditional-research')
    document['environment']['code_sha256'].pop('src/solar_simulator/spin_initial.py')
    payload = {k:v for k,v in document.items() if k!='payload_sha256'}
    document['payload_sha256'] = receipt.payload_checksum(payload)
    with pytest.raises(ValueError,match='source/state/contract/environment'): receipt.verify_receipt(document)
