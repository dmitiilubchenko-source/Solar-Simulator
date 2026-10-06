"""Учебные сценарии N тел: python examples/n_body.py --scenario sun-earth-moon."""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from solar_simulator.scenarios import earth_moon, binary_star, sun_earth_moon
from solar_simulator.runner import sampled_states
from solar_simulator.simulation import AU, total_energy

SCENARIOS = {"earth-moon": earth_moon, "binary-star": binary_star,
             "sun-earth-moon": sun_earth_moon}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="sun-earth-moon")
    parser.add_argument("--save", type=Path)
    parser.add_argument("--backend", choices=["python","rust"], default="python")
    args = parser.parse_args()
    bodies, period = SCENARIOS[args.scenario]()
    names = [body.name for body in bodies]
    paths = [[] for body in bodies]
    relative, errors = [], []
    initial_energy = total_energy(bodies)
    steps = 4000
    times=[]
    for index, bodies in sampled_states(bodies,2*period/steps,steps,backend=args.backend):
        times.append(index*2*period/steps/86400)
        for path, body in zip(paths, bodies):
            path.append((body.position.x / AU, body.position.y / AU))
        if args.scenario == "sun-earth-moon":
            delta = bodies[2].position.subtract(bodies[1].position)
            relative.append((delta.x / 1e6, delta.y / 1e6))
        errors.append((total_energy(bodies) - initial_energy) / abs(initial_energy))
    fig, axes = plt.subplots(1, 3 if relative else 2, figsize=(14 if relative else 10, 4), constrained_layout=True)
    for name, path in zip(names, paths):
        axes[0].plot(*zip(*path), label=name)
    axes[0].set(xlabel="x / AU", ylabel="y / AU", title=args.scenario, aspect="equal")
    axes[0].legend()
    if relative:
        axes[1].plot(*zip(*relative))
        axes[1].set(xlabel="x / 1000 km", ylabel="y / 1000 km", title="Moon relative to Earth", aspect="equal")
    axes[-1].plot(times, errors)
    axes[-1].set(xlabel="Time / days", ylabel="(E-E0)/|E0|", title="Energy error")
    for ax in axes:
        ax.grid(alpha=0.3)
    print(f"Maximum sampled relative energy error: {max(map(abs, errors)):.3e}")
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=160)
    else:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
