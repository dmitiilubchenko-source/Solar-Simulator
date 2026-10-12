"""Pinned SB441 initial states for 30 KBOs; future records are audit data only."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from solar_simulator.perturbers import solar_system_asteroids_catalog

if __package__:
    from .audit_perturbers import (CATALOG_SHA, MANIFEST_SHA, SOURCE_DIR,
        pinned_json, source_blocks, decode_inventory, validate_catalog)
    from .fetch_asteroid_catalog import decode_year
    from .fetch_asteroid_data import heliocentric_state
    from .fetch_figure_profile import HEADER_SHA, decode_header
    from .fetch_pluto_data import rotation
else:
    from audit_perturbers import (CATALOG_SHA, MANIFEST_SHA, SOURCE_DIR,
        pinned_json, source_blocks, decode_inventory, validate_catalog)
    from fetch_asteroid_catalog import decode_year
    from fetch_asteroid_data import heliocentric_state
    from fetch_figure_profile import HEADER_SHA, decode_header
    from fetch_pluto_data import rotation

YEAR_MANIFEST_SHA='e64668e4c375d262d197bda4d7e45ef7074c273288ae4f67d2562cc03d12c3da'
PACKED_SHA='c456421c59c9712f0d59ed2af749d1e5dd583000777b4e601e9a39a1260af267'


def inputs():
    catalog=pinned_json('de441-perturber-catalog.json',CATALOG_SHA)
    metadata=pinned_json('sb441-catalog-ranges.json',MANIFEST_SHA)
    manifest=pinned_json('sb441-kuiper-ranges.json',YEAR_MANIFEST_SHA)
    if (manifest['catalog_sha256']!=CATALOG_SHA or manifest['metadata_sha256']!=MANIFEST_SHA
            or manifest['url']!=metadata['url'] or manifest['total_bytes']!=metadata['total_bytes']
            or manifest['epoch_jd_tdb']!=2461321.5 or manifest['duration_seconds']!=31557600):
        raise ValueError('KBO source provenance mismatch')
    segments,_=decode_inventory(metadata,source_blocks(metadata),manifest['epoch_jd_tdb'],manifest['duration_seconds'])
    raw=(SOURCE_DIR/'validation/de441-header.441').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HEADER_SHA:
        raise ValueError('DE441 constants changed')
    constants=decode_header(raw)
    validate_catalog(constants,catalog,segments)
    rows=[r for r in catalog['bodies'] if r['group']=='kuiper-belt-object']
    if (len(rows)!=30 or len({r['id'] for r in rows})!=30 or len({r['name'] for r in rows})!=30
            or {r['constant'] for r in rows}!={f'MA80{i:02d}' for i in range(1,31)}
            or {r['id'] for r in rows}&{9,999,2134340}):
        raise ValueError('Incomplete/duplicate KBO group or Pluto counted again')
    return rows,manifest,segments,constants


def year_blocks(manifest, *, download=False):
    """Check every bounded range and its hash, optionally refetch from JPL."""
    packed=(SOURCE_DIR/'validation/sb441-kuiper-year.bin').read_bytes()
    if hashlib.sha256(packed).hexdigest()!=PACKED_SHA:
        raise ValueError('Pinned KBO coefficients changed')
    result={};offset=0
    for entry in manifest['entries']:
        role=entry['role'];first,last=entry['byte_range']
        if not 0<=first<=last<manifest['total_bytes'] or role in result:
            raise ValueError('Invalid/duplicate KBO source range')
        length=last-first+1
        raw=packed[offset:offset+length];offset+=length
        if len(raw)!=length or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise ValueError('KBO range hash mismatch: '+role)
        result[role]=raw
    if offset!=len(packed):
        raise ValueError('Extra/truncated KBO coefficient bytes')
    if download:
        cache=Path('.tools/sb441-kuiper');cache.mkdir(parents=True,exist_ok=True)
        def acquire(entry):
            role=entry['role'];first,last=entry['byte_range']
            path,headers=cache/(role+'.bin'),cache/(role+'.headers')
            subprocess.run(['curl.exe','--fail','--silent','--show-error','--proto','=https',
                '--max-time','45','--max-filesize',str(last-first+1),'--range',f'{first}-{last}',
                '--dump-header',str(headers),'--output',str(path),manifest['url']],check=True)
            raw=path.read_bytes()
            if (f"bytes {first}-{last}/{manifest['total_bytes']}" not in headers.read_text()
                    or len(raw)!=last-first+1 or hashlib.sha256(raw).hexdigest()!=entry['sha256']):
                raise ValueError('JPL KBO range mismatch: '+role)
            return role,raw
        with ThreadPoolExecutor(max_workers=4) as pool:
            result=dict(pool.map(acquire,manifest['entries']))
    return result


def initial_document(rows,manifest,constants,records):
    """One geometric epoch in the parent SSB frame, with unchanged parent bodies."""
    parent,origin=solar_system_asteroids_catalog()
    if (len(parent)!=354 or origin.epoch_jd_tdb!=manifest['epoch_jd_tdb']
            or set(records)!={r['id'] for r in rows} or {r['name'] for r in rows}&{b.name for b in parent}):
        raise ValueError('KBO epoch/identities/parent mismatch')
    sun=next(b for b in parent if b.name=='Sun')
    sun_state=np.array([sun.position.x,sun.position.y,sun.position.z,
        sun.velocity.x,sun.velocity.y,sun.velocity.z])
    transform=rotation();scale=(constants['AU']*1000)**3/86400**2
    bodies=[]
    for row in rows:
        state=(heliocentric_state(records[row['id']],origin.epoch_jd_tdb).reshape(2,3)@transform.T).ravel()+sun_state
        bodies.append(dict(id=row['id'],name=row['name'],gm_m3_s2=constants[row['constant']]*scale,
            position=state[:3].tolist(),velocity=state[3:].tolist()))
    return dict(schema=1,base_origin=asdict(origin),epoch_jd_tdb=origin.epoch_jd_tdb,
        frame=origin.frame,center=origin.center,units='SI',vector_correction='NONE',
        catalog_sha256=CATALOG_SHA,header_sha256=HEADER_SHA,range_manifest_sha256=YEAR_MANIFEST_SHA,
        packed_source_sha256=PACKED_SHA,source_url=manifest['url'],bodies=bodies,
        limitation='30 DE441 KBO point masses, separate from Pluto-System and the 36 ring masses. Parent states are not recentered. Runtime gets only one initial epoch; year records validate source reading and later free integration, never prescribe a trajectory. Individual KBO satellite motions are unresolved.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true')
    args=parser.parse_args(argv)
    rows,manifest,segments,constants=inputs()
    records=decode_year(manifest,year_blocks(manifest,download=args.download),segments,{r['id'] for r in rows})
    document=initial_document(rows,manifest,constants,records)
    raw=(json.dumps(document,indent=2,allow_nan=False)+'\n').encode('utf-8')
    Path('docs/kuiper-initial.json').write_bytes(raw)
    print('initial sha256',hashlib.sha256(raw).hexdigest(),'KBOs',len(document['bodies']),
        'source bytes',sum(e['byte_range'][1]-e['byte_range'][0]+1 for e in manifest['entries']),flush=True)


if __name__=='__main__':
    main()
