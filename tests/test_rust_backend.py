from pathlib import Path
import json
import subprocess

import pytest

from solar_simulator.rust_backend import evolve
from solar_simulator.simulation import sun_earth, total_energy, total_momentum, center_of_mass
from solar_simulator.diagnostics import angular_momentum


@pytest.fixture
def executable():
    path = Path(__file__).resolve().parents[1] / "rust/solar_core/target/release/solar_core.exe"
    if not path.exists():
        pytest.skip("Build Rust release executable before running integration tests")
    return path


def test_rust_diagnostics_match_python(executable):
    bodies, period = sun_earth(0.6)
    data = {"bodies": [{"name": b.name, "mass": b.mass,
                        "position": [b.position.x,b.position.y,b.position.z],
                        "velocity": [b.velocity.x,b.velocity.y,b.velocity.z]} for b in bodies],
            "dt": period / 4000, "steps": 1000}
    response = subprocess.run([str(executable)], input=json.dumps(data),
                              text=True, capture_output=True, check=True)
    output = json.loads(response.stdout)
    result = evolve(bodies, period / 4000, 1000, executable)
    diagnostics = output["diagnostics"]
    assert diagnostics["energy"] == pytest.approx(total_energy(result), rel=1e-13)
    for field, function, tolerance in [("momentum", total_momentum, 1e18),
                                       ("angular_momentum", angular_momentum, 1e-13),
                                       ("center_of_mass", center_of_mass, 1e-6)]:
        vector = function(result)
        assert diagnostics[field] == pytest.approx([vector.x,vector.y,vector.z],
                                                    rel=1e-13, abs=tolerance)


@pytest.mark.parametrize("dt", [0,-1])
def test_rust_rejects_invalid_dt(executable, dt):
    with pytest.raises(ValueError):
        evolve(sun_earth()[0],dt,1,executable)


def test_rust_zero_steps_preserves_state(executable):
    initial, _ = sun_earth()
    result = evolve(initial,1,0,executable)
    assert result[1].position.x == initial[1].position.x
    assert result[1].velocity.y == initial[1].velocity.y
