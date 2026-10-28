"""Synthetic SI inputs, not parameters of real planets or a user preset."""
import numpy as np
from scipy.spatial.transform import Rotation

from solar_simulator.experiment import Settings
from solar_simulator.nbody_rotation import RotationState
from solar_simulator.rotation import RigidFigure
from solar_simulator.simulation import Body
from solar_simulator.vector3 import Vector3


def fixture(third=False,backend='python'):
    masses=[1e15,2e14];fraction=masses[1]/sum(masses)
    rho=np.array([12000.,0.,0.]);velocity=np.array([0.,2.55,.2])
    offset=np.array([100.,-200.,50.]);drift=np.array([.02,-.01,.005])
    bodies=[Body('A',masses[0],Vector3(*(offset-fraction*rho)),Vector3(*(drift-fraction*velocity))),
            Body('B',masses[1],Vector3(*(offset+(1-fraction)*rho)),Vector3(*(drift+(1-fraction)*velocity)))]
    if third:bodies.append(Body('C',3e12,Vector3(30000.,10000.,-5000.),Vector3(-.03,.015,-.04)))
    states=[]
    for name,mass,moments,radius,angle,omega in (
        ('A',masses[0],(2e20,2.5e20,3e20),1000.,[.3,-.2,.4],[.0001,-.0002,.002]),
        ('B',masses[1],(3e19,4e19,5e19),900.,[-.25,.35,.1],[.0006,-.0005,.0015])):
        figure=RigidFigure(mass,moments,radius);matrix=Rotation.from_rotvec(angle)
        q=tuple(np.roll(matrix.as_quat(),1));spin=matrix.as_matrix()@(np.array(moments)*omega)
        states.append(RotationState(name,figure,q,tuple(spin),1e-13,float(np.linalg.norm(spin)*1e-13),
            'synthetic rigid Q2 validation380:'+name))
    settings=Settings(50.,backend=backend,integrator='dop853',rtol=1e-11,position_atol=1e-7,
        velocity_atol=1e-11,relative_pair=('A','B'))
    return bodies,tuple(states),settings
