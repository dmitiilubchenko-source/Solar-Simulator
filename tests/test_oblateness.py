"""J2 checks: analytic limits, potential variation, symmetries and independent integration."""
from copy import deepcopy
from dataclasses import replace
from math import pi, sqrt

import numpy as np
import pytest

from solar_simulator.accuracy import evolve_accurate
from solar_simulator.cli import main, report
from solar_simulator.diagnostics import model_invariants
from solar_simulator.ephemerides import solar_system
from solar_simulator.experiment import Settings, advance, create_experiment, preset, reset
from solar_simulator.oblateness import FixedJ2, acceleration, earth_j2, orbital_torque, potential_energy, prepare
from solar_simulator.simulation import Body, G
from solar_simulator.storage import from_document, load, save, to_document, SCHEMA_VERSION
from solar_simulator.vector3 import Vector3
from scripts.assess_oblateness import independent_j2, independent_reference, sample
from scripts.fetch_figure_profile import earth_pole


def pair():
    return [Body("A", 2/G, Vector3(-1, 0, 0), Vector3(0, -.1, 0)),
            Body("B", .3/G, Vector3(4, 2, 3), Vector3(.1, .2, .1))]


def arrays(bodies):
    return np.array([[b.position.x, b.position.y, b.position.z] for b in bodies], dtype=float), np.array([b.mass for b in bodies])


@pytest.mark.parametrize("position,expected", [((5, 0, 0), (-1, 0, 0)), ((0, 0, 5), (0, 0, 2))])
def test_equatorial_and_polar_force_and_finite_mass_reaction(position, expected):
    bodies = [Body("A", 2/G, Vector3(0, 0, 0), Vector3(0, 0, 0)),
              Body("B", .3/G, Vector3(*position), Vector3(0, 0, 0))]
    f = FixedJ2("A", .005, 1, (0, 0, 1))
    p, m = arrays(bodies)
    result = acceleration(p, m, prepare(bodies, (f,)))
    assert np.allclose(result[1], np.array(expected)*1.5*2*.005/5**4, rtol=2e-15, atol=1e-20)
    assert np.allclose(m[0]*result[0], -m[1]*result[1], rtol=2e-15, atol=1e-10)


def test_force_from_independent_complex_step_potential_gradient_multiple_figures():
    bodies = pair()+[Body("C", .7/G, Vector3(2, -3, 1), Vector3(0, 0, 0))]
    figures = (FixedJ2("A", .003, .4, (0, 0, 1)), FixedJ2("C", -.002, .2, (.6, .8, 0)))
    p, m = arrays(bodies)
    # Potential is directly the unnormalized Legendre P2 expansion.
    def energy(q):
        value = 0
        for f in figures:
            i = [b.name for b in bodies].index(f.body)
            for j in range(len(bodies)):
                if i != j:
                    r = q[j]-q[i]
                    length = np.sqrt(r @ r)
                    p2 = (3*(r @ np.array(f.axis)/length)**2-1)/2
                    value += G*m[i]*m[j]/length*f.coefficient*(f.reference_radius/length)**2*p2
        return value
    gradient = np.zeros_like(p)
    for i in range(len(bodies)):
        for k in range(3):
            q = p.astype(complex); q[i, k] += 1e-25j
            gradient[i, k] = energy(q).imag/1e-25
    actual = acceleration(p, m, prepare(bodies, figures))
    assert np.allclose(actual, -gradient/m[:, None], rtol=2e-14, atol=1e-19)
    assert potential_energy(bodies, figures) == pytest.approx(energy(p), rel=2e-15)


def test_tensor_force_rotation_translation_and_axis_reversal():
    bodies = pair()
    f = FixedJ2("A", .003, .4, (.6, .8, 0))
    p, m = arrays(bodies)
    a = acceleration(p, m, prepare(bodies, (f,)))
    tensor = f.coefficient*f.reference_radius**2*(3*np.outer(f.axis, f.axis)-np.eye(3))
    assert np.allclose(a, independent_j2(p, G*m, [(0, tensor)]), rtol=2e-14, atol=1e-19)
    rotation, _ = np.linalg.qr(np.random.default_rng(30).normal(size=(3, 3)))
    rotated = replace(f, axis=tuple(map(float, np.array(f.axis) @ rotation)))
    prepared = ((0, rotated.coefficient, rotated.reference_radius, np.array(rotated.axis)),)
    assert np.allclose(acceleration(p@rotation+10, m, prepared), a@rotation, rtol=3e-14, atol=1e-19)
    reversed_axis = replace(f, axis=tuple(-x for x in f.axis))
    assert np.array_equal(acceleration(p, m, prepare(bodies, (reversed_axis,))), a)


