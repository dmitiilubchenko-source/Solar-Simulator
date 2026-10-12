"""Independent CSPICE interpolation of pinned DE441 Pluto coefficients."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
sys.path.insert(0,str(Path('.tools/orientation-libs').resolve()))
import spiceypy as spice
if __package__:
    from .fetch_pluto_data import decode_vectors,segment,state,HEADER_SHA,SOURCE_SHA
else:
    from fetch_pluto_data import decode_vectors,segment,state,HEADER_SHA,SOURCE_SHA


def main():
    header=Path('.tools/de441-header.txt').read_bytes()
    raw=Path('.tools/de441-year-records.txt').read_bytes()
    if hashlib.sha256(header).hexdigest()!=HEADER_SHA or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA['range']:
        raise ValueError('Pinned sources changed')
    arrays,table=decode_vectors(raw,header)
    reference=json.loads(Path('docs/pluto-reference.json').read_text())
    epochs=sorted(set(reference['epochs_jd_tdb']+[float(a[0]) for a in arrays]+[float(arrays[-1][1])]))
    transform=spice.pxform('J2000','ECLIPJ2000',0.)
    maximum=np.zeros(2)
    for jd in epochs:
        coefficients,midpoint,half=segment(arrays,table,9,jd)
        values=np.array([spice.chbint(c,len(c)-1,[midpoint,half],jd) for c in coefficients])
        oracle=np.concatenate((transform@values[:,0],transform@values[:,1]/86400))*1000
        actual=state(arrays,table,9,jd)
        maximum=np.maximum(maximum,[np.linalg.norm(actual[:3]-oracle[:3]),np.linalg.norm(actual[3:]-oracle[3:])])
    if maximum[0]>.01 or maximum[1]>1e-8:
        raise RuntimeError(f'DE441/CSPICE interpolation mismatch: {maximum}')
    report=dict(oracle='CSPICE chbint plus J2000 -> ECLIPJ2000',spiceypy=spice.__version__,
        dataset_sha256=reference['dataset_sha256'],header_sha256=HEADER_SHA,records_sha256=SOURCE_SHA['range'],
        samples=len(epochs),record_boundaries_included=True,maximum_position_metres=float(maximum[0]),
        maximum_velocity_m_per_s=float(maximum[1]),horizons_crosscheck=reference['horizons_crosscheck'],checks_passed=True)
    Path('docs/pluto-source-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
