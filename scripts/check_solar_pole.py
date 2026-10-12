"""Optional independent CSPICE check of the pinned solar pole in ECLIPJ2000."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.tools/orientation-libs'))
import spiceypy as spice

from solar_simulator.oblateness import SOLAR_PROFILE_SHA256


def main():
    source=ROOT/'src/solar_simulator/data/solar-j2-20261008.json'
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOLAR_PROFILE_SHA256:
        raise ValueError('Solar profile changed')
    profile=json.loads(raw)
    pck=ROOT/'.tools/pck00011.tpc'
    if hashlib.sha256(pck.read_bytes()).hexdigest()!=profile['sources'][1]['sha256']:
        raise ValueError('Pinned NAIF kernel changed')
    samples=[]
    spice.furnsh(str(pck))
    try:
        for time in np.linspace(0,31557600,13):
            et=(profile['epoch_jd_tdb']-2451545)*86400+time
            matrix=spice.pxform('IAU_SUN','ECLIPJ2000',float(et))
            error=float(np.max(np.abs(matrix[:,2]-profile['axis'])))
            samples.append(dict(time_seconds=float(time),maximum_component_error=error))
    finally:
        spice.kclear()
    maximum=max(s['maximum_component_error'] for s in samples)
    if maximum>2e-14:
        raise RuntimeError(f'CSPICE solar pole mismatch: {maximum}')
    report=dict(oracle='CSPICE IAU_SUN -> ECLIPJ2000, third matrix column',spiceypy=spice.__version__,
        solar_profile_sha256=SOLAR_PROFILE_SHA256,pck_sha256=profile['sources'][1]['sha256'],
        maximum_component_error=maximum,samples=samples,checks_passed=True)
    (ROOT/'docs/solar-pole-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