@pytest.mark.parametrize("values", [dict(coefficient=0), dict(coefficient=True), dict(coefficient=.02),
    dict(coefficient=float("nan")), dict(reference_radius=0), dict(reference_radius=True),
    dict(axis=(0, 0, 2)), dict(axis=(True, 0, 0)), dict(axis=[0, 0, 1]), dict(body=""), dict(provenance="")])
def test_invalid_fixed_figure(values):
    original = dict(body="A", coefficient=.005, reference_radius=1, axis=(0, 0, 1))
    with pytest.raises(ValueError):
        FixedJ2(**dict(original, **values))


def test_guards_no_silent_wrong_backend_or_inside_source():
    f = FixedJ2("A", .005, 1, (0, 0, 1))
    for values in (dict(), dict(integrator="verlet"), dict(integrator="dop853", backend="rust"), dict(figures=(f, f))):
        with pytest.raises(ValueError):
            Settings(1, **dict(dict(figures=(f,)), **values))
    settings = Settings(1, integrator="dop853", figures=(f,))
    for bodies in ([replace(pair()[0], name="C")], [replace(pair()[0], radius=1)],
                   [replace(pair()[0], spin=Vector3(0, 0, 1))],
                   [pair()[0], replace(pair()[1], position=Vector3(-1, 0, .9))]):
        with pytest.raises(ValueError):
            create_experiment(bodies, settings)
    bodies = pair(); p, m = arrays(bodies)
    prepared = prepare(bodies, (f,)); p[1] = p[0]+[0, 0, .5]
    with pytest.raises(ValueError, match="радиуса"):
        acceleration(p, m, prepared)
    with pytest.raises(ValueError):
        earth_j2(*solar_system())


def test_newtonian_fixed_axis_energy_momentum_and_axis_angular_projection():
    a, e, fraction = 10, .3, .3/2.3
    r = a*(1-e); speed = sqrt(2.3*(1+e)/r)
    bodies = [Body("A", 2/G, Vector3(-fraction*r, 0, 0), Vector3(0, -fraction*speed*.8, -fraction*speed*.6)),
              Body("B", .3/G, Vector3((1-fraction)*r, 0, 0), Vector3(0, (1-fraction)*speed*.8, (1-fraction)*speed*.6))]
    figures = (FixedJ2("A", .005, 1, (0, 0, 1)),)
    period = 2*pi*sqrt(a**3/2.3)
    initial = create_experiment(bodies, Settings(period/32, integrator="dop853", figures=figures, rtol=3e-14,
                                                position_atol=1e-12, velocity_atol=1e-14))
    e0, p0, l0 = model_invariants(bodies, figures=figures)
    state = initial
    maximum_l = 0
    for _ in range(32):
        state = advance(state, 1)
        energy, momentum, angular = model_invariants(state.bodies, figures=figures)
        assert abs((energy-e0)/e0) < 1e-11
        assert momentum.distance_to(p0) < 1e-11*sum(b.mass*b.velocity.magnitude() for b in bodies)
        assert abs((angular.z-l0.z)/l0.z) < 1e-11
        maximum_l = max(maximum_l, angular.distance_to(l0)/l0.magnitude())
    assert maximum_l > 1e-5  # Full orbital L is physically not conserved.
    assert report(state)["orbital_angular_momentum_conserved"] is False
    assert reset(state).settings.figures == figures


def test_orbital_torque_is_rate_of_orbital_angular_momentum():
    bodies = pair(); figures = (FixedJ2("A", .005, 1, (0, 0, 1)),)
    p, m = arrays(bodies)
    a = acceleration(p, m, prepare(bodies, figures))
    def angular_at(h):
        changed = [replace(b, position=b.position.add(b.velocity.multiply(h)),
                           velocity=b.velocity.add(Vector3(*map(float, ai)).multiply(h))) for b, ai in zip(bodies, a)]
        return model_invariants(changed)[2]
    h = 1e-3
    derivative = angular_at(h).subtract(angular_at(-h)).divide(2*h)
    torque = orbital_torque(bodies, figures)
    assert derivative.distance_to(torque)/torque.magnitude() < 1e-8


