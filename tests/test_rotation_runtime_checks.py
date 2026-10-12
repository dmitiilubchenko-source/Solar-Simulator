"""Runtime symmetries, historical source preservation and real GUI continuation."""
from dataclasses import replace
import hashlib
import importlib.util
import importlib.machinery
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from solar_simulator.ephemerides import solar_system
from solar_simulator.experiment import create_experiment, Settings, advance
from solar_simulator.nbody_rotation import lunar_initial, integrate
from solar_simulator.rotation import rotation_matrix
from solar_simulator.simulation import Body
from solar_simulator.vector3 import Vector3


def test_rotation_covariance_translation_boost_and_body_permutation():
    base,origin=solar_system(resolved_moon=True)
    bodies=[b for b in base if b.name in {"Sun","Earth","Moon"}]
    rotations=lunar_initial(bodies,origin)
    from solar_simulator.cli import report
    info=report(create_experiment(bodies,Settings(3600.,integrator="dop853"),origin=origin,rotations=rotations))
    assert np.linalg.norm(info["dynamic_spin_torque"])>0
    assert np.array_equal(-np.array(info["dynamic_spin_torque"]),info["figure_orbital_torque"])
    matrix=Rotation.from_rotvec([.5,-.1,.2]).as_matrix()
    shift=np.array([1e9,-2e9,3e9]);boost=np.array([3e4,-4e4,2e4])
    transformed=[]
    for b in reversed(bodies):
        p=matrix@np.array([b.position.x,b.position.y,b.position.z])+shift
        v=matrix@np.array([b.velocity.x,b.velocity.y,b.velocity.z])+boost
        transformed.append(Body(b.name,b.mass,Vector3(*map(float,p)),Vector3(*map(float,v))))
    s=rotations[0]
    q=np.roll(Rotation.from_matrix(matrix@rotation_matrix(s.quaternion)).as_quat(),1)
    changed=replace(s,quaternion=tuple(q),angular_momentum=tuple(matrix@np.array(s.angular_momentum)))
    original=integrate(bodies,rotations,[0.,86400.],relative_pair=("Earth","Moon"))[-1]
    result=integrate(transformed,(changed,),[0.,86400.],relative_pair=("Moon","Earth"))[-1]
    actual={b.name:b for b in result[0]}
    for b in original[0]:
        expected=matrix@np.array([b.position.x,b.position.y,b.position.z])+shift+boost*86400
        other=actual[b.name]
        assert np.linalg.norm(expected-[other.position.x,other.position.y,other.position.z]) < .01
    assert np.linalg.norm(matrix@rotation_matrix(original[1][0].quaternion)-rotation_matrix(result[1][0].quaternion)) < 1e-9


@pytest.mark.parametrize("points",[36,144])
def test_legacy_ring_runtime_matches_exact_archived_experiment(monkeypatch,points):
    path=Path('scripts/validation/kuiper-ring-experiment-20261011.py.txt')
    assert hashlib.sha256(path.read_bytes()).hexdigest()=='3f17bc93f5ef21ee22503d55a31c9f3e83e360f2fb5d5a48a9a7e9726b4ebe81'
    name='solar_simulator._archived_ring_experiment'
    loader=importlib.machinery.SourceFileLoader(name,str(path))
    spec=importlib.util.spec_from_loader(name,loader)
    old=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,name,old);loader.exec_module(old)
    from solar_simulator.kuiper_ring import solar_system_ring
    from solar_simulator.oblateness import sun_earth_moon_quadrupoles
    bodies,origin=solar_system_ring(points,0)
    kwargs=dict(backend="rust",integrator="dop853",physics="eih-1pn",
        figures=sun_earth_moon_quadrupoles(bodies,origin),relative_pair=("Earth","Moon"))
    archived=old.advance(old.create_experiment(bodies,old.Settings(3600.,**kwargs),origin=origin),1)
    current=advance(create_experiment(bodies,Settings(3600.,**kwargs),origin=origin),1)
    assert current.time==archived.time and current.orientation_work==archived.orientation_work
    assert current.origin==archived.origin and current.rotations==()
    for a,b in zip(current.bodies,archived.bodies):
        assert a.name==b.name and a.position.distance_to(b.position)==0 and a.velocity.distance_to(b.velocity)==0


def test_real_gui_dynamic_rotation_continue_reset_and_reject_editor(tmp_path):
    # A fresh interpreter avoids this Windows Tcl runtime's repeated-init issue.
    code=r'''
import time,tkinter as tk
from solar_simulator.app import Laboratory
from solar_simulator.ephemerides import solar_system
from solar_simulator.nbody_rotation import lunar_initial
from solar_simulator.experiment import create_experiment,Settings
from solar_simulator.storage import save,load
from pathlib import Path
import sys
bodies,origin=solar_system(resolved_moon=True)
bodies=[b for b in bodies if b.name in {'Sun','Earth','Moon'}]
state=create_experiment(bodies,Settings(3600.,integrator='dop853',relative_pair=('Earth','Moon')),origin=origin,rotations=lunar_initial(bodies,origin))
root=tk.Tk();root.withdraw();app=Laboratory(root,state)
try:
 app._settings();app._submit(1)
 deadline=time.monotonic()+15
 while app.future is not None and time.monotonic()<deadline:
  root.update();time.sleep(.01)
 assert app.future is None and app.experiment.time==3600.
 assert 'вращение' in app.status.get()
 path=Path(sys.argv[1])/'gui-spin.json';save(app.experiment,path);app._set_experiment(load(path))
 assert len(app.experiment.rotations)==1
 try:app._edit()
 except ValueError:pass
 else:raise AssertionError('Editor silently lost rotation')
 app._reset();assert app.experiment.time==0 and app.experiment.rotations==state.rotations
finally:app.close()
'''
    result=subprocess.run([sys.executable,'-B','-c',code,str(tmp_path)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
