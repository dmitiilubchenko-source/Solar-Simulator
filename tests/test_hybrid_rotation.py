"""Action-level checks for the synthetic harmonic EIH/rotor contract."""
from dataclasses import replace
from decimal import Decimal, localcontext

import numpy as np
import pytest

from scripts import hybrid_rotation as prod
from scripts import independent_hybrid_rotation as ref
from scripts import decimal_hybrid_rotation as high
from scripts import assess_hybrid_rotation as audit


def test_action_velocity_gradient_and_hessian_are_independently_consistent():
    model = prod.Model(); x, v, _, _ = prod.unpack(prod.initial(), model)
    p = np.array(model.masses)[:, None]*v+ref.momentum1(x, v, model.masses, model.c)
    for k in range(v.size):
        shifted = v.astype(complex); shifted.ravel()[k] += 1e-25j
        assert ref.action(x, shifted, model.masses, model.c).imag/1e-25 == pytest.approx(p.ravel()[k], rel=3e-14, abs=1e-17)
    h, _ = ref.derivatives(x, v, model.masses, model.c)
    np.testing.assert_allclose(prod.hessian(x, v, model.masses, model.c), h, rtol=3e-14, atol=1e-22)
    np.testing.assert_allclose(h, h.T, rtol=3e-14, atol=1e-22)


def test_finite_action_matches_euler_lagrange_and_reduced_residual():
    model = prod.Model(); state = prod.initial(); x, v, q, _ = prod.unpack(state, model)
    h, euler_force = ref.derivatives(x, v, model.masses, model.c)
    m = np.array(model.masses); full_mass = np.diag(np.repeat(m, 3))+h
    r = audit.matrices(state[None, :], 3)[0]
    fq, _, _ = ref.body_field(x, m, r, model.moments, model.source, model.radius)
    exact, *_ = prod.fields(state, model, 'finite-action')
    reduced, *_ = prod.fields(state, model, 'order-reduced')
    assert np.linalg.norm(full_mass@exact.ravel()-(euler_force+fq).ravel()) < 2e-15
    an, ap = prod.force_terms(x, v, m, model.c)
    aq, _, _ = prod.figure_field(x, m, q, model)
    expected = h@(ap+aq).ravel()
    residual = full_mass@reduced.ravel()-(euler_force+fq).ravel()
    assert np.linalg.norm(residual-expected)/np.linalg.norm(expected) < 1e-7


def test_mass_solve_rejects_indefinite_matrix_without_fallback():
    with pytest.raises(ValueError, match='positive definite'):
        prod.mass_solve([1., 1.], -2*np.eye(6), np.ones((2, 3)))


def test_newton_limit_and_source_reaction_survive_explicit_si_similarity():
    model = replace(prod.Model(), c=1e12); state = prod.initial(model)
    x, v, q, _ = prod.unpack(state, model)
    exact = prod.fields(state, model, 'finite-action')[0]
    reduced = prod.fields(state, model, 'order-reduced')[0]
    np.testing.assert_allclose(exact, reduced, rtol=1e-14, atol=1e-16)
    a, _, _ = prod.figure_field(x, model.masses, q, model)
    f = a*np.array(model.masses)[:, None]
    assert np.linalg.norm(f.sum(axis=0))/np.linalg.norm(f) < 1e-14


def test_scalar_action_noether_readout_matches_whole_decimal_rotor():
    model = prod.Model(); state = prod.initial(); n = 3
    x, v, q, spin = prod.unpack(state, model)
    r = audit.matrices(state[None, :], n)[0]
    ordinary = ref.quantities(state, model.masses, model.c, model.moments, 0, r)
    with localcontext() as context:
        context.prec = 90
        exact_r = high.matrix(list(map(high.dec, q)))
        expected = high.quantities([[high.dec(z) for z in row] for row in x], [[high.dec(z) for z in row] for row in v],
            list(map(high.dec, model.masses)), list(map(high.dec, model.moments)), 0,
            high.dec(model.radius), high.dec(model.c), exact_r, list(map(high.dec, spin)))
    scales = np.r_[abs(ordinary[0]), [1.]*3, [np.linalg.norm(ordinary[4:])]*3]
    assert np.max(abs(ordinary-np.array(list(map(float, expected))))/scales) < 3e-14


