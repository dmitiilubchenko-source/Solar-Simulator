"""Eight exact source artifacts for offline fixtures, never a live qualification."""
import hashlib,json
from pathlib import Path
from zipfile import ZipFile

ARCHIVE='scripts/validation/source-before407.zip'
MANIFEST='scripts/validation/source-before407.json'
MANIFEST_SHA='eb490d4b82781dd31f1312f1f788d8f5e1dbd5c500982d334072b935fce37ea1'
CONTROL='src/solar_simulator/control_row.py'
CONTROL_SHA='0dbf30d3fc5212a3a58abc326fdda6d3f120be5f269827253d3ecffff85b2742'


def read_sources(root):
    """Authenticate the entire closure before exposing even one member."""
    root=Path(root).resolve();sha=lambda b:hashlib.sha256(b).hexdigest()
    raw=(root/MANIFEST).read_bytes()
    if sha(raw)!=MANIFEST_SHA:raise ValueError('Changed407 historical source manifest')
    m=json.loads(raw)
    raw=(root/ARCHIVE).read_bytes()
    if sha(raw)!=m['archive_SHA256']:raise ValueError('Changed407 historical source archive')
    with ZipFile(root/ARCHIVE) as z:
        if set(z.namelist())!=set(m['files']) or len(z.namelist())!=len(m['files']):
            raise ValueError('Missing/foreign407 historical source member')
        files={name:z.read(name) for name in m['files']}
    for name,b in files.items():
        if sha(b)!=m['files'][name]['working_SHA256']:raise ValueError('Changed407 historical member:'+name)
    return m,files


def restore_metadata032(root,destination):
    """Explicit accepted032 test checkout, not candidate033 or a portable gate."""
    root=Path(root).resolve();destination=Path(destination).resolve()
    if destination==root:raise ValueError('Refuse historical metadata in live source')
    m,files=read_sources(root)
    for name in m['metadata032']:
        path=destination/name
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(files[name])
