"""Portable402 observer and fixed-plan controls, never scientific trajectories."""
import json,math
from pathlib import Path
import numpy as np
from scripts.qualification402.metrics import geometry_controls,projected,angle,budgets
def test_zero_pi_and_antipodal_geometry():
 assert geometry_controls()['antipodal_q']
def test_polar_projection_keeps_raw_input():
 raw=np.eye(3);raw[0,1]=1e-5;before=raw.copy();matrix,defect,orth,det=projected(raw)
 assert np.array_equal(raw,before) and defect>0 and orth>0 and det>0
 assert np.linalg.norm(matrix.T@matrix-np.eye(3))<1e-12
def test_stable_sub_epsilon_angle_and_pi():
 x=1e-12;c=math.cos(x);s=math.sin(x);matrix=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
 assert abs(angle(np.eye(3),matrix)-x)<1e-26
 assert abs(angle(np.eye(3),matrix,independent=True)-x)<1e-26
def test_spin_budget_uses_initial_exact_components_at_both_precisions():
 d={'rotations':[{'angular_momentum':[3.,4.,0.]},{'angular_momentum':[0.,0.,13.]}]}
 b,delta,info=budgets(d,80);other=budgets(d,120)
 assert np.array_equal(b,other[0]) and b[-2:].tolist()==[5e-5,13e-5]
 assert delta[-2:].tolist()==[5e-4,13e-4]
def test_fixed_inventory_has_twenty_runtime_and_two_reference_jobs():
 p=json.loads((Path(__file__).resolve().parents[1]/'scripts/qualification402/plan.json').read_bytes())
 assert len(p['jobs'])==len({j['id'] for j in p['jobs']})==22
 assert sum(j['kind']=='reference' for j in p['jobs'])==2
 assert sum(bool(j.get('GUI')) for j in p['jobs'])==4
 assert all(j['epochs']==[0.,50.,100.,150.,200.] for j in p['jobs'] if j['kind']!='suffix')
