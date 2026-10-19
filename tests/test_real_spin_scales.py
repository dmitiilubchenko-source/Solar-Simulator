"""Independent limits for SI amplitudes and strict qualification inventory."""
import numpy as np
import pytest
from decimal import Decimal, localcontext

from scripts.canonical_initial import SIUnits
from scripts import real_spin_scales as formulas
from scripts import independent_real_spin as oracle
from scripts import assess_real_spin_scales as audit
from scripts.hybrid_rotation import hessian
from scripts.decimal_real_response import block_responses, agreement
from solar_simulator.simulation import G
from solar_simulator.relativity import C


def geometry():
    return np.array([[.4, -.1, .2], [-.4, .2, -.1], [3., .4, .6]]), np.array([
        [.1, .8, .2], [-.1, -.3, -.2], [-.05, .4, .1]]), np.array([.3, .7, .05]), np.array([.003, -.004, .002])


def test_circular_test_spin_has_known_leading_de_sitter_rate_and_angle():
    mass, radius = 2e30, 1.5e11
    speed = np.sqrt(G*mass/radius)
    x = np.array([[radius, 0., 0.], [0., 0., 0.]])
    v = np.array([[0., speed, 0.], [0., 0., 0.]])
    result = formulas.spin_orbit(x, v, [1., mass], [0., 0., 1.], 0)
    rate = 1.5*G*mass*speed/(C*C*radius*radius)
    np.testing.assert_allclose(result['omega'], [0., 0., rate], rtol=3e-15, atol=0.)
    angle = result['omega'][2]*(2*np.pi*radius/speed)
    assert angle == pytest.approx(3*np.pi*G*mass/(C*C*radius), rel=3e-15)


def test_isolated_spin_terms_match_scalar_hamiltonian_and_full_angular_identity():
    x, v, m, spin = geometry()
    result = formulas.spin_orbit(x, v, m, spin, 0, g=1., c=400.)
    expected = oracle.derivatives(x, v, m, spin, 0, 1., 400.)
    for name in expected:
        assert formulas.vector_relative(result[name]-expected[name], expected[name]) < 5e-13
    checks = formulas.spin_identities(x, v, m, spin, 0, result)
    assert checks['linear'] < 5e-14 and checks['angular'] < 5e-14
    assert checks['missing_velocity'] > 1e-3 and checks['missing_source_reaction'] > 1e-3


def test_zero_spin_keeps_precession_rate_but_exact_zero_orbital_reaction():
    x, v, m, _ = geometry()
    result = formulas.spin_orbit(x, v, m, np.zeros(3), 0, g=1., c=400.)
    assert np.linalg.norm(result['omega']) > 0
    for name in ('force', 'velocity_shift', 'acceleration'):
        np.testing.assert_array_equal(result[name], np.zeros_like(x))


def test_spin_rate_transport_is_the_velocity_operator_applied_to_spin_rate():
    x, v, m, spin = geometry(); rate = np.array([.001, .0002, -.0003])
    result = formulas.spin_orbit(x, v, m, spin, 0, spin_rate=rate, g=1., c=400.)
    expected = oracle.derivatives(x, v, m, rate, 0, 1., 400.)['velocity_shift']
    assert formulas.vector_relative(result['q_torque_transport']-expected, expected) < 5e-13


def test_mass_conditioning_matches_naive_finite_matrix_on_small_known_system():
    x = np.array([[-1., 0., 0.], [1., 0., 0.]])
    v = np.zeros_like(x); m = np.array([2., 1.]); b = np.array([[.1, .2, .3], [-.2, .1, -.1]])
    response, diagnostics = formulas.mixed_responses(x, v, m, {'test':b, 'zero':v}, SIUnits(1., 1., 1.), c=400.)
    h = hessian(x, v, m, 400.)
    np.testing.assert_allclose(h[:3, :3], 3*np.eye(3)/400**2, rtol=1e-14, atol=0.)
    np.testing.assert_allclose(h[:3, 3:], np.diag([-4., -3.5, -3.5])/400**2, rtol=1e-14, atol=0.)
    expected = np.linalg.solve(np.diag(np.repeat(m, 3))+h, h@b.ravel()).reshape(2, 3)
    np.testing.assert_allclose(response['test'][1], expected, rtol=2e-14, atol=1e-23)
    np.testing.assert_array_equal(response['zero'][0], v)
    np.testing.assert_array_equal(response['zero'][1], v)
    assert max(diagnostics['solve_relative'].values()) < 5e-13
    assert diagnostics['block_precision50_to70_relative'] < 1e-30


def test_distant_internal_pair_cancellation_has_analytic_nonzero_response():
    # Along x: -(4/c²)[2/(D+1)-2/(D-1)] = 16/[c²(D²-1)].
    x = np.array([[-1., 0., 0.], [1., 0., 0.], [1e14, 0., 0.]])
    b = np.array([[1., 0., 0.], [-2., 0., 0.], [0., 0., 0.]])
    masses = np.array([2., 1., .1]); components = {'pair':b}
    actual, diagnostics = formulas.mixed_responses(x, np.zeros_like(x), masses, components, SIUnits(1., 1., 1.), c=400.)
    with localcontext() as context:
        context.prec = 80
        expected = Decimal(16)/(Decimal(400)**2*(Decimal('1e14')**2-1))
    assert actual['pair'][0][2, 0] == pytest.approx(float(expected), rel=5e-13, abs=0.)
    assert diagnostics['block_precision50_to70_relative'] < 1e-30
    low = block_responses(x, np.zeros_like(x), masses, components, 1., 400., 50)
    high = block_responses(x, np.zeros_like(x), masses, components, 1., 400., 70)
    assert agreement(low, high) < 1e-30


