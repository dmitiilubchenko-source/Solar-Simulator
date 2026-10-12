"""Pinned additional DE441 bodies; no runtime trajectory interpolation."""
from dataclasses import dataclass, asdict, replace
import hashlib
from importlib.resources import files
import json
from math import isfinite

from .ephemerides import EphemerisOrigin, solar_system
from .simulation import Body, G
from .vector3 import Vector3

PLUTO_DATASET_SHA256 = "778ea14fa0377bd946f1e6dd52cce4ae7df318f32f070c1d5c6fa5701bf1de76"
PLUTO_GM_SHA256 = "b91c73997ba197141157f56134fd37c56d7a3f6b7c7542fbbb3146ef0623603c"
BASE_DATASET_SHA256 = "d58227299b10b217246aa5c63f33da51b0fd331b5c7a75bee400d577d6d1f702"
BASE_GM_SHA256 = "169cfed3b0927e73929d0a1b5c931f9afb5167a83b921064127ffc54a673df0c"
HEADER_SHA256 = "376cd6f6766356ba0f4c25dc5a7ff8130ea2826f3c34149e33c1e6ac970d6e7c"
RECORD_SHA256 = "1699167f07cf3ec4ee5d5827b99e2ada335ccb32b5ddec939c24eb50f81a21ab"
HEADER_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de441/header.441"
RECORD_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/ascii/de441/ascp02000.441"
ASTEROIDS_DATASET_SHA256 = "9e0cab041d7417daaa1a7235b034e1cdce913850cb8f3e1d92b5690748008a7e"
ASTEROIDS_GM_SHA256 = "96b099179df4afa33220fb0adb58aadff75fd54a12d4e77511e63f2ed0d54468"

ASTEROIDS_FULL_DATASET_SHA256 = 'ac6cbb16469320d017cb1ed07be4c836d380d6b715590f115f5ffcd75efb2394'
ASTEROIDS_FULL_GM_SHA256 = 'f93053a476eca58623aa0a2d5b34828543fcee54a8a5a9c86cdd4b091bd8d114'

@dataclass(frozen=True)
class SupplementSpec:
    """Data contract shared by planets, satellites and asteroid additions."""
    filename: str
    dataset_sha256: str
    gm_sha256: str
    parent_dataset_sha256: str
    parent_gm_sha256: str
    sources_sha256: str
    identities: tuple[tuple[int, str], ...]


def _sources_digest(sources):
    return hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest()


PLUTO_SPEC = SupplementSpec('pluto-system-20261008.json',PLUTO_DATASET_SHA256,PLUTO_GM_SHA256,
    BASE_DATASET_SHA256,BASE_GM_SHA256,_sources_digest([dict(url=HEADER_URL,sha256=HEADER_SHA256),
        dict(url=RECORD_URL,byte_range=[8180405,8529077],sha256=RECORD_SHA256)]),((9,'Pluto-System'),))
ASTEROIDS_SPEC = SupplementSpec('asteroids-20261008.json',ASTEROIDS_DATASET_SHA256,ASTEROIDS_GM_SHA256,
    PLUTO_DATASET_SHA256,PLUTO_GM_SHA256,'7d271ca4261e9b3c466d485824e4dac1844a93410713853476a7b093cb8bf4a0',
    ((2000001,'Ceres'),(2000002,'Pallas'),(2000004,'Vesta')))
ASTEROIDS_FULL_SPEC = SupplementSpec('asteroids-full-20261008.json',ASTEROIDS_FULL_DATASET_SHA256,ASTEROIDS_FULL_GM_SHA256,
    ASTEROIDS_DATASET_SHA256,ASTEROIDS_GM_SHA256,'8ecf73cd18a4e61ad07eac7ad51d6b58bc5b32359ab25a11d47a1ba7d5f9293c',
    tuple((2000000+number,name) for number,name in ((3,'Juno'),(7,'Iris'),(10,'Hygiea'),(15,'Eunomia'),
        (16,'Psyche'),(31,'Euphrosyne'),(52,'Europa'),(65,'Cybele'),(87,'Sylvia'),(88,'Thisbe'),
        (107,'Camilla'),(511,'Davida'),(704,'Interamnia'))))
