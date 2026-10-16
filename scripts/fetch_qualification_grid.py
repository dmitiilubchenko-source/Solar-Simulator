"""Fetch a predeclared denser DE441 grid; never overwrite the initial dataset."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse

from scripts.fetch_ephemerides import fetch, parse_result
from scripts.assess_sandbox_models import load_inputs
from solar_simulator.ephemerides import RESOLVED_IDS, SOURCE_URL

ROOT = Path(__file__).resolve().parents[1]


def epochs():
    _, origin, times, _, _ = load_inputs()
    days = sorted(set([i*.5 for i in range(65)]+list(range(35, 366, 7))+
        [float(t)/86400 for t in times]+[365.25]))
    return [origin.epoch_jd_tdb+d for d in days]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT/".tools/qualification138/jpl")
    parser.add_argument("--output", type=Path, default=ROOT/"docs/qualification-grid-reference.json")
    parser.add_argument("--cached", action="store_true")
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError("Preserve prior reference")
    args.cache.mkdir(parents=True, exist_ok=True)
    initial, origin, _, base, moon = load_inputs()
    grid = epochs()
    bodies = []
    for body_id, body in zip(RESOLVED_IDS, initial):
        params = dict(format="json", COMMAND=f"'{body_id}'", OBJ_DATA="'NO'", MAKE_EPHEM="'YES'",
            EPHEM_TYPE="'VECTORS'", CENTER="'500@0'", TLIST="'"+" ".join(f"{jd:.12f}" for jd in grid)+"'",
            TLIST_TYPE="'JD'", REF_SYSTEM="'ICRF'", REF_PLANE="'ECLIPTIC'", VEC_CORR="'NONE'",
            VEC_TABLE="'2'", OUT_UNITS="'KM-S'", CSV_FORMAT="'YES'", TIME_TYPE="'TDB'")
        url = SOURCE_URL+"?"+urllib.parse.urlencode(params)
        path = args.cache/f"horizons-{body_id}.json"
        if not args.cached:
            if path.exists():raise FileExistsError("Use --cached to reuse an existing response")
            path.write_bytes(fetch(url))
        raw = path.read_bytes()
        rows = parse_result(json.loads(raw), body_id, grid)
        historic = moon if body.name in ("Earth", "Moon") else base
        previous = next(b for b in historic["bodies"] if b["name"] == body.name)
        by_epoch = {row["jd_tdb"]:row for row in rows}
        max_position = max_velocity = 0.
        import numpy as np
        for old in previous["states"]:
            new = by_epoch[old["jd_tdb"]]
            max_position = max(max_position, float(np.linalg.norm(np.array(new["position"])-old["position"])))
            max_velocity = max(max_velocity, float(np.linalg.norm(np.array(new["velocity"])-old["velocity"])))
        if max_position > .01 or max_velocity > 1e-8:
            raise ValueError(f"JPL overlap changed: {body.name} {max_position}m {max_velocity}m/s")
        bodies.append(dict(id=body_id, name=body.name, states=rows, request_url=url,
            response_sha256=hashlib.sha256(raw).hexdigest(),
            overlap_position_metres=max_position, overlap_velocity_m_per_s=max_velocity))
        print(body.name, len(rows), "epochs; overlap", max_position, max_velocity, flush=True)
    from dataclasses import asdict
    result = dict(protocol="docs/qualification-extension-protocol.md", origin=asdict(origin),
        units="SI", epochs_jd_tdb=grid, bodies=bodies,
        fetched_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        initial_dataset_changed=False, physical_parameters_fitted=False)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")


if __name__ == "__main__":main()
