"""Recorded endpoints retain the old solver contract; playback never propagates."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from solar_simulator.experiment import Settings, advance, create_experiment, preset
from solar_simulator.simulation import Body
from solar_simulator.storage import to_document
from solar_simulator.vector3 import Vector3


def ballistic(integrator='dop853'):
    return create_experiment([Body('free',1.,Vector3(3.,4.,5.),Vector3(2.,-1.,.5))],Settings(10.,integrator=integrator))


def test_recorded_endpoints_match_independent_free_motion(tmp_path):
    from solar_simulator.trajectory import record_trajectory,Trajectory
    seed=ballistic();record_trajectory(seed,tmp_path/'track',25.25,packet_steps=2)
    track=Trajectory(tmp_path/'track')
    assert track.times==(0.,20.,25.25) and track.metadata['status']=='complete'
    for index,time in enumerate(track.times):
        state,parent=track.frame(index)
        assert parent is None and state.settings==seed.settings
        p=state.bodies[0].position
        assert (p.x,p.y,p.z)==pytest.approx((3+2*time,4-time,5+.5*time),abs=1e-12)


@pytest.mark.parametrize('backend',['python','rust'])
@pytest.mark.parametrize('profile',['branch','strict','rotation'])
def test_packets_equal_direct_continuation_with_full_state(tmp_path,backend,profile):
    from solar_simulator.trajectory import record_trajectory,Trajectory
    from solar_simulator.time_control import advance_towards
    parent=None
    if profile=='branch':
        from test_recovery_journey import make_branch
        branch=make_branch(backend);seed=branch.child;parent=branch.parent_snapshot
    elif profile=='strict':
        from solar_simulator.solar_profiles import solar_sandbox
        seed=solar_sandbox(profile='strict',backend=backend)
    else:
        from solar_simulator.application_profiles import lunar_rotation
        seed=lunar_rotation(backend=backend)
    before=to_document(seed);target=seed.time+seed.settings.dt*2.25
    record_trajectory(seed,tmp_path/'track',target,packet_steps=2,parent_snapshot=parent)
    track=Trajectory(tmp_path/'track');expected=seed
    for i,time in enumerate(track.times):
        if i:expected=advance_towards(expected,target,2)
        actual,snapshot=track.frame(i)
        assert time==expected.time and to_document(actual)==to_document(expected) and snapshot==parent
    assert to_document(seed)==before
    actual,_=track.frame(len(track.times)-1)
    assert to_document(advance(actual,2))==to_document(advance(expected,2))


@pytest.mark.parametrize('mode',['stop','bounce','merge'])
def test_contact_and_membership_changes_remain_full_checkpoints(tmp_path,mode):
    from solar_simulator.trajectory import record_trajectory,Trajectory
    from solar_simulator.time_control import advance_towards
    seed=create_experiment([Body('left',1.,Vector3(-5.,0.,0.),Vector3(1.,0.,0.),1.),
                           Body('right',1.,Vector3(5.,0.,0.),Vector3(-1.,0.,0.),1.)],Settings(3.,contact_mode=mode))
    record_trajectory(seed,tmp_path/'track',10.25,packet_steps=2)
    track=Trajectory(tmp_path/'track');expected=seed
    for i in range(1,len(track.times)):
        expected=advance_towards(expected,10.25,2)
        assert to_document(track.frame(i)[0])==to_document(expected)
    assert track.metadata['status']==('halted' if expected.halted and expected.time<10.25 else 'complete')


def test_stop_before_first_packet_preserves_initial_frame(tmp_path,monkeypatch):
    from solar_simulator import trajectory
    def forbidden(*a,**k):raise AssertionError('No packet after stop')
    monkeypatch.setattr(trajectory,'advance_towards',forbidden)
    trajectory.record_trajectory(ballistic(),tmp_path/'track',25.,stop_requested=lambda:True)
    track=trajectory.Trajectory(tmp_path/'track')
    assert track.times==(0.,) and track.metadata['status']=='stopped'


@pytest.mark.parametrize('failure',['worker','manifest'])
def test_failure_preserves_published_frames_and_latest_calculated_recovery(tmp_path,monkeypatch,failure):
    from solar_simulator import trajectory
    from solar_simulator.branch_io import open_experiment
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'local data'))
    advance_packet=trajectory.advance_towards;write=trajectory._write_document
    calls=[]
    def compute(*args):
        if failure=='worker' and calls:raise RuntimeError('controlled worker failure')
        result=advance_packet(*args);calls.append(to_document(result));return result
    def publish(document,path):
        if failure=='manifest' and document.get('status')=='recording' and len(document['frames'])==2:
            raise OSError('controlled manifest failure')
        write(document,path)
    monkeypatch.setattr(trajectory,'advance_towards',compute)
    monkeypatch.setattr(trajectory,'_write_document',publish)
    with pytest.raises(RuntimeError,match='recovery'):
        trajectory.record_trajectory(ballistic(),tmp_path/'track',50.,packet_steps=2)
    track=trajectory.Trajectory(tmp_path/'track')
    assert track.times==((0.,20.) if failure=='worker' else (0.,))
    assert track.metadata['status']=='failed'
    paths=list((tmp_path/'local data').rglob('checkpoint.json'));assert len(paths)==1
    assert to_document(open_experiment(paths[0])[0])==calls[-1]


@pytest.mark.parametrize('target,batch',[(-1.,20),(float('nan'),20),(25.,True),(25.,0)])
def test_invalid_request_creates_no_output(tmp_path,target,batch):
    from solar_simulator.trajectory import record_trajectory
    with pytest.raises(ValueError):record_trajectory(ballistic(),tmp_path/'track',target,packet_steps=batch)
    assert not (tmp_path/'track').exists()


@pytest.mark.parametrize('damage',['hash','escape','time','schema','settings','missing'])
def test_corrupt_trajectory_is_rejected(tmp_path,damage):
    from solar_simulator.trajectory import record_trajectory,Trajectory
    record_trajectory(ballistic(),tmp_path/'track',25.25,packet_steps=2)
    manifest=tmp_path/'track/manifest.json';doc=json.loads(manifest.read_bytes())
    frame=tmp_path/'track'/doc['frames'][1]['file']
    if damage=='hash':frame.write_bytes(frame.read_bytes()+b' ')
    elif damage=='escape':doc['frames'][1]['file']='../outside.json'
    elif damage=='time':doc['frames'][1]['time_seconds']=0.
    elif damage=='schema':doc['schema_version']=99
    elif damage=='missing':frame.unlink()
    else:
        state=json.loads(frame.read_bytes());state['settings']['dt']=5.
        frame.write_text(json.dumps(state),encoding='utf-8')
        doc['frames'][1]['sha256']=hashlib.sha256(frame.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(doc),encoding='utf-8')
    with pytest.raises((ValueError,OSError)):Trajectory(tmp_path/'track')


def test_different_playback_rates_and_seeking_never_call_solver_or_change_bytes(tmp_path,monkeypatch):
    from solar_simulator import trajectory
    from solar_simulator.playback import Playback
    trajectory.record_trajectory(ballistic(),tmp_path/'track',95.,packet_steps=2)
    original={p.name:p.read_bytes() for p in (tmp_path/'track').iterdir()}
    def forbidden(*a,**k):raise AssertionError('Playback must not propagate')
    monkeypatch.setattr(trajectory,'advance_towards',forbidden)
    monkeypatch.setattr('solar_simulator.experiment.advance',forbidden)
    for rate in (1.,25.):
        track=trajectory.Trajectory(tmp_path/'track');player=Playback(track)
        player.play()
        for _ in range(200):player.tick(.1,rate)
        assert player.index==len(track.times)-1 and not player.running
        player.seek(1);assert not player.running and player.state[0].time==20.
        player.seek(0);player.play();player.tick(100.,rate)
        assert to_document(player.state[0])==to_document(track.frame(len(track.times)-1)[0])
    assert original=={p.name:p.read_bytes() for p in (tmp_path/'track').iterdir()}


def test_cli_records_branch_without_overwriting_input(tmp_path,capsys):
    from solar_simulator.commands import main
    from solar_simulator.branch_io import save_experiment
    from solar_simulator.trajectory import Trajectory
    from test_recovery_journey import make_branch
    branch=make_branch();path=tmp_path/'source.json'
    save_experiment(branch.child,path,parent_snapshot=branch.parent_snapshot);before=path.read_bytes()
    target=branch.child.time+branch.child.settings.dt*2.25
    assert main(['record-trajectory',str(path),str(tmp_path/'track'),'--time',str(target),'--batch','2'])==0
    assert json.loads(capsys.readouterr().out)['status']=='complete'
    assert Trajectory(tmp_path/'track').frame(-1)[1]==branch.parent_snapshot and path.read_bytes()==before


def test_existing_output_is_never_reused(tmp_path):
    from solar_simulator.trajectory import record_trajectory
    (tmp_path/'keep.txt').write_bytes(b'user data')
    with pytest.raises(FileExistsError):record_trajectory(ballistic(),tmp_path,25.)
    assert (tmp_path/'keep.txt').read_bytes()==b'user data' and not (tmp_path/'manifest.json').exists()


def test_both_writes_fail_without_destroying_the_published_prefix(tmp_path,monkeypatch):
    from solar_simulator import trajectory
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'local data'))
    compute=trajectory.advance_towards
    def fail(*args):raise OSError('controlled disk failure')
    def compute_then_disk_failure(*args):
        result=compute(*args)
        monkeypatch.setattr('solar_simulator.storage.os.replace',fail)
        return result
    monkeypatch.setattr(trajectory,'advance_towards',compute_then_disk_failure)
    with pytest.raises(RuntimeError,match='recovery также не сохранена'):
        trajectory.record_trajectory(ballistic(),tmp_path/'track',25.)
    track=trajectory.Trajectory(tmp_path/'track')
    assert track.times==(0.,) and track.metadata['status']=='recording'


def test_cli_interruption_retains_a_readable_prefix_and_checkpoint(tmp_path,monkeypatch,capsys):
    from solar_simulator.commands import main
    from solar_simulator import trajectory
    from solar_simulator.branch_io import save_experiment,open_experiment
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'local data'))
    seed=ballistic();save_experiment(seed,tmp_path/'input.json')
    def interrupt(*args):raise KeyboardInterrupt
    monkeypatch.setattr(trajectory,'advance_towards',interrupt)
    assert main(['record-trajectory',str(tmp_path/'input.json'),str(tmp_path/'track'),'--time','25'])==130
    assert trajectory.Trajectory(tmp_path/'track').metadata['status']=='interrupted'
    path=next((tmp_path/'local data').rglob('checkpoint.json'))
    assert to_document(open_experiment(path)[0])==to_document(seed) and 'recovery' in capsys.readouterr().err


def test_initial_contact_keeps_before_and_after_at_the_same_epoch(tmp_path,monkeypatch):
    from solar_simulator.trajectory import record_trajectory,Trajectory
    from solar_simulator.time_control import advance_towards
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'local data'))
    seed=create_experiment([Body('left',1.,Vector3(-1.,0.,0.),Vector3(1.,0.,0.),1.),
                           Body('right',1.,Vector3(1.,0.,0.),Vector3(-1.,0.,0.),1.)],Settings(1.))
    expected=advance_towards(seed,2.,20)
    assert expected.halted and expected.time==seed.time==0.
    record_trajectory(seed,tmp_path/'track',2.)
    track=Trajectory(tmp_path/'track')
    assert track.times==(0.,0.) and track.metadata['status']=='halted'
    assert to_document(track.frame(0)[0])==to_document(seed)
    assert to_document(track.frame(1)[0])==to_document(expected)
