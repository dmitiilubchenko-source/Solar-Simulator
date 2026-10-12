"""Create an initial-only runtime supplement, preserving the 354-body parent."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from solar_simulator.perturbers import solar_system_asteroids_catalog, HEADER_URL
if __package__:
    from .fetch_kuiper_data import YEAR_MANIFEST_SHA,PACKED_SHA,HEADER_SHA,CATALOG_SHA
else:
    from fetch_kuiper_data import YEAR_MANIFEST_SHA,PACKED_SHA,HEADER_SHA,CATALOG_SHA

INITIAL_SHA='2d2454c8b5a04382779991151fdb3475b5f63512325b5bde3708b476cbcf3bda'


def document():
    raw=Path('docs/kuiper-initial.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=INITIAL_SHA:
        raise ValueError('Pinned KBO initial catalogue changed')
    data=json.loads(raw)
    bodies,parent=solar_system_asteroids_catalog()
    if (data['base_origin']!=asdict(parent) or data['range_manifest_sha256']!=YEAR_MANIFEST_SHA
            or data['packed_source_sha256']!=PACKED_SHA or len(data['bodies'])!=30
            or {r['name'] for r in data['bodies']}&{b.name for b in bodies}
            or {r['id'] for r in data['bodies']}&{9,999,2134340}):
        raise ValueError('KBO supplement parent/identities mismatch')
    gm=hashlib.sha256((parent.gm_sha256+'\n'+HEADER_SHA+'\n').encode()).hexdigest()
    sources=[dict(url=HEADER_URL,sha256=HEADER_SHA),
        dict(url='https://ssd.jpl.nasa.gov/ftp/eph/small_bodies/asteroids_de441/SB441_IOM392R-21-005_perturbers.pdf',
            catalog_sha256=CATALOG_SHA),
        dict(url=data['source_url'],initial_catalogue_sha256=INITIAL_SHA,range_manifest_sha256=YEAR_MANIFEST_SHA)]
    return dict(schema=1,base_origin=asdict(parent),gm_sha256=gm,units='SI',vector_correction='NONE',
        sources=sources,bodies=data['bodies'])


def main():
    doc=document();raw=(json.dumps(doc,indent=2,allow_nan=False)+'\n').encode('utf-8')
    Path('src/solar_simulator/data/kuiper-20261010.json').write_bytes(raw)
    print('dataset',hashlib.sha256(raw).hexdigest(),'GM',doc['gm_sha256'],'bytes',len(raw),
        'sources',hashlib.sha256(json.dumps(doc['sources'],sort_keys=True,separators=(',',':')).encode()).hexdigest())


if __name__=='__main__':
    main()
