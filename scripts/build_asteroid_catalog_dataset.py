"""Create a runtime initial-only supplement from the pinned SB441 catalogue."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from solar_simulator.perturbers import solar_system_asteroids_full, HEADER_URL
if __package__:
    from .fetch_asteroid_catalog import INITIAL_SHA, YEAR_MANIFEST_SHA, HEADER_SHA, CATALOG_SHA
    from .fetch_asteroid_data import ALL_IDENTITIES
else:
    from fetch_asteroid_catalog import INITIAL_SHA, YEAR_MANIFEST_SHA, HEADER_SHA, CATALOG_SHA
    from fetch_asteroid_data import ALL_IDENTITIES


def document():
    source=Path('docs/asteroids-343-initial.json')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=INITIAL_SHA:
        raise ValueError('Pinned source initial catalogue changed')
    data=json.loads(source.read_text(encoding='utf-8'))
    _,parent=solar_system_asteroids_full()
    if data['base_origin']!=asdict(parent):
        raise ValueError('Wrong runtime supplement parent')
    current={identity for identity,_,_ in ALL_IDENTITIES}
    added=[r for r in data['bodies'] if r['id'] not in current]
    if len(added)!=327 or len({r['id'] for r in added})!=327 or len({r['name'] for r in added})!=327:
        raise ValueError('Wrong missing asteroid identities')
    gm=hashlib.sha256((parent.gm_sha256+'\n'+HEADER_SHA+'\n').encode()).hexdigest()
    sources=[dict(url=HEADER_URL,sha256=HEADER_SHA),
        dict(url='https://ssd.jpl.nasa.gov/ftp/eph/small_bodies/asteroids_de441/SB441_IOM392R-21-005_perturbers.pdf',
             catalog_sha256=CATALOG_SHA),
        dict(url=data['source_url'],initial_catalogue_sha256=INITIAL_SHA,range_manifest_sha256=YEAR_MANIFEST_SHA)]
    return dict(schema=1,base_origin=asdict(parent),gm_sha256=gm,units='SI',
        vector_correction='NONE',sources=sources,bodies=added)


def main():
    doc=document()
    raw=(json.dumps(doc,indent=2,allow_nan=False)+'\n').encode('utf-8')
    path=Path('src/solar_simulator/data/asteroids-catalog-20261008.json')
    path.write_bytes(raw)
    print('dataset',hashlib.sha256(raw).hexdigest(),'GM',doc['gm_sha256'],'bytes',len(raw),
        'sources',hashlib.sha256(json.dumps(doc['sources'],sort_keys=True,separators=(',',':')).encode()).hexdigest())


if __name__=='__main__':
    main()
