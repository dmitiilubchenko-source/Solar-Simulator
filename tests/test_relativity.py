"""1PN physics checks, independent analytic and variational oracles."""
from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest

from solar_simulator.accuracy import evolve_accurate
from solar_simulator.cli import main, report
from solar_simulator.diagnostics import model_invariants
from solar_simulator.experiment import Settings, advance, create_experiment, preset
from solar_simulator.relativity import C, eih_acceleration, invariants
from solar_simulator.simulation import G, Body, total_energy, total_momentum
from solar_simulator.storage import from_document, to_document, save, load
from solar_simulator.vector3 import Vector3
from scripts.assess_relativity import independent_acceleration, measure_precession, mercury_pair


def test_arbitrary_three_body_acceleration_against_scalar_equation():
    rng = np.random.default_rng(20261009)
    for count in (2, 3, 9):
        p, v, masses = rng.normal(size=(count, 3))*1e10, rng.normal(size=(count, 3))*1e5, rng.uniform(1e28, 1e29, count)
        expected = independent_acceleration(p, v, G*masses, C)
        assert np.allclose(eih_acceleration(p, v, masses), expected, rtol=2e-15, atol=1e-15)


def test_two_body_equal_mass_relative_acceleration_analytic():
    # General two-body 1PN relative equation in a Newtonian COM frame.
    mu, eta, radius = 2e20, .25, 1e10
    r, v = np.array([radius, 0., 0.]), np.array([1e4, 9e4, -2e4])
    p, velocities = np.array([-r/2, r/2]), np.array([-v/2, v/2])
    result = eih_acceleration(p, velocities, np.array([mu/(2*G)]*2))
    n, radial = r/radius, v[0]
    expected = -mu*n/radius**2 + mu/(radius**2*C**2)*(n*((4+2*eta)*mu/radius
        -(1+3*eta)*np.dot(v, v)+1.5*eta*radial**2)+(4-2*eta)*radial*v)
    assert np.allclose(result[1]-result[0], expected, rtol=2e-15, atol=1e-15)


def test_eih_force_from_independent_lagrangian_variation():
    # Dimensionless G=1. Complex-step derivatives of the published L1,
    # plus centred time differentiation along the Newtonian flow, give
    # a_1 = (dL1/dq - d/dt(dL1/dv))/m. No EIH acceleration formula here.
    p = np.array([[-1., .2, .3], [1., .3, -.2], [.5, -1.1, .1]])
    v = np.array([[.1, .4, .1], [-.4, .1, .3], [.2, -.3, -.2]])
    masses = np.array([2., .7, .4])
    c = 1e3
    def l1(q, speed):
        kinetic = sum(masses[i]*np.dot(speed[i], speed[i])**2/8 for i in range(3))
        pair = triple = 0
        for i in range(3):
            potential = 0
            for j in range(3):
                if i == j:
                    continue
                displacement = q[i]-q[j]
                radius = np.sqrt(np.dot(displacement, displacement))
                n = displacement/radius
                pair += masses[i]*masses[j]/(4*radius)*(3*np.dot(speed[i], speed[i])
                    +3*np.dot(speed[j], speed[j])-7*np.dot(speed[i], speed[j])
                    -np.dot(n, speed[i])*np.dot(n, speed[j]))
                potential += masses[j]/radius
            triple -= masses[i]*potential**2/2
        return kinetic+pair+triple
    def gradient(q, speed, field):
        result = np.zeros((3, 3))
        for i in range(3):
            for k in range(3):
                a, b = q.astype(complex), speed.astype(complex)
                (a if field=="q" else b)[i, k] += 1e-25j
                result[i, k] = l1(a, b).imag/1e-25
        return result
    newton = np.zeros_like(p)
    for i in range(3):
        for j in range(3):
            if i != j:
                delta = p[j]-p[i]
                newton[i] += masses[j]*delta/np.linalg.norm(delta)**3
    h = 1e-5
    dpdt = (gradient(p+h*v, v+h*newton, "v")-gradient(p-h*v, v-h*newton, "v"))/(2*h)
    expected_correction = (gradient(p, v, "q")-dpdt)/masses[:, None]
    actual_correction = (eih_acceleration(p, v, masses/G, c=c)-newton)*c*c
    assert np.allclose(actual_correction, expected_correction, rtol=2e-8, atol=2e-8)


def test_newtonian_limit_rotation_translation_and_time_reversal():
    rng = np.random.default_rng(9)
    p, v, masses = rng.normal(size=(3, 3))*1e10, rng.normal(size=(3, 3))*1e4, np.array([2e29, 1e29, 3e28])
    a = eih_acceleration(p, v, masses)
    rotation, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    assert np.allclose(eih_acceleration(p@rotation+1e12, v@rotation, masses), a@rotation, rtol=2e-13, atol=1e-15)
    assert np.array_equal(eih_acceleration(p, -v, masses), a)
    newton = independent_acceleration(p, v, G*masses, 1e100)
    assert np.allclose(eih_acceleration(p, v, masses, c=1e100), newton, rtol=2e-15)
    # Galilean boosts are intentionally not a symmetry of a fixed 1PN frame.


def test_free_particle_noether_quantities():
    b = Body("free", 5, Vector3(1, 2, 3), Vector3(1e5, 2e5, -3e5))
    energy, momentum, angular = invariants([b])
    v2 = b.velocity.dot(b.velocity)
    assert energy == pytest.approx(.5*b.mass*v2+.375*b.mass*v2**2/C**2, rel=2e-15)
    expected = b.velocity.multiply(b.mass*(1+.5*v2/C**2))
    assert momentum.distance_to(expected) < 1e-8
    assert angular.distance_to(b.position.cross(expected)) < 1e-8
    result = evolve_accurate([b], 100, physics="eih-1pn")[0]
    assert result.position.distance_to(b.position.add(b.velocity.multiply(100))) == 0


