import csv
import hashlib
import json

import pytest

from solar_simulator.continuous_cli import main,run
from solar_simulator.storage import load,save,to_document
from test_continuous import free


def test_complete_run_records_every_frame_provenance_and_original_checkpoint(tmp_path):
    source=tmp_path/"source.json";save(free(),source)
    before=source.read_bytes()
    output=tmp_path/"run"
    result=run(source,10.25,output,packet_steps=2)
    assert source.read_bytes()==before
    assert result["status"]=="complete" and result["sample_times_seconds"]==[0.,6.,10.25]
    assert result["csv_rows"]==3 and result["packets"]==2
    assert result["input_sha256"]==hashlib.sha256(before).hexdigest()
    assert result["experimental"] and not result["automatically_scientifically_qualified"]
    assert not result["controller_buffers_saved"]
    final=load(output/"final.json")
    assert final.time==10.25
    rows=list(csv.DictReader((output/"snapshots.csv").open(encoding="utf-8")))
    assert [float(row["time_seconds"]) for row in rows]==[0.,6.,10.25]
    assert [float(rows[-1][field]) for field in ("x_m","y_m","z_m")]==[25.5,-24.75,48.]
    assert all(hashlib.sha256((output/name).read_bytes()).hexdigest()==sha
               for name,sha in result["output_sha256"].items())
    assert to_document(load(output/"initial.json"))==to_document(free())


def test_existing_result_is_preserved_before_loading_missing_input(tmp_path):
    output=tmp_path/"run";output.mkdir();marker=output/"keep.txt";marker.write_bytes(b"keep")
    with pytest.raises(FileExistsError):run(tmp_path/"missing.json",10.,output)
    assert marker.read_bytes()==b"keep" and list(output.iterdir())==[marker]


@pytest.mark.parametrize("target,steps",[(float("nan"),2),(float("inf"),2),(-1.,2),(10.,0),(10.,2001)])
def test_invalid_input_leaves_no_result_directory(tmp_path,target,steps):
    source=tmp_path/"seed.json";save(free(),source)
    output=tmp_path/"run"
    with pytest.raises(ValueError):run(source,target,output,packet_steps=steps)
    assert not output.exists()


@pytest.mark.parametrize("failure",[ValueError("force failed"),KeyboardInterrupt()])
def test_partial_run_is_marked_and_saves_only_last_committed_snapshot(tmp_path,monkeypatch,failure):
    from solar_simulator.continuous import ContinuousRun
    source=tmp_path/"seed.json";save(free(),source)
    original=ContinuousRun.next
    def interrupted(self,*args,**kw):
        if self.current.time>0:raise failure
        return original(self,*args,**kw)
    monkeypatch.setattr(ContinuousRun,"next",interrupted)
    output=tmp_path/"run"
    with pytest.raises(type(failure)):run(source,20.,output,packet_steps=2)
    assert not (output/"receipt.json").exists() and not (output/"final.json").exists()
    info=json.loads((output/"failure.json").read_bytes())
    assert info["last_committed_time_seconds"]==6.
    assert load(output/"interrupted.json").time==6.
    assert info["status"]==( "interrupted" if isinstance(failure,KeyboardInterrupt) else "failed")


def test_default_cli_output_stays_in_local_appdata(tmp_path,monkeypatch,capsys):
    source=tmp_path/"seed.json";save(free(),source)
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path/"local"))
    assert main(["--input",str(source),"--target","0"])==0
    result=json.loads(capsys.readouterr().out.splitlines()[-1])
    from pathlib import Path
    output=Path(result["output_directory"])
    assert output.is_relative_to(tmp_path/"local/SolarSimulator/experiments")
    assert result["experimental"] and result["final_time_seconds"]==0.