def test_response_is_invariant_under_body_permutation():
    x, v, m, _ = geometry(); b = np.array([[.1, -.2, .3], [.2, .1, -.1], [.01, .03, -.02]])
    units = SIUnits(1., 1., 1.); perm = [2, 0, 1]
    first, _ = formulas.mixed_responses(x, v, m, {'b':b}, units, c=400.)
    second, _ = formulas.mixed_responses(x[perm], v[perm], m[perm], {'b':b[perm]}, units, c=400.)
    for i in (0, 1):
        np.testing.assert_allclose(second['b'][i], first['b'][i][perm], rtol=2e-14, atol=0.)


def test_small_body_error_is_not_hidden_by_large_body_or_epsilon():
    expected = np.array([[1e10, 0., 0.], [1e-20, 0., 0.]])
    wrong = expected.copy(); wrong[1] = 0.
    assert formulas.vector_relative(wrong-expected, expected) == 1.
    with pytest.raises(ValueError, match='exact zero'):
        formulas.relative([1e-100], [0.])


def test_statistics_use_explicit_velocity_units_and_label_proxy_as_unqualified():
    values = np.array([[3., 4., 0.], [0., 0., 2.]])
    row = audit.statistics(values, [0., 1.], 'm/s', 'velocity')
    assert row['maximum'] == 5. and row['rms'] == pytest.approx(np.sqrt(14.5))
    assert row['unit'] == 'm/s' and row['ballistic_proxy_m'] == 5*audit.YEAR
    assert row['ballistic_proxy_is_error_bound'] is False


@pytest.mark.parametrize('bad', ['missing_field', 'missing_body_samples', 'missing_derivative', 'duplicate_epoch',
    'missing_solve', 'bad_bridge', 'missing_neptune', 'wrong_unit', 'proxy_claimed_as_bound'])
def test_incomplete_evidence_does_not_qualify_even_with_true_flags(bad):
    row = lambda:dict(hessian={k:1e-15 for k in audit.MIXED},
        spin={k:1e-15 for k in ('force', 'velocity_shift', 'omega')},
        identities=dict(linear=1e-16, angular=1e-16, missing_velocity=.1, missing_source_reaction=.5),
        matrix=dict(minimum_eigenvalue=1., block_precision50_to70_relative=1e-40,
            solve_relative={k:1e-16 for k in audit.MIXED}))
    def stats(name):
        # A proxy far above 1km must not fail an arithmetic qualification.
        proxy = 2*audit.YEAR if name in audit.VELOCITIES else audit.YEAR**2
        return dict(unit='m/s' if name in audit.VELOCITIES else 'm/s2', maximum=2., rms=2., initial=2.,
            final=2., worst_seconds=0., ballistic_proxy_m=proxy, ballistic_proxy_is_error_bound=False)
    fields = {k:dict(bodies={n:stats(k) for n in audit.de.NAMES}, moon_relative=stats(k))
        for k in audit.ACCELERATIONS+audit.VELOCITIES}
    report = dict(complete=True, samples=440, fields=fields,
        bridges=[row() for _ in range(440)], derivatives=[dict(index=i, checks_passed=True) for i in audit.INDICES])
    assert audit.qualification(report)
    if bad == 'missing_field': report['fields'].pop(next(iter(report['fields'])))
    if bad == 'missing_body_samples': report['samples'] = 439
    if bad == 'missing_derivative': report['derivatives'].pop()
    if bad == 'duplicate_epoch': report['derivatives'][-1]['index'] = 0
    if bad == 'missing_solve': report['bridges'][17]['matrix']['solve_relative'] = {}
    if bad == 'bad_bridge': report['bridges'][17]['spin']['force'] = 1e-7
    if bad == 'missing_neptune': report['fields']['so_velocity_shift']['bodies'].pop('Neptune')
    if bad == 'wrong_unit': report['fields']['so_velocity_shift']['moon_relative']['unit'] = 'm/s2'
    if bad == 'proxy_claimed_as_bound': report['fields']['moon_pnq_first']['moon_relative']['ballistic_proxy_is_error_bound'] = True
    assert not audit.qualification(report)


def test_existing_failed_audit_is_preserved_before_reader_load(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    target = tmp_path/'.tools'/'failed.json'; target.parent.mkdir()
    target.write_text('{"checks_passed":false}', encoding='utf8')
    with pytest.raises(ValueError, match='preserve failures'):
        audit.run(target, tmp_path/'missing-reader.json')
    assert target.read_text(encoding='utf8') == '{"checks_passed":false}'


@pytest.mark.parametrize('bad', ['spin_nan', 'source_bool', 'coincident', 'strong_field'])
def test_spin_diagnostic_rejects_unsupported_input(bad):
    x, v, m, s = geometry(); source = 0
    if bad == 'spin_nan': s[0] = np.nan
    if bad == 'source_bool': source = False
    if bad == 'coincident': x[1] = x[0]
    if bad == 'strong_field': v[0, 0] = 10.
    with pytest.raises(ValueError):
        formulas.spin_orbit(x, v, m, s, source, g=1., c=400.)
