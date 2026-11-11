"""Immutable407metadata ONLY; never a live runtime overlay."""
from pathlib import Path
import hashlib
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'tests/fixtures/metadata033-828c798.zip'
SHA='a1fe4cbdf213a6d97652a7d8e2108f584a1c0066ab8fcc5adb96bbc951b5c970'
MEMBERS={'pyproject.toml': 'f2ca791ae5b51b1f811f84dea21221333b6220b0776cb10614969689577405c5', 'rust/solar_core/Cargo.toml': '17af82fa9ed164f3c330ae83d6af29c7d9444d269a85f5ef13f061e82264f136', 'rust/solar_native/Cargo.toml': '27e51625e381c884f24f9d7e902881d65f07d6c358879f59da1319b0e7e00689', 'rust/solar_native/pyproject.toml': 'fa22135799f1473c149630444fe4b26356e970d851f68e4794d8e2ed1b54ea31', 'rust/solar_core/Cargo.lock': '853161d9d0557ad5e2189c9f29f654827eb3dadfe5601ecf5ba5eb57e99f2860', 'rust/solar_native/Cargo.lock': '45378a525e8c554723b068609f3cd08197a32f5231be07f4de33ced380ec28e9'}
def restore033(destination):
    destination=Path(destination).resolve()
    if destination==ROOT:raise ValueError('No historical overlay into live source')
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()!=SHA:raise ValueError('Historical033 archive SHA')
    with ZipFile(ARCHIVE) as z:
        if set(z.namelist())!=set(MEMBERS) or len(z.namelist())!=len(MEMBERS):raise ValueError('Historical033 members')
        files={n:z.read(n) for n in MEMBERS}
    if any(hashlib.sha256(b).hexdigest()!=MEMBERS[n] for n,b in files.items()):raise ValueError('Historical033 member SHA')
    for n,b in files.items():
        p=destination/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
