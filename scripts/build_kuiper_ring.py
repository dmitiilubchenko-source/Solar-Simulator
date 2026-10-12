"""Build initial-only ring supplements from pinned mass and explicit own policy."""
from dataclasses import asdict
import hashlib
import json
from math import cos, sin, pi, sqrt, fsum
from pathlib import Path

from solar_simulator.perturbers import solar_system_kuiper, HEADER_URL, HEADER_SHA256
from solar_simulator.simulation import G
from scripts.fetch_figure_profile import decode_header

ROOT=Path(__file__).resolve().parents[1]
POLICY_SHA256='73773129d24556b317c1a0c2796b060a610f8bd3eda0dff42c1457144062f006'


def parameters():
    raw=(ROOT/'scripts/validation/de441-header.441').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HEADER_SHA256:
        raise ValueError('Pinned DE441 ring mass source changed')
    constants=decode_header(raw)
    values=[constants[f'MA82{i:02d}'] for i in range(1,37)]
    if any(value<=0 or value!=values[0] for value in values):
        raise ValueError('36 equal positive residual ring masses required')
    scale=(constants['AU']*1000)**3/86400**2
    return constants['AU']*1000,fsum(values)*scale


def document(points,phase_index):
    """Use one snapshot; every original body and the Sun's SSB state stay intact."""
    if type(points) is not int or points not in (36,72,144) or type(phase_index) is not int or phase_index not in (0,1):
        raise ValueError('Ring policy supports 36/72/144 points and phases 0/1')
    initial,parent=solar_system_kuiper()
    sun=next(b for b in initial if b.name=='Sun')
    au,gm=parameters();radius=44*au;speed=sqrt(G*sun.mass/radius)
    policy=(ROOT/'scripts/kuiper-ring-policy.json').read_bytes()
    policy_sha=hashlib.sha256(policy).hexdigest()
    if policy_sha!=POLICY_SHA256:
        raise ValueError('Pinned own ring policy changed')
    entries=[]
    for i in range(points):
        angle=(2*i+phase_index)*pi/points;c,s=cos(angle),sin(angle)
        entries.append(dict(id=-(points*10000+phase_index*1000+i+1),
            name=f'Kuiper-Ring-{points:03d}-{phase_index}-{i+1:03d}',gm_m3_s2=gm/points,
            position=[sun.position.x+radius*c,sun.position.y+radius*s,sun.position.z],
            velocity=[sun.velocity.x-speed*s,sun.velocity.y+speed*c,sun.velocity.z]))
    sources=[dict(url=HEADER_URL,sha256=HEADER_SHA256,constants='MA8201-MA8236'),
        dict(url='https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf',section='2.2',radius_au=44),
        dict(own_policy_sha256=policy_sha,points=points,phase_index=phase_index,
            initial_states='own approximation; not DE441 ring states')]
    gm_digest=hashlib.sha256((parent.gm_sha256+'\n'+HEADER_SHA256+'\n'+policy_sha+'\n').encode()).hexdigest()
    return dict(schema=1,base_origin=asdict(parent),gm_sha256=gm_digest,units='SI',
        vector_correction='NONE',sources=sources,bodies=entries)


def main():
    manifest=dict(schema=1,own_policy_sha256=hashlib.sha256((ROOT/'scripts/kuiper-ring-policy.json').read_bytes()).hexdigest(),variants=[])
    for points in (36,72,144):
        for phase_index in (0,1):
            doc=document(points,phase_index)
            raw=(json.dumps(doc,indent=2,allow_nan=False)+'\n').encode()
            filename=f'kuiper-ring-{points:03d}-{phase_index}-20261011.json'
            (ROOT/'src/solar_simulator/data'/filename).write_bytes(raw)
            manifest['variants'].append(dict(points=points,phase_index=phase_index,filename=filename,
                dataset_sha256=hashlib.sha256(raw).hexdigest(),gm_sha256=doc['gm_sha256'],
                sources_sha256=hashlib.sha256(json.dumps(doc['sources'],sort_keys=True,separators=(',',':')).encode()).hexdigest()))
    raw=(json.dumps(manifest,indent=2)+'\n').encode()
    (ROOT/'src/solar_simulator/data/kuiper-ring-manifest.json').write_bytes(raw)
    print('manifest_sha256',hashlib.sha256(raw).hexdigest(),'total_gm',parameters()[1])


if __name__=='__main__':main()