def test_whole_rotor_directional_identity_has_high_precision_and_order_controls():
    model = prod.Model(); state = prod.initial()
    low = high.snapshot(state, model, 70); strong = high.snapshot(state, model, 90)
    assert low['checks_passed'] and strong['checks_passed']
    assert high.precision_agreement(low, strong)['checks_passed']
    assert strong['missing_spin_torque_relative'] > .9
    assert audit.algebra(state, model)['checks_passed']


@pytest.mark.parametrize('precision', [30, 80, True])
def test_undeclared_decimal_precision_is_rejected(precision):
    with pytest.raises(ValueError, match='precision'):
        high.snapshot(prod.initial(), prod.Model(), precision)


def test_budget_error_cannot_be_diluted_by_more_orbits():
    values = []
    for n in (3, 30):
        state = np.zeros(6*n+21); state[6*n] = 1.
        solver = prod.HybridDOP853(lambda t,y:np.zeros_like(y), 0., state, 1., body_count=n)
        stages = np.zeros((len(solver.E5), len(state))); stages[0, -1] = 1.
        values.append(solver._estimate_error_norm(stages, .1, np.ones_like(state)))
    assert values[0] > 0 and values[0] == values[1]


@pytest.mark.parametrize('bad', ['missing_job', 'duplicate_epoch', 'missing_mode', 'failed', 'blind_source'])
def test_partial_scientific_report_cannot_qualify(bad):
    report = dict(complete=True, times=list(range(129)),
        jobs={m+'-'+s:{} for m in audit.MODES for s in ('nominal', 'tight', 'ref0', 'ref1')},
        cases={m:dict(checks_passed=True) for m in audit.MODES},
        identities=[dict(index=i, checks_passed=True, low=dict(checks_passed=True),
            high=dict(checks_passed=True, missing_spin_torque_relative=1.)) for i in range(0, 129, 16)],
        algebra=[dict(index=i, checks_passed=True) for i in range(0, 129, 16)],
        source_visibility=dict(checks_passed=True))
    assert audit.qualification(report)
    if bad == 'missing_job': report['jobs'].pop(next(iter(report['jobs'])))
    if bad == 'duplicate_epoch': report['identities'][-1]['index'] = 0
    if bad == 'missing_mode': report['cases'].pop('finite-action')
    if bad == 'failed': report['cases']['order-reduced']['checks_passed'] = False
    if bad == 'blind_source': report['source_visibility']['checks_passed'] = False
    assert not audit.qualification(report)


def test_existing_failure_is_preserved_before_input_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    output = tmp_path/'.tools'/'original.json'; output.parent.mkdir()
    output.write_text('{"checks_passed":false}', encoding='utf8')
    with pytest.raises(ValueError, match='preserve failures'):
        audit.run(output)
    assert output.read_text(encoding='utf8') == '{"checks_passed":false}'


@pytest.mark.parametrize('mode', audit.MODES)
@pytest.mark.parametrize('bad', ['strong_field', 'coincidence'])
def test_reference_rejects_unsupported_domain_before_force_or_action(mode, bad, monkeypatch):
    model = prod.Model(); y = prod.initial(); r = audit.matrices(y[None, :], 3)[0]
    initial = np.r_[y[:18], r.ravel(), r.T@y[22:25], np.zeros(14)]
    if bad == 'strong_field': initial[9] = .02*model.c
    else: initial[6:9] = initial[3:6]
    def forbidden(*args):
        raise AssertionError('Invalid geometry reached reference force')
    monkeypatch.setattr(ref, 'body_field', forbidden)
    with pytest.raises(ValueError, match='weak-field|distinct'):
        ref.rhs(0., initial, model.masses, model.c, model.moments, model.source, model.radius, mode)
