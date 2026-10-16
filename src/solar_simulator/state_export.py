"""An orbital CSV slice with explicit units and checkpoint provenance."""
import csv
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .storage import to_document


def export_state(experiment,path):
    document=to_document(experiment)
    canonical=json.dumps(document,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
    digest=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    origin=experiment.origin
    metadata=dict(checkpoint_sha256=digest,time_seconds=experiment.time,
        epoch_jd_tdb=origin.epoch_jd_tdb+experiment.time/86400 if origin else "",
        time_scale="TDB" if origin else "elapsed SI seconds",
        frame=origin.frame if origin else "user-defined inertial",
        center=origin.center if origin else "unspecified user origin",
        scope="orbital slice; rotations, events and history remain in checkpoint JSON",
        settings_json=json.dumps(asdict(experiment.settings),ensure_ascii=False,allow_nan=False,separators=(",",":")))
    fields=list(metadata)+["name","mass_kg","radius_m","x_m","y_m","z_m","vx_m_s","vy_m_s","vz_m_s"]
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",newline="",dir=path.parent,
                                          prefix=".solar-csv-",suffix=".tmp",delete=False) as stream:
            temporary=Path(stream.name);writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            for body in experiment.bodies:
                writer.writerow(dict(metadata,name=body.name,mass_kg=body.mass,radius_m=body.radius,
                    x_m=body.position.x,y_m=body.position.y,z_m=body.position.z,
                    vx_m_s=body.velocity.x,vy_m_s=body.velocity.y,vz_m_s=body.velocity.z))
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
    return digest
