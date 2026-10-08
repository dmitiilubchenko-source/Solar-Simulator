"""Independent CSPICE check of DE441 interpolation/rotation and its derivative.

Developer-only: install SpiceyPy into .tools/orientation-libs, never runtime.
Build a temporary PCK from the exact published DE441 Euler coefficients.
No planetary position kernels are used. The resulting numerical oracle is
stored in docs/orientation-spice-reference.json for dependency-free tests.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

from solar_simulator.orientation import (DURATION, EPOCH, PROFILE_SHA256,
                                         lunar_rotation, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/orientation-spice-reference.json")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(".tools/orientation-libs").resolve()))
    import spiceypy as spice
    data = profile()
    records = data["lunar_records"]
    coefficients = np.asarray([r["coefficients"] for r in records]).reshape(-1, 3, 10)
    start = (records[0]["start_jd_tdb"]-2451545.0)*86400
    end = (records[-1]["end_jd_tdb"]-2451545.0)*86400
    # Type 2 binary PCK stores the 3-1-3 Euler angles, not a text PCK's RA/DEC/W.
    results = []
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        pck = directory/"de441-extract.bpc"
        handle = spice.pckopn(str(pck), "DE441 exact orientation extract", 0)
        try:
            spice.pckw02(handle, 131441, "J2000", start, end, "DE441 lunar mantle", 8*86400,
                         len(coefficients), 9, coefficients.ravel(), start)
        finally:
            spice.pckcls(handle)
        fk = directory/"frame.tf"
        fk.write_text("KPL/FK\n\\begindata\n"
            "FRAME_SOLAR_DE441_PA = 131441\nFRAME_131441_NAME = 'SOLAR_DE441_PA'\n"
            "FRAME_131441_CLASS = 2\nFRAME_131441_CLASS_ID = 131441\n"
            "FRAME_131441_CENTER = 301\n\\begintext\n", encoding="ascii")
        spice.furnsh(str(fk)); spice.furnsh(str(pck))
        try:
            boundaries = [max(0., (r["start_jd_tdb"]+i*8-EPOCH)*86400)
                          for r in records for i in range(4)]
            times = sorted(set([0., DURATION, 12345.6789, DURATION/2]
                               + [t for t in boundaries if 0 <= t <= DURATION]))
            for time in times:
                state = spice.sxform("SOLAR_DE441_PA", "ECLIPJ2000", (EPOCH-2451545.0)*86400+time)
                rotation, derivative = lunar_rotation(time)
                results.append(dict(time_seconds=time, rotation=state[:3, :3].tolist(),
                                    derivative_per_second=state[3:, :3].tolist(),
                                    rotation_difference=float(np.max(abs(rotation-state[:3, :3]))),
                                    derivative_difference=float(np.max(abs(derivative-state[3:, :3])))))
        finally:
            spice.kclear()
    maximum = max(r["rotation_difference"] for r in results)
    rate_maximum = max(r["derivative_difference"] for r in results)
    print("rotation", maximum, "derivative/s", rate_maximum)
    if maximum > 3e-12 or rate_maximum > 1e-17:
        raise AssertionError("DE441 orientation disagrees with independent CSPICE")
    Path(args.output).write_text(json.dumps(dict(profile_sha256=PROFILE_SHA256,
        reference=spice.tkvrsn("TOOLKIT")+" via SpiceyPy "+spice.__version__+"; exact DE441 type-2 PCK extract",
        source="https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/cspice/pckw02_c.html",
        samples=results), indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
