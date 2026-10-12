import json

import numpy as np
import pytest

from scripts import assess_metric_spin as audit
from scripts import independent_schwarzschild_spin as reference
from scripts import schwarzschild_metric as exact
from scripts.metric_spin_transport import transport


def policy():
    return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


def test_independent_derivative_circle_clock_and_fourth_order_limits():
    p = policy(); metrics, order = audit.instantaneous(p)
    assert all(type(value) is float for value in metrics.values())
    for key, value in metrics.items():
        if key in p['maximum']:
            assert value < p['maximum'][key], (key, value)
        else:
            assert value > p['minimum'][key], (key, value)
    assert all(15.9 < r < 16.1 for values in order['doubling_c_ratios'].values() for r in values)


def test_spherical_initial_spin_ssc_and_covariant_gram():
    gm = 1e12; rho = 1e6; c = 5e4
    z = reference.initial_covectors(gm, rho, c)
    gram, ssc = reference.invariants(z, gm, rho, c)
    assert np.linalg.norm(gram-np.eye(3)) < 1e-12
    assert np.linalg.norm(ssc) < 1e-12
    assert np.linalg.norm(reference.euclidean_basis(0., z, gm, rho, c)-np.eye(3)) < 1e-12
    dz = reference.spherical_generator(gm, rho, c)@z
    _, radius, epsilon, frequency = reference.constants(gm, rho, c)
    f = 1-2*epsilon
    assert np.linalg.norm(z.T@np.diag([-1/f, f, 1., 1.])@dz+dz.T@np.diag([-1/f, f, 1., 1.])@z) < 1e-12
    assert np.linalg.norm(dz[0]+frequency*radius/c*dz[3]) < 1e-12


@pytest.mark.parametrize('category', ['maximum', 'minimum', 'required_true'])
def test_every_predeclared_criterion_is_enforced(category):
    p = policy()
    metrics = dict([(k, bound/2) for k, bound in p['maximum'].items()]
                   +[(k, bound*2) for k, bound in p['minimum'].items()])
    confirmations = {k: True for k in p['required_true']}
    assert audit.failures(metrics, confirmations, p) == []
    for key in p[category]:
        m, c = dict(metrics), dict(confirmations)
        if category == 'required_true': c[key] = False
        else: m[key] = p[category][key]
        assert audit.failures(m, c, p) == [key]


@pytest.mark.parametrize('bad', ['missing', 'extra', 'bool', 'nan', 'confirmation'])
def test_malformed_audit_result_rejected(bad):
    p = policy()
    m = dict([(k, bound/2) for k, bound in p['maximum'].items()]
             +[(k, bound*2) for k, bound in p['minimum'].items()])
    c = {k: True for k in p['required_true']}
    if bad == 'missing': m.pop(next(iter(m)))
    elif bad == 'extra': m['undeclared'] = 0.
    elif bad == 'bool': m[next(iter(m))] = True
    elif bad == 'nan': m[next(iter(m))] = float('nan')
    elif bad == 'confirmation': c[next(iter(c))] = 1
    with pytest.raises(ValueError): audit.failures(m, c, p)


def test_source_closure_and_real_edit_rejection(tmp_path, monkeypatch):
    sources = audit.source_hashes()
    for name in ['scripts/external_metric.py', 'scripts/canonical_initial.py',
                 'src/solar_simulator/spin_initial.py', 'scripts/metric_spin_transport.py',
                 'scripts/schwarzschild_metric.py', 'scripts/independent_schwarzschild_spin.py',
                 'scripts/assess_metric_spin.py', audit.POLICY]:
        assert name in sources
    root = tmp_path/'clone'; folder = root/'scripts'; folder.mkdir(parents=True)
    (root/audit.POLICY).write_text('{}', encoding='utf-8')
    file = folder/'real.py'; file.write_text('# before\n', encoding='utf-8')
    monkeypatch.setattr(audit, 'ROOT', root)
    monkeypatch.setattr(audit, 'LOADED_SOURCES', audit.source_hashes())
    audit.check_sources()
    file.write_text('# after\n', encoding='utf-8')
    with pytest.raises(ValueError, match='changed'): audit.check_sources()


def test_old_outputs_and_paths_rejected_before_integrator(tmp_path, monkeypatch):
    root = tmp_path/'root'; root.mkdir()
    monkeypatch.setattr(audit, 'ROOT', root)
    def forbidden(*args, **kwargs): raise AssertionError('Integration must not start')
    monkeypatch.setattr(audit, 'solve_ivp', forbidden)
    old = root/'old.json'; old.write_bytes(b'preserve')
    with pytest.raises(FileExistsError): audit.audit(work=root/'new', output=old)
    assert old.read_bytes() == b'preserve' and not (root/'new').exists()
    with pytest.raises(ValueError): audit.audit(work=tmp_path/'outside', output=root/'new.json')


@pytest.mark.parametrize('position,gm,c', [([0., 0., 0.], 1e12, 5e4),
                                         ([100., 0., 0.], 1e12, 5e4),
                                         ([1e6, 0., 0.], -1., 5e4),
                                         ([1e6, 0., 0.], 1e12, True)])
def test_schwarzschild_invalid_or_interior_domain_rejected(position, gm, c):
    with pytest.raises(ValueError): exact.metric(position, gm, c)


def test_null_circle_and_invalid_orbit_rejected():
    with pytest.raises(ValueError): exact.circular_orbit(0., 400., 1e12, 5e4)
    with pytest.raises(ValueError): exact.circular_orbit(float('nan'), 1e6, 1e12, 5e4)
    with pytest.raises(ValueError): exact.circular_orbit(0., -1., 1e12, 5e4)
    x, v, a, _, _ = exact.circular_orbit(0., 1e6, 1e12, 5e4)
    assert np.linalg.norm(transport(exact.metric(x, 1e12, 5e4), v, 5e4).acceleration-a)/np.linalg.norm(a) < 1e-11


@pytest.mark.parametrize('method', ['RK45', 'DOP853'])
def test_raw_negative_zero_epoch0_and_actual_later_dynamics(method):
    initial = np.array([-0., 0., -0., 1.]); bits = initial.view(np.uint64).copy()
    grid = np.linspace(0., 1., 9); p = policy()
    states, nfev = audit.integrate_raw_initial(lambda t, z: np.array([1., 2., 3., 0.]),
        initial, grid, method, 2e-12, p)
    assert np.array_equal(states[0].view(np.uint64), bits)
    assert np.array_equal(initial.view(np.uint64), bits)
    assert np.allclose(states[1:], initial+grid[1:, None]*np.array([1., 2., 3., 0.]),
                       rtol=1e-12, atol=1e-12)
    assert states.shape == (len(grid), 4) and nfev > 0
