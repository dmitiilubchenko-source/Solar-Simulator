"""Обнаружить контакт и применить мгновенный удар гладких сфер."""
import argparse

from solar_simulator.contacts import run_until_contact
from solar_simulator.impacts import resolve_contact
from solar_simulator.simulation import Body,G,total_energy
from solar_simulator.vector3 import Vector3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend",choices=["python","rust"],default="rust")
    parser.add_argument("--restitution",type=float,default=0.5)
    args=parser.parse_args()
    if not 0<=args.restitution<=1:
        parser.error("Require restitution in [0,1]")
    bodies=[Body("A",1/G,Vector3(-5,0,0),Vector3(0,0,0),1),
            Body("B",1/G,Vector3(5,0,0),Vector3(0,0,0),1)]
    contact=run_until_contact(bodies,0.1,1000,backend=args.backend)
    event=contact.contact
    if event is None:
        raise RuntimeError("No contact in the selected interval")
    result=resolve_contact(contact.bodies,event.first,event.second,args.restitution,backend=args.backend)
    print(f"Contact at {contact.time:.6f} s; restitution={args.restitution}")
    print(f"Velocities before: {[b.velocity.x for b in contact.bodies]} m/s")
    print(f"Velocities after: {[b.velocity.x for b in result.bodies]} m/s")
    print(f"Dissipated kinetic energy: {result.dissipated_energy:.6e} J")
    scale=abs(total_energy(contact.bodies))
    error=abs(total_energy(result.bodies)+result.dissipated_energy-total_energy(contact.bodies))/scale
    print(f"Relative energy-budget residual: {error:.3e}")


if __name__=="__main__":
    main()
