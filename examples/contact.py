"""Остановка падающих друг к другу сфер без слияния."""
import argparse

from solar_simulator.contacts import run_until_contact
from solar_simulator.simulation import Body, G
from solar_simulator.vector3 import Vector3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend",choices=["python","rust"],default="rust")
    args=parser.parse_args()
    bodies=[Body("A",1/G,Vector3(-5,0,0),Vector3(0,0,0),1),
            Body("B",1/G,Vector3(5,0,0),Vector3(0,0,0),1)]
    result=run_until_contact(bodies,0.1,1000,backend=args.backend)
    print(f"Stopped at {result.time:.6f} s; contact: {result.contact}")
    print(f"Center distance: {result.bodies[0].position.distance_to(result.bodies[1].position):.6f} m")


if __name__=="__main__":
    main()
