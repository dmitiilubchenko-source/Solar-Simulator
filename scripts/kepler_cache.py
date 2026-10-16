"""Bind a generated Kepler verification receipt to its sources and NPZ."""
import hashlib
import json
from pathlib import Path


def load_receipt(path,root):
    path,root=Path(path),Path(root).resolve()
    raw=path.read_bytes()
    receipt=json.loads(raw)
    digest=receipt.get('npz_sha256')
    if not digest:
        raise ValueError('Legacy receipt has no NPZ binding; recompute with current scripts')
    if hashlib.sha256(path.with_suffix('.npz').read_bytes()).hexdigest()!=digest:
        raise ValueError('Kepler NPZ SHA256 mismatch')
    sources=receipt.get('source_sha256')
    if not isinstance(sources,dict) or not sources:
        raise ValueError('Kepler receipt has no source binding')
    for name,expected in sources.items():
        source=(root/name).resolve()
        if not source.is_relative_to(root) or hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
            raise ValueError('Kepler source SHA256 mismatch: '+name)
    return receipt,raw
