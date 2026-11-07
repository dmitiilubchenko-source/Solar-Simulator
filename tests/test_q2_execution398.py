"""Synthetic I/O/evaluator faults. No scientific trajectories in this suite."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import q2_execution398 as q
from scripts.two_q2_fixture380 import fixture
from scripts.two_q2_reference380 import independent_invariants
from scripts.q2_frame_observer393 import invariants as decimal_invariants
from scripts.q2_r_reuse394 import numeric_state
from scripts.validate_two_q2_380 import represented,difference as old_difference
from solar_simulator.experiment import create_experiment
from solar_simulator.storage import to_document
from solar_simulator.simulation import G


def state(case='two-bodies',backend='python'):
    b,r,s=fixture(case=='three-bodies',backend)
    return create_experiment(b,s,rotations=r[:1] if case=='one' else r)


def payload(job=None):
    job=job or dict(case='two-bodies',backend='python',recipe='continuous',level='standard',epochs=[0.,62.5])
    seed=state(job['case'],job.get('backend','python'));doc=to_document(seed);epochs=job['epochs']
    states=[replace(seed,time=t,settings=replace(seed.settings,dt=(t-epochs[i-1] if i and job.get('recipe')=='cold' else seed.settings.dt))) for i,t in enumerate(epochs)]
    a={k:v.tolist() for k,v in represented(states).items()}
    if job.get('recipe')=='continuous':
        first=q.initial_readout(doc)
        for key in ('positions','velocities'):a[key][0]=first[key]
    inv=[q.independent_by_id(a['positions'][i],a['velocities'][i],a['orientation'][i],a['spins'][i],doc) for i in range(len(epochs))]
    r=dict(job={k:v for k,v in job.items() if k not in ('role','id')},epochs=epochs,initial=doc,settings=doc['settings'],arrays=a,counters=dict(solver_calls=len(epochs)-1 if job.get('recipe')=='cold' else 1,RHS=68,nfev=68,compiled_native_calls=68 if job.get('backend')=='rust' else 0),documents=[to_document(s) for s in states],runtime_observables=dict(E_J=[x[0] for x in inv],P_kg_m_s=[x[1].tolist() for x in inv],L_kg_m2_s=[x[2].tolist() for x in inv]))
    return r


def test_old_observer_bodyB_failure_then_minimal_mapping():
    b,r,s=fixture();seed=create_experiment(b,s,rotations=r[1:]);doc=to_document(seed);raw=numeric_state(seed);v=represented([seed])
    args=[v[k][0] for k in ('positions','velocities','orientation','spins')]
    old=independent_invariants(*args,np.array([x.mass for x in b]),[np.array(r[1].figure.moments)])
    expected=float(decimal_invariants(raw,doc,G,80)['E_J']);new=q.independent_by_id(*args,doc)
    assert abs(old[0]/expected-1)>1e-12 and abs(new[0]/expected-1)<1e-12


def test_original_observer_order_is_bitwise_unchanged():
    seed=state();doc=to_document(seed);v=represented([seed]);args=[v[k][0] for k in ('positions','velocities','orientation','spins')]
    a=independent_invariants(*args,np.array([b.mass for b in seed.bodies]),[np.array(r.figure.moments) for r in seed.rotations]);b=q.independent_by_id(*args,doc)
    assert all(np.array(x).tobytes()==np.array(y).tobytes() for x,y in zip(a,b))


def test_atomic_publish_and_interruption(tmp_path):
    p=tmp_path/'value.json';q.atomic_json(p,{'x':1.});before=p.read_bytes()
    with pytest.raises(FileExistsError):q.atomic_json(p,{'x':2.})
    assert p.read_bytes()==before
    partial=tmp_path/'partial.json'
    def interrupt(stage):raise KeyboardInterrupt('synthetic power-loss boundary')
    with pytest.raises(KeyboardInterrupt):q.atomic_json(partial,{},fault=interrupt)
    assert not partial.exists() and partial.with_name('partial.json.partial').exists()
    with pytest.raises(FileExistsError):q.atomic_json(partial,{})


def test_unsupported_atomic_link_fails_closed(tmp_path,monkeypatch):
    def bad(*a):raise OSError('unsupported link')
    monkeypatch.setattr(q.os,'link',bad)
    with pytest.raises(OSError):q.atomic_json(tmp_path/'x.json',{})
    assert not (tmp_path/'x.json').exists() and (tmp_path/'x.json.partial').exists()


def completed(tmp_path):
    r=payload();binding={'scope':'synthetic-only','source':'A'};r['binding']=binding
    q.atomic_json(tmp_path/'initial.json',q.envelope(binding));q.atomic_json(tmp_path/'result.json',r)
    with (tmp_path/'states.jsonl').open('wb') as f:
        for t,d in zip(r['epochs'],r['documents']):f.write(q.canonical(q.envelope(dict(time=t,document=d)))+b'\n')
    files={n:dict(size=(tmp_path/n).stat().st_size,sha256=q.sha(tmp_path/n)) for n in ('initial.json','result.json','states.jsonl')}
    q.atomic_json(tmp_path/'complete.json',q.envelope(dict(binding=binding,files=files,frames=2)))
    return binding


@pytest.mark.parametrize('fault',['none','owner','missing','truncated','manifest','partial','initial'])
def test_completion_faults_never_modify_source(tmp_path,fault):
    binding=completed(tmp_path)
    if fault=='owner':binding={'scope':'synthetic-only','source':'other'}
    elif fault=='missing':(tmp_path/'states.jsonl').unlink()
    elif fault=='truncated':(tmp_path/'result.json').write_bytes(b'{}')
    elif fault=='manifest':(tmp_path/'complete.json').write_bytes(b'{}')
    elif fault=='partial':(tmp_path/'unfinished.partial').write_bytes(b'x')
    elif fault=='initial':(tmp_path/'initial.json').write_bytes(b'{}')
    before={p.name:p.read_bytes() for p in tmp_path.iterdir()}
    if fault=='none':assert len(q.verify_complete(tmp_path,binding)['documents'])==2
    else:
        with pytest.raises((ValueError,KeyError)):q.verify_complete(tmp_path,binding)
    assert before=={p.name:p.read_bytes() for p in tmp_path.iterdir()}


def test_numeric_evaluator_reuses_original_definition_and_rejects_missing():
    r=payload();a={k:np.array(v) for k,v in r['arrays'].items()};b=deepcopy(a);b['positions'][1,1,0]+=1e-5
    assert q.difference(a,b,r['initial'],r['epochs'])==old_difference(a,b,r['initial'])
    for bad in ({},{**a,'positions':a['positions'][:1]},{**a,'positions':np.full_like(a['positions'],np.nan)}):
        with pytest.raises(ValueError):q.difference(a,bad,r['initial'],r['epochs'])
    with pytest.raises(ValueError):q.drift(a,r['initial'],r['epochs'],dict(E_J=[0.,0.],P_kg_m_s=[[0.,0.,0.]]*2,L_kg_m2_s=[[0.,0.,0.]]*2))


def test_exact_source_comparison_and_checkpoint_mismatch():
    a=payload();b=deepcopy(a);assert q.source_equivalence(a,b)['exact']
    b['documents'].pop()
    with pytest.raises(ValueError):q.source_equivalence(a,b)
    b=deepcopy(a);b['documents'][1]['time']=0.
    with pytest.raises(ValueError):q.source_equivalence(a,b)
    b=deepcopy(a);b['counters']['RHS']+=1
    assert not q.source_equivalence(a,b)['exact']
    b=deepcopy(a);b['arrays']['quaternions'][1][0][1]+=1e-5
    with pytest.raises(ValueError):q.source_equivalence(a,b)


def test_continuous_t0_readout_is_not_an_experiment_checkpoint():
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    seed=state();doc=to_document(seed);raw=q.initial_readout(doc)
    bodies=tuple(Body(b.name,b.mass,Vector3(*p),Vector3(*v)) for b,p,v in zip(seed.bodies,raw['positions'],raw['velocities']))
    with pytest.raises(ValueError,match='t=0'):to_document(replace(seed,bodies=bodies))
    data=payload();q.validate_documents(data)
    assert data['documents'][0]==data['initial'] and data['arrays']['positions'][0]==raw['positions']


def test_source_identity_fails_before_any_numerical_call(tmp_path,monkeypatch):
    p=q.contract();owner=p['roles']['baseline'];monkeypatch.setattr(q,'ROOT',tmp_path)
    owner['root']=str(tmp_path/'synthetic-candidate')  # Native path grammar on each CI host.
    p['roles']['baseline']['environment']='profile.json';(tmp_path/'profile.json').write_text('{}')
    identity=dict(role='baseline',commit=owner['commit'],source=owner['root'],import_origin=str(Path(owner['root'])/'src/solar_simulator/__init__.py'),environment_LF_SHA256=__import__('hashlib').sha256(b'{}\n').hexdigest())
    q.require_identity({'role':'baseline'},p,identity)
    for field,value in [('commit','wrong'),('source',str(tmp_path)),('environment_LF_SHA256','bad')]:
        with pytest.raises(ValueError):q.require_identity({'role':'baseline'},p,{**identity,field:value})


def test_cli_refuses_an_unadmitted_plan_before_loading_any_runtime(tmp_path):
    from scripts.run_q2_qualification399 import read_plan
    path=tmp_path/'blocked.json';q.atomic_json(path,dict(status='BLOCKED_PREFLIGHT_PARTIAL'))
    with pytest.raises(ValueError,match='preflight is incomplete'):read_plan(path,q.sha(path))


def test_full58_synthetic_evaluator_separates_equivalence_from_scientific_pass(monkeypatch):
    p=q.contract();p['_tool_sources']={'synthetic':'not a scientific source'};results={};documents={}
    for job in p['jobs']:
        r=payload(job);doc=r['initial'];documents[job['id']]=doc
        r['binding']=dict(scope='scientific399',job=job,source={},initial_SHA256=__import__('hashlib').sha256(q.canonical(doc)).hexdigest(),tool_sources_SHA256=p['_tool_sources'],contract_SHA256=q.CONTRACT_SHA)
        if job.get('kind')=='reference':r['arrays'].pop('quaternions')
        results[job['id']]=r
    # This test isolates mathematical reductions with openly SYNTHETIC static
    # arrays. Real source/IC attestation is independently fault-tested above.
    monkeypatch.setattr(q,'require_identity',lambda *a:None)
    monkeypatch.setattr(q,'input_document',lambda job,p:documents[job['id']])
    report=q.assess_all(results,p)
    assert report['source_equivalence_status']=='PASS' and report['scientific_criteria_status']=='FAIL'
    assert all(not c['strict_pass'] for c in report['strict_convergence'])
    assert report['release_readiness']=='NO-GO'
    results.pop(next(iter(results)))
    with pytest.raises(ValueError,match='58'):q.assess_all(results,p)
