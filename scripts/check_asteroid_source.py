"""Check SB441 extraction using CSPICE SPK type-2 interpolation and frames.

An offline subset kernel is built from the downloaded original coefficients;
CSPICE chooses records and differentiates them independently of NumPy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path('.tools/orientation-libs').resolve()))
import spiceypy as spice
if __package__:
    from .fetch_asteroid_data import pinned_ranges,decode_segments,barycentric_state,IDENTITIES,ALL_IDENTITIES,HEADER_SHA,SOURCE_SHA
    from .fetch_pluto_data import decode_vectors,segment
else:
    from fetch_asteroid_data import pinned_ranges,decode_segments,barycentric_state,IDENTITIES,ALL_IDENTITIES,HEADER_SHA,SOURCE_SHA
    from fetch_pluto_data import decode_vectors,segment


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--full',action='store_true');args=parser.parse_args()
    identities=ALL_IDENTITIES if args.full else IDENTITIES
    manifest,blocks=pinned_ranges(full=args.full);segments=decode_segments(manifest,blocks,identities)
    header=Path('.tools/de441-header.txt').read_bytes();raw=Path('.tools/de441-year-records.txt').read_bytes()
    if hashlib.sha256(header).hexdigest()!=HEADER_SHA or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA['range']:
        raise ValueError('Pinned DE441 Sun/header changed')
    arrays,table=decode_vectors(raw,header)
    reference_raw=Path('docs/asteroids-full-reference.json' if args.full else 'docs/asteroids-reference.json').read_bytes()
    if hashlib.sha256(reference_raw).hexdigest()!=('e74e59990cec890803095972c3141fde7c1caa289b8118b7613867f811e6ce2a' if args.full else 'eb8c0f3db89c5945e5a597ba59f0ccf40513696a97acf2722873af22fe66b6ff'):
        raise ValueError('Pinned SB441 validation states changed')
    reference=json.loads(reference_raw)
    path=Path('.tools/sb441/subset-full-oracle.bsp' if args.full else '.tools/sb441/subset-oracle.bsp')
    if path.exists(): path.unlink()
    handle=spice.spkopn(str(path.resolve()),'Pinned SB441 year subset',0)
    for identity,_,_ in identities:
        records=segments[identity];start=records[0,0]-records[0,1];end=records[-1,0]+records[-1,1]
        spice.spkw02(handle,identity,10,'J2000',start,end,'SB441 source subset',records[0,1]*2,len(records),7,records[:,2:].ravel(),start)
    spice.spkcls(handle)
    spice.furnsh(str(path.resolve()))
    transform=spice.pxform('J2000','ECLIPJ2000',0.)
    result={}
    try:
        for identity,name,_ in identities:
            records=segments[identity]
            boundaries=(records[:,0]-records[:,1])/86400+2451545
            epochs=sorted(set(reference['epochs_jd_tdb']+[float(jd) for jd in boundaries
                if reference['epochs_jd_tdb'][0]<=jd<=reference['epochs_jd_tdb'][-1]]))
            maximum=np.zeros(2)
            for jd in epochs:
                asteroid,_=spice.spkgeo(identity,(jd-2451545)*86400,'ECLIPJ2000',10)
                coefficients,midpoint,half=segment(arrays,table,10,jd)
                sun=np.array([spice.chbint(c,len(c)-1,[midpoint,half],jd) for c in coefficients])
                oracle=(asteroid+np.concatenate((transform@sun[:,0],transform@sun[:,1]/86400)))*1000
                actual=barycentric_state(records,arrays,table,jd)
                maximum=np.maximum(maximum,[np.linalg.norm(actual[:3]-oracle[:3]),np.linalg.norm(actual[3:]-oracle[3:])])
            if maximum[0]>.01 or maximum[1]>1e-8:
                raise RuntimeError(f'SB441/CSPICE mismatch: {name} {maximum}')
            result[name]=dict(samples=len(epochs),maximum_position_metres=float(maximum[0]),maximum_velocity_m_per_s=float(maximum[1]))
    finally:
        spice.unload(str(path.resolve()))
    report=dict(oracle='CSPICE spkgeo on subset SPK built from original SB441 type-2 coefficients; independent Sun chbint and pxform',
        spiceypy=spice.__version__,dataset_sha256=reference['dataset_sha256'],bodies=result,
        record_boundaries_included=True,downloaded_kernel_bytes=sum(len(b) for b in blocks.values()),
        full_kernel_bytes=manifest['total_bytes'],checks_passed=True,
        limitation='Interpolation/frame/derivative agreement validates extraction, not independent accuracy of the JPL asteroid ephemeris.')
    Path('docs/asteroids-full-source-validation.json' if args.full else 'docs/asteroids-source-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
