import json

import pytest

from solar_simulator.experiment import Settings,advance,create_experiment
from solar_simulator.sandbox import branch_experiment,save_branch
from solar_simulator.simulation import Body
from solar_simulator.storage import load,save,to_document
from solar_simulator.vector3 import Vector3


def test_extract_each_side_preserves_complete_checkpoint_and_bundle(tmp_path):
    from test_sandbox_commands import command
    parent=advance(create_experiment([Body("a",1e20,Vector3(0.,0.,0.),Vector3(2.,0.,0.))],Settings(3.)),2)
    branch=branch_experiment(parent,additions=(Body("b",1e20,Vector3(1e10,0.,0.),Vector3(0.,0.,0.)),))
    path=tmp_path/"branch.json";save_branch(branch,path);original=path.read_bytes()
    for part,state in (("parent",branch.parent),("child",branch.child)):
        output=tmp_path/(part+".json")
        result=command("branch",path,output,"--part",part)
        assert result.returncode==0,result.stderr
        assert to_document(load(output))==to_document(state)
    assert path.read_bytes()==original
    output=tmp_path/"progress.json";result=command("run-until",path,output,"--time","6","--batch","2")
    assert result.returncode==0,result.stderr
    from solar_simulator.branch_io import open_experiment
    continued,snapshot=open_experiment(output)
    assert to_document(continued)==to_document(advance(branch.child,2))
    assert snapshot==branch.parent_snapshot


@pytest.mark.parametrize("kind",["ordinary","tampered"])
def test_invalid_branch_extraction_preserves_output(tmp_path,kind):
    from test_sandbox_commands import command
    state=create_experiment([Body("a",1e20,Vector3(0.,0.,0.),Vector3(2.,0.,0.))],Settings(3.))
    path=tmp_path/"input.json";output=tmp_path/"keep.json";output.write_bytes(b"keep")
    if kind=="ordinary":save(state,path)
    else:
        branch=branch_experiment(state,additions=(Body("b",1e20,Vector3(1e10,0.,0.),Vector3(0.,0.,0.)),))
        save_branch(branch,path);doc=json.loads(path.read_text());doc["parent"]["time"]=99;path.write_text(json.dumps(doc))
    result=command("branch",path,output,"--part","parent")
    assert result.returncode==2 and output.read_bytes()==b"keep"
