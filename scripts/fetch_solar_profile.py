"""Reproduce the solar J2 profile from pinned DE441 and NAIF constants."""
import argparse
import hashlib
import json
from math import cos, radians, sin
from pathlib import Path
import re

from solar_simulator.ephemerides import solar_system
if __package__:
    from .fetch_ephemerides import fetch
    from .fetch_figure_profile import decode_header,HEADER_URL,HEADER_SHA,PCK_URL,PCK_SHA
else:
    from fetch_ephemerides import fetch
    from fetch_figure_profile import decode_header,HEADER_URL,HEADER_SHA,PCK_URL,PCK_SHA


def solar_pole(pck):
    data="\n".join(part.split("\\begintext")[0] for part in pck.decode("ascii").split("\\begindata")[1:])
    def constant(name):
        matches=re.findall(r"\b"+name+r"\s*=\s*\(([^)]+)\)",data)
        if len(matches)!=1:
            raise ValueError("Expected one solar pole assignment")
        values=[float(v.replace("D","E")) for v in matches[0].split()]
        if len(values)!=3 or values[1:]!=[0.,0.]:
            raise ValueError("The pinned solar pole must be constant")
        return values[0]
    ra,dec=constant("BODY10_POLE_RA"),constant("BODY10_POLE_DEC")
    a,d,eps=map(radians,(ra,dec,84381.448/3600))
    x,y,z=cos(d)*cos(a),cos(d)*sin(a),sin(d)
    return [x,cos(eps)*y+sin(eps)*z,-sin(eps)*y+cos(eps)*z],ra,dec


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached",action="store_true")
    parser.add_argument("--output",default="src/solar_simulator/data/solar-j2-20261008.json")
    args=parser.parse_args()
    cache=Path(".tools"); cache.mkdir(exist_ok=True)
    data=[]
    for url,sha,name in ((HEADER_URL,HEADER_SHA,"de441-header.txt"),(PCK_URL,PCK_SHA,"pck00011.tpc")):
        path=cache/name
        raw=path.read_bytes() if args.cached else fetch(url)
        if hashlib.sha256(raw).hexdigest()!=sha:
            raise ValueError("Pinned official source changed; review before updating")
        if not args.cached:
            path.write_bytes(raw)
        data.append(raw)
    constants=decode_header(data[0])
    axis,ra,dec=solar_pole(data[1])
    _,origin=solar_system(resolved_moon=True)
    _,other=solar_system()
    profile=dict(schema_version=1,model="fixed-axis-j2",body="Sun",units="SI",
        coefficient=constants["J2SUN"],reference_radius_metres=constants["ASUN"]*1000,axis=axis,
        frame=origin.frame,center=origin.center,epoch_jd_tdb=origin.epoch_jd_tdb,
        dataset_sha256=[other.dataset_sha256,origin.dataset_sha256],gm_sha256=origin.gm_sha256,
        pole_ra_degrees=ra,pole_dec_degrees=dec,obliquity_arcsec=84381.448,
        sources=[dict(url=HEADER_URL,sha256=HEADER_SHA),dict(url=PCK_URL,sha256=PCK_SHA)],
        provenance=f"DE441 J2SUN/ASUN ({HEADER_SHA}); NAIF pck00011 solar pole ({PCK_SHA}); fixed Ecliptic J2000 axis; unnormalized J2",
        limitation="Solar J2 only, with fixed pole and source reaction. No solar spin evolution, Lense-Thirring acceleration, mass loss, higher harmonics or mixed figure/1PN terms. DE441 ASUN is the reference radius for this J2, not the current nominal photospheric radius.")
    output=Path(args.output)
    output.write_text(json.dumps(profile,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(output,hashlib.sha256(output.read_bytes()).hexdigest())


if __name__=="__main__":
    main()
