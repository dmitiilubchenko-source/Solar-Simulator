"""Independent analytic limits and sensitivity of the snapshot audit."""
from dataclasses import replace

import numpy as np
import pytest

from scripts import assess_lunar_coupling as audit
from scripts.independent_lunar_coupling import derivatives
from solar_simulator.rotation import RigidFigure


def test_complex_derivative_has_known_radial_force_and_power_in_si():
    moments = np.array([2., 3., 4.])
    # U = G m (3A-tr I)/(2r^3) = -15/r^3, with G=2 and m=5.
    force, torque, u, rate = derivatives([[10., 0., 0.]], [[.7, 0., 0.]],
        [5.], moments, np.eye(3), [0., 0., .2], 2.)
    np.testing.assert_allclose(force, [[-45/10**4, 0., 0.]], rtol=2e-14, atol=0.)
    np.testing.assert_array_equal(torque, np.zeros(3))
    assert u == pytest.approx(-15/10**3, rel=2e-14)
    assert rate == pytest.approx(45*.7/10**4, rel=2e-14)


def test_spatial_torque_sign_and_orientation_power_have_analytic_value():
    r = np.array([[10., 10., 0.]])
    radius = np.sqrt(200.)
    force, torque, _, rate = derivatives(r, np.zeros((1, 3)), [5.], [2., 3., 4.],
        np.eye(3), [0., 0., .2], 2.)
    expected = 15/radius**3
    np.testing.assert_allclose(torque, [0., 0., expected], rtol=2e-14, atol=0.)
    assert rate == pytest.approx(-.2*expected, rel=2e-14)
    np.testing.assert_allclose(np.cross(r[0], force[0])+torque, np.zeros(3), atol=1e-17)


def test_gravity_does_not_determine_mean_inertia_or_spin_energy():
    figure = RigidFigure(10., (20., 25., 30.), 3.)
    shifted = replace(figure, moments=tuple(i+4 for i in figure.moments))
    np.testing.assert_array_equal(figure.quadrupole, shifted.quadrupole)
    assert audit.coefficients(figure, 2.) == audit.coefficients(shifted, 2.)
    # Same measured angular velocity gives different kinetic energy and S.
    omega = np.array([.1, -.2, .3])
    assert .5*np.dot(figure.moments, omega**2) != .5*np.dot(shifted.moments, omega**2)


@pytest.mark.parametrize('radius', [0., -1., np.nan, np.inf])
def test_invalid_reference_radius_is_rejected(radius):
    with pytest.raises(ValueError):
        audit.coefficients(RigidFigure(10., (20., 25., 30.), 3.), radius)


def test_coupling_identity_uses_reaction_and_spin_power(monkeypatch):
    from scipy.spatial.transform import Rotation
    from solar_simulator.nbody_rotation import correction
    from solar_simulator.oblateness import PrescribedQuadrupole, prepare, acceleration
    from solar_simulator.orientation import PROFILE_SHA256
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    figure = RigidFigure(1e15, (2e20, 2.5e20, 3e20), 1000.)
    matrix = Rotation.from_rotvec([.3, -.2, .1]).as_matrix()
    q = np.roll(Rotation.from_matrix(matrix).as_quat(), 1)
    p = np.array([[0., 0., 0.], [12000., 7000., 1000.], [-50000., 30000., 20000.]])
    v = np.array([[0., 0., 0.], [.5, -1., .3], [-2., 1., 0.]])
    masses = np.array([figure.mass, 2e14, 5e15])
    # The named evaluator is only a bridge; core correction has no name dependency.
    bodies = [Body(n, m, Vector3(*x), Vector3(*u)) for n, m, x, u in zip(('Moon', 'Earth', 'star'), masses, p, v)]
    # Reference-radius rescaling represents the same tensor and leaves J2/C22
    # inside the prescribed evaluator's existing .01 coefficient domain.
    j2, c22 = audit.coefficients(figure, 3000.)
    descriptor = PrescribedQuadrupole('Moon', j2, 3000., c22, 'moon-de441', PROFILE_SHA256)
    import solar_simulator.orientation as orientation
    monkeypatch.setattr(orientation, 'lunar_rotation', lambda time: (matrix, np.zeros((3, 3))))
    field = acceleration(p, masses, prepare(bodies, (descriptor,)))
    args = (p, v, masses, 0, figure, q, matrix, np.array([.0001, -.0002, .002]), (0, 1, p[1]), field)
    _, checks, controls = audit.coupling_checks(*args)
    assert max(checks.values()) < 5e-12
    assert min(controls.values()) > 1e-3
    def no_reaction(*params):
        a, torque, energy = correction(*params)
        a[0] = 0.
        return a, torque, energy
    monkeypatch.setattr(audit, 'correction', no_reaction)
    _, broken, _ = audit.coupling_checks(*args)
    assert broken['linear'] > .1
    assert broken['prescribed_bridge'] > .1


@pytest.mark.parametrize('bad', ['empty', 'partial', 'missing_key', 'failed_force', 'failed_power', 'blind_control', 'nan'])
def test_incomplete_or_failed_scientific_evidence_cannot_qualify(bad):
    rows = [{k: 1e-15 for k in audit.CHECKS} for _ in range(440)]
    controls = [{k: .01 for k in audit.CONTROLS} for _ in range(440)]
    assert audit.qualification(rows, controls)
    if bad == 'empty': rows = []
    if bad == 'partial': rows.pop()
    if bad == 'missing_key': rows[123].pop('torque')
    if bad == 'failed_force': rows[123]['force'] = 1e-8
    if bad == 'failed_power': rows[123]['power'] = 1e-8
    if bad == 'blind_control':
        for r in controls: r['missing_torque'] = 0.
    if bad == 'nan': controls[123]['missing_spin_power'] = np.nan
    assert not audit.qualification(rows, controls)


def test_exact_zero_scale_cannot_hide_a_nonzero_defect():
    assert audit.fraction(0., 0.) == 0.
    with pytest.raises(ValueError, match='exact zero'):
        audit.fraction(1e-100, 0.)


def test_model_snapshot_compares_numeric_state_and_detects_a_real_change():
    from solar_simulator.experiment import create_experiment, Settings
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    def model(mass):
        return create_experiment([Body('star', mass, Vector3(1., 2., 3.), Vector3(0., 0., 0.))], Settings(1.))
    state = model(1e20)
    assert audit.model_snapshot(state) == audit.model_snapshot(state)
    assert audit.model_snapshot(state) == audit.model_snapshot(model(1e20))
    assert audit.model_snapshot(state) != audit.model_snapshot(model(2e20))


def test_existing_failed_audit_is_preserved_before_any_input_read(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    target = tmp_path/'.tools'/'failed.json'
    target.parent.mkdir()
    target.write_text('{"checks_passed":false}', encoding='utf8')
    with pytest.raises(ValueError, match='preserve failures'):
        audit.run(target, tmp_path/'nonexistent.json')
    assert target.read_text(encoding='utf8') == '{"checks_passed":false}'
