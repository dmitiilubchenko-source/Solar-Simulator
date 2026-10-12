"""Source-bound conditional ten-body lunar input; no caller x/v substitution."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path

import numpy as np

from scripts.canonical_initial import SIUnits
from scripts.canonical_checkpoint import numeric_array,parse_json
from scripts.lunar_initial_boundary import PURPOSE,from_lunar_profile
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.rigid_pn_model import Parameters
from solar_simulator.rotation import RigidFigure
from solar_simulator.spin_initial import lunar_solid_equivalent_initial
from solar_simulator.relativity import C
from solar_simulator.simulation import G


DATASET_NAME = 'solar-system-moon-20261008.json'
DATASET_SHA256 = 'd58227299b10b217246aa5c63f33da51b0fd331b5c7a75bee400d577d6d1f702'
BODY_ORDER = ('Sun','Mercury','Venus','Earth','Moon','Mars','Jupiter','Saturn','Uranus','Neptune')
LENGTH_SCALE_M = 149597870700.


def array_digest(array):
    """Shape + explicit little-endian float64 bytes, including signed zero."""
    shape = np.asarray(array,dtype=object).shape
    a = numeric_array(array,shape,'fingerprinted array').astype('<f8',copy=False)
    header = json.dumps(dict(shape=list(shape),dtype='little-endian-float64'),sort_keys=True).encode('ascii')
    return hashlib.sha256(header+b'\n'+a.tobytes(order='C')).hexdigest()


def source_inputs(dataset_path=None):
    raw = (files('solar_simulator.data').joinpath(DATASET_NAME).read_bytes()
        if dataset_path is None else Path(dataset_path).read_bytes())
    if hashlib.sha256(raw).hexdigest()!=DATASET_SHA256:
        raise ValueError('Changed pinned orbital dataset')
    data = parse_json(raw.decode('utf-8'));figure,_,_,profile = lunar_solid_equivalent_initial()
    expected = dict(schema=1,epoch_jd_tdb=profile['epoch_jd_tdb'],frame=profile['frame'],
        center=profile['source_center'],ephemeris='DE441',units='SI',vector_correction='NONE')
    for key,value in expected.items():
        if type(data.get(key)) is not type(value) or data[key]!=value:
            raise ValueError('Incompatible orbital '+key)
    if profile['parent_dataset_sha256']!=DATASET_SHA256:
        raise ValueError('Incompatible profile parent dataset')
    bodies = data['bodies'];names = tuple(b['name'] for b in bodies)
    if names!=BODY_ORDER:raise ValueError('Incompatible pinned body order')
    if (bodies[3]['gm_m3_s2']!=profile['earth_gm_m3_s2']
            or bodies[4]['gm_m3_s2']!=profile['moon_gm_m3_s2']):
        raise ValueError('Incompatible Earth/Moon GM')
    units = SIUnits(bodies[0]['gm_m3_s2']/G,LENGTH_SCALE_M,G)
    masses = tuple(b['gm_m3_s2']/G/units.mass_kg for b in bodies)
    parameters = Parameters(PointParameters(masses,C/units.velocity_m_s),
        RigidFigure(masses[4],tuple(np.array(figure.moments)/units.inertia_kg_m2),
            figure.bounding_radius/units.length_m),4)
    x = numeric_array([b['position'] for b in bodies],(10,3),'pinned positions')/units.length_m
    v = numeric_array([b['velocity'] for b in bodies],(10,3),'pinned velocities')/units.velocity_m_s
    r = np.array(profile['rotation']);h = np.array(profile['rotation_derivative_per_second'])@r.T
    w = np.array([h[2,1]-h[1,2],h[0,2]-h[2,0],h[1,0]-h[0,1]])/2
    return dict(positions=x,velocities=v,parameters=parameters,units=units,body_names=names,
        epoch_jd_tdb=data['epoch_jd_tdb'],frame=data['frame'],
        velocity_scales=np.linalg.norm(v,axis=1),rate_scale=np.linalg.norm(w)*units.time_s)


def from_pinned_dataset(*,purpose,dataset_path=None):
    """Derive every body/parameter/x/v from the pinned input in its fixed order."""
    if type(purpose) is not str or purpose!=PURPOSE:
        raise ValueError('Only explicit conditional-research; physical mapping is not certified')
    args = source_inputs(dataset_path);state,info = from_lunar_profile(**args,purpose=purpose)
    info['orbital_input'] = dict(resource='solar_simulator.data/'+DATASET_NAME,sha256=DATASET_SHA256,
        body_names=list(args['body_names']),center='Solar System Barycenter',time_coordinate='TDB',
        units_SI_similarity=vars(args['units']),positions_model_sha256=array_digest(args['positions']),
        velocities_model_sha256=array_digest(args['velocities']),
        coordinates='pinned harmonic ephemeris values assigned to conditional canonical centres; no physical transformation')
    return state,info
