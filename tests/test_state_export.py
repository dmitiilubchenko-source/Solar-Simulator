import csv
import hashlib
import json
import struct

import pytest

from solar_simulator.experiment import Settings,create_experiment
from solar_simulator.simulation import Body
from solar_simulator.storage import save,to_document
from solar_simulator.state_export import export_state
from solar_simulator.vector3 import Vector3


def test_export_preserves_float_bits_quoted_names_and_input(tmp_path):
    body=Body('Земля, "demo"',1.234567890123456e20,Vector3(.1,-2.5,1e11),Vector3(3.,4.,5.))
    state=create_experiment([body],Settings(3.));before=to_document(state);path=tmp_path/'state.csv'
    digest=export_state(state,path)
    with path.open(encoding='utf-8',newline='') as stream:row=next(csv.DictReader(stream))
    for field,value in [('mass_kg',body.mass),('x_m',body.position.x),('z_m',body.position.z),('vx_m_s',body.velocity.x)]:
        assert struct.pack('d',float(row[field]))==struct.pack('d',value)
    assert row['name']==body.name and row['epoch_jd_tdb']==''
    assert row['checkpoint_sha256']==digest and to_document(state)==before
    canonical=json.dumps(before,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    assert digest==hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def test_csv_jpl_metadata_and_actual_cli(tmp_path):
    from test_sandbox_commands import command
    from solar_simulator.application_profiles import solar_sandbox
    state=solar_sandbox();initial=tmp_path/'input.json';path=tmp_path/'solar.csv';save(state,initial)
    result=command('export-state',initial,path)
    assert result.returncode==0,result.stderr
    with path.open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==10 and rows[0]['frame']==state.origin.frame
    assert rows[0]['time_scale']=='TDB' and rows[0]['center']==state.origin.center
    assert float(rows[0]['epoch_jd_tdb'])==state.origin.epoch_jd_tdb
    assert json.loads(rows[0]['settings_json'])['physics']=='eih-1pn'


def test_failed_atomic_export_preserves_old_file_and_removes_temporary(tmp_path,monkeypatch):
    import solar_simulator.state_export as exporter
    state=create_experiment([Body('a',1e20,Vector3(0.,0.,0.),Vector3(2.,0.,0.))],Settings(3.))
    path=tmp_path/'keep.csv';path.write_bytes(b'keep')
    def fail(*args):raise OSError('disk failure')
    monkeypatch.setattr(exporter.os,'replace',fail)
    with pytest.raises(OSError):export_state(state,path)
    assert path.read_bytes()==b'keep' and not list(tmp_path.glob('.solar-csv-*'))


@pytest.mark.parametrize('operation',['export-state','run-until','branch'])
def test_new_cli_operations_reject_overwriting_their_input(tmp_path,operation):
    from test_sandbox_commands import command
    state=create_experiment([Body('a',1e20,Vector3(0.,0.,0.),Vector3(2.,0.,0.))],Settings(3.))
    path=tmp_path/'input.json';save(state,path);original=path.read_bytes()
    extra=['--time','6'] if operation=='run-until' else ['--part','parent'] if operation=='branch' else []
    result=command(operation,path,path,*extra)
    assert result.returncode==2 and path.read_bytes()==original