def test_pole_frame_conversion_and_pinned_profile():
    kernel = b"\\begindata\n BODY399_POLE_RA = ( 0 0 0 )\n BODY399_POLE_DEC = ( 90 0 0 )\n\\begintext"
    axis, _, _ = earth_pole(kernel, 2451545.0)
    assert axis == pytest.approx([0, .3977771559319137, .9174820620691818], abs=1e-15)
    initial, origin = solar_system(resolved_moon=True)
    figure, = earth_j2(initial, origin)
    assert figure.coefficient == .00108262539 and figure.reference_radius == 6378136.6
    assert .002 < figure.axis[0] < .003 and .397 < figure.axis[1] < .399
    assert "376cd6f676" in figure.provenance and "3dff7b1d" in figure.provenance


@pytest.mark.parametrize("physics", ["newtonian", "eih-1pn"])
def test_checkpoint_resume_and_explicit_model_tag(tmp_path, physics):
    initial, origin = solar_system(resolved_moon=True)
    figures = earth_j2(initial, origin)
    state = create_experiment(initial, Settings(86400, integrator="dop853", physics=physics, figures=figures), origin=origin)
    partial = advance(state, 16)
    path = tmp_path/"j2.json"; save(partial, path)
    restored = load(path)
    assert restored.settings.figures == figures and to_document(restored) == to_document(partial)
    resumed, whole = advance(restored, 16), advance(state, 32)
    for a, b in zip(resumed.bodies, whole.bodies):
        assert a.position.distance_to(b.position) < 10
        assert a.velocity.distance_to(b.velocity) < 1e-4
    assert report(resumed)["energy_joules"] == model_invariants(resumed.bodies, physics, figures)[0]
    assert "fixed axes" in report(resumed)["conservation_scope"]
    document = to_document(partial)
    assert document["model"].endswith("-fixed-j2")
    for field, value in (("axis", [0, 0, 2]), ("body", "missing"), ("coefficient", True)):
        bad = deepcopy(document); bad["settings"]["figures"][0][field] = value
        with pytest.raises(ValueError):
            from_document(bad)
    bad = deepcopy(document); bad["model"] = physics+"-dop853"
    with pytest.raises(ValueError, match="Физическая модель"):
        from_document(bad)


@pytest.mark.parametrize("physics", ["newtonian", "eih-1pn"])
def test_v5_migration_does_not_enable_figures_or_mutate_input(physics):
    state = preset("solar-system-moon")
    document = to_document(replace(state, settings=replace(state.settings, physics=physics)))
    document["schema_version"] = 5; del document["settings"]["figures"]
    del document["orientation_work"]
    before = deepcopy(document)
    restored = from_document(document)
    assert document == before and restored.settings.physics == physics and restored.settings.figures == ()
    assert to_document(restored)["schema_version"] == SCHEMA_VERSION


def test_cli_j2_roundtrip_and_tolerance_diagnostics(tmp_path, capsys):
    from solar_simulator.convergence import compare_tolerances
    path, output = tmp_path/"initial.json", tmp_path/"final.json"
    assert main(["new", "solar-system-moon", str(path), "--physics", "eih-1pn", "--figures", "earth-j2"]) == 0
    assert main(["run", str(path), str(output), "--steps", "24"]) == 0
    state = load(output)
    assert len(state.settings.figures) == 1
    result = compare_tolerances(state, 24)
    assert result["figures"][0]["body"] == "Earth"
    assert "mixed J2/c^2" in capsys.readouterr().out


def test_month_against_independent_tensor_force_rk45_reference():
    initial, origin = solar_system(resolved_moon=True)
    figures = earth_j2(initial, origin)
    times = np.linspace(0, 32*86400, 33)
    reference, consistency = independent_reference(initial, figures, times)
    actual, _ = sample(initial, origin, times, figures)
    assert consistency < 10
    assert np.linalg.norm(actual[:, :, :3]-reference[:, :, :3], axis=2).max() < 10
    assert np.linalg.norm(actual[:, :, 3:]-reference[:, :, 3:], axis=2).max() < 1e-4
