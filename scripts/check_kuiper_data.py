"""CSPICE source/frame/velocity oracle for all 30 KBOs, including record joins."""
import hashlib
import json
from pathlib import Path
import sys
import uuid

import numpy as np
sys.path.insert(0,str(Path('.tools/orientation-libs').resolve()))
import spiceypy as spice

if __package__:
    from .fetch_kuiper_data import inputs,year_blocks,decode_year,heliocentric_state,rotation,YEAR_MANIFEST_SHA,PACKED_SHA
    from .fetch_resolved_moon import MOON_EPOCHS
else:
    from fetch_kuiper_data import inputs,year_blocks,decode_year,heliocentric_state,rotation,YEAR_MANIFEST_SHA,PACKED_SHA
    from fetch_resolved_moon import MOON_EPOCHS


def main():
    rows,manifest,descriptors,_=inputs()
    records=decode_year(manifest,year_blocks(manifest),descriptors,{r['id'] for r in rows})
    folder=Path('.tools/sb441-kuiper');folder.mkdir(exist_ok=True)
    path=folder/('cspice-subset-'+uuid.uuid4().hex+'.bsp')
    handle=spice.spkopn(str(path.resolve()),'Original SB441 KBO year records',0)
    try:
        for row in rows:
            values=records[row['id']]
            start,end=values[0,0]-values[0,1],values[-1,0]+values[-1,1]
            spice.spkw02(handle,row['id'],10,'J2000',start,end,'SB441 original coefficients',
                2*values[0,1],len(values),7,values[:,2:].ravel(),start)
    finally:
        spice.spkcls(handle)
    transform=rotation()
    if not np.allclose(transform,spice.pxform('J2000','ECLIPJ2000',0.),rtol=0.,atol=2e-16):
        raise RuntimeError('CSPICE frame disagreement')
    results={}
    spice.furnsh(str(path.resolve()))
    try:
        for row in rows:
            values=records[row['id']]
            boundaries=(values[:,0]-values[:,1])/86400+2451545
            mids=values[:,0]/86400+2451545
            epochs=set(MOON_EPOCHS)
            for jd in np.concatenate((boundaries,mids)):
                for sample in (np.nextafter(jd,-np.inf),jd,np.nextafter(jd,np.inf)):
                    if MOON_EPOCHS[0]<=sample<=MOON_EPOCHS[-1]: epochs.add(float(sample))
            maximum=np.zeros(2)
            for jd in sorted(epochs):
                oracle,_=spice.spkgeo(row['id'],(jd-2451545)*86400,'ECLIPJ2000',10)
                actual=(heliocentric_state(values,jd).reshape(2,3)@transform.T).ravel()
                delta=actual-oracle*1000
                maximum=np.maximum(maximum,[np.linalg.norm(delta[:3]),np.linalg.norm(delta[3:])])
            if maximum[0]>.01 or maximum[1]>1e-8:
                raise RuntimeError(f'KBO/CSPICE disagreement: {row["name"]} {maximum}')
            results[row['name']]=dict(id=row['id'],samples=len(epochs),
                maximum_position_metres=float(maximum[0]),maximum_velocity_m_per_s=float(maximum[1]))
    finally:
        spice.unload(str(path.resolve()));path.unlink()
    report=dict(oracle='CSPICE spkgeo on original SB441-N373s coefficients; no shared Chebyshev evaluator',
        spiceypy=spice.__version__,manifest_sha256=YEAR_MANIFEST_SHA,packed_source_sha256=PACKED_SHA,
        bodies=results,body_count=len(results),samples=sum(r['samples'] for r in results.values()),
        maximum_position_metres=max(r['maximum_position_metres'] for r in results.values()),
        maximum_velocity_m_per_s=max(r['maximum_velocity_m_per_s'] for r in results.values()),
        record_boundaries_and_neighbours_included=True,checks_passed=True,
        code_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
            ('scripts/fetch_kuiper_data.py','scripts/check_kuiper_data.py','scripts/fetch_asteroid_catalog.py','scripts/fetch_asteroid_data.py')},
        limitation='Validates source decoding, analytic velocity and frame. Does not establish physical ephemeris accuracy or millimetre accuracy of a propagated orbit.')
    Path('docs/kuiper-source-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print({k:v for k,v in report.items() if k not in ('bodies','code_sha256')},flush=True)


if __name__=='__main__':
    main()
