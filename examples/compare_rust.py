"""Сборка и независимый запуск: python examples/compare_rust.py."""
from pathlib import Path
from time import perf_counter
import json
import shutil
import subprocess

from solar_simulator.simulation import step, sun_earth
from solar_simulator.scenarios import earth_moon, binary_star, sun_earth_moon
from solar_simulator.rust_backend import evolve


def main():
    root = Path(__file__).resolve().parents[1]
    cargo = shutil.which("cargo") or str(Path.home() / ".cargo/bin/cargo.exe")
    manifest = root / "rust/solar_core/Cargo.toml"
    subprocess.run([cargo, "build", "--release", "--manifest-path", str(manifest)], check=True)
    executable = root / "rust/solar_core/target/release/solar_core.exe"
    results = []
    for name, factory in [("circle", sun_earth), ("ellipse", lambda: sun_earth(0.6)),
                          ("earth-moon", earth_moon), ("binary-star", binary_star),
                          ("sun-earth-moon", sun_earth_moon)]:
        initial, period = factory()
        steps, dt = 8000, period / 4000
        start = perf_counter()
        actual = evolve(initial, dt, steps, executable)
        rust_seconds = perf_counter() - start
        reference = initial
        start = perf_counter()
        for _ in range(steps):
            reference = step(reference, dt)
        python_seconds = perf_counter() - start
        position_error = max(a.position.distance_to(b.position) for a, b in zip(actual, reference))
        velocity_error = max(a.velocity.distance_to(b.velocity) for a, b in zip(actual, reference))
        length_scale = initial[-1].position.distance_to(initial[-2].position)
        speed_scale = initial[-1].velocity.subtract(initial[-2].velocity).magnitude()
        if position_error / length_scale > 1e-9 or velocity_error / speed_scale > 1e-9:
            raise AssertionError(f"Rust/Python disagreement for {name}")
        results.append(dict(scenario=name, steps=steps, dt=dt,
                            max_position_error_m=position_error, max_velocity_error_m_s=velocity_error,
                            python_seconds=python_seconds, rust_process_seconds=rust_seconds))
    path = root / "docs/rust-comparison.json"
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
