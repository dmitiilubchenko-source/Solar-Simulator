"""Do not certify truncated packets or reuse changed scientific evidence."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.assess_edited_solar_year import epoch_grid as six_grid
from scripts.verify_edited_solar_packets import check_packet_boundaries, shared_indices, run, verified_input


def completed_packets():
    return dict(packet_endpoints=epoch_grid()[1:].tolist(), packets=439, finished=True, failed=False)


def test_full_twenty_hour_packets_are_accepted_with_short_final_packet():
    check_packet_boundaries(completed_packets())


@pytest.mark.parametrize('change', ({'packets':438},{'finished':False},{'failed':True}))
def test_unfinished_or_miscounted_packet_run_cannot_pass(change):
    with pytest.raises(ValueError):
        check_packet_boundaries(dict(completed_packets(),**change))


@pytest.mark.parametrize('kind', ('six-hour','missing-terminal'))
def test_output_truncation_and_missing_terminal_packet_are_detected(kind):
    stats = completed_packets()
    stats['packet_endpoints'] = six_grid('regular')[1:] if kind=='six-hour' else epoch_grid()[1:-1]
    with pytest.raises(AssertionError):
        check_packet_boundaries(stats)


def test_shared_comparison_retains_exact_epochs_and_both_endpoints():
    common, a, b = shared_indices(epoch_grid(), six_grid('regular'))
    assert len(common)==148 and common[0]==0. and common[-1]==31557600.
    np.testing.assert_array_equal(common, epoch_grid()[a])
    np.testing.assert_array_equal(common, six_grid('regular')[b])


@pytest.mark.parametrize('which', ('packet','six'))
def test_changed_time_cannot_be_replaced_with_a_nearby_epoch(which):
    packet, six = epoch_grid(), six_grid('regular')
    if which=='packet':
        packet[1]+=1.
    else:
        six[1]+=1.
    with pytest.raises(AssertionError):
        shared_indices(packet,six)


def test_existing_operational_evidence_is_preserved_before_input_reads(monkeypatch,tmp_path):
    from scripts import verify_edited_solar_packets as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    output=tmp_path/'.tools'/'kept'
    output.mkdir(parents=True)
    marker=output/'receipt.json'
    marker.write_text('saved failure',encoding='utf-8')
    with pytest.raises(ValueError,match='fresh'):
        run(output,'unused','unused')
    assert marker.read_text(encoding='utf-8')=='saved failure'


@pytest.mark.parametrize('corruption', ('incomplete','source','archive'))
def test_incomplete_or_changed_receipt_is_rejected(tmp_path,corruption):
    path=tmp_path/'audit.json'
    path.with_suffix('.npz').write_bytes(b'not a valid trajectory')
    document=dict(complete=True,source_input_dependencies_unchanged=True,
        source_sha256={},input_sha256={},dependency_sha256={},npz_sha256='wrong digest')
    if corruption=='incomplete':
        document['complete']=False
    if corruption=='source':
        source=tmp_path/'force.py'
        source.write_text('changed',encoding='utf-8')
        document['source_sha256']={str(source):'old digest'}
    path.write_text(json.dumps(document),encoding='utf-8')
    with pytest.raises(ValueError):
        verified_input(path)


def test_real_gui_year_packets_preserve_an_analytically_stationary_body(tmp_path):
    pytest.importorskip('solar_native')
    from solar_simulator.experiment import Settings, create_experiment
    from solar_simulator.simulation import Body
    from solar_simulator.storage import save
    from solar_simulator.vector3 import Vector3
    initial = create_experiment([Body('stationary',1e20,Vector3(1e11,-2e11,3e11),Vector3(0.,0.,0.))],
        Settings(3600.,backend='rust',integrator='dop853'))
    source, output, expected = tmp_path/'input.json', tmp_path/'gui', tmp_path/'expected.npz'
    save(initial,source)
    analytic = np.tile(np.array([[[1e11,-2e11,3e11,0.,0.,0.]]]),(440,1,1))
    np.savez_compressed(expected,stationary_legacy_rust=analytic)
    code = 'import sys; from scripts.verify_edited_solar_packets import gui_worker; gui_worker(*sys.argv[1:])'
    result = subprocess.run([sys.executable,'-X','utf8','-B','-c',code,str(source),str(output),str(expected),'stationary'],
        capture_output=True,text=True,timeout=120)
    assert result.returncode==0, result.stdout+result.stderr
    receipt = json.loads((output/'receipt.json').read_bytes())
    assert receipt['checks_passed'] and receipt['packets']==439 and receipt['samples']==440
    with np.load(output/'states.npz',allow_pickle=False) as data:
        np.testing.assert_array_equal(data['states'],analytic)
        np.testing.assert_array_equal(data['times'],epoch_grid())
