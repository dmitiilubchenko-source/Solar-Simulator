import json

import numpy as np
import pytest

from scripts import assess_bound_body as audit
from scripts import bound_body as body
from scripts import independent_bound_reference as independent


def policy():
    return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


def test_radial_reduction_matches_full_hamiltonian_off_circular_equilibrium():
    p=policy();cases,reduced=audit.models(p);pars=cases['breathing'][0]
    m=p['equilateral_mass_kg'];ell=reduced['ell']
    for radius,speed,phase in [(2.12,.17,.31),(1.9,-.13,-.27)]:
        z=np.array([[radius/p['length_scale_m'],speed/p['velocity_scale_m_s'],phase]])
        cart=independent.radial_cartesian(z,m,ell,p['length_scale_m'],p['velocity_scale_m_s'],p['momentum_scale_kg_m_s'])[0]
        y=audit.physical(cart,pars,p);x,momentum,masses=body.unpack(y,pars)
        actual=body.rhs(0.,y,pars)[9:].reshape(3,3)/m
        er=x/radius;et=np.cross([0.,0.,1.],er)
        radial_flow=independent.radial_rhs(0.,z[0],m,p['equilateral_stiffness_N_m'],reduced['rest_length'],pars.gravitational_constant,ell,1.,p['length_scale_m'],p['velocity_scale_m_s'])
        # Cartesian acceleration = (Rddot-R phidot²)er; tangential parts cancel.
        expected=(radial_flow[1]*p['velocity_scale_m_s']-ell**2/radius**3)*er
        assert np.linalg.norm(actual-expected)/np.linalg.norm(actual)<1e-11
        out=body.rotation_split(y,pars)
        assert abs(out['spin'][2]-3*m*ell)<1e-11
        assert np.linalg.norm(out['residual_velocities']-speed*er)<1e-11
        expected_h=1.5*m*(speed**2+ell**2/radius**2)-np.sqrt(3)*pars.gravitational_constant*m**2/radius+1.5*p['equilateral_stiffness_N_m']*(np.sqrt(3)*radius-reduced['rest_length'])**2
        assert abs(out['energy']-expected_h)<1e-11


def test_scaled_cartesian_gradient_preserves_units_and_off_origin_COM():
    p=policy();cases,_=audit.models(p);pars,initial,duration=cases['asymmetric']
    actual=independent.cartesian_rhs(.3,initial,pars.masses,pars.links,pars.gravitational_constant,duration,p['length_scale_m'],p['momentum_scale_kg_m_s'])
    scale=audit.physical(np.ones(len(initial)),pars,p)
    expected=duration*body.rhs(.3*duration,initial*scale,pars)/scale
    assert np.linalg.norm(actual-expected)/np.linalg.norm(expected)<1e-11
    out=body.diagnostics(initial*scale,pars)
    assert np.linalg.norm(out['centre'])>.01 and np.linalg.norm(out['momentum'])>.01


@pytest.mark.parametrize('category',['maximum','minimum','required_true'])
def test_every_predeclared_criterion_is_enforced(category):
    p=policy();metrics={**{k:v/2 for k,v in p['maximum'].items()},**{k:v*2 for k,v in p['minimum'].items()}}
    confirms={k:True for k in p['required_true']}
    assert audit.failures(metrics,confirms,p)==[]
    for key in p[category]:
        wrong,flags=metrics.copy(),confirms.copy()
        if category=='required_true':flags[key]=False
        else:wrong[key]=p[category][key]
        assert audit.failures(wrong,flags,p)==[key]


def test_source_guard_includes_imported_helpers_and_used_policies(tmp_path,monkeypatch):
    sources=audit.source_hashes()
    for name in ('scripts/bound_body.py','scripts/independent_bound_reference.py','scripts/density_moments.py','scripts/external_metric.py','scripts/assess_metric_spin.py',*audit.USED_POLICIES):assert name in sources
    (tmp_path/'scripts').mkdir()
    for name in audit.USED_POLICIES:(tmp_path/name).write_text('{}')
    (tmp_path/'scripts/model.py').write_text('# frozen\n')
    monkeypatch.setattr(audit,'ROOT',tmp_path);monkeypatch.setattr(audit,'LOADED_SOURCES',audit.source_hashes())
    audit.check_sources();(tmp_path/'scripts/model.py').write_text('# changed\n')
    with pytest.raises(ValueError,match='changed'):audit.check_sources()


def test_existing_output_and_outside_paths_rejected_before_source_reads(tmp_path,monkeypatch):
    root=tmp_path/'root';root.mkdir();monkeypatch.setattr(audit,'ROOT',root)
    def forbidden():raise AssertionError('No scientific jobs or reads permitted')
    monkeypatch.setattr(audit,'check_sources',forbidden)
    old=root/'old.json';old.write_bytes(b'unchanged')
    with pytest.raises(FileExistsError):audit.audit(work=root/'work',output=old)
    with pytest.raises(ValueError):audit.audit(work=tmp_path/'outside',output=root/'new.json')
    assert old.read_bytes()==b'unchanged' and not(root/'work').exists()
