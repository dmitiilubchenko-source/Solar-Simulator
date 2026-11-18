"""Windows-only research supervisor. No changes to the frozen409 monitor.

Job membership is established while the root is suspended. Job accounting
includes exited and unsampled processes; individual process discovery is sampled.
The job handle is non-inheritable and KILL_ON_JOB_CLOSE is a crash backstop.
"""
import ctypes as c
from ctypes import wintypes as w
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import time
import msvcrt

import psutil

OLD = Path(__file__).resolve().parents[1]/'qualification409/monitor200.py'
spec = importlib.util.spec_from_file_location('old_guard_helpers', OLD)
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
save, disk_size, exceeded = old.save, old.disk_size, old.exceeded
K = c.WinDLL('kernel32', use_last_error=True)
H, D, P = w.HANDLE, w.DWORD, c.c_void_p


class Basic(c.Structure):
    _fields_ = [(n, c.c_int64) for n in ('user', 'kernel', 'period_user', 'period_kernel')]+[(n,D) for n in ('faults','total','active','terminated')]


class Limits(c.Structure):
    _fields_ = [('process_time',c.c_int64),('job_time',c.c_int64),('flags',D),('min_ws',c.c_size_t),('max_ws',c.c_size_t),('active',D),('affinity',c.c_size_t),('priority',D),('scheduling',D)]


class Extended(c.Structure):
    _fields_ = [('basic',Limits),('io',c.c_uint64*6),('process_memory',c.c_size_t),('job_memory',c.c_size_t),('peak_process',c.c_size_t),('peak_job',c.c_size_t)]


class Startup(c.Structure):
    _fields_ = [('cb',D),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR)]+[(n,D) for n in ('x','y','xs','ys','xc','yc','fill','flags')]+[('show',w.WORD),('cb2',w.WORD),('reserved2',P),('stdin',H),('stdout',H),('stderr',H)]


class Process(c.Structure):
    _fields_ = [('process',H),('thread',H),('pid',D),('tid',D)]


class StartupEx(c.Structure):
    _fields_=[('startup',Startup),('attributes',P)]


def api(name, types, result=w.BOOL):
    f=getattr(K,name);f.argtypes=types;f.restype=result;return f


create_job=api('CreateJobObjectW',[P,w.LPCWSTR],H)
query_job=api('QueryInformationJobObject',[H,c.c_int,P,D,P])
set_job=api('SetInformationJobObject',[H,c.c_int,P,D])
assign=api('AssignProcessToJobObject',[H,H])
terminate_job=api('TerminateJobObject',[H,w.UINT])
close=api('CloseHandle',[H])
wait=api('WaitForSingleObject',[H,D],D)
get_exit=api('GetExitCodeProcess',[H,c.POINTER(D)])
create=api('CreateProcessW',[w.LPCWSTR,w.LPWSTR,P,P,w.BOOL,D,P,w.LPCWSTR,P,c.POINTER(Process)])
init_attributes=api('InitializeProcThreadAttributeList',[P,D,D,c.POINTER(c.c_size_t)])
update_attributes=api('UpdateProcThreadAttribute',[P,D,c.c_size_t,P,c.c_size_t,P,P])
delete_attributes=api('DeleteProcThreadAttributeList',[P],None)
resume=api('ResumeThread',[H],D)
terminate_process=api('TerminateProcess',[H,w.UINT])
open_process=api('OpenProcess',[D,w.BOOL,D],H)
is_in_job=api('IsProcessInJob',[H,H,c.POINTER(w.BOOL)])


def process_handle(pid):
    return checked(open_process(0x1000|0x100000,False,pid)) # query + SYNCHRONIZE


def checked(ok):
    if not ok: raise c.WinError(c.get_last_error())
    return ok


def accounting(job):
    a=Basic();checked(query_job(job,1,c.byref(a),c.sizeof(a),None))
    return dict(CPU_seconds=(a.user+a.kernel)/1e7,active=a.active,total=a.total,user_100ns=a.user,kernel_100ns=a.kernel,terminated=a.terminated,snapshot_perf=time.perf_counter())