def test_eccentric_orbit_conserves_1pn_quantities_not_newtonian_energy():
    bodies, period, _ = mercury_pair()
    energy0, momentum0, angular0 = invariants(bodies)
    newton0, newton_p0 = total_energy(bodies), total_momentum(bodies)
    momentum_scale = sum(b.mass*b.velocity.magnitude() for b in bodies)
    max_energy = max_momentum = max_angular = max_newton = max_newton_p = 0.0
    for _ in range(32):
        bodies = evolve_accurate(bodies, period/32, physics="eih-1pn", rtol=3e-14)
        energy, momentum, angular = invariants(bodies)
        max_energy = max(max_energy, abs((energy-energy0)/energy0))
        max_momentum = max(max_momentum, momentum.distance_to(momentum0)/momentum_scale)
        max_angular = max(max_angular, angular.distance_to(angular0)/angular0.magnitude())
        max_newton = max(max_newton, abs((total_energy(bodies)-newton0)/newton0))
        max_newton_p = max(max_newton_p, total_momentum(bodies).distance_to(newton_p0)/momentum_scale)
    assert max_energy < 1e-11 and max_momentum < 1e-11 and max_angular < 1e-11
    assert max_newton > 1e-8 and max_newton_p > 1e-9


@pytest.mark.parametrize("values", [{"physics":"unknown"}, {"physics":"eih-1pn"},
    {"physics":"eih-1pn", "integrator":"verlet"},
    {"physics":"eih-1pn", "integrator":"dop853", "backend":"rust"}])
def test_invalid_model_settings(values):
    with pytest.raises(ValueError):
        Settings(1, **values)


def test_weak_field_and_spin_guards():
    b = Body("a", 1e30, Vector3(0, 0, 0), Vector3(0, 0, 0))
    settings = Settings(1, integrator="dop853", physics="eih-1pn")
    for changed in (replace(b, velocity=Vector3(.01*C, 0, 0)),
                    replace(b, spin=Vector3(0, 0, 1)), replace(b, radius=1)):
        with pytest.raises(ValueError):
            create_experiment([changed], settings)
    with pytest.raises(ValueError, match="слабого"):
        create_experiment([b, replace(b, name="b", position=Vector3(1e6, 0, 0))], settings)
    with pytest.raises(ValueError, match="Совпадающие"):
        evolve_accurate([b, replace(b, name="b")], 1, physics="eih-1pn")


@pytest.mark.parametrize("version", [3, 4])
def test_old_checkpoint_stays_newtonian(version):
    document = to_document(preset("sun-earth"))
    document["schema_version"] = version
    del document["orientation_work"]
    del document["settings"]["physics"]
    del document["settings"]["figures"]
    if version == 3:
        del document["origin"]
    before = deepcopy(document)
    restored = from_document(document)
    assert restored.settings.physics == "newtonian" and document == before
    assert to_document(restored)["schema_version"] == 7


def test_relativistic_checkpoint_fixed_frame_resume_and_diagnostics(tmp_path):
    initial = preset("solar-system")
    settings = replace(initial.settings, physics="eih-1pn", dt=86400)
    original = create_experiment(initial.bodies, settings, origin=initial.origin)
    # Large frame drift makes accidental recomputation in a COM frame visible.
    moved = [replace(b, velocity=b.velocity.add(Vector3(1e5, 2e4, -3e4))) for b in original.bodies]
    original = create_experiment(moved, settings)
    partial = advance(original, 30)
    save(partial, tmp_path/"pn.json")
    restored = load(tmp_path/"pn.json")
    assert to_document(restored) == to_document(partial)
    resumed, whole = advance(restored, 30), advance(original, 60)
    for a, b in zip(resumed.bodies, whole.bodies):
        assert a.position.distance_to(b.position) < 10
        assert a.velocity.distance_to(b.velocity) < 1e-5
    values = report(resumed)
    assert values["physics"] == "eih-1pn" and "O(c^-4)" in values["conservation_scope"]
    assert values["energy_joules"] == model_invariants(resumed.bodies, "eih-1pn")[0]
    assert values["energy_joules"] != total_energy(resumed.bodies)
    bad = to_document(restored); bad["model"] = "newtonian-dop853"
    with pytest.raises(ValueError, match="Физическая модель"):
        from_document(bad)


def test_relativistic_cli_roundtrip_and_tolerance_comparison(tmp_path, capsys):
    from solar_simulator.convergence import compare_tolerances
    path, output = tmp_path/"initial.json", tmp_path/"final.json"
    assert main(["new", "solar-system", str(path), "--physics", "eih-1pn"]) == 0
    assert main(["run", str(path), str(output), "--steps", "20"]) == 0
    state = load(output)
    assert state.settings.physics == "eih-1pn"
    assert compare_tolerances(state, 20)["physics"] == "eih-1pn"
    assert '"physics": "eih-1pn"' in capsys.readouterr().out


@pytest.mark.parametrize("physics", ["newtonian", "eih-1pn"])
def test_production_perihelion_advance(physics):
    result = measure_precession(physics, orbits=3)
    if physics == "newtonian":
        assert abs(result["measured_radians_per_orbit"]) < 1e-10
    else:
        assert result["relative_difference"] < 1e-4
        assert 42.9 < result["measured_arcsec_per_century"] < 43.1
