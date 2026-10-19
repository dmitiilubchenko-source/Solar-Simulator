"""Amplified algebraic controls, separate from frozen precision221 evidence."""
from decimal import Decimal

import numpy as np

from scripts import ias15_eih as scalar_action
from scripts.decimal_noether import quantities
from scripts.fixed_j2_year import inputs
from scripts.assess_sandbox_planets import states


def test_amplified_pn_analytic_readout_matches_scalar_action_for_ten_bodies(monkeypatch):
    # An algebraic coefficient control, not a propagated physical variant.
    seed,*_ = inputs()
    q = states(seed.bodies)
    q[:,:3] /= 1e11
    q[:,3:] /= 1e4
    mass = np.array([b.mass/seed.bodies[0].mass for b in seed.bodies])
    monkeypatch.setattr(scalar_action,'G',1.)
    monkeypatch.setattr(scalar_action,'C',100.)
    old = scalar_action.noether(q,mass)
    high = np.array(list(map(float,quantities(q,mass,g=1.,c=100.))))
    # Fixed physical scales, rather than division by small net momentum.
    energy = abs(old[0]);momentum = np.sum(mass*np.linalg.norm(q[:,3:],axis=1))
    angular = np.linalg.norm(old[4:])
    scale = np.r_[energy,[momentum]*3,[angular]*3]
    assert max(abs(old-high)/scale) < 5e-14


def test_static_pair_has_the_positive_potential_squared_energy_term():
    # r=2, G=1, masses=(2,1): E_N=-1; sum(m U^2)/2c^2=.0075.
    value = quantities([[-1.,0.,0.,0.,0.,0.],[1.,0.,0.,0.,0.,0.]],[2.,1.],g=1.,c=10.)
    assert value[0] == Decimal('-.9925')
    assert value[1:] == (Decimal(0),)*6
