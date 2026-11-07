"""Synthetic controller contracts only: no integrations or scientific receipts."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import q2_execution398 as q
from scripts import run_q2_qualification399 as c


LIMITS = dict(cpu_seconds=144,wall_seconds=288,private_bytes=900*1024**2,disk_bytes=112*1024**2)


def attempt(directory, *, corrupt=None):
    """Openly synthetic resource counters, never a scientific job result."""
    guard=directory/'guard-001';guard.mkdir()
    record=dict(complete=True,exit_code=0,limit_reason=None,error=None,
                worker_CPU_seconds=1.,parent_supervision_CPU_seconds=.1,
                wall_seconds=2.,peak_private_tree_sampled=10,disk_bytes=20)
    (guard/'supervisor.json').write_text(json.dumps(record),encoding='utf-8')
    row=dict(cohort='baseline:python',complete=True,guard_record=record,
             cumulative_CPU_seconds=1.2,cumulative_active_wall_seconds=2.1)
    if corrupt=='missing':(guard/'supervisor.json').unlink()
    if corrupt=='changed':(guard/'supervisor.json').write_text('{}',encoding='utf-8')
    if corrupt=='refund':row['cumulative_CPU_seconds']=-1.
    if corrupt=='stopped':row['complete']=False
    if corrupt=='partial':(guard/'pending.partial').write_text('partial',encoding='utf-8')
    q.atomic_json(directory/'attempt-001.json',q.envelope(row))
    return row


def test_resume_rejects_unconfirmed_guard_before_any_worker(tmp_path,monkeypatch):
    args=SimpleNamespace(output=str(tmp_path),sha='synthetic-only',resume_completed=True)
    execution=dict(status='SEALED_GO_FOR_SEPARATELY_AUTHORIZED_399',limits=LIMITS,tool_commit='synthetic',monitor_SHA256='synthetic')
    p={'jobs':[]}
    q.atomic_json(tmp_path/'run.json',q.envelope(dict(plan_SHA256=args.sha,scope='scientific399',tool_commit='synthetic',jobs=[])))
    attempt(tmp_path,corrupt='missing')
    # A resource history without the original guard record must reject before
    # monitor source loading, not accidentally fail later for another reason.
    def reached(*a,**k):raise AssertionError('Unconfirmed attempt reached worker preparation')
    monkeypatch.setattr(q,'require_sha',reached)
    with pytest.raises(ValueError,match='[Rr]esource|[Gg]uard'):
        c.controller(args,execution,p)


@pytest.mark.parametrize('fault',['missing','changed','refund','stopped','partial'])
def test_history_rejects_damage_and_refunds_without_writing(tmp_path,fault):
    attempt(tmp_path,corrupt=fault)
    before={str(x.relative_to(tmp_path)):x.read_bytes() for x in tmp_path.rglob('*') if x.is_file()}
    with pytest.raises(ValueError):c.attempt_history(tmp_path,LIMITS)
    assert before=={str(x.relative_to(tmp_path)):x.read_bytes() for x in tmp_path.rglob('*') if x.is_file()}


def test_verified_history_preserves_consumed_resources(tmp_path):
    row=attempt(tmp_path)
    assert c.attempt_history(tmp_path,LIMITS)==[row]


def test_worker_resumes_verified_jobs_only_and_never_integrates(tmp_path,monkeypatch):
    job={'id':'synthetic-test','role':'baseline','backend':'rust'}
    p={'jobs':[job],'_tool_sources':{'synthetic':'fixture'}}
    execution={'tool_sources':{}}
    identity={'scope':'synthetic-only'};binding={'scope':'synthetic-only','owner':'baseline'}
    monkeypatch.setattr(q,'load_runtime',lambda *a:({},identity))
    monkeypatch.setattr(c,'expected_binding',lambda *a:binding)
    monkeypatch.setattr(q,'run_job',lambda *a,**k:pytest.fail('Resume attempted integration'))
    target=tmp_path/job['id'];target.mkdir()
    q.atomic_json(target/'initial.json',q.envelope(binding))
    q.atomic_json(target/'result.json',dict(binding=binding,epochs=[0.,1.],synthetic_only=True))
    (target/'states.jsonl').write_bytes(b''.join(q.canonical(q.envelope(dict(time=t,document=None)))+b'\n' for t in (0.,1.)))
    files={name:dict(size=(target/name).stat().st_size,sha256=q.sha(target/name)) for name in ('initial.json','result.json','states.jsonl')}
    q.atomic_json(target/'complete.json',q.envelope(dict(binding=binding,files=files,frames=2)))
    args=SimpleNamespace(worker='baseline:rust',output=str(tmp_path),resume_completed=True)
    c.worker(args,execution,p)
    with pytest.raises(FileExistsError):c.worker(SimpleNamespace(**{**vars(args),'resume_completed':False}),execution,p)
    monkeypatch.setattr(c,'expected_binding',lambda *a:{**binding,'owner':'candidate'})
    with pytest.raises(ValueError,match='Mixed'):c.worker(args,execution,p)
    monkeypatch.setattr(c,'expected_binding',lambda *a:binding)
    (target/'result.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError):c.worker(args,execution,p)


def test_read_plan_refuses_wrong_digest_and_unadmitted_plan(tmp_path):
    plan=tmp_path/'blocked.json';q.atomic_json(plan,dict(status='SYNTHETIC_BLOCKED'))
    with pytest.raises(ValueError,match='SHA'):c.read_plan(plan,'bad')
    with pytest.raises(ValueError,match='No admitted'):c.read_plan(plan,q.sha(plan))


def test_partial_controller_publication_refuses_before_loading_worker(tmp_path,monkeypatch):
    (tmp_path/'run.json.partial').write_bytes(b'partial')
    args=SimpleNamespace(output=str(tmp_path),sha='synthetic-only',resume_completed=True)
    execution=dict(status='SEALED_GO_FOR_SEPARATELY_AUTHORIZED_399',limits=LIMITS,tool_commit='synthetic')
    with pytest.raises(ValueError,match='Partial controller'):c.controller(args,execution,{'jobs':[]})


@pytest.mark.parametrize('fault',['source','environment','tool'])
def test_plan_provenance_faults_precede_runtime(tmp_path,monkeypatch,fault):
    # Deliberately incompatible tiny synthetic contract. It cannot be admitted
    # by the real q.contract() and is never written as a scientific GO plan.
    p={'jobs':[{'id':'synthetic-only'}],'source_binding':{'candidate_freeze':'freeze.json','candidate_freeze_SHA256':'frozen'},'roles':{role:{'environment':role+'.json'} for role in ('baseline','candidate')}}
    execution={'status':'SEALED_GO_FOR_SEPARATELY_AUTHORIZED_399','contract_SHA256':q.CONTRACT_SHA,'jobs':p['jobs'],'tool_sources':{},'tool_commit':'synthetic'}
    required=('q2_execution398.py','run_q2_qualification399.py','q2_reference397.py','two_q2_reference380.py','validate_two_q2_380.py','q2_frame_observer393.py','q2_source_adapter396.py')
    execution['tool_sources']={**{'scripts/'+name:'tool' for name in required},'freeze.json':'frozen','baseline.json':'baseline-env','candidate.json':'candidate-env'}
    (tmp_path/'freeze.json').write_text(json.dumps({'baseline_environment_SHA256':'baseline-env','candidate_environment_SHA256':'candidate-env'}),encoding='utf-8')
    monkeypatch.setattr(c,'ROOT',tmp_path);monkeypatch.setattr(q,'contract',lambda:p)
    path=tmp_path/'synthetic-plan.json'
    if fault=='environment':execution['tool_sources']['candidate.json']='wrong'
    elif fault=='source':execution['jobs']=[{'id':'foreign'}]
    else:execution['tool_sources']['scripts/q2_execution398.py']='bad-tool'
    q.atomic_json(path,execution);digest=q.sha(path)
    def check(p,h):
        if Path(p)==path:assert h==digest
        elif h=='bad-tool':raise ValueError('Source/input SHA mismatch')
    monkeypatch.setattr(q,'require_sha',check)
    with pytest.raises(ValueError):c.read_plan(path,digest)


def test_unknown_job_is_rejected_before_initialization(tmp_path):
    with pytest.raises(ValueError,match='outside fixed58'):
        q.run_job(tmp_path/'uncreated',{'id':'unknown'},{'jobs':[]},{},{})
    assert not (tmp_path/'uncreated').exists()
