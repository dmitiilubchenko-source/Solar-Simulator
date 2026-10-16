"""Bounded sequential Horizons requests for the predeclared dense grid."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse

import numpy as np

from scripts.fetch_ephemerides import fetch, parse_result
from scripts.fetch_qualification_grid import epochs
from scripts.assess_sandbox_models import load_inputs
from solar_simulator.ephemerides import RESOLVED_IDS, SOURCE_URL

ROOT = Path(__file__).resolve().parents[1]
BATCH = 40  # Short URLs avoid the failed full-grid request; same epochs.


def request_url(body_id, grid):
    params = dict(format="json", COMMAND=f"'{body_id}'", OBJ_DATA="'NO'", MAKE_EPHEM="'YES'",
        EPHEM_TYPE="'VECTORS'", CENTER="'500@0'", TLIST="'"+" ".join(f"{jd:.12f}" for jd in grid)+"'",
        TLIST_TYPE="'JD'", REF_SYSTEM="'ICRF'", REF_PLANE="'ECLIPTIC'", VEC_CORR="'NONE'",
        VEC_TABLE="'2'", OUT_UNITS="'KM-S'", CSV_FORMAT="'YES'", TIME_TYPE="'TDB'")
    return SOURCE_URL+"?"+urllib.parse.urlencode(params)


def overlap(rows, previous):
    by_epoch = {row["jd_tdb"]:row for row in rows}
    position = velocity = 0.
    for old in previous["states"]:
        new = by_epoch[old["jd_tdb"]]
        position = max(position, float(np.linalg.norm(np.array(new["position"])-old["position"])))
        velocity = max(velocity, float(np.linalg.norm(np.array(new["velocity"])-old["velocity"])))
    if position > .01 or velocity > 1e-8:
        raise ValueError(f"Changed JPL overlap: {position}m {velocity}m/s")
    return position, velocity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError("Preserve existing reference")
    args.cache.mkdir(parents=True, exist_ok=True)
    initial, origin, _, base, moon = load_inputs()
    grid = epochs()
    bodies = []
    for body_id, body in zip(RESOLVED_IDS, initial):
        rows, requests = [], []
        for start in range(0, len(grid), BATCH):
            batch = grid[start:start+BATCH]
            url = request_url(body_id, batch)
            path = args.cache/f"horizons-{body_id}-{start:03d}.json"
            manifest = path.with_suffix(".request.json")
            if path.exists():
                if not manifest.exists():raise ValueError("Incomplete cached request provenance")
                record = json.loads(manifest.read_bytes())
                if record["url"] != url or record["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
                    raise ValueError("Cached request changed")
            else:
                if manifest.exists():raise ValueError("Cached request body missing")
                raw = fetch(url)
                # Reject errors, wrong frame/time/target/DE441 before archiving.
                parse_result(json.loads(raw), body_id, batch)
                path.write_bytes(raw)
                manifest.write_text(json.dumps(dict(url=url, sha256=hashlib.sha256(raw).hexdigest()), indent=2), encoding="utf-8")
            raw = path.read_bytes()
            rows.extend(parse_result(json.loads(raw), body_id, batch))
            requests.append(dict(request_url=url, response_sha256=hashlib.sha256(raw).hexdigest(),
                epochs_jd_tdb=batch))
            print(body.name, start+len(batch), "/", len(grid), flush=True)
        historic = moon if body.name in ("Earth", "Moon") else base
        previous = next(b for b in historic["bodies"] if b["name"] == body.name)
        position, velocity = overlap(rows, previous)
        bodies.append(dict(id=body_id, name=body.name, states=rows, requests=requests,
            overlap_position_metres=position, overlap_velocity_m_per_s=velocity))
    sources = ["scripts/fetch_dense_jpl.py", "scripts/fetch_ephemerides.py",
        "scripts/fetch_qualification_grid.py", "scripts/assess_sandbox_models.py"]
    result = dict(protocol="docs/qualification-extension-protocol.md", origin=asdict(origin), units="SI",
        epochs_jd_tdb=grid, bodies=bodies, fetched_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources},
        initial_dataset_changed=False, physical_parameters_fitted=False,
        request_batch=BATCH, requests_sequential=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")


if __name__ == "__main__":main()
