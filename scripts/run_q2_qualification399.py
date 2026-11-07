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
from time import process_time,perf_counter

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
    if subprocess.run(['git','-C',str(ROOT),'merge-base','--is-ancestor',tool_commit,'HEAD'],capture_output=True).returncode:raise ValueError('Tool commit not present in current history')
    p['_tool_sources']=execution['tool_sources']
    return execution,p


def expected_binding(job,p,modules,identity):
    doc=modules['storage'].to_document(q.initial(job,p,modules))
    return dict(scope='scientific399',job=job,source=identity,initial_SHA256=__import__('hashlib').sha256(q.canonical(doc)).hexdigest(),epochs=job['epochs'],contract_SHA256=q.CONTRACT_SHA,tool_sources_SHA256=p['_tool_sources'])


def worker(args,execution,p):
    role,backend=args.worker.split(':')
    modules,identity=q.load_runtime(role,p);directory=Path(args.output)
    if backend=='evaluate':
        results={}
        for job in p['jobs']:
            # Read expected identity from a verified completed receipt, then
            # validate role/commit/profile and frozen IC independently below.
            receipt=q.read_envelope(directory/job['id']/'complete.json');binding=receipt['binding']
            q.require_identity(job,p,binding['source'])
            results[job['id']]=q.verify_complete(directory/job['id'],binding)
        summary=q.assess_all(results,p)
        q.atomic_json(directory/'summary.json',q.envelope(summary))
        if summary['source_equivalence_status']!='PASS':raise ArithmeticError('SOURCE EQUIVALENCE FAIL; summary/reproducer retained')
        return
    jobs=[j for j in p['jobs'] if j.get('role')==role and j.get('backend')==backend]
    if role=='baseline' and backend=='python':jobs += [j for j in p['jobs'] if j.get('kind')=='reference']
    for job in jobs:
        expected=expected_binding(job,p,modules,identity);target=directory/job['id']
        if target.exists():
            if not args.resume_completed:raise FileExistsError('Existing job is not authorized for repeat')
            q.verify_complete(target,expected)  # No numerical call on resume.
        else:q.run_job(target,job,p,modules,identity)
    after_modules,after=q.load_runtime(role,p)
    if after!=identity:raise ValueError('Source/environment changed during cohort')
    for name,h in execution['tool_sources'].items():q.require_sha(ROOT/name,h)


def attempt_history(directory,limits):
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
        if row.get('guard_record')!=record or row.get('complete') is not True or record.get('complete') is not True or record.get('exit_code')!=0 or record.get('limit_reason') is not None or record.get('error') is not None:raise ValueError('Stopped or mismatched resource attempt')
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


def controller(args,execution,p):
    if execution['status']!='SEALED_GO_FOR_SEPARATELY_AUTHORIZED_399':raise ValueError('Execution plan is NO-GO or unapproved')
    if execution['limits']!=dict(cpu_seconds=144,wall_seconds=288,private_bytes=900*1024**2,disk_bytes=112*1024**2):raise ValueError('Changed resource policy')
    directory=Path(args.output)
    expected=dict(plan_SHA256=args.sha,scope='scientific399',tool_commit=execution['tool_commit'],jobs=p['jobs'])
    if directory.exists():
        if list(directory.glob('*.partial')):raise ValueError('Partial controller output requires separate recovery authorization')
        if not args.resume_completed or q.read_envelope(directory/'run.json')!=expected:raise ValueError('Wrong existing run')
        # A partial job or incomplete guard record needs a new explicit budget/
        # recovery decision; do not silently discard its consumed resources.
        for job in p['jobs']:
            target=directory/job['id']
            if target.exists() and not (target/'complete.json').is_file():raise ValueError('Partial job requires separate recovery authorization')
        if (directory/'summary.json').exists():raise FileExistsError('Finished run is immutable')
    else:q.initialize(directory,expected)
    old=attempt_history(directory,execution['limits'])
    prior_cpu=old[-1]['cumulative_CPU_seconds'] if old else 0.;prior_wall=old[-1]['cumulative_active_wall_seconds'] if old else 0.
    guard=load_monitor(execution)
    import psutil
    parent=psutil.Process();start=perf_counter();workers_cpu=0.
    def hook(sample):
        if parent.memory_info().private+sample['private_tree']>execution['limits']['private_bytes']:raise MemoryError('Combined private resource limit')
    for cohort in ('baseline:python','baseline:rust','candidate:python','candidate:rust','baseline:evaluate'):
        # Every invocation is guard-owned, including source attestation and I/O.
        number=len(old)+1;name=f'{number:03d}';out=directory/('guard-'+name)
        command=[sys.executable,'-I','-X','utf8','-B',str(Path(__file__).resolve()),'--plan',str(Path(args.plan).resolve()),'--sha',args.sha,'--output',str(directory.resolve()),'--worker',cohort]
        if args.resume_completed:command.append('--resume-completed')
        for key in ('VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONHASHSEED','PYTHONHOME','PYTHONPATH'):os.environ.pop(key,None)
        os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        os.environ['SOLAR_Q2_399_GUARDED_PLAN_SHA256']=args.sha
        record=guard.monitor(command,out,directory,execution['limits'],used_cpu=prior_cpu+workers_cpu+process_time(),stage_start=start-prior_wall,hook=hook)
        workers_cpu+=record['worker_CPU_seconds']
        row=dict(cohort=cohort,complete=record['complete'],guard_record=record,cumulative_CPU_seconds=prior_cpu+workers_cpu+process_time(),cumulative_active_wall_seconds=prior_wall+perf_counter()-start)
        q.atomic_json(directory/('attempt-'+name+'.json'),q.envelope(row));old.append(row)
        if not record['complete']:raise RuntimeError('Guarded cohort STOP; preserve completed/partial data and original traceback')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True);parser.add_argument('--sha',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--execute-399',action='store_true');parser.add_argument('--resume-completed',action='store_true')
    parser.add_argument('--worker',choices=['baseline:python','baseline:rust','candidate:python','candidate:rust','baseline:evaluate'])
    args=parser.parse_args();execution,p=read_plan(args.plan,args.sha)
    if args.worker:
        if os.environ.get('SOLAR_Q2_399_GUARDED_PLAN_SHA256')!=args.sha:raise ValueError('Worker requires its owned resource supervisor')
        worker(args,execution,p)
    elif args.execute_399:controller(args,execution,p)
    else:parser.error('Explicit --execute-399 required; no execution during398')


if __name__=='__main__':main()