def members(job):
    # Refuse overflow rather than silently truncate ownership discovery.
    class IDs(c.Structure):
        _fields_=[('assigned',D),('count',D),('pids',c.c_size_t*1024)]
    a=IDs();checked(query_job(job,3,c.byref(a),c.sizeof(a),None))
    if a.count>1024 or a.assigned>a.count: raise RuntimeError('Incomplete job PID list')
    return list(a.pids[:a.count])


def process_times(handle):
    values=[c.c_uint64() for _ in range(4)]
    f=api('GetProcessTimes',[H]+[c.POINTER(c.c_uint64)]*4)
    checked(f(handle,*(c.byref(x) for x in values)))
    return dict(creation_FILETIME=values[0].value,exit_FILETIME=values[1].value,kernel_100ns=values[2].value,user_100ns=values[3].value,CPU_seconds=(values[2].value+values[3].value)/1e7)


def identity(handle):
    t=process_times(handle);return t['creation_FILETIME'],t['CPU_seconds']


def authoritative_accounting(job):
    return accounting(job)


def monitor(command,out,stage_root,limits,*,used_cpu=0.,stage_start=None,hook=None,phase_hook=None,expected_sha=None,cwd=None,env=None):
    """Same resource fields as409; receipts additionally require an empty Job.

    No process is killed by PID. Termination targets only the owned kernel job.
    hook is test-only after a genuine sample. Cleanup is bounded to five seconds.
    """
    if expected_sha is not None and hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=expected_sha:
        raise ValueError('Tooling SHA mismatch before launch')
    out=Path(out);out.mkdir(exist_ok=False);stage_root=Path(stage_root)
    start=time.perf_counter();stage_start=start if stage_start is None else stage_start
    parent_start=time.process_time();job=None;pi=Process();owned={};reason=None;errors=[];last=None;peak=0;samples=0;final=None;root_code=None;cleanup=False;files=[];attributes=None;assigned=False;snapshots=[]
    phases=[];previous=None;attribute_list_ready=False;vanished=[]

    def phase(name, **details):
        phases.append(name)
        if phase_hook:
            phase_hook(name, details)

    def sample_job(name, *, final_read=False):
        nonlocal previous
        phase(name, job=job, root=pi.process)
        current=authoritative_accounting(job) if final_read else accounting(job)
        ticks=(current['user_100ns'],current['kernel_100ns'])
        if min(ticks)<0 or (previous is not None and any(a<b for a,b in zip(ticks,previous))):
            raise ValueError('Job CPU counters negative or decreased')
        previous=ticks
        return current

    def failure(where, exc):
        nonlocal reason
        reason=reason or where
        errors.append(dict(phase=where,type=type(exc).__name__,message=str(exc)))

    try:
        job=checked(create_job(None,None));ex=Extended();ex.basic.flags=0x2000
        checked(set_job(job,9,c.byref(ex),c.sizeof(ex))) # KILL_ON_JOB_CLOSE, no breakaway
        si=StartupEx();si.startup.cb=c.sizeof(si);si.startup.flags=0x100
        files.append(open(os.devnull,'rb'))
        files.append((out/'stdout.log').open('xb'))
        handles=(H*2)(*(msvcrt.get_osfhandle(f.fileno()) for f in files))
        for h in handles:os.set_handle_inheritable(h,True)
        size=c.c_size_t();init_attributes(None,2,0,c.byref(size))
        attributes=c.create_string_buffer(size.value)
        checked(init_attributes(attributes,2,0,c.byref(size)));attribute_list_ready=True;si.attributes=c.cast(attributes,P)
        checked(update_attributes(attributes,0,0x20002,handles,c.sizeof(handles),None,None))
        # JOB_LIST binds the suspended root during creation, including if the
        # supervisor dies before it gets a chance to inspect PROCESS_INFORMATION.
        jobs=(H*1)(job)
        checked(update_attributes(attributes,0,0x2000d,jobs,c.sizeof(jobs),None,None))
        si.startup.stdin=handles[0];si.startup.stdout=handles[1];si.startup.stderr=handles[1]
        child_env={k.upper():v for k,v in (os.environ if env is None else env).items()}
        for key in list(child_env):
            if key.upper() in ('PYTHONPATH','PYTHONHOME'):del child_env[key]
        child_env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        block=c.create_unicode_buffer('\0'.join(k+'='+v for k,v in sorted(child_env.items(),key=lambda x:x[0].upper()))+'\0\0')
        cmd=c.create_unicode_buffer(subprocess.list2cmdline(command))
        phase('before-create',job=job)
        checked(create(None,cmd,None,None,True,4|0x400|0x80000,block,str(Path(cwd or os.getcwd()).resolve()),c.byref(si),c.byref(pi)))
        phase('created-suspended',job=job,root=pi.process,pid=pi.pid)
        belongs=w.BOOL()
        checked(is_in_job(pi.process,job,c.byref(belongs)))
        if not belongs.value:raise RuntimeError('Root missing from Job after process creation')
        assigned=True
        initial=sample_job('initial')
        if initial['active']!=1 or initial['total']!=1:
            raise RuntimeError('Unexpected Job membership before root resume')
        if resume(pi.thread)==0xffffffff: raise c.WinError(c.get_last_error())
        for h in handles:os.set_handle_inheritable(h,False)
        while True:
            a=sample_job('periodic');private=0
            for pid in members(job):
                if phase_hook:phase_hook('before-handle',dict(pid=pid,job=job))
                try:
                    handle=process_handle(pid)
                except OSError as exc:
                    # A vanished short process is covered by kernel job CPU.
                    if getattr(exc,'winerror',None)==87:
                        vanished.append(pid)
                        continue
                    raise
                try:
                    belongs=w.BOOL();checked(is_in_job(handle,job,c.byref(belongs)))
                    if not belongs.value:raise RuntimeError('PID identity no longer belongs to owned job')
                    birth,cpu=identity(handle);key=(pid,birth)
                    if key not in owned:owned[key]=dict(handle=handle,last_CPU=cpu);handle=None
                    else:owned[key]['last_CPU']=cpu
                    try: private+=psutil.Process(pid).memory_info().private
                    except psutil.NoSuchProcess:pass
                finally:
                    if handle:close(handle)
            peak=max(peak,private);samples+=1
            last=dict(worker_cpu=a['CPU_seconds'],parent_cpu=time.process_time()-parent_start,private_tree=private,disk=disk_size(stage_root))
            reason=exceeded(last,limits,used_cpu,time.perf_counter()-stage_start)
            if reason:break
            if hook:hook(last)
            if wait(pi.process,0)==0:
                a=sample_job('root-exit')
                code=D();checked(get_exit(pi.process,c.byref(code)));root_code=code.value
                if a['active']:reason='unexpected-owned-descendant'
                elif root_code:reason='root-nonzero'
                break
            time.sleep(.2)
    except BaseException as exc:
        reason='interrupted' if isinstance(exc,KeyboardInterrupt) else 'monitor-error'
        errors.append(dict(type=type(exc).__name__,message=str(exc)))
    finally:
        try:
            if job:
                a=sample_job('cleanup-entry')
                if a['active']:
                    cleanup=True
                    phase('before-terminate',job=job,root=pi.process)
                    checked(terminate_job(job,1));deadline=time.perf_counter()+5
                    while accounting(job)['active'] and time.perf_counter()<deadline:time.sleep(.02)
                stopped=sample_job('post-cleanup')
                if stopped['active']:raise RuntimeError('Job still active after bounded cleanup')
            if pi.process:
                # Also covers failure to assign the still-suspended root.
                if not assigned and wait(pi.process,0)!=0:checked(terminate_process(pi.process,1))
                if wait(pi.process,5000)!=0:raise RuntimeError('Root cleanup not confirmed')
                code=D();checked(get_exit(pi.process,c.byref(code)));root_code=code.value
        except BaseException as exc:
            failure('cleanup-unresolved',exc)
            # A failed group operation must not skip cleanup of an unassigned root.
            if pi.process and not assigned:
                try:
                    if wait(pi.process,0)!=0:checked(terminate_process(pi.process,1))
                    if wait(pi.process,1000)!=0:raise RuntimeError('Unassigned root still alive')
                except BaseException as fallback:failure('unassigned-root-unresolved',fallback)
        processes=[]
        deadline=time.perf_counter()+5
        for (pid,birth),data in owned.items():
            try:
                if wait(data['handle'],max(0,int((deadline-time.perf_counter())*1000)))!=0:
                    raise RuntimeError('Retained owned process termination not confirmed')
                actual,cpu=identity(data['handle']);assert actual==birth
                code=D();checked(get_exit(data['handle'],c.byref(code)))
                alive=wait(data['handle'],0)!=0
                if alive:raise RuntimeError('Retained owned process alive')
                processes.append(dict(pid=pid,creation_FILETIME=birth,last_CPU_seconds=data['last_CPU'],final_CPU_seconds=cpu,exit_code=code.value,alive=False,job_membership_confirmed=True,times=process_times(data['handle'])))
            except BaseException as exc:
                reason=reason or 'final-process-unresolved';errors.append(dict(type=type(exc).__name__,message=str(exc)))
        if job and not errors:
            for _ in range(3):
                try:
                    snapshots.append(dict(job_before=sample_job('snapshot-before'),process_times=[dict(pid=pid,**process_times(data['handle'])) for (pid,birth),data in owned.items()],job_after=sample_job('snapshot-after')))
                except BaseException as exc:
                    reason=reason or 'snapshot-unresolved';errors.append(dict(type=type(exc).__name__,message=str(exc)))
                time.sleep(.02)
        if job:
            try:
                candidate=sample_job('final-authoritative',final_read=True)
                if candidate['active']!=0:raise RuntimeError('Final Job is not quiescent')
                final=candidate
            except BaseException as exc:
                failure('final-accounting-unresolved',exc)
        pending_handles=[data['handle'] for data in owned.values()]
        pending_handles.extend(h for h in (pi.thread,pi.process,job) if h)
        failed_closes=[]
        for handle in pending_handles:
            try:
                phase('close-handle',handle=handle)
                checked(close(handle))
            except BaseException as exc:
                failure('close-unresolved',exc)
                failed_closes.append(handle)
        for handle in failed_closes:
            try:checked(close(handle))
            except BaseException as exc:failure('close-retry-unresolved',exc)
        if attribute_list_ready:delete_attributes(attributes)
        for f in files:
            try:f.close()
            except BaseException as exc:failure('close-stream-unresolved',exc)
        parent=time.process_time()-parent_start
        cpu=None if final is None else final['CPU_seconds']
        if cpu is not None:
            reason=reason or exceeded(dict(worker_cpu=cpu,parent_cpu=parent,private_tree=peak,disk=disk_size(stage_root)),limits,used_cpu,time.perf_counter()-stage_start)
        complete=reason is None and not errors and root_code==0 and final is not None and final['active']==0
        record=dict(complete=complete,exit_code=root_code,limit_reason=reason,error=errors,final_job=final,processes=processes,post_termination_snapshots=snapshots,cleanup_performed=cleanup,worker_CPU_seconds=cpu,parent_supervision_CPU_seconds=parent,parent_interjob_CPU_excluded=True,receipt_write_CPU_excluded=True,wall_seconds=time.perf_counter()-start,peak_private_tree_sampled=peak,last_sample=last,samples=samples,poll_seconds=.2,disk_bytes=disk_size(stage_root),monitor_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),phases=phases,vanished_pids=vanished,measurement_limitations='Job group CPU once; process CPU diagnostic. Individual identities/private memory sampled. Writer cost belongs to caller ledger.')
        phase('receipt-write')
        save(out/'supervisor.json',record)
    return record
