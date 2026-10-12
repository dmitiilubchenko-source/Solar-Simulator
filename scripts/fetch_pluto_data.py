"""Extract Pluto-system initial state from pinned DE441 ASCII records.

Future vectors are exported only to a validation document, never runtime data.
Other initial bodies remain byte-for-byte values of the resolved Moon snapshot.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from math import cos, sin, radians
from pathlib import Path
import re
import subprocess

import numpy as np
from numpy.polynomial.chebyshev import chebval, chebder
from solar_simulator.ephemerides import solar_system
if __package__:
    from .fetch_figure_profile import HEADER_URL, HEADER_SHA, decode_header
    from .fetch_ephemerides import fetch
    from .fetch_orientation_data import URL, SOURCE_SHA, BYTE_START, BYTE_END, parse_records
    from .fetch_resolved_moon import MOON_EPOCHS
else:
    from fetch_figure_profile import HEADER_URL, HEADER_SHA, decode_header
    from fetch_ephemerides import fetch
    from fetch_orientation_data import URL, SOURCE_SHA, BYTE_START, BYTE_END, parse_records
    from fetch_resolved_moon import MOON_EPOCHS

BASE_REFERENCE_SHA = "aad15839a53f1c709c0e84a8202ffc4f9b6d13837f2bdeed2d28abb4c2ed6995"
COLUMNS = {1:0, 2:1, 3:2, 4:3, 5:4, 6:5, 7:6, 8:7, 9:8, 10:10}


def decode_vectors(raw, header):
    """Verify record sequence/coverage before reading 1-based DE pointers."""
    validated=parse_records(raw,header)
    table=np.array([list(map(int,row.split())) for row in
        header.decode('ascii').split('GROUP   1050')[1].split('GROUP   1070')[0].strip().splitlines()])
    if tuple(table[:,8])!=(423,6,1):
        raise ValueError('Unexpected DE441 Pluto layout')
    tokens=raw.decode('ascii').split()
    arrays=[]
    offset=0
    for record in validated:
        count=int(tokens[offset+1]); offset+=2
        values=np.array([float(v.replace('D','E')) for v in tokens[offset:offset+count]])
        offset+=count
        if tuple(values[:2])!=(record['start_jd_tdb'],record['end_jd_tdb']):
            raise ValueError('Inconsistent DE record')
        arrays.append(values)
    return arrays,table


def segment(arrays,table,body_id,jd):
    if not np.isfinite(jd) or jd<arrays[0][0] or jd>arrays[-1][1]:
        raise ValueError('DE epoch outside pinned record coverage')
    # Pick the record to the right at an internal boundary; no extrapolation.
    record=next((a for a in arrays if a[0]<=jd<a[1]),arrays[-1])
    pointer,count,subdivisions=table[:,COLUMNS[body_id]]
    width=(record[1]-record[0])/subdivisions
    index=min(int((jd-record[0])/width),subdivisions-1)
    midpoint=record[0]+(index+.5)*width
    first=pointer-1+index*3*count
    if first<2 or first+3*count>len(record):
        raise ValueError('DE pointer outside record')
    return record[first:first+3*count].reshape(3,count),float(midpoint),float(width/2)


def rotation():
    eps=radians(84381.448/3600)
    return np.array([[1.,0.,0.],[0.,cos(eps),sin(eps)],[0.,-sin(eps),cos(eps)]])


def state(arrays,table,body_id,jd):
    coefficients,midpoint,half=segment(arrays,table,body_id,jd)
    x=(jd-midpoint)/half
    positions=np.array([chebval(x,c) for c in coefficients])
    velocities=np.array([chebval(x,chebder(c))/half/86400 for c in coefficients])
    transform=rotation()
    return np.concatenate((transform@positions,transform@velocities))*1000


def crosscheck_horizons(arrays,table,reference):
    """Existing independent Horizons responses verify frame, scale and columns."""
    results={}
    for body in reference['bodies']:
        actual=np.array([state(arrays,table,body['id'],jd) for jd in reference['epochs_jd_tdb']])
        expected=np.array([s['position']+s['velocity'] for s in body['states']])
        difference=actual-expected
        results[body['name']]=dict(maximum_position_metres=float(np.max(np.linalg.norm(difference[:,:3],axis=1))),
            maximum_velocity_m_per_s=float(np.max(np.linalg.norm(difference[:,3:],axis=1))))
    if any(v['maximum_position_metres']>.01 or v['maximum_velocity_m_per_s']>1e-8 for v in results.values()):
        raise ValueError(f'DE ASCII/Horizons mismatch: {results}')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('src/solar_simulator/data/pluto-system-20261008.json'))
    parser.add_argument('--reference',type=Path,default=Path('docs/pluto-reference.json'))
    args=parser.parse_args()
    cache=Path('.tools'); cache.mkdir(exist_ok=True)
    if not args.cached:
        (cache/'de441-header.txt').write_bytes(fetch(HEADER_URL))
        subprocess.run(['curl.exe','--fail','--silent','--show-error','--max-time','45','--proto','=https',
            '--max-filesize','2000000','--range',f'{BYTE_START}-{BYTE_END}','--dump-header',
            str(cache/'de441-year.headers'),'--output',str(cache/'de441-year-records.txt'),URL],check=True)
    header=(cache/'de441-header.txt').read_bytes()
    raw=(cache/'de441-year-records.txt').read_bytes()
    response=(cache/'de441-year.headers').read_text()
    if (hashlib.sha256(header).hexdigest()!=HEADER_SHA or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA['range']
        or len(raw)!=BYTE_END-BYTE_START+1 or not re.search(r'HTTP/\S+ 206',response)
        or f'bytes {BYTE_START}-{BYTE_END}/306161715' not in response):
        raise ValueError('Pinned DE441 source/range changed')
    reference_file=Path('docs/solar-system-reference.json')
    if hashlib.sha256(reference_file.read_bytes()).hexdigest()!=BASE_REFERENCE_SHA:
        raise ValueError('Pinned Horizons reference changed')
    arrays,table=decode_vectors(raw,header)
    horizons=crosscheck_horizons(arrays,table,json.loads(reference_file.read_text()))
    constants=decode_header(header)
    initial,origin=solar_system(resolved_moon=True)
    gm=constants['GM9']*(constants['AU']*1000)**3/86400**2
    vector=state(arrays,table,9,origin.epoch_jd_tdb)
    composite_gm=hashlib.sha256((origin.gm_sha256+'\n'+HEADER_SHA+'\n').encode('ascii')).hexdigest()
    sources=[dict(url=HEADER_URL,sha256=HEADER_SHA),dict(url=URL,byte_range=[BYTE_START,BYTE_END],sha256=SOURCE_SHA['range'])]
    supplement=dict(schema=1,base_origin=asdict(origin),gm_sha256=composite_gm,
        units='SI',vector_correction='NONE',sources=sources,
        bodies=[dict(id=9,name='Pluto-System',gm_m3_s2=gm,position=vector[:3].tolist(),velocity=vector[3:].tolist())])
    data=(json.dumps(supplement,indent=2,allow_nan=False)+'\n').encode('utf-8')
    args.output.write_bytes(data)
    reference=dict(schema=1,dataset_sha256=hashlib.sha256(data).hexdigest(),gm_sha256=composite_gm,
        base_dataset_sha256=origin.dataset_sha256,epoch_jd_tdb=origin.epoch_jd_tdb,
        frame=origin.frame,center=origin.center,ephemeris=origin.ephemeris,units='SI',sources=sources,
        epochs_jd_tdb=MOON_EPOCHS,bodies=[dict(id=9,name='Pluto-System',gm_m3_s2=gm,
            states=[dict(jd_tdb=jd,position=state(arrays,table,9,jd)[:3].tolist(),
                         velocity=state(arrays,table,9,jd)[3:].tolist()) for jd in MOON_EPOCHS])],
        horizons_crosscheck=horizons,base_reference_sha256=BASE_REFERENCE_SHA,
        limitation='Pluto system barycentre, not resolved satellites. Future DE441 vectors are validation only; runtime integrates from a single initial state.')
    args.reference.write_text(json.dumps(reference,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('Supplement SHA256',reference['dataset_sha256'],'composite GM SHA256',composite_gm,flush=True)
    print('Horizons crosscheck',horizons,flush=True)


if __name__=='__main__':
    main()
