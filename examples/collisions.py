"""Повторные упругие отскоки двух притягивающихся сфер."""
import argparse

from solar_simulator.collisions import simulate_collisions
from solar_simulator.simulation import Body, G, total_energy
from solar_simulator.vector3 import Vector3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend",choices=["python","rust"],default="rust")
    parser.add_argument("--dt",type=float,default=.05)
    parser.add_argument("--steps",type=int,default=2000)
    parser.add_argument("--restitution",type=float,default=1)
    args = parser.parse_args()
    bodies = [Body("a",1/G,Vector3(-5,0,0),Vector3(0,0,0),1),
              Body("b",1/G,Vector3(5,0,0),Vector3(0,0,0),1)]
    result = simulate_collisions(bodies,args.dt,args.steps,
                                restitution=args.restitution,backend=args.backend)
    print(f"Time: {result.time:.6f} s; impacts: {len(result.events)}")
    for event in result.events:
        print(f"Impact {event.first}-{event.second}: {event.time:.9f} s")
    print(f"Dissipated energy: {result.dissipated_energy:.9e} J")
    residual = total_energy(result.bodies)+result.dissipated_energy-total_energy(bodies)
    print(f"Relative energy budget residual: {abs(residual)/abs(total_energy(bodies)):.9e}")


if __name__ == "__main__":
    main()
