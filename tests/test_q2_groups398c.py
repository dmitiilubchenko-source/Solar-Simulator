"""Grouped-controller tests use openly synthetic fixtures, never trajectories."""
from types import SimpleNamespace
from pathlib import Path
import json
from copy import deepcopy

import pytest

from scripts import q2_execution398 as q
from scripts import run_q2_qualification399 as c

KEYS=('baseline:python','baseline:rust','candidate:python','candidate:rust')
LIMITS=dict(cpu_seconds=144,wall_seconds=288,private_bytes=900*1024**2,disk_bytes=112*1024**2)


def synthetic_execution():
    return dict(status='SEALED_GO_FOR_SEPARATELY_AUTHORIZED_399',group_schema=1,
                limits=LIMITS,tool_commit='SYNTHETIC-NOT-ADMITTED',tool_sources={},
                source_identities={x:{'role':x,'synthetic_only':True} for x in ('baseline','candidate')},
                groups={k:dict(directory=k.replace(':','-'),job_ids=[],limits=dict(LIMITS),caps=dict(cpu_seconds=180,wall_seconds=360,private_bytes=1024**3,disk_bytes=128*1024**2)) for k in KEYS+('baseline:evaluate',)},
                monitor_SHA256='synthetic')


def test_one_selected_group_never_dispatches_the_other_groups(tmp_path,monkeypatch):
    execution=synthetic_execution();p={'jobs':[],'_tool_sources':{}}
    args=SimpleNamespace(output=str(tmp_path/'SYNTHETIC-ONLY'),sha='synthetic',plan='NO-REAL-PLAN',group='baseline:rust',resume_completed=False)
    calls=[]
    def monitor(command,out,directory,limits,**kwargs):
        key=command[command.index('--worker')+1];calls.append(key)
        out.mkdir();record=dict(complete=True,exit_code=0,limit_reason=None,error=None,worker_CPU_seconds=0.,parent_supervision_CPU_seconds=0.,wall_seconds=0.,peak_private_tree_sampled=1,disk_bytes=1)
        (out/'supervisor.json').write_text(json.dumps(record),encoding='utf-8')
        if hasattr(c,'worker_proof'):
            q.atomic_json(Path(directory)/'verified.json',q.envelope(c.worker_proof(directory,execution,p,key,args.sha)))
        return record
    monkeypatch.setattr(c,'load_monitor',lambda _:SimpleNamespace(monitor=monitor))
    c.controller(args,execution,p)
    assert calls==['baseline:rust'], 'Selecting a group must not launch the former all-cohort loop'


def rig(tmp_path,monkeypatch,key='baseline:python',jobs=None):
    execution=synthetic_execution();p={'jobs':jobs or [],'_tool_sources':{}}
    args=SimpleNamespace(output=str(tmp_path/'SYNTHETIC-ONLY'),sha='synthetic',plan='NO-REAL-PLAN',group=key,resume_completed=False)
    calls=[]
    def monitor(command,out,directory,limits,**kwargs):
        selected=command[command.index('--worker')+1];calls.append((selected,kwargs['used_cpu'],kwargs['stage_start']))
        out.mkdir();record=dict(complete=True,exit_code=0,limit_reason=None,error=None,worker_CPU_seconds=0.,parent_supervision_CPU_seconds=0.,wall_seconds=0.,peak_private_tree_sampled=1,disk_bytes=1)
        (out/'supervisor.json').write_text(json.dumps(record),encoding='utf-8')
        q.atomic_json(Path(directory)/'verified.json',q.envelope(c.worker_proof(directory,execution,p,selected,args.sha)))
        return record
    monkeypatch.setattr(c,'load_monitor',lambda _:SimpleNamespace(monitor=monitor))
    monkeypatch.setattr(c,'launch_elapsed',lambda:.01)
    return execution,p,args,calls


def files(root):
    return {str(x.relative_to(root)):x.read_bytes() for x in root.rglob('*') if x.is_file()}


