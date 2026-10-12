import json
from pathlib import Path

import numpy as np
import pytest

from scripts import assess_local_rotation as audit


def policy():
    return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


def passing_values(p):
    return (dict([(key, bound/2) for key, bound in p['maximum'].items()]
                 + [(key, bound*2) for key, bound in p['minimum'].items()]),
            {key: True for key in p['required_true']})


def test_independent_instantaneous_full_H_K_and_clock_basis_checks():
    p = policy(); metrics = audit.instantaneous(p)
    assert metrics and all(type(value) is float for value in metrics.values())
    for key, value in metrics.items():
        assert value < p['maximum'][key], (key, value)
    assert p['physical_lunar_mapping_certified'] is False
    assert p['physical_accuracy_certified'] is False
    json.dumps(metrics, allow_nan=False)


@pytest.mark.parametrize('category', ['maximum', 'minimum', 'required_true'])
def test_every_predeclared_criterion_is_required(category):
    p = policy(); metrics, confirmations = passing_values(p)
    assert audit.failures(metrics, confirmations, p) == []
    for key in p[category]:
        wrong_m, wrong_c = dict(metrics), dict(confirmations)
        if category == 'required_true': wrong_c[key] = False
        else: wrong_m[key] = p[category][key]
        assert audit.failures(wrong_m, wrong_c, p) == [key]


@pytest.mark.parametrize('bad', ['missing', 'extra', 'bool', 'nan', 'confirmation'])
def test_malformed_metrics_or_confirmations_rejected(bad):
    p = policy(); metrics, confirmations = passing_values(p)
    if bad == 'missing': metrics.pop(next(iter(metrics)))
    if bad == 'extra': metrics['undeclared'] = 0.
    if bad == 'bool': metrics[next(iter(metrics))] = True
    if bad == 'nan': metrics[next(iter(metrics))] = float('nan')
    if bad == 'confirmation': confirmations[next(iter(confirmations))] = 1
    with pytest.raises(ValueError): audit.failures(metrics, confirmations, p)


def test_source_discovery_includes_transitive_local_imports_and_rejects_edit(tmp_path, monkeypatch):
    sources = audit.source_hashes()
    for name in ['scripts/local_multipole.py', 'scripts/local_rotation_transfer.py',
                 'scripts/independent_local_multipole.py', 'scripts/assess_local_rotation.py',
                 'src/solar_simulator/rotation.py', 'src/solar_simulator/simulation.py',
                 'src/solar_simulator/relativity.py', 'src/solar_simulator/vector3.py']:
        assert name in sources
    root = tmp_path/'clone'; file = root/'src/solar_simulator/rotation.py'
    file.parent.mkdir(parents=True); file.write_text('# before\n', encoding='utf-8')
    (root/'scripts').mkdir(); (root/audit.POLICY).write_text('{}', encoding='utf-8')
    monkeypatch.setattr(audit, 'ROOT', root)
    before = audit.source_hashes(); monkeypatch.setattr(audit, 'LOADED_SOURCES', before)
    audit.check_sources()
    file.write_text('# after\n', encoding='utf-8')
    with pytest.raises(ValueError, match='changed'): audit.check_sources()


def test_audit_rejects_existing_outputs_before_integration(tmp_path, monkeypatch):
    root = tmp_path/'root'; root.mkdir(); (root/'scripts').mkdir()
    (root/audit.POLICY).write_text(json.dumps(policy()), encoding='utf-8')
    monkeypatch.setattr(audit, 'ROOT', root)
    monkeypatch.setattr(audit, 'LOADED_SOURCES', audit.source_hashes())
    def forbidden(*args, **kwargs): raise AssertionError('integrator must not be reached')
    monkeypatch.setattr(audit, 'solve_ivp', forbidden)
    old = root/'old.json'; old.write_bytes(b'existing result')
    with pytest.raises(FileExistsError): audit.audit(work=root/'new-work', output=old)
    assert old.read_bytes() == b'existing result'
    assert not (root/'new-work').exists()
    with pytest.raises(ValueError): audit.audit(work=tmp_path/'outside', output=root/'new.json')


def test_noncommuting_provider_and_reference_representation_preserve_body_spin():
    p = policy(); params, state, period, scales = audit.synthetic(p)
    b, qb, _ = audit.frame(.7*period, period, p)
    assert np.linalg.norm(np.asarray(b.basis_acceleration)) > 0
    matrix = audit.matrix_states(state[None, :])[:, 9:].reshape(3, 3)
    reference = np.r_[state[:6], matrix.T@state[6:9], matrix.ravel()][None, :]
    converted = audit.reference_states(reference)
    assert np.allclose(converted[0, :9], state[:9], rtol=1e-14, atol=0)
    assert np.array_equal(converted[0, 9:], matrix.ravel())
    assert scales.shape == (3,) and params.reduced_mass > 0