ASTEROIDS_CATALOG_DATASET_SHA256 = '5df76143a986ebe0d540b936b08e6e38c17577c851ad2d19a34c25a6a1ea98ad'
ASTEROIDS_CATALOG_GM_SHA256 = 'dfe52a636c1d74311dc3fc7b9e5abda68814afabee21324772072c2d0c4f531b'


def _catalog_spec():
    filename='asteroids-catalog-20261008.json'
    raw=files('solar_simulator.data').joinpath(filename).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ASTEROIDS_CATALOG_DATASET_SHA256:
        raise ValueError('Изменено закреплённое дополнение 343 астероидов')
    identities=tuple((r['id'],r['name']) for r in json.loads(raw)['bodies'])
    return SupplementSpec(filename,ASTEROIDS_CATALOG_DATASET_SHA256,ASTEROIDS_CATALOG_GM_SHA256,
        ASTEROIDS_FULL_DATASET_SHA256,ASTEROIDS_FULL_GM_SHA256,
        'ea3f0ff56014174369f5dcdeb1036029769cf54437b29c5276a0874645486ff9',identities)


ASTEROIDS_CATALOG_SPEC = _catalog_spec()
KUIPER_DATASET_SHA256 = '22bc4852169214a14f2375c89ed2cb6e443ebb649a69ad792c69457d4a70d856'
KUIPER_GM_SHA256 = 'cc3d3e7d8492230ef0ce52d530531c0d7a5a8abfbf5d75e3a49e814b7ff04d78'


def _kuiper_spec():
    filename='kuiper-20261010.json'
    raw=files('solar_simulator.data').joinpath(filename).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=KUIPER_DATASET_SHA256:
        raise ValueError('Изменено закреплённое дополнение 30 объектов Койпера')
    identities=tuple((r['id'],r['name']) for r in json.loads(raw)['bodies'])
    return SupplementSpec(filename,KUIPER_DATASET_SHA256,KUIPER_GM_SHA256,
        ASTEROIDS_CATALOG_DATASET_SHA256,ASTEROIDS_CATALOG_GM_SHA256,
        'cad63a2d9dc61481eb3033e59d8e3bb2b15bf32457fd70313f23eb630ac41868',identities)


KUIPER_SPEC = _kuiper_spec()
SUPPLEMENTS = {spec.dataset_sha256:spec for spec in
    (PLUTO_SPEC,ASTEROIDS_SPEC,ASTEROIDS_FULL_SPEC,ASTEROIDS_CATALOG_SPEC,KUIPER_SPEC)}


def decode_supplement(raw):
    """Compatibility entry point for the original Pluto supplement."""
    return decode_body_dataset(raw,PLUTO_SPEC)


