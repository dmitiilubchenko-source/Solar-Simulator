"""Product packet/restart contract and safeguards of the bounded observer."""
from dataclasses import replace
from decimal import Decimal as D,localcontext
import os
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from scripts.check_runtime_reliability376 import metrics,invariants
from solar_simulator.experiment import Settings,advance,create_experiment
from solar_simulator.simulation import sun_earth
from solar_simulator.storage import save,load,to_document


@pytest.mark.parametrize('backend',['python','rust'])
@pytest.mark.parametrize('relative',[False,True])
def test_same_packets_file_restart_is_exact_for_product_dop853(tmp_path,backend,relative):
    if backend=='rust':
        import solar_native
        assert callable(solar_native.point_acceleration)  # require real native, no silent skip
    bodies,period=sun_earth(.95)
    state=create_experiment(bodies,Settings(period/2000,backend=backend,integrator='dop853',rtol=3e-14,
        relative_pair=tuple(b.name for b in bodies) if relative else None))
    prefix=advance(state,3);save(prefix,tmp_path/'checkpoint.json');restored=load(tmp_path/'checkpoint.json')
    assert to_document(restored)==to_document(prefix)
    for steps in (2,5,1):
        prefix=advance(prefix,steps);restored=advance(restored,steps)
        assert to_document(restored)==to_document(prefix)


def test_independent_observer_energy_COM_and_zero_reference_error():
    speed=2.**-20  # bound at SI G and 0.5kg masses, exactly representable
    array=np.array([[[-.5,0.,0.,.25,-speed,0.],[.5,0.,0.,.25,speed,0.]]])
    ref=[((D(1),D(0),D(0)),(D(0),D.from_float(2*speed),D(0)))]
    maximum,rows=metrics(array,ref,[.5,.5])
    assert maximum['r']==maximum['v']==maximum['E']==maximum['L']==maximum['P']==0
    with localcontext() as ctx:
        ctx.prec=130;inv=invariants(array[0],[.5,.5])
        assert inv['COM_identity']==0 and inv['P']==[D('.25'),D(0),D(0)]


@pytest.mark.parametrize('bad',['missing_reference','missing_body','nonfinite'])
def test_observer_rejects_incomplete_or_nonfinite_results(bad):
    state=np.zeros((1,2,6));reference=[((D(1),)*3,(D(1),)*3)]
    if bad=='missing_reference':reference=[]
    if bad=='missing_body':state=state[:,:1]
    if bad=='nonfinite':state[0,0,0]=float('nan')
    with pytest.raises(ValueError):metrics(state,reference,[1.,1.])


def test_unrepresentable_requested_epoch_is_rejected_before_any_solver(monkeypatch):
    from solar_simulator.time_control import advance_towards
    bodies,period=sun_earth(.5)
    previous=float.fromhex('0x1.ed15bbd55cbf8p+14');target=float.fromhex('0x1.342d956559f7bp+18')
    dt=target-previous
    assert previous+dt!=target
    seed=create_experiment(bodies,Settings(dt,integrator='dop853'))
    def forbidden(*args,**kwargs):raise AssertionError('Solver must not run for an invalid target')
    monkeypatch.setattr('solar_simulator.time_control.advance',forbidden)
    with pytest.raises(ValueError,match='float64'):advance_towards(replace(seed,time=previous),target,1)


def test_scientific_grid_uses_exact_packet_intervals_without_dropping_points():
    from scripts.check_runtime_reliability376 import PROTOCOL,read
    for case in read(PROTOCOL)['cases']:
        times=case['epochs']
        assert len(times)==len(case['requested_epochs'])==49
        assert max(abs(t-q) for t,q in zip(times,case['requested_epochs']))<=2**-21
        assert all(a+(b-a)==b for a,b in zip(times,times[1:]))


@pytest.mark.parametrize('backend',['python','rust'])
def test_checkpoint_identical_packets_in_a_fresh_process(tmp_path,backend):
    bodies,period=sun_earth(.95)
    state=create_experiment(bodies,Settings(period/2000,backend=backend,integrator='dop853',rtol=3e-14,
        relative_pair=tuple(b.name for b in bodies)))
    prefix=advance(state,3);source=tmp_path/'input.json';target=tmp_path/'output.json';save(prefix,source)
    expected=prefix
    for count in (2,5,1):expected=advance(expected,count)
    code='''import sys
from solar_simulator.storage import load,save
from solar_simulator.experiment import advance
s=load(sys.argv[1])
for count in (2,5,1):s=advance(s,count)
save(s,sys.argv[2])
'''
    env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    subprocess.run([sys.executable,'-X','utf8','-B','-c',code,str(source),str(target)],check=True,
        timeout=20,cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True)
    assert to_document(load(target))==to_document(expected)