def test_between_groups_resume_does_not_reenter_finished_group(tmp_path,monkeypatch):
    e,p,args,calls=rig(tmp_path,monkeypatch)
    c.controller(args,e,p)
    first=c.group_directory(args.output,e,args.group);before=files(first)
    # Equivalent to returning after a process interruption between groups:
    # select the next independent group; no attempt-index based skipping.
    args.group='baseline:rust';args.resume_completed=True
    c.controller(args,e,p)
    assert [x[0] for x in calls]==['baseline:python','baseline:rust']
    assert files(first)==before
    c.verify_group(args.output,e,p,'baseline:python',args.sha)
    args.group='baseline:python'
    with pytest.raises(FileExistsError,match='immutable'):c.controller(args,e,p)
    assert files(first)==before and len(calls)==2


@pytest.mark.parametrize('fault',['missing','corrupt','refund','number','group','claim'])
def test_closed_group_damage_is_read_only_stop(tmp_path,monkeypatch,fault):
    e,p,args,_=rig(tmp_path,monkeypatch);c.controller(args,e,p)
    d=c.group_directory(args.output,e,args.group)
    if fault=='missing':(d/'guard-001/supervisor.json').unlink()
    elif fault=='corrupt':(d/'guard-001/supervisor.json').write_text('{}')
    elif fault in ('refund','group'):
        path=d/'attempt-001.json';row=q.read_envelope(path)
        if fault=='refund':row['cumulative_CPU_seconds']=-1.
        else:row['cohort']='candidate:rust'
        path.write_bytes(q.canonical(q.envelope(row)))
    elif fault=='number':(d/'attempt-001.json').rename(d/'attempt-002.json')
    else:(d/'launch-001.json').unlink()
    before=files(d)
    with pytest.raises((ValueError,FileNotFoundError)):c.verify_group(args.output,e,p,args.group,args.sha)
    assert before==files(d)


def test_evaluator_cannot_launch_before_all_groups(tmp_path,monkeypatch):
    e,p,args,calls=rig(tmp_path,monkeypatch,key='baseline:evaluate')
    with pytest.raises((ValueError,FileNotFoundError)):c.controller(args,e,p)
    assert not calls


def completed_job(directory,binding):
    directory.mkdir();q.atomic_json(directory/'initial.json',q.envelope(binding))
    q.atomic_json(directory/'result.json',dict(binding=binding,epochs=[0.,1.],synthetic_only=True))
    (directory/'states.jsonl').write_bytes(b''.join(q.canonical(q.envelope(dict(time=t,document=None)))+b'\n' for t in (0.,1.)))
    metadata={name:dict(size=(directory/name).stat().st_size,sha256=q.sha(directory/name)) for name in ('initial.json','result.json','states.jsonl')}
    q.atomic_json(directory/'complete.json',q.envelope(dict(binding=binding,files=metadata,frames=2)))


def test_confirmed_interrupt_between_jobs_preserves_budget_and_skips_complete(tmp_path,monkeypatch):
    jobs=[dict(id='synthetic-'+str(i),role='baseline',backend='python') for i in (0,1)]
    e,p,args,calls=rig(tmp_path,monkeypatch,jobs=jobs)
    identity=e['source_identities']['baseline'];integrations=[];interrupt=[True]
    make_binding=lambda job,*a:dict(scope='synthetic-only',job=job)
    monkeypatch.setattr(c,'expected_binding',make_binding);monkeypatch.setattr(c,'saved_binding',make_binding)
    monkeypatch.setattr(q,'load_runtime',lambda *a:({},identity))
    def run(directory,job,*a):
        integrations.append(job['id']);completed_job(directory,make_binding(job))
        if interrupt[0]:raise KeyboardInterrupt('between finished synthetic jobs')
    monkeypatch.setattr(q,'run_job',run)
    records=[]
    def monitor(command,out,directory,limits,**kwargs):
        calls.append((args.group,kwargs['used_cpu'],kwargs['stage_start']));out.mkdir()
        wa=SimpleNamespace(worker=args.group,output=args.output,sha=args.sha,resume_completed=args.resume_completed)
        stopped=False
        try:c.worker(wa,e,p)
        except KeyboardInterrupt:stopped=True
        record=dict(complete=not stopped,exit_code=15 if stopped else 0,limit_reason='interrupted' if stopped else None,error=dict(type='KeyboardInterrupt') if stopped else None,last_sample={'worker_cpu':0.},worker_CPU_seconds=0.,parent_supervision_CPU_seconds=0.,wall_seconds=0.,peak_private_tree_sampled=1,disk_bytes=1)
        (out/'supervisor.json').write_text(json.dumps(record));records.append(record)
        return record
    monkeypatch.setattr(c,'load_monitor',lambda _:SimpleNamespace(monitor=monitor))
    with pytest.raises(RuntimeError,match='STOP'):c.controller(args,e,p)
    d=c.group_directory(args.output,e,args.group);old=q.read_envelope(d/'attempt-001.json')
    first=files(d/'synthetic-0');interrupt[0]=False;args.resume_completed=True
    c.controller(args,e,p)
    assert integrations==['synthetic-0','synthetic-1'] and files(d/'synthetic-0')==first
    final=c.verify_group(args.output,e,p,args.group,args.sha)
    assert final['charged_CPU_seconds']>=old['cumulative_CPU_seconds'] and calls[-1][1]>=old['cumulative_CPU_seconds']
    assert final['charged_active_wall_seconds']>=old['cumulative_active_wall_seconds']
    before=files(d)
    with pytest.raises(FileExistsError):c.controller(args,e,p)
    assert files(d)==before


