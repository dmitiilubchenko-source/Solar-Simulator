"""Source/native-bound offline evidence; separate from portable contract tests."""
import json
import pytest


def test_scientific_metrics_are_recomputed_from_raw_arrays_before_accepting_flags(tmp_path):
    from scripts.assess_runtime_reliability376 import REPORT,ARRAYS,verify
    result=verify(historical=True)
    assert result['state_observations']==1576 and result['source_mode']=='historical_replay_only'
    assert result['current_runtime_qualified'] is False
    proof=json.loads(REPORT.read_text(encoding='utf8'))
    proof['runs'][0]['maxima']['r']+=1.0
    altered=tmp_path/'altered-report.json';altered.write_text(json.dumps(proof),encoding='utf8')
    # All saved successful flags/SHA and raw arrays are unchanged; only a
    # measurement is false. The independent scalar reader must reject it.
    with pytest.raises(ValueError,match='Independent raw metric disagreement'):
        verify(altered,ARRAYS,historical=True)


def test_scientific_array_corruption_is_rejected_before_measurement(tmp_path):
    from scripts.assess_runtime_reliability376 import REPORT,ARRAYS,verify
    changed=tmp_path/'changed.npz';changed.write_bytes(ARRAYS.read_bytes()+b'corruption')
    with pytest.raises(ValueError,match='Protocol/array SHA mismatch'):verify(REPORT,changed,historical=True)


def test_historical_snapshot_cannot_authorize_changed_current_sources():
    from scripts.assess_runtime_reliability376 import verify
    with pytest.raises(ValueError,match='Frozen source changed'):verify()
