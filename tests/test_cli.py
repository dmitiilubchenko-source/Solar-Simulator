import json

import pytest

from solar_simulator.cli import main
from solar_simulator.storage import load


def test_cli_create_run_inspect(tmp_path,capsys):
    initial=str(tmp_path/"initial.json")
    final=str(tmp_path/"final.json")
    assert main(["new","sun-earth",initial])==0
    capsys.readouterr()
    assert main(["run",initial,final,"--steps","50"])==0
    report=json.loads(capsys.readouterr().out)
    assert report["time_seconds"]==load(final).time>0
    assert main(["inspect",final])==0
    assert json.loads(capsys.readouterr().out)==report


def test_invalid_cli_does_not_create_output(tmp_path):
    output=tmp_path/"bad.json"
    with pytest.raises(SystemExit) as error:
        main(["new","spheres",str(output),"--dt","-1"])
    assert error.value.code==2 and not output.exists()


def test_cli_accuracy_defaults_and_explicit_verlet(tmp_path,capsys):
    output=str(tmp_path/"accurate.json")
    assert main(["new","sun-earth",output])==0
    assert load(output).settings.integrator=="dop853"
    assert main(["new","sun-earth",output,"--integrator","verlet"])==0
    assert load(output).settings.integrator=="verlet"
    assert main(["new","spheres",output])==0
    assert load(output).settings.integrator=="verlet"
    assert main(["new","sun-earth",output,"--backend","rust"])==0
    assert load(output).settings.integrator=="verlet"