@pytest.mark.parametrize('fault',['partial','orphan'])
def test_partial_job_and_orphan_launcher_stop_before_worker(tmp_path,monkeypatch,fault):
    jobs=[dict(id='synthetic-partial',role='baseline',backend='python')] if fault=='partial' else []
    e,p,args,calls=rig(tmp_path,monkeypatch,jobs=jobs)
    root=Path(args.output);q.initialize(root,c.run_binding(e,p,args.sha))
    d=c.group_directory(root,e,args.group);q.initialize(d,c.group_binding(e,p,args.group,args.sha))
    if fault=='orphan':q.atomic_json(d/'launch-001.json',q.envelope({'group':args.group}))
    else:(d/'synthetic-partial').mkdir()
    args.resume_completed=True
    with pytest.raises(ValueError,match='launcher|Partial job'):c.controller(args,e,p)
    assert not calls


def test_real58_partition_and_budget_tampering(tmp_path,monkeypatch):
    p=q.contract();e=synthetic_execution();e['execution_order']=list(KEYS+('baseline:evaluate',))
    monkeypatch.setattr(q,'ROOT',tmp_path)
    for role in ('baseline','candidate'):
        # Native test paths on Linux/Windows; no dependency on private caches.
        owner=p['roles'][role];owner['root']=str(tmp_path/role)
        owner['environment']=role+'-profile.json';profile={}
        (tmp_path/owner['environment']).write_text('{}',encoding='utf-8')
        e['source_identities'][role]=dict(role=role,commit=owner['commit'],source=owner['root'],import_origin=str(Path(owner['root'])/'src/solar_simulator/__init__.py'),environment_LF_SHA256=__import__('hashlib').sha256((json.dumps(profile,indent=2)+'\n').encode()).hexdigest())
    for key,g in e['groups'].items():g['job_ids']=[j['id'] for j in c.group_jobs(p,key)]
    c.validate_group_plan(e,p)
    assert [len(e['groups'][k]['job_ids']) for k in KEYS]==[16,14,14,14]
    for bad in ('job','directory','cap','identity'):
        broken=deepcopy(e)
        if bad=='job':broken['groups']['baseline:rust']['job_ids'].pop()
        elif bad=='directory':broken['groups']['baseline:rust']['directory']='../foreign'
        elif bad=='cap':broken['groups']['baseline:rust']['caps']['cpu_seconds']=1000
        else:broken['source_identities']['candidate']['commit']='foreign'
        with pytest.raises(ValueError):c.validate_group_plan(broken,p)


def test_assessor_rejects_foreign_protocol_before_reading_states(monkeypatch):
    p=q.contract();results={j['id']:{} for j in p['jobs']};job=p['jobs'][0]
    results[job['id']]=dict(binding=dict(scope='scientific399',job=job,source={},contract_SHA256='foreign'),epochs=job['epochs'])
    def reached(*a):raise AssertionError('Foreign protocol reached scientific state processing')
    monkeypatch.setattr(q,'require_identity',reached)
    with pytest.raises(ValueError,match='protocol'):q.assess_all(results,p)
