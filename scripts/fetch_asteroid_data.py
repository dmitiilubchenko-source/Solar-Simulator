"""Extract a pinned year of SB441 type-2 records; runtime gets one epoch only.

About 12 KB (three bodies) or 48 KB (all 16) of the 616 MB kernel are fetched.
Every byte range is verified.
SB441 states are heliocentric J2000: add the independently checked DE441 Sun
and rotate once to the existing SSB Ecliptic J2000 frame. No fitted trajectory
is used by the simulator after initialization.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
from numpy.polynomial.chebyshev import chebval,chebder
from solar_simulator.perturbers import solar_system_pluto,solar_system_asteroids
if __package__:
    from .fetch_ephemerides import fetch
    from .fetch_pluto_data import decode_vectors,state,rotation,crosscheck_horizons,BASE_REFERENCE_SHA
    from .fetch_figure_profile import decode_header,HEADER_SHA,HEADER_URL
    from .fetch_orientation_data import SOURCE_SHA,URL,BYTE_START,BYTE_END
    from .fetch_resolved_moon import MOON_EPOCHS
else:
    from fetch_ephemerides import fetch
    from fetch_pluto_data import decode_vectors,state,rotation,crosscheck_horizons,BASE_REFERENCE_SHA
    from fetch_figure_profile import decode_header,HEADER_SHA,HEADER_URL
    from fetch_orientation_data import SOURCE_SHA,URL,BYTE_START,BYTE_END
    from fetch_resolved_moon import MOON_EPOCHS

MANIFEST_SHA='c2d2820326821927279e23f8388e147b6c7c28cd6c7940f61f6e33250cdc2395'
IDENTITIES=((2000001,'Ceres','MA0001'),(2000002,'Pallas','MA0002'),(2000004,'Vesta','MA0004'))
OTHER_IDENTITIES=tuple((2000000+number,name,f'MA{number:04d}') for number,name in (
    (3,'Juno'),(7,'Iris'),(10,'Hygiea'),(15,'Eunomia'),(16,'Psyche'),(31,'Euphrosyne'),
    (52,'Europa'),(65,'Cybele'),(87,'Sylvia'),(88,'Thisbe'),(107,'Camilla'),(511,'Davida'),(704,'Interamnia')))
ALL_IDENTITIES=IDENTITIES+OTHER_IDENTITIES
FULL_MANIFEST_SHA='ffb845a31c319cbc2e42d4f497095ae0d62e42ab254c7dbd556ad4a9f3de77f6'


def pinned_ranges(download=False,*,full=False):
    raw=Path(__file__).with_name('sb441-full-ranges.json' if full else 'sb441-ranges.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=(FULL_MANIFEST_SHA if full else MANIFEST_SHA):
        raise ValueError('SB441 source manifest changed')
    manifest=json.loads(raw)
    cache=Path('.tools/sb441');cache.mkdir(parents=True,exist_ok=True)
    result={}
    for entry in manifest['entries']:
        start,end=entry['byte_range'];role=entry['role'];path=cache/(role+'.bin')
        headers=cache/(role+'.headers')
        if download:
            subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https',
                '--max-time','45','--max-filesize',str(end-start+1),'--range',f'{start}-{end}',
                '--dump-header',str(headers),'--output',str(path),manifest['url']],check=True)
        value=path.read_bytes()
        if (len(value)!=end-start+1 or hashlib.sha256(value).hexdigest()!=entry['sha256']
                or f"bytes {start}-{end}/{manifest['total_bytes']}" not in headers.read_text()):
            raise ValueError(f'SB441 range changed: {role}')
        result[role]=value
    return manifest,result


def decode_segments(manifest,blocks,identities=IDENTITIES):
    """Validate DAF linkage, exact centre/frame/type and type-2 record addresses."""
    header=blocks['header']
    if header[:8]!=b'DAF/SPK ' or struct.unpack_from('<2i',header,8)!=(2,6) or header[88:96]!=b'LTL-IEEE':
        raise ValueError('Unsupported DAF format')
    entries={entry['role']:entry for entry in manifest['entries']}
    first=(manifest['epoch_jd_tdb']-2451545)*86400
    last=first+manifest['duration_seconds']
    r=struct.unpack_from('<i',header,76)[0];previous=0;seen=set();found={}
    while r:
        if r in seen: raise ValueError('Cyclic DAF summary chain')
        seen.add(r);block=blocks[f'summary-{r}']
        nex,prev,n=struct.unpack_from('<3d',block)
        if prev!=previous or not 0<=n<=25 or n!=int(n) or nex!=int(nex):
            raise ValueError('Invalid DAF summary')
        for j in range(int(n)):
            start,end=struct.unpack_from('<2d',block,24+j*40)
            body,center,frame,kind,a,z=struct.unpack_from('<6i',block,40+j*40)
            if body in [i[0] for i in identities] and start<=first and end>=last:
                if body in found or (center,frame,kind)!=(10,1,2):
                    raise ValueError('Ambiguous/unsupported asteroid segment')
                init,interval,size,count=struct.unpack('<4d',blocks[f'tail-{body}'])
                if size!=26 or count!=50000 or interval!=2764800 or a+int(size*count)+3!=z:
                    raise ValueError('Invalid type-2 directory')
                if entries[f'tail-{body}']['byte_range']!=[(z-4)*8,z*8-1]:
                    raise ValueError('DAF tail pointer mismatch')
                low=int((first-init)//interval);high=int((last-init)//interval)
                begin=(a-1+low*int(size))*8;finish=(a-1+(high+1)*int(size))*8-1
                if entries[f'records-{body}']['byte_range']!=[begin,finish]:
                    raise ValueError('DAF record pointer mismatch')
                records=np.frombuffer(blocks[f'records-{body}'],dtype='<f8').reshape(-1,int(size)).copy()
                expected=init+(np.arange(low,high+1)+.5)*interval
                if (not np.all(np.isfinite(records)) or not np.array_equal(records[:,0],expected)
                        or not np.all(records[:,1]==interval/2)):
                    raise ValueError('Invalid type-2 intervals')
                found[body]=records
        previous,r=r,int(nex)
    if set(found)!={i[0] for i in identities}: raise ValueError('Missing asteroids')
    return found


def heliocentric_state(records,jd):
    """SI state from Chebyshev positions; velocity is their analytic derivative."""
    et=(jd-2451545)*86400
    if not np.isfinite(et) or et<records[0,0]-records[0,1] or et>records[-1,0]+records[-1,1]:
        raise ValueError('Asteroid epoch outside pinned intervals')
    index=min(int((et-(records[0,0]-records[0,1]))/(2*records[0,1])),len(records)-1)
    record=records[index];x=(et-record[0])/record[1];coefficients=record[2:].reshape(3,-1)
    return np.concatenate(([chebval(x,c) for c in coefficients],
        [chebval(x,chebder(c))/record[1] for c in coefficients]))*1000


def barycentric_state(records,arrays,table,jd):
    vector=heliocentric_state(records,jd).reshape(2,3)@rotation().T
    return vector.ravel()+state(arrays,table,10,jd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached',action='store_true')
    parser.add_argument('--full',action='store_true',help='All 16 SB441 asteroids; preserve the existing 14-body parent')
    args=parser.parse_args()
    identities=ALL_IDENTITIES if args.full else IDENTITIES
    manifest,blocks=pinned_ranges(download=not args.cached,full=args.full)
    segments=decode_segments(manifest,blocks,identities)
    if not args.cached:
        Path('.tools/de441-header.txt').write_bytes(fetch(HEADER_URL))
        subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https',
            '--max-time','45','--max-filesize','2000000','--range',f'{BYTE_START}-{BYTE_END}',
            '--dump-header','.tools/de441-year.headers','--output','.tools/de441-year-records.txt',URL],check=True)
    header=Path('.tools/de441-header.txt').read_bytes();raw=Path('.tools/de441-year-records.txt').read_bytes()
    if hashlib.sha256(header).hexdigest()!=HEADER_SHA or hashlib.sha256(raw).hexdigest()!=SOURCE_SHA['range']:
        raise ValueError('Pinned DE441 header/Sun records changed')
    planet_path=Path('docs/solar-system-reference.json')
    if hashlib.sha256(planet_path.read_bytes()).hexdigest()!=BASE_REFERENCE_SHA:
        raise ValueError('Pinned Horizons comparison changed')
    arrays,table=decode_vectors(raw,header)
    crosscheck=crosscheck_horizons(arrays,table,json.loads(planet_path.read_text()))
    constants=decode_header(header);_,parent=(solar_system_asteroids if args.full else solar_system_pluto)()
    scale=(constants['AU']*1000)**3/86400**2
    gm_sha=hashlib.sha256((parent.gm_sha256+'\n'+HEADER_SHA+'\n').encode()).hexdigest()
    sources=[dict(url=HEADER_URL,sha256=HEADER_SHA),
        dict(url=URL,byte_range=[BYTE_START,BYTE_END],sha256=SOURCE_SHA['range'])]
    sources+=[dict(url=manifest['url'],byte_range=e['byte_range'],sha256=e['sha256']) for e in manifest['entries']]
    bodies=[];references=[]
    for identity,name,constant in identities:
        vector=barycentric_state(segments[identity],arrays,table,parent.epoch_jd_tdb)
        gm=constants[constant]*scale
        if not args.full or (identity,name,constant) in OTHER_IDENTITIES:
            bodies.append(dict(id=identity,name=name,gm_m3_s2=gm,position=vector[:3].tolist(),velocity=vector[3:].tolist()))
        references.append(dict(id=identity,name=name,gm_m3_s2=gm,states=[dict(jd_tdb=jd,
            position=barycentric_state(segments[identity],arrays,table,jd)[:3].tolist(),
            velocity=barycentric_state(segments[identity],arrays,table,jd)[3:].tolist()) for jd in MOON_EPOCHS]))
    supplement=dict(schema=1,base_origin=asdict(parent),gm_sha256=gm_sha,units='SI',vector_correction='NONE',sources=sources,bodies=bodies)
    output=Path('src/solar_simulator/data/'+('asteroids-full-20261008.json' if args.full else 'asteroids-20261008.json'))
    output.write_text(json.dumps(supplement,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    reference=dict(schema=1,dataset_sha256=digest,base_dataset_sha256=parent.dataset_sha256,gm_sha256=gm_sha,
        epoch_jd_tdb=parent.epoch_jd_tdb,frame=parent.frame,center=parent.center,ephemeris='SB441-N16 + DE441 Sun',
        units='SI',sources=sources,epochs_jd_tdb=MOON_EPOCHS,bodies=references,horizons_planet_crosscheck=crosscheck,
        limitation=('All 16 SB441 asteroids' if args.full else 'Three asteroids')+', nominal DE441 MA constants. SB441 trajectories are validation only, not runtime prescriptions. No Dawn-final asteroid fit is substituted.')
    ref=Path('docs/asteroids-full-reference.json' if args.full else 'docs/asteroids-reference.json');ref.write_text(json.dumps(reference,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('dataset',digest,'GM',gm_sha,'sources',hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
          'reference',hashlib.sha256(ref.read_bytes()).hexdigest(),flush=True)


if __name__=='__main__':
    main()
