"""Build a one-epoch lunar model input; never store future orientations."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from solar_simulator.ephemerides import solar_system
from solar_simulator.orientation import PROFILE_SHA256, lunar_rotation
from solar_simulator.simulation import G


def build():
    bodies, origin = solar_system(resolved_moon=True)
    by_name = {b.name: b for b in bodies}
    earth, moon = by_name["Earth"], by_name["Moon"]
    rotation, derivative = lunar_rotation(0.)
    # Williams et al. 2014 section 5: permanent mean solid moments, not
    # DE441 undistorted beta/gamma, nor whole-Moon fluid-core inertia.
    normalized_mean = .392728
    offsets = np.array([-.00011260, -.00002289, .00013549])
    reference_radius = 1738000.
    moments = moon.mass*reference_radius**2*(normalized_mean+offsets)
    position = earth.position.subtract(moon.position)
    velocity = earth.velocity.subtract(moon.velocity)
    return dict(schema_version=1, model="rigid-solid-equivalent", units="SI",
        epoch_jd_tdb=origin.epoch_jd_tdb, frame=origin.frame,
        relative_position="Earth minus Moon", source_center=origin.center,
        ephemeris=origin.ephemeris, parent_dataset_sha256=origin.dataset_sha256,
        orientation_profile_sha256=PROFILE_SHA256,
        moon_gm_m3_s2=moon.mass*G, earth_gm_m3_s2=earth.mass*G,
        gravitational_constant_m3_kg_s2=G, reference_radius_m=reference_radius,
        exclusion_radius_m=1800000., normalized_mean_solid_inertia=normalized_mean,
        normalized_mean_uncertainty=.000012, normalized_moment_offsets=offsets.tolist(),
        moments_kg_m2=moments.tolist(), rotation=rotation.tolist(),
        rotation_derivative_per_second=derivative.tolist(),
        earth_minus_moon_position_m=[position.x, position.y, position.z],
        earth_minus_moon_velocity_m_s=[velocity.x, velocity.y, velocity.z],
        sources=[dict(url="https://doi.org/10.1002/2013JE004559", publication="Williams et al. 2014",
                      location="section 5, mean solid moment and A_s-I_s/B_s-I_s/C_s-I_s",
                      method="explicit transcription verified against primary full-text; no raw source SHA claimed"),
                 dict(file="solar-system-moon-20261008.json", sha256=origin.dataset_sha256),
                 dict(file="orientation-de441-20261008.json", sha256=PROFILE_SHA256)],
        limitations=["Whole GM with effective permanent mean solid inertia: rigid surrogate, not the measured total lunar inertia",
                     "No fluid core, time-varying tide/spin distortion, higher harmonics, solar forcing or relativity",
                     "Published offsets are rounded and share correlations; common mean uncertainty is sensitivity only",
                     "Exclusion radius 1800 km is a model domain, not a measured topographic/reference radius"])


if __name__ == "__main__":
    path = ROOT/"src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json"
    raw = (json.dumps(build(), indent=2, ensure_ascii=False)+"\n").encode("utf-8")
    if path.exists() and path.read_bytes() != raw:
        raise FileExistsError("Pinned profile exists with other bytes; preserve and review before replacing")
    path.write_bytes(raw)
    print(path.name, hashlib.sha256(raw).hexdigest())
