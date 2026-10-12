"""Ring mass, geometry, force oracle and real checkpoint checks."""
from dataclasses import replace
import hashlib
import json
from math import fsum
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad_vec
from scipy.special import ellipk

from scripts.build_kuiper_ring import document,parameters
from scripts.assess_resolved_moon import states
from scripts.independent_eih_rust import load_oracle
from solar_simulator.kuiper_ring import RING_SPECS,solar_system_ring
from solar_simulator.perturbers import solar_system_kuiper,figure_parent_origin
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.native_forces import prepare
from solar_simulator.relativity import C
from solar_simulator.simulation import G
from solar_simulator.storage import load,save
from solar_simulator.experiment import preset,advance


@pytest.mark.parametrize('points,phase',list(RING_SPECS))
def test_pinned_ring_keeps_parent_and_total_residual_mass(points,phase):
    original,origin=solar_system_kuiper();bodies,new_origin=solar_system_ring(points,phase)
    def properties(b):return b.name,b.mass,b.radius,b.spin.x,b.spin.y,b.spin.z
    assert [properties(b) for b in bodies[:384]]==[properties(b) for b in original]
    assert np.array_equal(states(bodies[:384]),states(original))
    assert len(bodies)==384+points and len({b.name for b in bodies})==len(bodies)
    assert sum(b.name=='Pluto-System' for b in bodies)==1
    au,gm=parameters();q=states(bodies[384:])-states(original)[0]
    assert np.max(np.abs(np.linalg.norm(q[:,:3],axis=1)/(44*au)-1))<5e-16
    assert np.max(np.abs(q[:,2]))==0 and np.max(np.abs(q[:,5]))==0
    assert fsum(b.mass*G for b in bodies[384:])==pytest.approx(gm,rel=2e-16)
    assert np.max(np.abs(np.sum(q[:,:3],axis=0)))/(44*au*points)<2e-16
    assert np.max(np.abs(np.sum(q[:,3:],axis=0)))/(np.linalg.norm(q[0,3:])*points)<2e-16
    assert np.max(np.abs(np.sum(q[:,:3]*q[:,3:],axis=1)))/(44*au*np.linalg.norm(q[0,3:]))<3e-16
    spec=RING_SPECS[points,phase]
    raw=(json.dumps(document(points,phase),indent=2,allow_nan=False)+'\n').encode()
    assert raw==Path('src/solar_simulator/data',spec.filename).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==new_origin.dataset_sha256
    assert figure_parent_origin(new_origin)==figure_parent_origin(origin)
    assert sun_earth_moon_quadrupoles(bodies,new_origin)==sun_earth_moon_quadrupoles(original,origin)


@pytest.mark.parametrize('points,phase',[(True,0),(36.,0),(35,0),(36,2),(36,False)])
def test_ring_options_reject_unpinned_geometry(points,phase):
    with pytest.raises(ValueError):solar_system_ring(points,phase)


def continuous_field(point,radius,gm):
    point=np.asarray(point,dtype=float)
    def integrand(angle):
        d=radius*np.array([np.cos(angle),np.sin(angle),0.])-point
        return gm/(2*np.pi)*d/np.linalg.norm(d)**3
    return quad_vec(integrand,0,2*np.pi,epsabs=1e-28,epsrel=1e-13)[0]


def test_ring_field_matches_independent_quadrature_gradient_symmetry_and_far_mass():
    au,gm=parameters();radius=44*au
    for fraction in (0.,.25,.7,.95,3.):
        p=radius*np.array([fraction,.03,.12])
        exact=continuous_field(p,radius,gm)
        rho=np.linalg.norm(p[:2]);den=np.sqrt((radius+rho)**2+p[2]**2)
        def potential(value):
            cylindrical=np.linalg.norm(value[:2]);d=np.sqrt((radius+cylindrical)**2+value[2]**2)
            return -2*gm*ellipk(4*radius*cylindrical/d**2)/(np.pi*d)
        step=radius*1e-5
        gradient=np.array([(-potential(p+2*step*np.eye(3)[i])+8*potential(p+step*np.eye(3)[i])
            -8*potential(p-step*np.eye(3)[i])+potential(p-2*step*np.eye(3)[i]))/(12*step) for i in range(3)])
        assert np.linalg.norm(exact+gradient)/np.linalg.norm(exact)<1e-9
        for n in (36,72,144):
            bodies,_=solar_system_ring(n)
            points=states(bodies[384:])[:,:3]-states(bodies)[0,:3]
            d=points-p
            field=np.sum(gm/n*d/np.linalg.norm(d,axis=1)[:,None]**3,axis=0)
            if fraction<=.7 or n==144:
                assert np.linalg.norm(field-exact)/np.linalg.norm(exact)<2e-5
    centre=continuous_field(np.zeros(3),radius,gm)
    assert np.linalg.norm(centre)<1e-28
    far=np.array([0.,0.,radius*100])
    analytic=-gm*far/(radius**2+far[2]**2)**1.5
    assert np.linalg.norm(continuous_field(far,radius,gm)-analytic)<1e-30
    assert abs(analytic[2]/(-gm/far[2]**2)-1)<.00015


