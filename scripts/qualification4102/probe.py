import ctypes,json,os,subprocess,sys,time
from pathlib import Path
mode=sys.argv[1];out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
k=ctypes.WinDLL('kernel32',use_last_error=True);h=k.GetCurrentProcess;k.GetCurrentProcess.restype=ctypes.c_void_p
v=[ctypes.c_uint64() for _ in range(4)];k.GetProcessTimes.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(ctypes.c_uint64)]*4;k.GetProcessTimes(h(),*(ctypes.byref(x) for x in v))
(out/(str(os.getpid())+'.pid.json')).write_text(json.dumps(dict(pid=os.getpid(),birth=v[0].value)))
if mode=='echo':
 print(json.dumps(dict(argv=sys.argv[3:],cwd=os.getcwd(),stdin=sys.stdin.read(),env={x:os.environ.get(x) for x in ('PYTHONPATH','PYTHONHOME','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS')}),ensure_ascii=True),flush=True);print('stderr-token',file=sys.stderr,flush=True)
elif mode=='gui':
 import tkinter as tk
 root=tk.Tk();root.update();root.destroy();print('tk-clean',flush=True)
elif mode=='burn':
 data=bytearray(16*1024**2);end=time.perf_counter()+3
 while time.perf_counter()<end:sum(range(5000))
elif mode in ('orphan','grand','joined','short'):
 child=subprocess.Popen([sys.executable,'-I','-B',__file__,'short' if mode=='grand' else 'burn',str(out)])
 if mode=='joined':child.wait()
 else:time.sleep(.02 if mode=='short' else .5)
elif mode=='nonzero':raise SystemExit(7)
elif mode=='crash':os._exit(9)
elif mode=='disk':(out/'payload').write_bytes(bytes(2*1024**2));time.sleep(2)
elif mode=='sleep':time.sleep(3)
elif mode=='handle':
 flags=ctypes.c_ulong();f=k.GetHandleInformation;f.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)];print('foreign-handle-valid',bool(f(int(sys.argv[3]),ctypes.byref(flags))),flush=True)
