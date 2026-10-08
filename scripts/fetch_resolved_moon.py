"""Fetch Earth and Moon with the pinned GM kernel, frame and epoch.

Existing nine-body initial states remain byte-for-byte reproducible. A new
reference covers daily samples in the first month and the original year grid.
Sequential HTTPS requests only; raw responses stay in the local cache.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import urllib.parse

from solar_simulator.ephemerides import (SOURCE_URL, DATASET_NAME, RESOLVED_IDS,
    RESOLVED_DATASET_NAME, decode_snapshot, solar_system)
if __package__:
    from .fetch_ephemerides import EPOCH, EPOCHS, fetch, gm_values, parse_result
else:
    from fetch_ephemerides import EPOCH, EPOCHS, fetch, gm_values, parse_result

MOON_EPOCHS = sorted(set(EPOCHS+[EPOCH+i for i in range(1, 33)]))


def request_url(body_id):
    params=dict(format="json",COMMAND=f"'{body_id}'",OBJ_DATA="'NO'",MAKE_EPHEM="'YES'",
        EPHEM_TYPE="'VECTORS'",CENTER="'500@0'",TLIST="'"+" ".join(f"{jd:.12f}" for jd in MOON_EPOCHS)+"'",
        TLIST_TYPE="'JD'",REF_SYSTEM="'ICRF'",REF_PLANE="'ECLIPTIC'",VEC_CORR="'NONE'",
        VEC_TABLE="'2'",OUT_UNITS="'KM-S'",CSV_FORMAT="'YES'",TIME_TYPE="'TDB'")
    return SOURCE_URL+"?"+urllib.parse.urlencode(params)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache",type=Path,default=Path(".tools/jpl-moon-20261008"))
    parser.add_argument("--base-cache",type=Path,default=Path(".tools/jpl-20261008"))
    parser.add_argument("--base-reference",type=Path,default=Path("docs/solar-system-reference.json"))
    parser.add_argument("--output",type=Path,default=Path("src/solar_simulator/data")/RESOLVED_DATASET_NAME)
    parser.add_argument("--reference",type=Path,default=Path("docs/solar-system-moon-reference.json"))
    parser.add_argument("--cached",action="store_true")
    args=parser.parse_args()
    initial,origin=solar_system()
    base=json.loads(args.base_reference.read_text(encoding="utf-8"))
    if (base["dataset_sha256"]!=origin.dataset_sha256 or base["epochs_jd_tdb"]!=EPOCHS
            or base["frame"]!=origin.frame or base["center"]!=origin.center or base["ephemeris"]!=origin.ephemeris
            or base["units"]!="SI"):
        raise ValueError("Base reference does not match pinned initial states")
    gm_data=(args.base_cache/"gm_Horizons.pck").read_bytes()
    if hashlib.sha256(gm_data).hexdigest()!=origin.gm_sha256:
        raise ValueError("GM kernel differs from the original snapshot")
    gm=gm_values(gm_data,RESOLVED_IDS+(3,))
    if abs(gm[399]+gm[301]-gm[3])>gm[3]*1e-14:
        raise ValueError("Earth and Moon GM do not sum to the Earth-Moon system GM")
    args.cache.mkdir(parents=True,exist_ok=True)
    raw_records=[]
    # An explicit body-3 control checks the weighted Earth/Moon barycentre.
    for body_id,name in ((399,"Earth"),(301,"Moon"),(3,"Earth-Moon")):
        url=request_url(body_id)
        file=args.cache/f"horizons-{body_id}.json"
        if not args.cached:
            file.write_bytes(fetch(url))
        raw=file.read_bytes()
        rows=parse_result(json.loads(raw),body_id,MOON_EPOCHS)
        raw_records.append(dict(id=body_id,name=name,gm_m3_s2=gm[body_id],states=rows,
            response_sha256=hashlib.sha256(raw).hexdigest(),request_url=url))
        print(f"Validated {name}, {len(rows)} epochs",flush=True)
    earth,moon,emb=raw_records
    weight=gm[301]/gm[3]
    for e,m,b in zip(earth["states"],moon["states"],emb["states"]):
        for field,tolerance in (("position",0.01),("velocity",1e-8)):
            # Difference-based interpolation avoids adding two large coordinates.
            reconstructed=[x+weight*(y-x) for x,y in zip(e[field],m[field])]
            if max(abs(x-y) for x,y in zip(reconstructed,b[field]))>tolerance:
                raise ValueError("Resolved pair does not reproduce JPL Earth-Moon barycentre")
    old_snapshot=json.loads(files("solar_simulator.data").joinpath(DATASET_NAME).read_bytes())
    by_id={b["id"]:b for b in old_snapshot["bodies"]}
    for record in (earth,moon):
        by_id[record["id"]]=dict(id=record["id"],name=record["name"],gm_m3_s2=record["gm_m3_s2"],
            position=record["states"][0]["position"],velocity=record["states"][0]["velocity"])
    snapshot={key:value for key,value in old_snapshot.items() if key!="bodies"}
    snapshot["bodies"]=[by_id[i] for i in RESOLVED_IDS]
    data=(json.dumps(snapshot,indent=2,allow_nan=False)+"\n").encode()
    resolved,resolved_origin=decode_snapshot(data)
    # All other systems and their GM must remain identical to the base dataset.
    old={b.name:b for b in initial}
    for b in resolved:
        if b.name in old and (b.mass!=old[b.name].mass or b.position.distance_to(old[b.name].position)!=0
                             or b.velocity.distance_to(old[b.name].velocity)!=0):
            raise ValueError("Unrelated initial state changed")
    reference=dict(schema=1,generated_utc=datetime.now(timezone.utc).isoformat(),source=SOURCE_URL,
        dataset_sha256=resolved_origin.dataset_sha256,gm_sha256=origin.gm_sha256,
        base_dataset_sha256=origin.dataset_sha256,base_reference_sha256=hashlib.sha256(args.base_reference.read_bytes()).hexdigest(),
        frame=origin.frame,center=origin.center,ephemeris=origin.ephemeris,units="SI",
        epochs_jd_tdb=MOON_EPOCHS,bodies=raw_records)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.reference.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_bytes(data)
    args.reference.write_text(json.dumps(reference,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(f"Offline dataset: {args.output}; SHA256 {resolved_origin.dataset_sha256}")


if __name__=="__main__":
    main()