@pytest.mark.parametrize('points',[36,144])
def test_420_body_native_force_and_reaction_include_ring_self_gravity(points):
    pytest.importorskip('solar_native')
    bodies,_=solar_system_ring(points);q=states(bodies)
    masses=np.array([b.mass for b in bodies]);mu=masses*G
    native=prepare(masses);hint=3,4,q[4,:3]-q[3,:3]
    actual=native(q[:,:3],q[:,3:],C,hint)
    independent=load_oracle()(q[:,:3],q[:,3:],mu,C,hint)
    assert np.max(np.linalg.norm(actual-independent,axis=1))<3e-16
    newton=native(q[:,:3],q[:,3:],relative_pair=hint)
    total=np.sum(masses[:,None]*newton,axis=0)
    assert np.linalg.norm(total)/np.sum(masses*np.linalg.norm(newton,axis=1))<2e-15
    ring=q[384:,:3];d=ring[None,:,:]-ring[:,None,:]
    distance=np.linalg.norm(d,axis=2);np.fill_diagonal(distance,np.inf)
    self_field=np.sum(mu[384:][None,:,None]*d/distance[:,:,None]**3,axis=1)
    assert np.max(np.linalg.norm(self_field,axis=1))>0


def test_ring_checkpoint_restores_registered_figures_and_numerical_controls(tmp_path):
    pytest.importorskip('solar_native')
    state=preset('solar-system-kuiper-ring',backend='rust')
    state=replace(state,settings=replace(state.settings,integrator='dop853',physics='eih-1pn',
        figures=sun_earth_moon_quadrupoles(state.bodies,state.origin),relative_pair=('Earth','Moon'),
        rtol=3e-14,position_atol=1e-7,velocity_atol=1e-13))
    one=advance(state,2);path=tmp_path/'ring.json';save(one,path);resumed=advance(load(path),2)
    direct=advance(state,4)
    assert len(resumed.bodies)==420 and resumed.origin==state.origin and resumed.settings==state.settings
    assert resumed.orientation_work!=0
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(direct.bodies)[:,:3],axis=1))<.02


def test_changed_generation_policy_is_rejected_without_reinterpreting_mass(monkeypatch):
    from scripts import build_kuiper_ring as module
    monkeypatch.setattr(module,'POLICY_SHA256','0'*64)
    with pytest.raises(ValueError,match='policy changed'):module.document(36,0)


def test_ring_force_screen_includes_outer_planets_and_stable_tidal_difference():
    from scripts.assess_kuiper_ring import field_diagnostic
    result=field_diagnostic()
    assert result['total_gm_m3_s2']==parameters()[1]
    assert set(result['points'])=={'centre','Earth_radius','Neptune_radius','near_ring','far_axis'}
    for name in ('Earth_radius','Neptune_radius','far_axis'):
        for variant in result['points'][name]['variants'].values():
            assert variant['absolute_error_m_per_s2']<1e-17
    assert result['independent_quadrature_tidal_error_m_per_s2']<1e-27
    assert np.linalg.norm(result['moon_minus_earth_m_per_s2'])>0


@pytest.mark.parametrize('changed',['policy_sha256','manifest_sha256','archive_sha256'])
def test_incompatible_ring_cache_is_rejected_before_arrays_are_loaded(tmp_path,monkeypatch,changed):
    from scripts import assess_kuiper_ring as module
    monkeypatch.chdir(tmp_path);(tmp_path/'.tools').mkdir()
    data=dict(policy_sha256=module.POLICY_SHA256,manifest_sha256=module.MANIFEST_SHA256,archive_sha256='expected')
    data[changed]='changed'
    (tmp_path/'.tools/test-meta.json').write_text(json.dumps(data),encoding='utf-8')
    monkeypatch.setattr(module,'digest',lambda path:'expected')
    with pytest.raises(ValueError,match='Wrong ring experiment cache'):
        module.checked_cache('test',np.array([0.,31557600.]))


