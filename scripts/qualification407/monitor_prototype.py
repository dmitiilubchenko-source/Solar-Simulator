# REJECTED407PROTOTYPE: real Windows directory race; use original385monitor.
"""Offline-only owned worker guard. No progress-based budget resets.

50 ms sampling is retained from pilot.monitor. Interrupted workers are killed
and reaped before the supervisor record is atomically committed in finally.
On Windows the retained Popen handle supplies final root CPU even after exit;
descendant CPU and all memory peaks remain sampled (short spikes can be missed).
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time, sleep

import psutil


def save(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    temporary = path.with_suffix(path.suffix + '.partial')
    with temporary.open('x', encoding='utf8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    os.rename(temporary, path)


def disk_size(root):
    total = 0
    pending = [os.fspath(root)]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                try:
                    if entry.is_file(): total += entry.stat().st_size
                    elif entry.is_dir(follow_symlinks=False): pending.append(entry.path)
                except FileNotFoundError:
                    pass  # Same rename race policy; no frequency/quota relaxation.
    return total



def exceeded(s, limits, used_cpu, stage_elapsed):
    if s['private_tree'] > limits['private_bytes']: return 'private-memory'
    if s['disk'] > limits['disk_bytes']: return 'stage-disk'
    if stage_elapsed > limits['wall_seconds']: return 'stage-wall'
    if used_cpu + s['parent_cpu'] + s['worker_cpu'] > limits['cpu_seconds']: return 'stage-CPU'
    return None


def windows_cpu(handle):
    if os.name != 'nt': return None
    values = [ctypes.c_uint64() for _ in range(4)]
    fun = ctypes.windll.kernel32.GetProcessTimes
    fun.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_uint64)] * 4
    fun.restype = ctypes.c_int
    if not fun(int(handle), *(ctypes.byref(v) for v in values)):
        raise ctypes.WinError()
    return (values[2].value + values[3].value) / 1e7


def process_handle(pid):
    if os.name!='nt':return None
    fun=ctypes.windll.kernel32.OpenProcess
    fun.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];fun.restype=ctypes.c_void_p
    handle=fun(0x1000,False,pid)  # QUERY_LIMITED_INFORMATION, retained until final accounting
    if not handle:raise ctypes.WinError()
    return handle


def close_handle(handle):
    fun=ctypes.windll.kernel32.CloseHandle;fun.argtypes=[ctypes.c_void_p];fun.restype=ctypes.c_int
    if not fun(handle):raise ctypes.WinError()


def monitor(command, out, stage_root, limits, *, used_cpu=0., stage_start=None, hook=None):
    """used_cpu excludes this invocation; caller includes parent inter-job work.

    hook is solely for deterministic fault injection after a genuine sample.
    A CPU cap is a sampled stop, not an OS scheduling quota; overshoot is reported.
    """
    out, stage_root = Path(out), Path(stage_root)
    out.mkdir(exist_ok=False)
    start = perf_counter(); stage_start = start if stage_start is None else stage_start
    parent_start = process_time(); last = None; samples = 0; cpus = {}; peak_private = peak_rss = 0
    reason = None; failure = None; child = None; tree = []; final_cpu = None; handles={};final_processes=[]
    env = os.environ.copy()
    env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    try:
        with (out/'stdout.log').open('x', encoding='utf8') as log:
            child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
            try: root = psutil.Process(child.pid)
            except psutil.NoSuchProcess: root = None
            while child.poll() is None:
                try: tree = [root] + root.children(recursive=True) if root is not None else []
                except psutil.NoSuchProcess: break
                private = rss = 0
                for p in tree:
                    try:
                        mem = p.memory_info(); c = p.cpu_times()
                        key=(p.pid,p.create_time())
                        if key not in handles and os.name=='nt':handles[key]=process_handle(p.pid)
                        cpus[key] = c.user+c.system
                        private += getattr(mem, 'private', mem.vms); rss += mem.rss
                    except psutil.NoSuchProcess:
                        continue
                peak_private = max(peak_private, private); peak_rss = max(peak_rss, rss)
                last = dict(worker_cpu=sum(cpus.values()), parent_cpu=process_time()-parent_start,
                            private_tree=private, rss_tree=rss, disk=disk_size(stage_root),
                            elapsed=perf_counter()-start)
                samples += 1
                reason = exceeded(last, limits, used_cpu, perf_counter()-stage_start)
                if reason: break
                if hook: hook(last)
                sleep(.05)
    except BaseException as exc:
        reason = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'monitor-error'
        failure = dict(type=type(exc).__name__, message=str(exc))
    finally:
        if child is not None:
            if child.poll() is None:
                try: tree = [psutil.Process(child.pid)] + psutil.Process(child.pid).children(recursive=True)
                except psutil.NoSuchProcess: tree = []
                for p in reversed(tree):
                    try: p.kill()
                    except psutil.NoSuchProcess: pass
            child.wait(timeout=5)
            final_cpu = windows_cpu(child._handle) if os.name=='nt' else None
        for key,handle in handles.items():
            value=windows_cpu(handle)
            final_processes.append(dict(pid=key[0],creation_time=key[1],CPU_seconds=value,
                                        role='launcher' if child is not None and key[0]==child.pid else 'analyzer_or_audit_descendant'))
            cpus[key]=max(cpus.get(key,0),value);close_handle(handle)
        sampled_cpu = max((last or {}).get('worker_cpu', 0), sum(cpus.values()))
        # Root final CPU replaces its sampled value, without double counting it.
        root_sample = sum(v for (pid, _), v in cpus.items() if child is not None and pid == child.pid)
        worker_cpu = sampled_cpu if final_cpu is None else sampled_cpu-root_sample+final_cpu
        parent_cpu = process_time()-parent_start
        final = dict(worker_cpu=worker_cpu, parent_cpu=parent_cpu, private_tree=peak_private,
                     disk=disk_size(stage_root))
        final_reason = exceeded(final, limits, used_cpu, perf_counter()-stage_start)
        reason = reason or final_reason
        record = dict(exit_code=None if child is None else child.returncode, limit_reason=reason,
                      error=failure, last_sample=last, samples=samples, poll_seconds=.05,
                      worker_CPU_seconds=worker_cpu, root_final_CPU_seconds=final_cpu,
                      parent_supervision_CPU_seconds=parent_cpu,
                      parent_interjob_CPU_excluded=True, peak_private_tree_sampled=peak_private,
                      processes=final_processes,
                      peak_rss_tree_sampled=peak_rss, wall_seconds=perf_counter()-start,
                      disk_bytes=final['disk'], complete=reason is None and child is not None and child.returncode == 0,
                      measurement_limitations='memory peaks and tree discovery sampled; final CPU of every discovered Windows process via retained handles; short unseen descendants possible; 50ms cap overshoot possible')
        save(out/'supervisor.json', record)
    return record
