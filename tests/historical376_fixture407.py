"""Complete376 source fixture; never import/execute its historical dependencies."""
import hashlib,json,os
from pathlib import Path
from zipfile import ZipFile
from scripts.historical_sources407 import read_sources
from scripts.release_history import HISTORICAL_ARCHIVES

EXTRA='scripts/validation/source376-before407.zip'
EXTRA_SHA='8c60e7b4e02f8dd088b61e85a9cbabfb2cb4677237069b5af2e9eee71da6b8c7'
BUNDLE_SHA='2326775712ab071ec6354b01f529ba2749c22bbee773e5f26948c11408cc38d5'


def checkout(root,destination):
    root=Path(root);destination=Path(destination)
    if root.resolve()==destination.resolve():raise ValueError('Historical fixture must be separate')
    protocol=json.loads((root/'scripts/runtime-reliability-376-protocol-v2.json').read_bytes())
    report=json.loads((root/'docs/runtime-reliability-376-validation.json').read_bytes())
    sha=lambda b:hashlib.sha256(b).hexdigest()
    bundle=Path(os.environ.get('SOLAR_HISTORICAL376_BUNDLE','historical376-inputs.zip'))
    if not bundle.is_file():raise ValueError('Missing exact offline376 forensic input bundle; see407restore instructions')
    if sha(bundle.read_bytes())!=BUNDLE_SHA:raise ValueError('Changed offline376 forensic input bundle')
    _,extra=read_sources(root)
    if sha((root/EXTRA).read_bytes())!=EXTRA_SHA:raise ValueError('Changed extra376 source archive')
    with ZipFile(root/EXTRA) as z:extra.update({n:z.read(n) for n in z.namelist()})
    with ZipFile(bundle) as z:
        manifest=json.loads(z.read('MANIFEST.json'))
        for name,row in manifest['files'].items():extra[name]=z.read(row['member'])
    archives=[]
    for name in HISTORICAL_ARCHIVES:
        if name.endswith('.zip'):
            with ZipFile(root/name) as z:archives.append({n:z.read(n) for n in z.namelist()})
    required={**protocol['source_SHA256'],'scripts/assess_runtime_reliability376.py':report['analysis_source_SHA256']}
    payload={}
    for name,expected in required.items():
        current=root/name
        variants=([current.read_bytes()] if current.is_file() else [])+[m[name] for m in [extra,*archives] if name in m]
        matches=[raw for raw in variants if sha(raw)==expected]
        if not matches:raise ValueError('Unavailable exact376 historical source:'+name)
        target=(destination/name).resolve()
        if not target.is_relative_to(destination.resolve()):raise ValueError('Historical path escapes fixture')
        payload[target]=matches[0]
    for target,raw in payload.items():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    return destination