def test_published_original_ring_audit_retains_failed_geometry_and_current_sources():
    report=json.loads(Path('docs/kuiper-ring-validation.json').read_text(encoding='utf-8'))
    bodies,origin=solar_system_ring()
    assert report['body_count']==420 and report['dataset_sha256']==origin.dataset_sha256
    assert report['samples']==45 and report['duration_seconds']==31557600
    assert report['numerical_checks_passed'] and all(report['checks'].values())
    assert report['geometry_criterion_passed'] is False and report['checks_passed'] is False
    assert report['geometry_comparisons']['phase_0_vs_1_36']['major_systems']['maximum_position_metres']>.1
    assert len(report['variants'])==8 and len(report['geometry_comparisons'])==7
    assert set(report['increment_by_parent_body'])=={b.name for b in bodies[:384]}
    for n in (36,72,144):
        for phase in (0,1):
            variant=report['variants'][f'ring_{n}_{phase}']
            assert variant['dataset_sha256']==RING_SPECS[n,phase].dataset_sha256
            assert variant['body_count']==384+n and variant['options']['error_control']=='per-body'
    for path,checksum in report['code_sha256'].items():
        source = Path('scripts/validation/kuiper-ring-experiment-20261011.py.txt') if path == 'src/solar_simulator/experiment.py' else Path(path)
        assert hashlib.sha256(source.read_bytes()).hexdigest()==checksum


def test_native_polygon_self_gravity_matches_closed_radial_sum_and_grows_with_resolution():
    from scripts.check_ring_field import self_gravity_checks
    au,gm=parameters();rows=self_gravity_checks(44*au,gm)
    values=[rows[str(n)]['inward_acceleration_m_per_s2'] for n in (36,72,144)]
    assert 0<values[0]<values[1]<values[2]
    for row in rows.values():
        assert row['native_analytic_maximum_difference_m_per_s2']<row['inward_acceleration_m_per_s2']*1e-12


def test_published_refined_ring_audit_verifies_all_528_and_unchanged_criteria():
    report=json.loads(Path('docs/kuiper-ring-refinement-validation.json').read_text(encoding='utf-8'))
    _,origin=solar_system_ring(144,0)
    assert report['body_count']==528 and report['dataset_sha256']==origin.dataset_sha256
    assert report['gm_sha256']==origin.gm_sha256 and report['checks_passed']
    assert all(report['checks'].values()) and report['original_audit_passed'] is False
    assert report['policy']['selected_points']==144 and report['policy']['selected_phase_index']==0
    assert report['samples']==45 and report['duration_seconds']==31557600
    assert hashlib.sha256(Path('docs/kuiper-ring-validation.json').read_bytes()).hexdigest()==report['original_audit_sha256']
    assert hashlib.sha256(Path('scripts/kuiper-ring-refinement-policy.json').read_bytes()).hexdigest()==report['policy_sha256']
    assert report['policy']['numerical_all_bodies_metres']==.1
    assert report['policy']['numerical_relative_moon_metres']==.02
    for row in report['numerical_checks'].values():
        assert 0<row['all_bodies']['maximum_position_metres']<.1
        assert 0<row['moon_relative_to_earth']['maximum_position_metres']<.02
    for row in report['geometry_comparisons'].values():
        assert row['major_systems']['maximum_position_metres']<.1
        assert row['moon_relative_to_earth']['maximum_position_metres']<.02
    for path,checksum in report['code_sha256'].items():
        source = Path('scripts/validation/kuiper-ring-experiment-20261011.py.txt') if path == 'src/solar_simulator/experiment.py' else Path(path)
        assert hashlib.sha256(source.read_bytes()).hexdigest()==checksum


def test_actual_kbo_initial_field_audit_keeps_near_ring_resolution_errors():
    report=json.loads(Path('docs/kuiper-ring-field-validation.json').read_text(encoding='utf-8'))
    bodies,_=solar_system_ring()
    expected={b.name for b in bodies[:11]+bodies[354:384]}
    assert report['checks_passed'] and report['target_count']==41 and set(report['targets'])==expected
    assert report['gm_m3_s2']==parameters()[1]
    assert report['targets']['2007 JJ43']['variants']['36_0']['relative_error']>.2
    for row in report['targets'].values():
        assert set(row['variants'])=={f'{n}_{p}' for n in (36,72,144) for p in (0,1)}
        assert row['distance_to_continuous_circle_au']>0
        assert row['elliptic_gradient_error_m_per_s2']<1e-8*np.linalg.norm(row['continuous_vector_m_per_s2'])+1e-26
    for path,checksum in report['code_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==checksum


def test_future_kbo_source_comparison_preserves_worse_residuals_for_all_geometries():
    report=json.loads(Path('docs/kuiper-ring-kbo-validation.json').read_text(encoding='utf-8'))
    bodies,_=solar_system_ring();names={b.name for b in bodies[354:384]}
    assert report['audit_checks_passed'] and report['body_count']==30 and report['source_samples']==13
    assert len(report['variants'])==8
    for variant in report['variants'].values():
        assert set(variant['bodies'])==names
    old=max(v['maximum_position_metres'] for v in report['variants']['no_ring']['bodies'].values())
    refined=max(v['maximum_position_metres'] for v in report['variants']['ring_144_0']['bodies'].values())
    assert old<5 and refined>300
    for path,checksum in report['code_sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==checksum
