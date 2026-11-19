"""Audit existing snapshots with the packaged interpreter, without solver or GUI execution."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from solar_simulator.app import Laboratory
from solar_simulator.diagnostics import model_invariants
from solar_simulator.inspection import experimental_q2_warning
from solar_simulator.storage import load
from solar_simulator.vector3 import Vector3


class TextVariable:
    """Read the value set by the actual packaged GUI presentation method."""
    def __init__(self):
        self.value=""
    def set(self,value):
        self.value=value
    def get(self):
        return self.value


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root=Path.cwd().resolve()
fresh=Path(sys.argv[1])
old_root=Path(sys.argv[2])
assert sys.flags.isolated and Path(sys.prefix).resolve()==root/"runtime"
legacy=old_root/"accepted/one-q2-dop853-python/frame-1.json"
two_file=old_root/"two-q2.json"
legacy_sha="bdb3ec1147785014646a8656bc38a5762c85d0ad5fb6c3f9d127b2a70f18c1dc"
two_sha="a56269a82892b6dc740b309e77db2a085dca7ad3ed563e40e1964e3e66461055"
assert sha(legacy)==legacy_sha and sha(two_file)==two_sha
one=load(legacy)
two=load(two_file)
zero=load(root/"scenarios/spheres.json")
assert [len(item.rotations) for item in (zero,one,two)]==[0,1,2]
old_doc=json.loads(legacy.read_bytes())
assert old_doc["time"]==one.time and [x["name"] for x in old_doc["bodies"]]==[b.name for b in one.bodies]
warnings=[]
for model in (zero,one,two):
    view=SimpleNamespace(experiment=model,origin_info="",model_info=TextVariable())
    Laboratory._update_profile_info(view)
    warnings.append(view.model_info.get())
warning=experimental_q2_warning(two.rotations)
assert warning and warning in warnings[2] and warning not in warnings[0] and warning not in warnings[1]
assert "экспериментальная" in warning and "выпуск не разрешён" in warning
assert sha(legacy)==legacy_sha and sha(two_file)==two_sha
seed=load(root/"verification/initial.json")
physics,figures=seed.settings.physics,seed.settings.figures
energy0,_,_=model_invariants(seed.initial,physics,figures)
max_drift=0.
rows=0
with (fresh/"states.jsonl").open(encoding="utf8") as stream:
    for line in stream:
        state=json.loads(line)
        bodies=[replace(body,position=Vector3(*row[:3]),velocity=Vector3(*row[3:]))
                for body,row in zip(seed.bodies,state["states"],strict=True)]
        energy,_,_=model_invariants(bodies,physics,figures)
        max_drift=max(max_drift,abs(energy-energy0)/abs(energy0))
        rows+=1
claim=json.loads((fresh/"result.json").read_bytes())
assert rows==125 and max_drift==claim["energy_residual"]
print(json.dumps(dict(legacy_032_sha=legacy_sha,legacy_time=one.time,
    legacy_schema=old_doc["schema_version"],legacy_bodies=[b.name for b in one.bodies],
    two_q2_sha=two_sha,experimental_warning=warning,presentation_counts=[0,1,2],
    energy_residual_from_fresh_raw=max_drift,energy_rows=rows,
    scope="Read-only packaged storage, actual presentation method and energy diagnostics on saved states. No Tk window or integrator execution."),ensure_ascii=False))
