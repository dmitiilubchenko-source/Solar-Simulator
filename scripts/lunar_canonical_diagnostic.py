"""Conditional real-scale three-body initial projection, NOT runtime PN Moon."""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

from scripts.canonical_initial import SIUnits, from_velocities_and_rate
from scripts.canonical_checkpoint import CanonicalCheckpoint, CORE_SOURCES, canonical_text
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.rigid_pn_model import Parameters
from solar_simulator.rotation import RigidFigure


ROOT = Path(__file__).resolve().parents[1]


def initial_checkpoint(policy):
    orbital_path = 'src/solar_simulator/data/solar-system-moon-20261008.json'
    spin_path = 'src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json'
    sha = lambda name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    if sha(orbital_path) != policy['orbital_data_sha256'] or sha(spin_path) != policy['spin_profile_sha256']:
        raise ValueError('Changed pinned lunar inputs')
    data = json.loads((ROOT/orbital_path).read_text(encoding='utf-8'))
    profile = json.loads((ROOT/spin_path).read_text(encoding='utf-8'))
    if (data['epoch_jd_tdb'] != profile['epoch_jd_tdb'] or data['epoch_jd_tdb'] != policy['epoch_jd_tdb']
            or data['frame'] != profile['frame'] or data['frame'] != policy['frame']
            or data['center'] != profile['source_center'] or data['center'] != policy['center']
            or data['units'] != 'SI' or profile['units'] != 'SI'
            or profile['parent_dataset_sha256'] != sha(orbital_path)
            or policy['body_names'] != ['Sun', 'Earth', 'Moon']
            or policy['physical_lunar_mapping_certified'] is not False):
        raise ValueError('Incompatible conditional lunar contract')
    by_name = {b['name']:b for b in data['bodies']}
    bodies = [by_name[n] for n in policy['body_names']]
    if bodies[1]['gm_m3_s2'] != profile['earth_gm_m3_s2'] or bodies[2]['gm_m3_s2'] != profile['moon_gm_m3_s2']:
        raise ValueError('Unmatched Earth/Moon GM')
    g = profile['gravitational_constant_m3_kg_s2']
    units = SIUnits(bodies[0]['gm_m3_s2']/g, policy['length_scale_m'], g)
    masses = tuple(b['gm_m3_s2']/g/units.mass_kg for b in bodies)
    figure = RigidFigure(masses[2], tuple(np.array(profile['moments_kg_m2'])/units.inertia_kg_m2),
                        profile['exclusion_radius_m']/units.length_m)
    parameters = Parameters(PointParameters(masses, policy['c_m_s']/units.velocity_m_s), figure, 2)
    r = np.array(profile['rotation']); rd = np.array(profile['rotation_derivative_per_second'])
    omega_hat = rd@r.T
    if (np.linalg.norm(r.T@r-np.eye(3)) > 1e-12 or abs(np.linalg.det(r)-1)>1e-12
            or np.linalg.norm(omega_hat+omega_hat.T)/np.linalg.norm(rd)>1e-12):
        raise ValueError('Invalid orientation matrix/tangent')
    w_si = .5*np.array([omega_hat[2, 1]-omega_hat[1, 2], omega_hat[0, 2]-omega_hat[2, 0],
                       omega_hat[1, 0]-omega_hat[0, 1]])
    q = np.roll(Rotation.from_matrix(r).as_quat(), 1)
    x = np.array([b['position'] for b in bodies])/units.length_m
    v = np.array([b['velocity'] for b in bodies])/units.velocity_m_s
    state, inversion = from_velocities_and_rate(x, v, q, w_si*units.time_s, np.zeros_like(x), parameters,
        velocity_scales=np.linalg.norm(v, axis=1), rate_scale=np.linalg.norm(w_si)*units.time_s)
    spin_scale = np.linalg.norm(state[:-4].reshape(3, 3, 3)[2, 2])
    spin_atol = np.full((3, 3), policy['zero_point_spin_atol_model_units'])
    spin_atol[2] = policy['figure_spin_atol_relative_to_initial_norm']*spin_scale
    atol = np.r_[np.full(9, policy['position_atol_m']/units.length_m),
        np.repeat(np.array(masses)*policy['momentum_atol_equivalent_velocity_m_s']/units.velocity_m_s,3),
        spin_atol.ravel(), np.full(4,policy['quaternion_atol'])]
    paths = list(CORE_SOURCES)+['scripts/lunar_canonical_diagnostic.py', 'scripts/lunar-canonical-policy.json',
        'scripts/assess_lunar_canonical.py', 'tests/test_lunar_canonical_diagnostic.py',
        'scripts/independent_rigid_pn.py', 'scripts/independent_nbody_pn_spin.py', orbital_path, spin_path]
    metadata = dict(frame=dict(name=policy['frame']+'; conditional SSB canonical boundary',
        centre='canonical-ADM-centres', spin_basis='finite-H-spatial-Euclidean',
        time_coordinate='TDB-as-input-coordinate-time', epoch_jd=policy['epoch_jd_tdb'], evolution='fixed-no-reboost'),
        units=dict(kind='SI-similarity',**vars(units)),
        integration=dict(method='canonical-per-block-DOP853',rtol=policy['production_rtol'],atol=atol.tolist(),
                         max_step=policy['max_step_seconds']/units.time_s),
        provenance=dict(interpretation=policy['projection'], physical_mapping_certified=False,
                        sources=[dict(path=p,sha256=sha(p)) for p in paths]))
    checkpoint = CanonicalCheckpoint(parameters,tuple(state),tuple(state),0.,canonical_text(metadata))
    return checkpoint, units, dict(inversion=inversion, body_names=policy['body_names'],
        input_velocity_m_s=[b['velocity'] for b in bodies], input_attitude_rate_per_s=w_si.tolist(),
        point_spins='Sun/Earth zero ideal point-spin; one rigid Moon',
        parent_file_body_count=len(data['bodies']), selected_body_count=3)


def differences(first_orbit, first_matrices, second_orbit, second_matrices, units, initial_spin):
    """Absolute SI positions AND Earth-Moon internal orbit; raw matrix agreement."""
    a, b = np.asarray(first_orbit), np.asarray(second_orbit)
    if a.shape != b.shape or a.ndim != 2 or a.shape[1] != 27 or not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError('Matched finite three-body canonical grids required')
    ra, rb = np.asarray(first_matrices), np.asarray(second_matrices)
    if ra.shape != rb.shape or ra.shape != (len(a),3,3) or not np.all(np.isfinite(ra)) or not np.all(np.isfinite(rb)):
        raise ValueError('Matched finite attitude matrix grids required')
    if not np.isfinite(initial_spin) or initial_spin <= 0:
        raise ValueError('Positive initial figure-spin scale required')
    aa, bb = a.reshape(-1,3,3,3), b.reshape(-1,3,3,3)
    positions = np.linalg.norm((aa[:,0]-bb[:,0])*units.length_m,axis=-1)
    relative = ((aa[:,0,2]-aa[:,0,1])-(bb[:,0,2]-bb[:,0,1]))*units.length_m
    return dict(positions_m=float(positions.max()), positions_per_body_m=positions.max(axis=0).tolist(),
        earth_moon_position_m=float(np.linalg.norm(relative,axis=1).max()),
        figure_spin_relative=float(np.linalg.norm(aa[:,2,2]-bb[:,2,2],axis=1).max()/initial_spin),
        attitude_matrix=float(np.linalg.norm(ra-rb,axis=(1,2)).max()))
