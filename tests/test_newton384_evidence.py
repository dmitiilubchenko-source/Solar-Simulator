"""A sealed read-only audit must retain labels and refuse altered assets."""
import shutil
import pytest
from scripts.assess_newton384 import audit,EVIDENCE


def test_all_fresh_cases_are_independently_reduced_without_requalification():
    result=audit()
    assert (result['jobs'],result['state_observations'],result['moderate_passes'])==(36,1576,8)
    assert result['recorded_exact_restart_cases']==8
    assert not result['current_runtime_qualified'] and not result['actual_current_environment_checked']


@pytest.mark.parametrize('asset',['manifest.json','summary.npz','protocol.json','environment.json'])
def test_corrupted_evidence_refused_without_writes(tmp_path,asset):
    folder=tmp_path/'evidence';shutil.copytree(EVIDENCE,folder)
    path=folder/asset;path.write_bytes(path.read_bytes()+b'corruption')
    before={p.name:p.read_bytes() for p in folder.iterdir()}
    with pytest.raises(ValueError,match='changed'):audit(folder)
    assert {p.name:p.read_bytes() for p in folder.iterdir()}==before
