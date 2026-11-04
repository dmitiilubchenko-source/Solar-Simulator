"""Short external-domain regressions; no qualification trajectories or waiver."""
from dataclasses import replace
from math import nextafter, inf

import numpy as np
import pytest

from scripts.two_q2_fixture380 import fixture
from solar_simulator.experiment import create_experiment
from solar_simulator.nbody_rotation import corrections
from solar_simulator.oblateness import FixedJ2
from solar_simulator.storage import to_document
from solar_simulator.vector3 import Vector3


@pytest.mark.parametrize('distance',[1899.,1900.,nextafter(1900.,inf)])
def test_bounding_spheres_strict_external_domain_at_constructor_and_rhs(distance):
    bodies,rotations,settings=fixture()
    bodies[1]=replace(bodies[1],position=bodies[0].position.add(Vector3(distance,0.,0.)))
    positions=np.array([[b.position.x,b.position.y,b.position.z] for b in bodies])
    masses=np.array([b.mass for b in bodies])
    if distance<=1900.:
        with pytest.raises(ValueError,match='сферы'):
            create_experiment(bodies,settings,rotations=rotations)
        with pytest.raises(ValueError,match='сферы'):
            corrections(positions,masses,(0,1),rotations)
    else:
        state=create_experiment(bodies,settings,rotations=rotations)
        before=to_document(state)
        corrections(positions,masses,(0,1),rotations)
        assert to_document(state)==before
        # Mathematical external-domain acceptance is not a full-field accuracy claim.
        assert len(state.rotations)==2


@pytest.mark.parametrize('mode',['eih','fixed_j2','contact_radius','passive_spin'])
def test_two_dynamic_figures_do_not_silently_enable_other_models(mode):
    bodies,rotations,settings=fixture()
    if mode=='eih':settings=replace(settings,physics='eih-1pn')
    elif mode=='fixed_j2':settings=replace(settings,figures=(FixedJ2('A',.001,1000.,(0.,0.,1.)),))
    elif mode=='contact_radius':bodies[0]=replace(bodies[0],radius=1.)
    else:bodies[0]=replace(bodies[0],spin=Vector3(1.,0.,0.))
    before=(tuple(bodies),rotations,settings)
    with pytest.raises(ValueError):create_experiment(bodies,settings,rotations=rotations)
    assert (tuple(bodies),rotations,settings)==before
