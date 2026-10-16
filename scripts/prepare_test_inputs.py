"""Explicit restoration of seven public, byte-pinned research test inputs.

No trajectories are calculated here. Corrupted existing inputs are rejected.
The historical test/source/report fingerprints are deliberately unchanged.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PATHS=(".tools/rotation63/initial.json", ".tools/rotation57/rigid-pn-trajectories.npz",
       ".tools/rotation59/conditional-lunar-initial.json", ".tools/rotation62/production.npz",
       ".tools/rotation62/tighter.npz", ".tools/rotation62/reference-0.npz",
       ".tools/rotation62/reference-1.npz")


def restore(root=ROOT, *, bundle=None, manifest=None):
    root=Path(root).resolve()
    bundle=Path(bundle or ROOT/"tests/data/research63-inputs.zip")
    manifest=Path(manifest or ROOT/"tests/data/research63-inputs.json")
    document=json.loads(manifest.read_text(encoding="utf-8"))
    if (set(document)!={"kind","version","bundle_sha256","files","origin"}
            or document["kind"]!="solar-research63-test-inputs" or type(document["version"]) is not int
            or document["version"]!=1 or set(document["files"])!=set(PATHS)):
        raise ValueError("Unsupported public test-input manifest")
    if bundle.stat().st_size>2_000_000 or hashlib.sha256(bundle.read_bytes()).hexdigest()!=document["bundle_sha256"]:
        raise ValueError("Public test bundle SHA256 mismatch")
    payloads={}; missing=[]
    with zipfile.ZipFile(bundle) as archive:
        members=archive.infolist()
        if len(members)!=len(PATHS) or {m.filename for m in members}!=set(PATHS):
            raise ValueError("Unexpected public test bundle members")
        for member in members:
            if member.file_size>1_000_000:raise ValueError("Oversized test input")
            data=archive.read(member)
            expected=document["files"][member.filename]
            if hashlib.sha256(data).hexdigest()!=expected:raise ValueError("Test input SHA256 mismatch")
            path=(root/member.filename).resolve()
            if not path.is_relative_to(root):raise ValueError("Test input outside destination root")
            if path.exists():
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                    raise ValueError("Corrupted existing test input: "+member.filename)
            else:missing.append((path,data))
            payloads[member.filename]=expected
    for path,data in missing:
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("xb") as stream:stream.write(data)
    return dict(restored=len(missing),verified=len(payloads))


if __name__=="__main__":print(restore())
