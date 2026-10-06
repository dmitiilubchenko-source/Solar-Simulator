"""Запуск: python examples/sun_earth.py [--save путь.png]."""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from solar_simulator.simulation import AU, sun_earth, total_energy
from solar_simulator.runner import sampled_states
from solar_simulator.diagnostics import angular_momentum, orbit_parameters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", type=Path, help="Сохранить график вместо открытия окна")
    parser.add_argument("--eccentricity", type=float, default=0.0, help="Эксцентриситет: от 0 до 1 (не включая 1)")
    parser.add_argument("--steps", type=int, default=4000, help="Число шагов на период")
    parser.add_argument("--backend", choices=["python","rust"], default="python")
    args = parser.parse_args()
    if not 0 <= args.eccentricity < 1 or args.steps < 100:
        parser.error("Require 0 <= eccentricity < 1 and steps >= 100")
    bodies, period = sun_earth(args.eccentricity)
    initial_energy = total_energy(bodies)
    initial_l = angular_momentum(bodies)
    max_l_error = 0.0
    dt = period / args.steps
    x, y, days, errors = [], [], [], []
    for index, bodies in sampled_states(bodies,dt,args.steps,backend=args.backend):
        max_l_error = max(max_l_error, angular_momentum(bodies).distance_to(initial_l) / initial_l.magnitude())
        relative = bodies[1].position.subtract(bodies[0].position)
        x.append(relative.x / AU)
        y.append(relative.y / AU)
        days.append(index * dt / 86400)
        errors.append((total_energy(bodies) - initial_energy) / abs(initial_energy))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    axes[0].plot(x, y, label="Earth relative to Sun")
    axes[0].scatter([0], [0], color="orange", label="Sun")
    axes[0].set(xlabel="x / AU", ylabel="y / AU", title=f"Newtonian orbit: e={args.eccentricity:g}", aspect="equal")
    axes[0].legend()
    axes[1].plot(days, errors)
    axes[1].set(xlabel="Time / days", ylabel="(E - E0) / |E0|", title="Relative energy error")
    for ax in axes:
        ax.grid(alpha=0.3)
    print(f"Analytical period: {period / 86400:.4f} days")
    print(f"Maximum sampled relative energy error: {max(map(abs, errors)):.3e}")
    orbit = orbit_parameters(*bodies)
    print(f"Maximum sampled relative angular momentum error: {max_l_error:.3e}")
    print(f"Final eccentricity: {orbit.eccentricity:.8f}; semi-major axis: {orbit.semi_major_axis / AU:.8f} AU")
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=160)
        print(f"Saved: {args.save}")
    else:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
