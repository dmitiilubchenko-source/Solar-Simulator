"""Analytic Kepler solution validates production DOP853 independently of solve_ivp."""
from dataclasses import replace
from math import cos, sin, sqrt, pi

import pytest

from solar_simulator.accuracy import evolve_accurate
from solar_simulator.experiment import Settings, advance, create_experiment, preset
from solar_simulator.simulation import AU, Body, sun_earth, total_energy
from solar_simulator.storage import from_document, to_document, save, load
from solar_simulator.vector3 import Vector3


from scripts.assess_accuracy import kepler_relative


@pytest.mark.parametrize("eccentricity", [0, .3, .6, .9])
def test_adaptive_orbit_against_analytic_kepler(eccentricity):
    bodies, period = sun_earth(eccentricity)
    maximum_position = maximum_velocity = 0
    energy = total_energy(bodies)
    for i in range(1, 101):
        bodies = evolve_accurate(bodies, period/100)
        expected_r, expected_v = kepler_relative(eccentricity, i/100, period)
        actual_r = bodies[1].position.subtract(bodies[0].position)
        actual_v = bodies[1].velocity.subtract(bodies[0].velocity)
        maximum_position = max(maximum_position, actual_r.distance_to(expected_r))
        maximum_velocity = max(maximum_velocity, actual_v.distance_to(expected_v))
    # Bounds measured over a whole period, including high-eccentricity pericentre.
    assert maximum_position < 100, maximum_position
    assert maximum_velocity < 1e-3, maximum_velocity
    assert abs((total_energy(bodies)-energy)/energy) < 1e-10


def test_accurate_checkpoint_resume(tmp_path):
    original = preset("sun-earth")
    settings = replace(original.settings, integrator="dop853", dt=original.settings.dt*40)
    original = create_experiment(original.bodies, settings)
    whole = advance(original, 100)
    partial = advance(original, 50)
    save(partial, tmp_path/"state.json")
    restored = load(tmp_path/"state.json")
    assert to_document(restored) == to_document(partial)
    resumed = advance(restored, 50)
    for a, b in zip(resumed.bodies, whole.bodies):
        # Adaptive restart is numerically close, not bitwise equivalent.
        assert a.position.distance_to(b.position) < 100
        assert a.velocity.distance_to(b.velocity) < 1e-3


def test_free_motion_in_shifted_frame_and_metadata():
    b = Body("free", 2, Vector3(1e12, -2e12, 3e12), Vector3(10, 20, -30), spin=Vector3(1, 2, 3))
    result = evolve_accurate([b], 100)[0]
    assert result.position.distance_to(b.position.add(b.velocity.multiply(100))) == 0
    assert result.velocity.distance_to(b.velocity) == 0
    assert result.spin.distance_to(b.spin) == 0


@pytest.mark.parametrize("values", [{"rtol":0}, {"rtol":1e-16}, {"position_atol":True},
    {"velocity_atol":float("nan")}, {"integrator":"unknown"}, {"backend":"rust", "integrator":"dop853"}])
def test_invalid_accuracy_settings(values):
    with pytest.raises(ValueError):
        Settings(1, **values)


def test_contacts_cannot_silently_use_point_mass_solver():
    experiment = preset("spheres")
    settings = replace(experiment.settings, integrator="dop853")
    with pytest.raises(ValueError, match="точечные"):
        create_experiment(experiment.bodies, settings)
    with pytest.raises(ValueError, match="точечные"):
        advance(replace(experiment, settings=settings), 10)


def test_v2_checkpoint_migration_is_exact_and_non_mutating():
    document = to_document(preset("sun-earth", backend="rust"))
    document["schema_version"] = 2
    del document["orientation_work"]
    del document["origin"]
    for key in ("integrator", "rtol", "position_atol", "velocity_atol", "physics", "figures"):
        del document["settings"][key]
    restored = from_document(document)
    assert restored.settings.integrator == "verlet"
    assert restored.settings.backend == "rust"
    assert "integrator" not in document["settings"]
    assert to_document(restored)["schema_version"] == 7


def test_point_mass_singularity_fails_explicitly():
    b = Body("a", 1, Vector3(0, 0, 0), Vector3(0, 0, 0))
    with pytest.raises(ValueError, match="Совпадающие"):
        evolve_accurate([b, replace(b, name="b")], 1)


def test_equilateral_three_body_solution():
    # Equal masses at the vertices form an exact rigidly rotating solution.
    # Independent three-body oracle exercises every pair in the production RHS.
    from solar_simulator.simulation import G
    mass, radius = 1e24, 1e9
    omega = sqrt(G*mass/(sqrt(3)*radius**3))
    period = 2*pi/omega
    initial = [Body(str(i), mass,
        Vector3(radius*cos(i*2*pi/3), radius*sin(i*2*pi/3), 0),
        Vector3(-omega*radius*sin(i*2*pi/3), omega*radius*cos(i*2*pi/3), 0)) for i in range(3)]
    result = evolve_accurate(initial, period*.25)
    for i, b in enumerate(result):
        angle = i*2*pi/3+pi/2
        expected = Vector3(radius*cos(angle), radius*sin(angle), 0)
        assert b.position.distance_to(expected) < 1


def test_accurate_rotation_translation_and_boost():
    from scripts.assess_accuracy import kepler_relative
    initial, period = sun_earth(.6)
    shift, boost = Vector3(3e11, -2e11, 4e11), Vector3(500, -800, 300)
    def rotate(v):
        return Vector3(v.z, v.x, v.y)
    transformed = [replace(b, position=rotate(b.position).add(shift),
                           velocity=rotate(b.velocity).add(boost)) for b in initial]
    result = evolve_accurate(transformed, period/2)
    baseline = evolve_accurate(initial, period/2)
    for a, b in zip(baseline, result):
        assert rotate(a.position).add(shift).add(boost.multiply(period/2)).distance_to(b.position) < 10
        assert rotate(a.velocity).add(boost).distance_to(b.velocity) < 1e-5


def test_longer_orbit_against_analytic_solution():
    initial, period = sun_earth(.6)
    result = evolve_accurate(initial, period*10)
    expected_r, expected_v = kepler_relative(.6, 10, period)
    assert result[1].position.subtract(result[0].position).distance_to(expected_r) < 1000
    assert result[1].velocity.subtract(result[0].velocity).distance_to(expected_v) < 1e-3


def test_model_integrator_mismatch_rejected():
    document = to_document(preset("sun-earth"))
    document["settings"]["integrator"] = "dop853"
    with pytest.raises(ValueError, match="модель"):
        from_document(document)


def test_adaptive_tolerance_comparison_is_not_richardson():
    from solar_simulator.convergence import compare_steps
    experiment=preset("sun-earth")
    experiment=replace(experiment,settings=replace(experiment.settings,integrator="dop853"))
    result=compare_steps(experiment,4000)
    assert result["comparison"]=="adaptive_tolerances"
    assert len({r["final_time_seconds"] for r in result["runs"]})==1
    assert result["finest_position_error_estimate_metres"] is None
    assert all(value<100 for value in result["position_differences_metres"])
    experiment=replace(experiment,settings=replace(experiment.settings,rtol=3e-14))
    with pytest.raises(ValueError,match="float64"):
        compare_steps(experiment,1)
