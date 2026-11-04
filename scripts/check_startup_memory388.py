"""Read-only Windows startup probe. Never executes preparation or integration.

Only Import/ImportFrom nodes before the first assignment in the preserved
387 prepare() are executed. Self counters use Win32, independent of psutil.
"""
import argparse
import ast
import ctypes as ct
from ctypes import wintypes as wt
import hashlib
import json
import os
from pathlib import Path
import sys
from time import perf_counter,process_time,sleep

THREAD_KEYS=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONHASHSEED')
ORIGINAL_SHA='2102fba85c7a25c147ebc6fda2af8d0b1c995409c236ca9f116df076901e138f'
EARLY_PRIVATE=900*1024**2


class Counters(ct.Structure):
    _fields_=[('cb',wt.DWORD),('PageFaultCount',wt.DWORD)]+[(name,ct.c_size_t) for name in (
        'PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
        'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]


def windows_memory(pid=None):
    if os.name!='nt':raise OSError('Windows API required')
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    open_process=kernel.OpenProcess;open_process.argtypes=[wt.DWORD,wt.BOOL,wt.DWORD];open_process.restype=wt.HANDLE
    close=kernel.CloseHandle;close.argtypes=[wt.HANDLE];close.restype=wt.BOOL
    handle=open_process(0x410,False,os.getpid() if pid is None else pid)
    if not handle:raise ct.WinError(ct.get_last_error())
    try:
        fun=ct.WinDLL('psapi',use_last_error=True).GetProcessMemoryInfo
        fun.argtypes=[wt.HANDLE,ct.POINTER(Counters),wt.DWORD];fun.restype=wt.BOOL
        c=Counters();c.cb=ct.sizeof(c)
        if not fun(handle,ct.byref(c),c.cb):raise ct.WinError(ct.get_last_error())
        return {name:int(getattr(c,name)) for name,_ in Counters._fields_}
    finally:close(handle)


def unique_private(rows):
    seen=set();total=0
    for r in rows:
        key=(r['pid'],r['create_time'])
        if key in seen:raise ValueError('Duplicate process identity')
        seen.add(key);total+=r['private']
    return total


def import_prefix(text):
    module=ast.parse(text)
    function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='prepare')
    result=[]
    for node in function.body:
        if not isinstance(node,(ast.Import,ast.ImportFrom)):break
        result.append(node)
    if not result:raise ValueError('Missing original import prefix')
    return result


def configure(profile):
    if profile not in ('blas1-only','all1-current','cleared387'):raise ValueError('Unknown diagnostic profile')
    for key in THREAD_KEYS:os.environ.pop(key,None)
    if profile=='blas1-only':os.environ['OPENBLAS_NUM_THREADS']='1'
    elif profile=='all1-current':
        for key in THREAD_KEYS[:3]:os.environ[key]='1'
    return {key:os.environ.get(key) for key in THREAD_KEYS}


def loaded_blas():
    """Query readonly thread-count functions on already loaded DLL handles only."""
    kernel=ct.WinDLL('kernel32',use_last_error=True)
    get=kernel.GetModuleHandleW;get.argtypes=[wt.LPCWSTR];get.restype=wt.HMODULE
    address=kernel.GetProcAddress;address.argtypes=[wt.HMODULE,ct.c_char_p];address.restype=ct.c_void_p
    result=[]
    for package in ('numpy','scipy'):
        module=sys.modules.get(package)
        if module is None or not getattr(module,'__file__',None):continue
        directory=Path(module.__file__).parent.parent/(package+'.libs')
        for dll in directory.glob('*blas*.dll'):
            handle=get(dll.name)
            if not handle:continue
            for symbol in ('scipy_openblas_get_num_threads64_','scipy_openblas_get_num_threads','openblas_get_num_threads64_','openblas_get_num_threads'):
                ptr=address(handle,symbol.encode())
                if ptr:
                    result.append(dict(package=package,dll=dll.name,symbol=symbol,threads=ct.CFUNCTYPE(ct.c_int)(ptr)()))
                    break
    return result


def probe(original,profile):
    raw=original.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORIGINAL_SHA:raise ValueError('Preserved387 worker SHA mismatch')
    environment=configure(profile)
    start=perf_counter();cpu0=process_time();events=0;active=False
    def mark(stage,major=True):
        nonlocal events,active
        if active:return
        active=True
        try:
            mem=windows_memory()
            record=dict(event=events,pid=os.getpid(),profile=profile,stage=stage,
                monotonic=perf_counter(),wall_seconds=perf_counter()-start,CPU_seconds=process_time()-cpu0,
                windows=mem,thread_variables=environment)
            if major:record['loaded_blas']=loaded_blas()
            print(json.dumps(record),flush=True);events+=1
            if mem['PrivateUsage']>EARLY_PRIVATE:
                print(json.dumps(dict(stop='private-memory-self',pid=os.getpid(),private_bytes=mem['PrivateUsage'])),flush=True)
                os._exit(90)
        finally:active=False
        if major:sleep(.08)  # stable observation window; no numerical integration
    mark('instrumentation-ready')
    # Re-execute the original module's stdlib-only top-level imports; never its main.
    tree=ast.parse(raw.decode('utf-8'))
    namespace={}
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            mark('before original top-level: '+ast.unparse(node));exec(compile(ast.Module(body=[node],type_ignores=[]),str(original),'exec'),namespace)
    import builtins
    saved=builtins.__import__;nested=0
    def traced(name,globals=None,locals=None,fromlist=(),level=0):
        nonlocal nested
        selected=not active and nested<80 and any(x in name for x in ('_multiarray','_fblas','_ufuncs','scipy.linalg','scipy.spatial'))
        if selected:nested+=1;mark('nested-before:'+name,False)
        value=saved(name,globals,locals,fromlist,level)
        if selected:mark('nested-after:'+name,False)
        return value
    builtins.__import__=traced
    try:
        for node in import_prefix(raw.decode('utf-8')):
            name=ast.unparse(node);mark('before original prepare: '+name)
            exec(compile(ast.Module(body=[node],type_ignores=[]),str(original),'exec'),namespace)
            mark('after original prepare: '+name)
        mark('original-import-prefix-complete')
        if profile!='cleared387':
            # These are explicitly additional readonly startup controls, not original387 imports.
            import importlib
            for name in ('scipy.integrate','matplotlib','tkinter','solar_simulator.app','solar_native'):
                mark('before additional: '+name);module=importlib.import_module(name);mark('after additional: '+name)
            compiled=getattr(module,'solar_native',module)
            digest=hashlib.sha256(Path(compiled.__file__).read_bytes()).hexdigest()
            if digest!='0cbc389f139854628f287c04a7cea52c530a18294c2c3a0670faa48bf53c0601':raise ValueError('Wrong actual032 native')
            from solar_simulator.native_forces import prepare
            prepare([1.,2.])  # validates/owns masses and returns closure; no force or integration call
            mark('runtime-ready-no-IC-no-integrations')
    finally:builtins.__import__=saved


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original',type=Path,required=True)
    p.add_argument('--profile',choices=['blas1-only','all1-current','cleared387'],required=True)
    a=p.parse_args();probe(a.original,a.profile)


if __name__=='__main__':main()
