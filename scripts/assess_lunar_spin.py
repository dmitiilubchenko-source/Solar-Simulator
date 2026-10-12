"""One-epoch lunar rigid surrogate: 32-day conservative independent audit."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from solar_simulator.rotation import integrate, invariants, rotation_matrix, RigidFigure
from solar_simulator.spin_initial import lunar_solid_equivalent_initial
# The existing independent matrix implementation is unchanged; include SHA.
from assess_rotation import reference, reference_difference, production_as_matrix

POLICY = dict(energy_relative=1e-8, angular_momentum_relative=1e-8,
    quaternion_norm=1e-8, reference_difference=1e-7, reference_uncertainty=1e-8,
    initial_rotation=3e-12, initial_omega_per_second=1e-17)


def assess():
    figure, point, initial, data = lunar_solid_equivalent_initial()
    times = np.linspace(0, 32*86400., 129)
    spin_scale = np.linalg.norm(initial[10:])
    atol = np.array([1e-4]*3+[1e-10]*3+[1e-13]*4+[spin_scale*1e-13]*3)
    states = integrate(figure, initial, times, point_mass=point, rtol=1e-11, atol=atol, max_step=21600.)
    strict = integrate(figure, initial, times, point_mass=point, rtol=3e-13, atol=atol*.03, max_step=10800.)
    refs = [reference(figure, initial, times, point, tol, 21600.) for tol in (3e-12, 3e-13)]
    values = [invariants(figure, state, point) for state in states]
    energy = np.array([v[0] for v in values])
    angular = np.array([v[1] for v in values])
    oracle = json.loads((ROOT/"docs/orientation-spice-reference.json").read_text())
    oracle0 = next(v for v in oracle["samples"] if v["time_seconds"] == 0)
    r0, rd0 = np.array(oracle0["rotation"]), np.array(oracle0["derivative_per_second"])
    omega0 = .5*sum(np.cross(r0[:, i], rd0[:, i]) for i in range(3))
    from solar_simulator.rotation import angular_velocity
    metrics = dict(energy_relative=float(np.max(abs(energy-energy[0]))/abs(energy[0])),
        angular_momentum_relative=float(np.max(np.linalg.norm(angular-angular[0], axis=1))/np.linalg.norm(angular[0])),
        quaternion_norm=float(np.max(abs(np.linalg.norm(states[:, 6:10], axis=1)-1))),
        reference_difference=reference_difference(production_as_matrix(states, True), refs[-1], initial, True),
        reference_uncertainty=reference_difference(refs[0], refs[1], initial, True),
        production_sensitivity=reference_difference(production_as_matrix(states, True), production_as_matrix(strict, True), initial, True),
        initial_rotation=float(np.linalg.norm(rotation_matrix(initial[6:10])-r0)),
        initial_omega_per_second=float(np.linalg.norm(angular_velocity(figure, initial[6:10], initial[10:])-omega0)))
    # Only after ALL free trajectories exist: compare orientations with the
    # later ephemeris, which cannot influence the already finished integration.
    from solar_simulator.orientation import lunar_rotation
    residuals = []
    for time, state in zip(times, states):
        difference = rotation_matrix(state[6:10]).T@lunar_rotation(float(time))[0]
        # atan2 avoids arccos loss of precision near zero.
        sine = .5*np.array([difference[2, 1]-difference[1, 2], difference[0, 2]-difference[2, 0], difference[1, 0]-difference[0, 1]])
        residuals.append(float(np.arctan2(np.linalg.norm(sine), .5*(np.trace(difference)-1))))
    # Common isotropic mean shift is observational sensitivity, not a new
    # fit or independently known error covariance for the three moments.
    sensitivity = []
    for sign in [-1, 1]:
        delta = sign*data["normalized_mean_uncertainty"]*figure.mass*data["reference_radius_m"]**2
        alternate = RigidFigure(figure.mass, tuple(np.array(figure.moments)+delta), figure.bounding_radius)
        start = initial.copy()
        omega = angular_velocity(figure, initial[6:10], initial[10:])
        r = rotation_matrix(initial[6:10])
        start[10:] = r@(np.array(alternate.moments)*(r.T@omega))
        varied = integrate(alternate, start, times, point_mass=point, rtol=1e-11, atol=atol, max_step=21600.)
        matrix_errors = [np.linalg.norm(rotation_matrix(a[6:10])-rotation_matrix(b[6:10])) for a,b in zip(states, varied)]
        sensitivity.append(dict(common_mean_shift_sigma=sign, max_rotation_frobenius=float(max(matrix_errors))))
    paths = ["src/solar_simulator/rotation.py", "src/solar_simulator/spin_initial.py",
        "src/solar_simulator/orientation.py", "scripts/assess_rotation.py", "scripts/assess_lunar_spin.py",
        "scripts/build_lunar_spin.py", "tests/test_spin_initial.py",
        "src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json", "docs/orientation-spice-reference.json"]
    return dict(model=data["model"], epoch_jd_tdb=data["epoch_jd_tdb"], frame=data["frame"],
        policy=POLICY, duration_seconds=float(times[-1]), sample_times_seconds=times.tolist(),
        initial=initial.tolist(), moments_kg_m2=figure.moments, point_mass_kg=point,
        production_rtol=[1e-11, 3e-13], production_atol=atol.tolist(),
        reference_rtol=[3e-12, 3e-13], reference_atol="0.01 rtol on scaled variables",
        production_max_steps_seconds=[21600, 10800], reference_max_step_seconds=21600,
        metrics=metrics, common_mean_inertia_sensitivity=sensitivity,
        ephemeris_comparison_after_free_run=dict(max_rotation_residual_rad=max(residuals),
            final_rotation_residual_rad=residuals[-1], residuals_rad=residuals,
            interpretation="Model discrepancy, no physical accuracy pass criterion; omitted solar forcing/core/distortions/relativity/higher moments"),
        code_and_data_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        passed=all(metrics[key] < limit for key,limit in POLICY.items()))


if __name__ == "__main__":
    path = ROOT/"docs/lunar-spin-initial-validation.json"
    if path.exists():
        raise FileExistsError("Preserve the previous audit")
    result = assess()
    path.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2), "PASS" if result["passed"] else "FAIL")
    print("Later DE441 orientation discrepancy [rad]", result["ephemeris_comparison_after_free_run"]["max_rotation_residual_rad"])
    sys.exit(0 if result["passed"] else 1)
