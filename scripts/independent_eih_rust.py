"""Compile/cache the developer scalar EIH oracle; never used by runtime physics."""
import ctypes
import hashlib
from pathlib import Path
import subprocess
import numpy as np


def load_oracle():
    source=Path(__file__).with_name('validation')/'eih_scalar.rs'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    cache=source.parents[2]/'.tools';cache.mkdir(exist_ok=True)
    library=cache/f'independent-eih-{digest[:16]}.dll'
    compiler=Path.home()/'.cargo/bin/rustc.exe'
    version=subprocess.run([str(compiler),'--version'],check=True,capture_output=True,text=True).stdout.strip()
    if not library.exists():
        subprocess.run([str(compiler),'--edition','2021','--crate-type','cdylib','-C','opt-level=3',
            '--crate-name','independent_eih',str(source),'-o',str(library)],check=True)
    function=ctypes.CDLL(str(library)).scalar_eih
    ptr=ctypes.POINTER(ctypes.c_double)
    function.argtypes=[ctypes.c_size_t,ptr,ptr,ptr,ctypes.c_double,ctypes.c_ssize_t,ctypes.c_ssize_t,ptr,ptr]
    function.restype=ctypes.c_int
    def acceleration(p,v,mu,light_speed,relative_pair=None):
        # Separate, aligned C arrays satisfy the Rust slice/aliasing contract.
        p,v,mu=[np.array(a,dtype=np.float64,order='C',copy=True) for a in (p,v,mu)]
        if mu.ndim!=1 or p.shape!=(len(mu),3) or v.shape!=p.shape:
            raise ValueError('Independent oracle array shapes')
        first,second,relative=(-1,-1,np.zeros(3)) if relative_pair is None else relative_pair
        relative=np.array(relative,dtype=np.float64,order='C',copy=True)
        if relative.shape!=(3,): raise ValueError('Independent oracle pair shape')
        out=np.empty_like(p)
        args=[a.ctypes.data_as(ptr) for a in (p,v,mu,relative,out)]
        code=function(len(mu),args[0],args[1],args[2],float(light_speed),int(first),int(second),args[3],args[4])
        if code: raise ValueError(f'Independent scalar EIH rejected input: {code}')
        return out
    acceleration.source_sha256=digest
    acceleration.compiler_version=version
    return acceleration
