"""Narrow provenance/output checks for Q2-396; no solver or physical model."""
import hashlib
import json
from pathlib import Path

from scripts.qualify_newton384 import write


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def require_sha(path,expected):
    if sha(path)!=expected:raise ValueError('Source/input SHA mismatch: '+str(path))


def require_environment(actual,expected):
    if actual!=expected:raise ValueError('Actual source/dependency/native environment mismatch')


def require_origins(package_file,dependency_files,source_root,prefix,expected_prefix):
    source_root=Path(source_root).resolve();prefix=Path(prefix).resolve()
    if prefix!=Path(expected_prefix).resolve():raise ValueError('Wrong interpreter environment')
    if not Path(package_file).resolve().is_relative_to(source_root/'src'):raise ValueError('Wrong runtime source origin')
    if any(not Path(p).resolve().is_relative_to(prefix) for p in dependency_files):raise ValueError('Mixed dependency/native origin')


def new_output(path):
    """Never reuse an existing directory, including empty/partial/symlink ones."""
    Path(path).mkdir(exist_ok=False)


def save_result(path,payload,binding):
    """An interrupted pair is partial, never a completed or replaceable result."""
    path=Path(path);sidecar=path.with_suffix(path.suffix+'.sha256.json')
    if path.exists() or sidecar.exists():raise FileExistsError(path)
    write(path,dict(binding=binding,payload=payload))
    write(sidecar,dict(name=path.name,size=path.stat().st_size,sha256=sha(path)))
    return json.loads(sidecar.read_bytes())


def read_result(path,binding):
    path=Path(path);sidecar=path.with_suffix(path.suffix+'.sha256.json')
    if not path.is_file() or not sidecar.is_file():raise ValueError('Incomplete result: payload or SHA sidecar absent')
    meta=json.loads(sidecar.read_bytes())
    if meta.get('name')!=path.name or meta.get('size')!=path.stat().st_size:raise ValueError('Result size/name mismatch')
    require_sha(path,meta.get('sha256'))
    result=json.loads(path.read_bytes())
    if result.get('binding')!=binding:raise ValueError('Result source/input binding mismatch')
    return result['payload']


def require_reference_shape(result,document,times):
    """Observe original RK45 output without projection, normalization or repair."""
    import numpy as np
    T,N,K=len(times),len(document['bodies']),len(document['rotations'])
    expected=dict(positions=(T,N,3),velocities=(T,N,3),orientation=(T,K,3,3),spins=(T,K,3))
    for name,shape in expected.items():
        value=np.asarray(result[name])
        if value.shape!=shape or not np.isfinite(value).all():raise ValueError('Invalid reference output shape/values: '+name)
