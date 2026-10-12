import json

import numpy as np
import pytest

from scripts import assess_boundary_cloud as audit
from scripts.independent_sr_reference import gradient_velocity


def policy():
    return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


def test_predeclared_order_limits_and_independent_hamiltonian_gradient():
    p = policy(); event, spin, order = audit.order_checks(p)
    assert event < p['maximum']['event_fourth_order_ratio_deviation']
    assert spin < p['maximum']['spin_fourth_order_ratio_deviation']
    assert all(15.9 < r < 16.1 for values in order['doubling_c_ratios'].values() for r in values)
    system = audit.cloud(p, p['light_speeds_m_s'][0])
    four = system.momenta@audit.sr.boost(p['frame_velocity_m_s'], system.c).T
    expected = system.c*four[:, 1:]/four[:, 0, None]
    actual = gradient_velocity(four[:, 1:], system.masses, system.c)
    assert np.linalg.norm(actual-expected)/np.linalg.norm(expected) < 1e-11


@pytest.mark.parametrize('category', ['maximum', 'minimum', 'required_true'])
def test_all_audit_criteria_are_required(category):
    p = policy(); m = dict([(k, v/2) for k, v in p['maximum'].items()]
                           +[(k, v*2) for k, v in p['minimum'].items()])
    c = {k: True for k in p['required_true']}
    assert audit.failures(m, c, p) == []
    for key in p[category]:
        wrong_m, wrong_c = m.copy(), c.copy()
        if category == 'required_true': wrong_c[key] = False
        else: wrong_m[key] = p[category][key]
        assert audit.failures(wrong_m, wrong_c, p) == [key]


def test_used_policy_closure_and_source_change_guard(tmp_path, monkeypatch):
    sources = audit.source_hashes()
    for name in ['scripts/local_event_map.py', 'scripts/sr_cloud.py', 'scripts/density_moments.py',
                 'scripts/independent_sr_reference.py', 'scripts/assess_metric_spin.py',
                 'scripts/canonical_initial.py', 'src/solar_simulator/spin_initial.py', *audit.USED_POLICIES]:
        assert name in sources
    root = tmp_path/'clone'; (root/'scripts').mkdir(parents=True)
    for name in audit.USED_POLICIES: (root/name).write_text('{}', encoding='utf-8')
    (root/'scripts/one.py').write_text('# source\n', encoding='utf-8')
    monkeypatch.setattr(audit, 'ROOT', root)
    monkeypatch.setattr(audit, 'LOADED_SOURCES', audit.source_hashes())
    audit.check_sources()
    (root/audit.USED_POLICIES[1]).write_text('{"changed":true}', encoding='utf-8')
    with pytest.raises(ValueError, match='changed'): audit.check_sources()


def test_no_overwrite_or_outside_project_before_integration(tmp_path, monkeypatch):
    root = tmp_path/'root'; root.mkdir(); monkeypatch.setattr(audit, 'ROOT', root)
    def forbidden(*args, **kwargs): raise AssertionError('Integration must not start')
    monkeypatch.setattr(audit, 'integrate_raw_initial', forbidden)
    old = root/'old.json'; old.write_bytes(b'preserve')
    with pytest.raises(FileExistsError): audit.audit(work=root/'new', output=old)
    assert old.read_bytes() == b'preserve' and not (root/'new').exists()
    with pytest.raises(ValueError): audit.audit(work=tmp_path/'outside', output=root/'new.json')
