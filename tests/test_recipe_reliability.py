"""Read-only recipe explanation; fixtures use exact inertial motion, no solver."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from solar_simulator import commands,recipe,trajectory
from solar_simulator.experiment import Settings,create_experiment
from solar_simulator.simulation import Body
from solar_simulator.vector3 import Vector3


def snapshot(directory):
    return {p.relative_to(directory).as_posix():p.read_bytes() for p in directory.rglob('*') if p.is_file()}


@pytest.fixture
def recording(tmp_path,monkeypatch):
    fingerprint=dict(application_version='synthetic',package_files={'fixture.py':'a'*64},
        dependencies={'fixture':dict(version='1',files={'fixture.py':'b'*64},inventory_complete=True)})
    monkeypatch.setattr(recipe,'runtime_fingerprint',lambda backend:deepcopy(fingerprint))
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path/'appdata'))
    def make(status='complete',*,start=0.,backend='python'):
        folder=tmp_path/status
        state=create_experiment([Body('free',1.,Vector3(3.,4.,5.),Vector3(2.,-1.,.5))],
                                Settings(10.,backend=backend,integrator='dop853',error_control='per-body'))
        state=replace(state,time=start,bodies=[replace(b,position=b.position.add(b.velocity.multiply(start))) for b in state.bodies])
        calls=0
        def exact_free_motion(current,target,batch):
            nonlocal calls
            calls+=1
            if calls>1 and status in ('failed','interrupted'):
                if status=='interrupted':raise KeyboardInterrupt('synthetic interruption')
                raise RuntimeError('synthetic failure')
            end=min(current.time+current.settings.dt*batch,target)
            bodies=[replace(b,position=b.position.add(b.velocity.multiply(end-current.time))) for b in current.bodies]
            return replace(current,bodies=bodies,time=end)
        monkeypatch.setattr(trajectory,'advance_towards',exact_free_motion)
        stop_calls=0
        def stop():
            nonlocal stop_calls
            stop_calls+=1
            return status=='stopped' and stop_calls>1
        target=start+(25.25 if status=='complete' else 100.)
        if status in ('failed','interrupted'):
            with pytest.raises(KeyboardInterrupt if status=='interrupted' else RuntimeError):
                trajectory.record_trajectory(state,folder,target,packet_steps=2)
        else:
            trajectory.record_trajectory(state,folder,target,packet_steps=2,stop_requested=stop)
        return folder,fingerprint
    return make


def test_opt_in_reports_committed_fractional_packets_without_changing_default(recording,capsys):
    folder,_=recording();before=snapshot(folder)
    expected=recipe.audit_recipe(trajectory.Trajectory(folder))
    assert commands.main(['check-recipe',str(folder)])==0
    assert capsys.readouterr().out==json.dumps(expected,ensure_ascii=False,allow_nan=False)+'\n'
    assert commands.main(['check-recipe',str(folder),'--reliability'])==0
    result=json.loads(capsys.readouterr().out)
    detail=result.pop('recording_reliability')
    assert result==expected and snapshot(folder)==before
    assert detail['completed_packet_count']==2 and detail['confirmed_frame_count']==3
    assert detail['packet_boundaries_seconds']==[[0.,20.],[20.,25.25]]
    assert detail['manifest_status']=='complete' and detail['requested_target_seconds']==25.25


@pytest.mark.parametrize('status',['stopped','failed','interrupted'])
def test_prefix_preserves_original_target_and_actual_status(recording,capsys,status):
    folder,_=recording(status);before=snapshot(folder)
    assert commands.main(['check-recipe',str(folder),'--reliability'])==0
    result=json.loads(capsys.readouterr().out)['recording_reliability']
    assert result['manifest_status']==status and not result['requested_target_reached']
    assert result['start_time_seconds']==0. and result['last_confirmed_time_seconds']==20.
    assert result['requested_target_seconds']==100. and result['completed_packet_count']==1
    assert result['confirmed_frame_count']==2 and result['packet_boundaries_seconds']==[[0.,20.]]
    assert snapshot(folder)==before


def test_old_fingerprint_is_incompatible_not_corrupt(recording,monkeypatch,capsys):
    folder,fingerprint=recording();before=snapshot(folder)
    current=deepcopy(fingerprint);current['package_files']['fixture.py']='c'*64
    monkeypatch.setattr(recipe,'runtime_fingerprint',lambda backend:current)
    assert commands.main(['check-recipe',str(folder),'--reliability'])==1
    result=json.loads(capsys.readouterr().out);detail=result['recording_reliability']
    assert result['differences']==['package_files']
    assert detail['integrity']['status']=='verified_against_stored_hashes'
    assert detail['recording_environment']['endpoint_fingerprints_equal']
    assert not detail['current_environment']['recorded_start_fields_match']
    assert not detail['reproducibility']['strict_replay_preconditions_met']
    assert snapshot(folder)==before


def test_recording_can_start_from_a_nonzero_checkpoint_time(recording,capsys):
    folder,_=recording(start=37.)
    assert commands.main(['check-recipe',str(folder),'--reliability'])==0
    detail=json.loads(capsys.readouterr().out)['recording_reliability']
    assert detail['start_time_seconds']==37. and detail['last_confirmed_time_seconds']==62.25
    assert detail['requested_target_seconds']==62.25 and detail['packet_boundaries_seconds']==[[37.,57.],[57.,62.25]]


@pytest.mark.parametrize('failure',[ModuleNotFoundError,RuntimeError])
def test_unavailable_current_environment_does_not_hide_verified_history(recording,monkeypatch,capsys,failure):
    folder,_=recording(backend='rust');before=snapshot(folder)
    def unavailable(backend):raise failure('synthetic unavailable installation')
    monkeypatch.setattr(recipe,'runtime_fingerprint',unavailable)
    # The old, strict command keeps its original failure behavior.
    with pytest.raises(SystemExit) as error:commands.main(['check-recipe',str(folder)])
    assert error.value.code==2
    capsys.readouterr()
    assert commands.main(['check-recipe',str(folder),'--reliability'])==1
    detail=json.loads(capsys.readouterr().out)['recording_reliability']
    assert detail['current_environment']['status']=='unavailable'
    assert detail['current_environment']['recorded_start_fields_match'] is None
    assert detail['integrity']['status']=='verified_against_stored_hashes'
    assert detail['completed_packet_count']==2 and not detail['reproducibility']['strict_replay_preconditions_met']
    assert snapshot(folder)==before


def test_recording_endpoint_drift_is_separate_from_current_start_match(recording,capsys):
    folder,fingerprint=recording()
    # Synthetic failed finalization: all target frames committed, then the end
    # fingerprint differs. A reached target must not promote status to complete.
    manifest=trajectory.Trajectory(folder).metadata;manifest['status']='failed'
    recipe._write_document(manifest,folder/'manifest.json')
    end=deepcopy(fingerprint);end['application_version']='changed-at-end'
    recipe.write_recipe(folder,manifest,fingerprint,end);before=snapshot(folder)
    assert commands.main(['check-recipe',str(folder),'--reliability'])==1
    detail=json.loads(capsys.readouterr().out)['recording_reliability']
    assert detail['manifest_status']=='failed' and detail['requested_target_reached']
    assert not detail['recording_environment']['endpoint_fingerprints_equal']
    assert detail['current_environment']['recorded_start_fields_match']
    assert not detail['reproducibility']['strict_replay_preconditions_met']
    assert snapshot(folder)==before


def test_equal_incomplete_inventories_do_not_prove_replay_compatibility(recording,capsys):
    folder,fingerprint=recording();fingerprint['dependencies']['fixture']['inventory_complete']=False
    recipe.write_recipe(folder,trajectory.Trajectory(folder).metadata,fingerprint,fingerprint)
    before=snapshot(folder)
    assert commands.main(['check-recipe',str(folder),'--reliability'])==1
    detail=json.loads(capsys.readouterr().out)['recording_reliability']
    assert detail['current_environment']['recorded_start_fields_match']
    assert detail['current_environment']['unverified_dependencies']==['fixture']
    assert not detail['reproducibility']['strict_replay_preconditions_met'] and snapshot(folder)==before


@pytest.mark.parametrize('damage',['no-recipe','recipe-sha','manifest-schema','manifest-link','frame-sha','missing-frame','bounds'])
def test_invalid_or_missing_evidence_fails_closed_without_writes(recording,capsys,damage):
    folder,_=recording()
    if damage=='no-recipe':(folder/'recipe.json').unlink()
    elif damage=='recipe-sha':
        doc=json.loads((folder/'recipe.json').read_bytes());doc['sha256']='0'*64
        recipe._write_document(doc,folder/'recipe.json')
    elif damage=='manifest-schema':recipe._write_document({},folder/'manifest.json')
    elif damage=='manifest-link':
        doc=json.loads((folder/'manifest.json').read_bytes());doc['status']='stopped'
        recipe._write_document(doc,folder/'manifest.json')
    elif damage=='frame-sha':
        path=folder/'frame-000001.json';path.write_bytes(path.read_bytes()+b' ')
    elif damage=='missing-frame':(folder/'frame-000001.json').unlink()
    else:
        import hashlib
        from solar_simulator.sandbox import _canonical
        doc=json.loads((folder/'recipe.json').read_bytes())
        doc['payload']['packet_boundaries_seconds'][0][1]=19.
        doc['sha256']=hashlib.sha256(_canonical(doc['payload']).encode('utf8')).hexdigest()
        recipe._write_document(doc,folder/'recipe.json')
    before=snapshot(folder)
    with pytest.raises(SystemExit) as error:commands.main(['check-recipe',str(folder),'--reliability'])
    assert error.value.code==2 and snapshot(folder)==before
    assert 'Ошибка:' in capsys.readouterr().err


@pytest.mark.parametrize('edit',[False,True])
def test_loose_checkpoint_never_inherits_recording_history(recording,tmp_path,edit,capsys):
    from solar_simulator.inspection import report
    from solar_simulator.storage import load,save
    folder,_=recording();state=load(folder/'frame-000001.json')
    if edit:state=replace(state,bodies=[replace(state.bodies[0],velocity=Vector3(9.,8.,7.))])
    loose=tmp_path/'unrelated.json';save(state,loose);before=snapshot(tmp_path)
    detail=report(load(loose))['numerical_reliability']
    assert not detail['time_and_packets']['packet_history_available']
    assert not detail['qualification']['current_trajectory_certified']
    with pytest.raises(SystemExit) as error:commands.main(['check-recipe',str(loose),'--reliability'])
    assert error.value.code==2 and snapshot(tmp_path)==before


def test_no_integration_invariants_or_recipe_commands_and_detached_report(recording,monkeypatch):
    from solar_simulator.inspection import recipe_report
    folder,fingerprint=recording()
    fingerprint['commands']=['DO NOT EXECUTE'];fingerprint['code']='raise AssertionError()'
    recipe.write_recipe(folder,trajectory.Trajectory(folder).metadata,fingerprint,fingerprint)
    # The unindexed file is not a frame and must remain untouched.
    (folder/'frame-999999.json').write_bytes(b'not a published frame')
    track=trajectory.Trajectory(folder);before=snapshot(folder);metadata=track.metadata
    def forbidden(*args,**kwargs):raise AssertionError('Read-only report must not execute numerical work or recipe commands')
    for name in ('solar_simulator.trajectory.advance_towards','solar_simulator.experiment.advance',
                 'solar_simulator.recipe.replay_trajectory','solar_simulator.cli.report',
                 'solar_simulator.inspection._native_status','scipy.integrate.solve_ivp','os.system','subprocess.run'):
        monkeypatch.setattr(name,forbidden)
    result=recipe_report(track);detail=result['recording_reliability']
    assert detail['completed_packet_count']==2 and detail['confirmed_frame_count']==3
    assert detail['units']=='SI' and detail['configured_packet_steps']==2
    controls=detail['initial_frame']['execution']['adaptive_controls']
    assert controls['rtol']==track.frame(0)[0].settings.rtol and controls['error_control']=='per-body'
    assert controls['position_atol_metres']==track.frame(0)[0].settings.position_atol
    assert controls['velocity_atol_m_per_s']==track.frame(0)[0].settings.velocity_atol
    assert detail['initial_frame']['sha256']==metadata['frames'][0]['sha256']
    assert detail['unrecorded']==dict(internal_steps_seconds=None,rejected_attempts=None,controller_state=None)
    assert detail['reproducibility']['replay_performed'] is False and detail['reproducibility']['reproduced_prefix'] is None
    assert not detail['accuracy']['physical_accuracy_claim'] and not detail['accuracy']['numerical_accuracy_assessed']
    detail['packet_boundaries_seconds'][0][1]=999.
    detail['integrity']['verified_frames'][0]['sha256']='0'*64
    controls['rtol']=1.
    assert track.metadata==metadata and snapshot(folder)==before
    assert recipe.read_recipe(track)['packet_boundaries_seconds']==[[0.,20.],[20.,25.25]]


def test_real_fingerprint_and_fresh_process_report_need_no_numerical_packets(tmp_path,monkeypatch):
    import subprocess,sys
    state=create_experiment([Body('free',1.,Vector3(3.,4.,5.),Vector3(2.,-1.,.5))],Settings(10.))
    def forbidden(*args,**kwargs):raise AssertionError('Zero-packet fixture must not integrate')
    monkeypatch.setattr(trajectory,'advance_towards',forbidden)
    folder=tmp_path/'real fingerprint'
    trajectory.record_trajectory(state,folder,0.)
    before=snapshot(folder)
    process=subprocess.run([sys.executable,'-X','utf8','-B','-m','solar_simulator','check-recipe',str(folder),'--reliability'],
                           capture_output=True,text=True,encoding='utf8',timeout=30)
    assert process.returncode==0,process.stderr
    result=json.loads(process.stdout);detail=result['recording_reliability']
    assert result['compatible'] and detail['completed_packet_count']==0 and detail['confirmed_frame_count']==1
    assert detail['packet_boundaries_seconds']==[] and detail['requested_target_reached']
    assert detail['initial_frame']['execution']['adaptive_controls'] is None
    assert detail['reproducibility']['replay_performed'] is False and snapshot(folder)==before