def decode_body_dataset(raw,spec):
    """Common SI body template with a registered, exact provenance contract."""
    def unique(items):
        result={}
        for key,value in items:
            if key in result:
                raise ValueError('Повторяющееся поле дополнения DE441')
            result[key]=value
        return result
    def invalid(value):
        raise ValueError('Неконечное число дополнения DE441')
    if not isinstance(raw,bytes) or len(raw)>max(100000,8192+1024*len(spec.identities)):
        raise ValueError('Неверный размер дополнения DE441')
    data=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)
    if (type(data) is not dict or set(data)!={'schema','base_origin','gm_sha256','units','vector_correction','sources','bodies'}
            or type(data['schema']) is not int or data['schema']!=1 or data['units']!='SI' or data['vector_correction']!='NONE'):
        raise ValueError('Неверные поля дополнения DE441')
    expected=EphemerisOrigin(2461321.5,'Ecliptic J2000','Solar System Barycenter','DE441',spec.parent_dataset_sha256,spec.parent_gm_sha256)
    if data['base_origin']!=asdict(expected) or data['gm_sha256']!=spec.gm_sha256:
        raise ValueError('Несогласованное происхождение дополнения DE441')
    if _sources_digest(data['sources'])!=spec.sources_sha256:
        raise ValueError('Неверные источники дополнения DE441')
    if type(data['bodies']) is not list or len(data['bodies'])!=len(spec.identities):
        raise ValueError('Неверное число тел дополнения DE441')
    bodies=[]
    for record,(identity,name) in zip(data['bodies'],spec.identities):
        if (type(record) is not dict or set(record)!={'id','name','gm_m3_s2','position','velocity'}
                or type(record['id']) is not int or record['id']!=identity or record['name']!=name):
            raise ValueError('Неверное тело дополнения DE441')
        gm=record['gm_m3_s2']
        if type(gm) not in (int,float) or not isfinite(gm) or gm<=0:
            raise ValueError('Неверный GM дополнения DE441')
        vectors=[]
        for field in ('position','velocity'):
            value=record[field]
            if (type(value) is not list or len(value)!=3
                    or any(type(x) not in (int,float) or not isfinite(x) for x in value)):
                raise ValueError('Неверный вектор дополнения DE441')
            vectors.append(Vector3(*value))
        bodies.append(Body(name,gm/G,*vectors))
    return bodies,expected


def _supplement():
    return _load_supplement(PLUTO_SPEC)


def _load_supplement(spec):
    raw=files('solar_simulator.data').joinpath(spec.filename).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=spec.dataset_sha256:
        raise ValueError('Изменено закреплённое дополнение DE441')
    return decode_body_dataset(raw,spec)


def figure_parent_origin(origin):
    """Only the registered, exact extension may inherit pinned base figures.

    A checkpoint retains its complete extension digest and combined GM digest.
    This compatibility check never replaces its saved provenance with the parent.
    """
    if origin is None or origin.dataset_sha256 not in SUPPLEMENTS:
        return origin
    spec=SUPPLEMENTS[origin.dataset_sha256]
    _,parent=_load_supplement(spec)
    expected=replace(parent,dataset_sha256=spec.dataset_sha256,gm_sha256=spec.gm_sha256)
    if origin!=expected:
        raise ValueError('Несогласованное происхождение расширенного DE441')
    return figure_parent_origin(parent)


def additional_names(origin):
    """Names along the verified supplement lineage, for figure compatibility."""
    figure_parent_origin(origin)
    result=set()
    while origin is not None and origin.dataset_sha256 in SUPPLEMENTS:
        spec=SUPPLEMENTS[origin.dataset_sha256]
        additions,origin=_load_supplement(spec)
        result.update(body.name for body in additions)
    return result


def extend_system(spec):
    additions,parent=_load_supplement(spec)
    if parent.dataset_sha256 in SUPPLEMENTS:
        initial,origin=extend_system(SUPPLEMENTS[parent.dataset_sha256])
    else:
        initial,origin=solar_system(resolved_moon=True)
    if origin!=parent or set(b.name for b in initial)&set(b.name for b in additions):
        raise ValueError('Исходный набор не совпадает с закреплённым дополнением')
    return initial+additions,replace(origin,dataset_sha256=spec.dataset_sha256,gm_sha256=spec.gm_sha256)


def solar_system_pluto():
    return extend_system(PLUTO_SPEC)


def solar_system_asteroids():
    return extend_system(ASTEROIDS_SPEC)


def solar_system_asteroids_full():
    return extend_system(ASTEROIDS_FULL_SPEC)


def solar_system_asteroids_catalog():
    return extend_system(ASTEROIDS_CATALOG_SPEC)


def solar_system_kuiper():
    """384 interacting bodies: unchanged 354 plus 30 separate KBOs, no ring."""
    return extend_system(KUIPER_SPEC)
