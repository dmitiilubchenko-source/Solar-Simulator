"""Reproduce the frozen Earth J2 profile from pinned official text sources."""
import argparse
import hashlib
import json
from math import cos, radians, sin
from pathlib import Path
import re

from solar_simulator.ephemerides import solar_system

if __package__:
    from .fetch_ephemerides import fetch
else:
    from fetch_ephemerides import fetch

HEADER_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de441/header.441"
HEADER_SHA = "376cd6f6766356ba0f4c25dc5a7ff8130ea2826f3c34149e33c1e6ac970d6e7c"
PCK_URL = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc"
PCK_SHA = "3dff7b1dbeceaa01f25467767d3fa25816051c85d162d1edf04acb310ee28bb1"


def decode_header(data):
    text = data.decode("ascii")
    names = text.split("GROUP   1040")[1].split("GROUP   1041")[0].split()
    values = text.split("GROUP   1041")[1].split("GROUP   1050")[0].split()
    if int(names[0]) != len(names)-1 or int(values[0]) != len(values)-1 or len(names) != len(values):
        raise ValueError("Invalid DE constant counts")
    constants = dict(zip(names[1:], (float(v.replace("D", "E")) for v in values[1:])))
    if len(constants) != len(names)-1 or constants["DENUM"] != 441:
        raise ValueError("Expected unique DE441 constants")
    return constants


def earth_pole(pck, epoch):
    # Read only kernel data blocks; prose contains obsolete assignments.
    text = "\n".join(part.split("\\begintext")[0] for part in pck.decode("ascii").split("\\begindata")[1:])
    def triple(name):
        matches = re.findall(r"\b"+name+r"\s*=\s*\(([^)]+)\)", text)
        if len(matches) != 1:
            raise ValueError("Expected one PCK pole assignment")
        values = [float(v.replace("D", "E")) for v in matches[0].split()]
        if len(values) != 3:
            raise ValueError("Expected quadratic pole polynomial")
        return values
    centuries = (epoch-2451545.0)/36525
    ra = sum(v*centuries**i for i, v in enumerate(triple("BODY399_POLE_RA")))
    dec = sum(v*centuries**i for i, v in enumerate(triple("BODY399_POLE_DEC")))
    a, d, eps = radians(ra), radians(dec), radians(84381.448/3600)
    equatorial = [cos(d)*cos(a), cos(d)*sin(a), sin(d)]
    x, y, z = equatorial
    axis = [x, cos(eps)*y+sin(eps)*z, -sin(eps)*y+cos(eps)*z]
    return axis, ra, dec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--output", default="src/solar_simulator/data/earth-j2-20261008.json")
    args = parser.parse_args()
    cache = Path(".tools")
    cache.mkdir(exist_ok=True)
    sources = []
    for url, expected, name in ((HEADER_URL, HEADER_SHA, "de441-header.txt"), (PCK_URL, PCK_SHA, "pck00011.tpc")):
        path = cache/name
        data = path.read_bytes() if args.cached else fetch(url)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("Official source has changed; review before updating pinned parameters")
        if not args.cached:
            path.write_bytes(data)
        sources.append(data)
    constants = decode_header(sources[0])
    bodies, origin = solar_system(resolved_moon=True)
    axis, ra, dec = earth_pole(sources[1], origin.epoch_jd_tdb)
    profile = dict(schema_version=1, model="fixed-axis-j2", body="Earth", units="SI",
        coefficient=constants["J2E"], reference_radius_metres=1000*constants["RE"], axis=axis,
        frame=origin.frame, epoch_jd_tdb=origin.epoch_jd_tdb, dataset_sha256=origin.dataset_sha256,
        bodies=[b.name for b in bodies], pole_ra_degrees=ra, pole_dec_degrees=dec,
        obliquity_arcsec=84381.448,
        sources=[dict(url=HEADER_URL, sha256=HEADER_SHA), dict(url=PCK_URL, sha256=PCK_SHA)],
        provenance=f"DE441 nominal J2E/RE ({HEADER_SHA}); IAU Earth pole pck00011 ({PCK_SHA}); frozen JD {origin.epoch_jd_tdb} TDB; Horizons obliquity 84381.448 arcsec",
        limitation="Constant nominal J2 and approximate IAU pole frozen at initial epoch; no precession/nutation evolution, secular J2 change, higher harmonics, lunar figure, spin dynamics or tides.",
        lunar_constants_not_enabled=dict(reference_radius_km=constants["AM"], J2M=constants["J2M"], C22M=constants["C22M"]))
    output = Path(args.output)
    output.write_text(json.dumps(profile, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(output, hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
