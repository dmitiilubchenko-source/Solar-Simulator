"""Guarded fixed58 executor. 398 never invokes --execute-399.

Resume skips only SHA-verified completed jobs; a partial scientific job refuses.
No code/commands from plans are evaluated. Worker command is fixed in this file.
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from time import process_time,perf_counter

LAUNCH_START=perf_counter()
GROUPS=('baseline:python','baseline:rust','candidate:python','candidate:rust')
EVALUATOR='baseline:evaluate'

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import q2_execution398 as q


def read_plan(path,digest):
    q.require_sha(path,digest);execution=json.loads(Path(path).read_bytes())
    if execution.get('status')!='SEALED_GO_FOR_SEPARATELY_AUTHORIZED_399':raise ValueError('No admitted sealed399plan; preflight is incomplete')
    p=q.contract()
    if execution['contract_SHA256']!=q.CONTRACT_SHA or execution['jobs']!=p['jobs']:raise ValueError('Changed fixed58 plan')
    required={'scripts/q2_execution398.py','scripts/run_q2_qualification399.py','scripts/q2_reference397.py','scripts/two_q2_reference380.py','scripts/validate_two_q2_380.py','scripts/q2_frame_observer393.py','scripts/q2_source_adapter396.py'}
    freeze_name=p['source_binding']['candidate_freeze'];q.require_sha(ROOT/freeze_name,p['source_binding']['candidate_freeze_SHA256'])
    freeze=json.loads((ROOT/freeze_name).read_bytes())
    data={freeze_name:p['source_binding']['candidate_freeze_SHA256'],**{p['roles'][role]['environment']:freeze[role+'_environment_SHA256'] for role in ('baseline','candidate')}}
    if not required<=set(execution['tool_sources']) or any(execution['tool_sources'].get(name)!=h for name,h in data.items()):raise ValueError('Missing frozen tool/environment bindings')
    for name,h in execution['tool_sources'].items():
        from scripts.release_history import evidence_path
        q.require_sha(evidence_path(ROOT,name),h)
    tool_commit=execution['tool_commit']
    if len(tool_commit)!=40 or any(x not in '0123456789abcdef' for x in tool_commit):raise ValueError('Expected exact tool Git commit')
    if subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',tool_commit,'HEAD'],capture_output=True).returncode:raise ValueError('Tool commit not present in current history')
    tracked=[name for name in execution['tool_sources'] if not name.startswith('.tools/')]
    if subprocess.run(['git','-C',str(ROOT),'diff','--quiet',tool_commit,'--',*tracked],capture_output=True).returncode:raise ValueError('Tool commit does not match current tool/data files')
    p['_tool_sources']=execution['tool_sources']
    validate_group_plan(execution,p)
    return execution,p


def expected_binding(job,p,modules,identity):
    doc=modules['storage'].to_document(q.initial(job,p,modules))
    return dict(scope='scientific399',job=job,source=identity,initial_SHA256=__import__('hashlib').sha256(q.canonical(doc)).hexdigest(),epochs=job['epochs'],contract_SHA256=q.CONTRACT_SHA,tool_sources_SHA256=p['_tool_sources'])


def group_jobs(p,key):
    if key==EVALUATOR:return p['jobs']
    if key not in GROUPS:raise ValueError('Unknown source/backend group')
    role,backend=key.split(':')
    return [j for j in p['jobs'] if (j.get('role')==role and j.get('backend')==backend) or (key=='baseline:python' and j.get('kind')=='reference')]


def validate_group_plan(execution,p):
    if execution.get('group_schema')!=1 or set(execution.get('groups',{}))!=set(GROUPS+(EVALUATOR,)):raise ValueError('Grouped resource policy required')
    ids=[]
    ceilings=dict(cpu_seconds=180,wall_seconds=360,private_bytes=1024**3,disk_bytes=128*1024**2)
    for key in GROUPS+(EVALUATOR,):
        g=execution['groups'][key];expected=[j['id'] for j in group_jobs(p,key)]
        if g['directory']!=key.replace(':','-') or g['job_ids']!=expected:raise ValueError('Wrong group directory/job IDs')
        if key!=EVALUATOR:ids+=expected
        for which in ('caps','limits'):
            values=g[which]
            if set(values)!=set(ceilings) or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in values.values()):raise ValueError('Invalid group resource limits')
        if any(g['limits'][k]>=g['caps'][k] or g['caps'][k]>ceilings[k] for k in ceilings):raise ValueError('Group resource cap/early-stop mismatch')
    if len(ids)!=58 or len(set(ids))!=58 or set(ids)!={j['id'] for j in p['jobs']}:raise ValueError('Groups must partition all58jobs')
    if execution.get('execution_order')!=list(GROUPS+(EVALUATOR,)):raise ValueError('Changed execution order')
    for job in p['jobs']:q.require_identity(job,p,execution['source_identities'][job.get('role','baseline')])


def run_binding(execution,p,digest):
    return dict(scope='scientific399_grouped',plan_SHA256=digest,tool_commit=execution['tool_commit'],jobs=p['jobs'])


def group_binding(execution,p,key,digest):
    return dict(**run_binding(execution,p,digest),group=key,job_ids=[j['id'] for j in group_jobs(p,key)],resources=execution['groups'][key])


def group_directory(root,execution,key):
    if key not in GROUPS+(EVALUATOR,):raise ValueError('Unknown source/backend group')
    name=execution['groups'][key]['directory']
    if name!=key.replace(':','-'):raise ValueError('Wrong group directory')
    return Path(root)/name


def saved_binding(job,p,identity):
    return dict(scope='scientific399',job=job,source=identity,initial_SHA256=__import__('hashlib').sha256(q.canonical(q.input_document(job,p))).hexdigest(),epochs=job['epochs'],contract_SHA256=q.CONTRACT_SHA,tool_sources_SHA256=p['_tool_sources'])


def worker_proof(directory,execution,p,key,digest=None,*,return_results=False):
    """Validate exact saved owners and files; no runtime is loaded or advanced."""
    results={};hashes={}
    for job in group_jobs(p,key):
        identity=execution['source_identities'][job.get('role','baseline')]
        target=Path(directory)/job['id']
        result=q.verify_complete(target,saved_binding(job,p,identity))
        hashes[job['id']]=q.sha(target/'complete.json')
        if return_results:results[job['id']]=result
    proof=dict(binding=group_binding(execution,p,key,digest),job_SHA256=hashes)
    return (proof,results) if return_results else proof


def publish_or_verify(path,value,resume):
    if Path(path).exists():
        if not resume:raise FileExistsError('Existing immutable worker receipt')
        if q.read_envelope(path)!=value:raise ValueError('Changed existing worker receipt')
    else:q.atomic_json(path,q.envelope(value))


def worker(args,execution,p):
    key=args.worker;role,backend=key.split(':')
    modules,identity=q.load_runtime(role,p)
    if identity!=execution['source_identities'][role]:raise ValueError('Actual runtime identity changed')
    directory=group_directory(args.output,execution,key)
    if backend=='evaluate':
        results={};inputs={}
        for cohort in GROUPS:
            values=verify_group(args.output,execution,p,cohort,args.sha,return_results=True)
            if set(results)&set(values):raise ValueError('Duplicate evaluator job IDs')
            results.update(values);inputs[cohort]=q.sha(group_directory(args.output,execution,cohort)/'final.json')
        summary=q.assess_all(results,p)
        publish_or_verify(directory/'summary.json',summary,args.resume_completed)
        proof=dict(binding=group_binding(execution,p,key,args.sha),group_final_SHA256=inputs,summary_SHA256=q.sha(directory/'summary.json'))
    else:
        for job in group_jobs(p,key):
            expected=expected_binding(job,p,modules,identity);target=directory/job['id']
            if expected!=saved_binding(job,p,identity):raise ValueError('Frozen IC codec changed')
            if target.exists():
                if not args.resume_completed:raise FileExistsError('Existing job is not authorized for repeat')
                q.verify_complete(target,expected)
            else:q.run_job(target,job,p,modules,identity)
        proof=worker_proof(directory,execution,p,key,args.sha)
    _,after=q.load_runtime(role,p)
    if after!=identity:raise ValueError('Source/environment changed during group')
    for name,h in execution['tool_sources'].items():q.require_sha(ROOT/name,h)
    publish_or_verify(directory/'verified.json',proof,args.resume_completed)


def attempt_history(directory,limits,*,allow_interrupted=False):
    """Resume requires the original complete guard records, without refunds.

    A checksum envelope alone is not confirmation that a guard finished. Match
    its separately persisted record and reject gaps, partials and undercounts.
    """
    directory=Path(directory)
    paths=sorted(directory.glob('attempt-*.json'))
    if paths!=[directory/('attempt-'+f'{i:03d}'+'.json') for i in range(1,len(paths)+1)]:raise ValueError('Resource attempt sequence has gaps')
    guards=sorted(directory.glob('guard-*'))
    if guards!=[directory/('guard-'+f'{i:03d}') for i in range(1,len(paths)+1)]:raise ValueError('Missing guard resource accounting after interruption')
    old=[];cpu=wall=0.
    for path,guard in zip(paths,guards):
        row=q.read_envelope(path)
        if not guard.is_dir() or list(guard.rglob('*.partial')) or not (guard/'supervisor.json').is_file():raise ValueError('Unconfirmed guard resource record')
        record=json.loads((guard/'supervisor.json').read_bytes())
        complete=row.get('complete') is True and record.get('complete') is True and record.get('exit_code')==0 and record.get('limit_reason') is None and record.get('error') is None
        interrupted=allow_interrupted and row.get('complete') is False and record.get('complete') is False and record.get('limit_reason')=='interrupted' and isinstance(record.get('error'),dict) and record['error'].get('type')=='KeyboardInterrupt' and type(record.get('exit_code')) is int and record.get('last_sample') is not None
        if row.get('guard_record')!=record or not (complete or interrupted):raise ValueError('Stopped or mismatched resource attempt')
        if row.get('cohort') not in ('baseline:python','baseline:rust','candidate:python','candidate:rust','baseline:evaluate'):raise ValueError('Unknown resource cohort')
        values=[record.get(k) for k in ('worker_CPU_seconds','parent_supervision_CPU_seconds','wall_seconds','peak_private_tree_sampled','disk_bytes')]+[row.get(k) for k in ('cumulative_CPU_seconds','cumulative_active_wall_seconds')]
        if any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in values):raise ValueError('Invalid resource counters')
        worker,parent,elapsed,private,disk,total_cpu,total_wall=values
        if total_cpu+1e-9<cpu+worker+parent or total_wall+1e-9<wall+elapsed:raise ValueError('Resource refund or cumulative undercount')
        if total_cpu>=limits['cpu_seconds'] or total_wall>=limits['wall_seconds'] or private>limits['private_bytes'] or disk>limits['disk_bytes']:raise ValueError('Prior resource budget exhausted')
        old.append(row);cpu,wall=total_cpu,total_wall
    return old


def load_monitor(execution):
    """Load only the fixed SHA-bound supervisor, never a command from JSON."""
    monitor_path=ROOT/'.tools/qualification385/offline_monitor.py';q.require_sha(monitor_path,execution['monitor_SHA256'])
    spec=importlib.util.spec_from_file_location('q2_guard399',monitor_path);guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    return guard


def group_history(directory,execution,key):
    old=attempt_history(directory,execution['groups'][key]['limits'],allow_interrupted=True)
    directory=Path(directory)
    expected=[directory/f'launch-{i:03d}.json' for i in range(1,len(old)+1)]
    if sorted(directory.glob('launch-*.json'))!=expected:raise ValueError('Unconfirmed launcher resource accounting')
    for path,row in zip(expected,old):
        launch=q.read_envelope(path)
        if row['cohort']!=key or launch.get('group')!=key or row.get('launch_SHA256')!=q.sha(path):raise ValueError('Mixed launcher/group resource history')
    return old


def verify_group(root,execution,p,key,digest,*,return_results=False,proof_only=False):
    directory=group_directory(root,execution,key);expected=group_binding(execution,p,key,digest)
    if list(directory.glob('*.partial')):raise ValueError('Partial group publication')
    if q.read_envelope(Path(root)/'run.json')!=run_binding(execution,p,digest) or q.read_envelope(directory/'run.json')!=expected:raise ValueError('Wrong group/run binding')
    final=q.read_envelope(directory/'final.json');old=group_history(directory,execution,key)
    if not old or not old[-1]['complete'] or final.get('binding')!=expected:raise ValueError('Incomplete group resource receipt')
    wanted={f'attempt-{i:03d}.json':q.sha(directory/f'attempt-{i:03d}.json') for i in range(1,len(old)+1)}
    if final.get('attempt_SHA256')!=wanted or final.get('verified_SHA256')!=q.sha(directory/'verified.json'):raise ValueError('Changed final group receipt')
    if final.get('charged_CPU_seconds')!=old[-1]['cumulative_CPU_seconds'] or final.get('charged_active_wall_seconds')!=old[-1]['cumulative_active_wall_seconds']:raise ValueError('Changed final group budget')
    stored=q.read_envelope(directory/'verified.json')
    if key==EVALUATOR:
        inputs={g:q.sha(group_directory(root,execution,g)/'final.json') for g in GROUPS}
        expected_proof=dict(binding=expected,group_final_SHA256=inputs,summary_SHA256=q.sha(directory/'summary.json'))
        q.read_envelope(directory/'summary.json');results={}
    elif proof_only:
        hashes={j['id']:q.sha(directory/j['id']/'complete.json') for j in group_jobs(p,key)}
        expected_proof=dict(binding=expected,job_SHA256=hashes);results={}
    else:expected_proof,results=worker_proof(directory,execution,p,key,digest,return_results=True)
    if stored!=expected_proof:raise ValueError('Wrong/mixed completed group proof')
    return results if return_results else final


def launch_elapsed():
    import psutil
    return max(0.,time.time()-psutil.Process().create_time(),perf_counter()-LAUNCH_START)


def controller(args,execution,p):
    if execution['status']!='SEALED_GO_FOR_SEPARATELY_AUTHORIZED_399':raise ValueError('Execution plan is NO-GO or unapproved')
    root=Path(args.output)
    if root.exists() and list(root.glob('*.partial')):raise ValueError('Partial controller output requires separate recovery authorization')
    key=args.group
    if key not in GROUPS+(EVALUATOR,):raise ValueError('Select one independent group')
    if root.exists():
        if q.read_envelope(root/'run.json')!=run_binding(execution,p,args.sha):raise ValueError('Wrong existing run')
    else:q.initialize(root,run_binding(execution,p,args.sha))
    directory=group_directory(root,execution,key);expected=group_binding(execution,p,key,args.sha)
    if directory.exists():
        if (directory/'final.json').exists():raise FileExistsError('Final group immutable; no worker or budget reset')
        if not args.resume_completed or q.read_envelope(directory/'run.json')!=expected:raise ValueError('Wrong existing group')
        if list(directory.glob('*.partial')):raise ValueError('Partial group publication requires recovery authorization')
    else:q.initialize(directory,expected)
    for job in group_jobs(p,key) if key!=EVALUATOR else []:
        target=directory/job['id']
        if target.exists() and not (target/'complete.json').is_file():raise ValueError('Partial job requires separate recovery authorization')
    old=group_history(directory,execution,key)
    if key==EVALUATOR:
        # Completeness is verified before an evaluator worker may be launched.
        for cohort in GROUPS:verify_group(root,execution,p,cohort,args.sha,proof_only=True)
    prior_cpu=old[-1]['cumulative_CPU_seconds'] if old else 0.;prior_wall=old[-1]['cumulative_active_wall_seconds'] if old else 0.
    limits=execution['groups'][key]['limits'];guard=load_monitor(execution)
    import psutil
    parent=psutil.Process();start=perf_counter()-launch_elapsed()
    number=len(old)+1;name=f'{number:03d}'
    claim=directory/('launch-'+name+'.json')
    q.atomic_json(claim,q.envelope(dict(group=key,binding=expected,prior_CPU_seconds=prior_cpu,prior_wall_seconds=prior_wall,launcher_PID=os.getpid(),CPU_seconds_at_claim=process_time())))
    command=[sys.executable,'-I','-X','utf8','-B',str(Path(__file__).resolve()),'--plan',str(Path(args.plan).resolve()),'--sha',args.sha,'--output',str(root.resolve()),'--worker',key]
    if args.resume_completed:command.append('--resume-completed')
    for envkey in ('VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONHASHSEED','PYTHONHOME','PYTHONPATH'):os.environ.pop(envkey,None)
    os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',SOLAR_Q2_399_GUARDED_PLAN_SHA256=args.sha,SOLAR_Q2_399_GUARDED_GROUP=key)
    def hook(sample):
        mem=parent.memory_info()
        if getattr(mem,'peak_pagefile',mem.vms)+sample['private_tree']>limits['private_bytes']:raise MemoryError('Combined private resource limit')
    if prior_cpu+process_time()+.25>=limits['cpu_seconds'] or prior_wall+perf_counter()-start+.25>=limits['wall_seconds']:
        record=dict(complete=False,exit_code=None,limit_reason='admission-budget-exhausted',error=None,worker_CPU_seconds=0.,parent_supervision_CPU_seconds=process_time(),wall_seconds=perf_counter()-start,peak_private_tree_sampled=0,disk_bytes=0)
        out=directory/('guard-'+name);out.mkdir();q.atomic_json(out/'supervisor.json',record)
    else:record=guard.monitor(command,directory/('guard-'+name),directory,limits,used_cpu=prior_cpu+process_time(),stage_start=start-prior_wall,hook=hook)
    # Explicit charge for the small receipt/fsync/exit tail. It is an allowance,
    # not a measured upper bound; hard-vs-early headroom remains unchanged.
    row=dict(cohort=key,complete=record['complete'],guard_record=record,launch_SHA256=q.sha(claim),tail_allowance_CPU_seconds=.25,tail_allowance_wall_seconds=.25,cumulative_CPU_seconds=prior_cpu+record['worker_CPU_seconds']+process_time()+.25,cumulative_active_wall_seconds=prior_wall+perf_counter()-start+.25)
    q.atomic_json(directory/('attempt-'+name+'.json'),q.envelope(row))
    if not record['complete']:raise RuntimeError('Guarded group STOP; preserve all data and resource receipts')
    proof=q.read_envelope(directory/'verified.json')
    if proof.get('binding')!=expected:raise ValueError('Missing/mixed verified group proof')
    if row['cumulative_CPU_seconds']>=limits['cpu_seconds'] or row['cumulative_active_wall_seconds']>=limits['wall_seconds']:raise RuntimeError('Group exhausted early budget during finalization')
    attempts={f'attempt-{i:03d}.json':q.sha(directory/f'attempt-{i:03d}.json') for i in range(1,number+1)}
    q.atomic_json(directory/'final.json',q.envelope(dict(binding=expected,verified_SHA256=q.sha(directory/'verified.json'),attempt_SHA256=attempts,charged_CPU_seconds=row['cumulative_CPU_seconds'],charged_active_wall_seconds=row['cumulative_active_wall_seconds'],status='COMPLETE_EXECUTION_NOT_SCIENTIFIC_PASS')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True);parser.add_argument('--sha',required=True);parser.add_argument('--output')
    parser.add_argument('--execute-399',action='store_true');parser.add_argument('--resume-completed',action='store_true')
    parser.add_argument('--group',choices=GROUPS+(EVALUATOR,));parser.add_argument('--check-plan',action='store_true')
    parser.add_argument('--worker',choices=['baseline:python','baseline:rust','candidate:python','candidate:rust','baseline:evaluate'])
    args=parser.parse_args();execution,p=read_plan(args.plan,args.sha)
    if args.check_plan:
        if args.worker or args.execute_399:parser.error('Plan inspection cannot execute workers')
        print(json.dumps(dict(plan_SHA256=args.sha,jobs=len(p['jobs']),groups=list(execution['groups']),scope='Technical plan inspection only; no399execution authorized or performed')));return
    if not args.output:parser.error('Explicit --output required for execution')
    if args.worker:
        if os.environ.get('SOLAR_Q2_399_GUARDED_PLAN_SHA256')!=args.sha or os.environ.get('SOLAR_Q2_399_GUARDED_GROUP')!=args.worker:raise ValueError('Worker requires its owned group resource supervisor')
        worker(args,execution,p)
    elif args.execute_399:controller(args,execution,p)
    else:parser.error('Explicit --execute-399 required; no execution during398')


if __name__=='__main__':main()
